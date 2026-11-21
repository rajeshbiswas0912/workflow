"""role permissions stored procedure

Revision ID: e1294e646441
Revises: da442a7e8531
Create Date: 2026-11-20 02:13:08.548394

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1294e646441'
down_revision: Union[str, Sequence[str], None] = 'da442a7e8531'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_parse_permission_area(p_area TEXT)
        RETURNS permission_area_enum
        LANGUAGE plpgsql
        STABLE
        AS $$
        DECLARE
            v_clean TEXT;
        BEGIN
            IF p_area IS NULL OR length(trim(p_area)) = 0 THEN
                RAISE EXCEPTION 'Area is required'
                    USING ERRCODE = '22004'; -- null_value_not_allowed
            END IF;

            v_clean := lower(trim(p_area));

            IF v_clean <> ALL (enum_range(NULL::permission_area_enum)::text[]) THEN
                RAISE EXCEPTION 'Invalid area "%". Allowed values: %',
                    v_clean, array_to_string(enum_range(NULL::permission_area_enum), ', ')
                    USING ERRCODE = '22023'; -- invalid_parameter_value
            END IF;

            RETURN v_clean::permission_area_enum;
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_parse_permission_level(p_level TEXT)
        RETURNS permission_level_enum
        LANGUAGE plpgsql
        STABLE
        AS $$
        DECLARE
            v_clean TEXT;
        BEGIN
            IF p_level IS NULL OR length(trim(p_level)) = 0 THEN
                RAISE EXCEPTION 'Access level is required'
                    USING ERRCODE = '22004';
            END IF;

            v_clean := lower(trim(p_level));

            IF v_clean <> ALL (enum_range(NULL::permission_level_enum)::text[]) THEN
                RAISE EXCEPTION 'Invalid access level "%". Allowed values: %',
                    v_clean, array_to_string(enum_range(NULL::permission_level_enum), ', ')
                    USING ERRCODE = '22023';
            END IF;

            RETURN v_clean::permission_level_enum;
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_assert_role_permissions_editable(p_role_id INTEGER)
        RETURNS VOID
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_name VARCHAR(50);
        BEGIN
            IF p_role_id IS NULL OR p_role_id <= 0 THEN
                RAISE EXCEPTION 'Role ID must be a positive integer'
                    USING ERRCODE = '22023';
            END IF;

            SELECT r.name INTO v_name
            FROM roles r
            WHERE r.id = p_role_id AND r.deleted_at IS NULL;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'Role with ID % not found', p_role_id
                    USING ERRCODE = 'P0002'; -- no_data_found
            END IF;

            IF lower(v_name) = 'admin' THEN
                RAISE EXCEPTION 'The Admin role permissions cannot be changed'
                    USING ERRCODE = '22023';
            END IF;
        END;
        $$;
        """
    )

    # ---------- Set ONE permission (create or update) ----------
    op.execute(
        """
        CREATE OR REPLACE PROCEDURE sp_set_role_permission(
            IN p_role_id INTEGER,
            IN p_area VARCHAR(30),
            IN p_access_level VARCHAR(10),
            OUT out_role_id INTEGER,
            OUT out_area permission_area_enum,
            OUT out_access_level permission_level_enum,
            OUT out_updated_at TIMESTAMPTZ
        )
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_area permission_area_enum;
            v_level permission_level_enum;
        BEGIN
            PERFORM fn_assert_role_permissions_editable(p_role_id);

            v_area := fn_parse_permission_area(p_area);
            v_level := fn_parse_permission_level(p_access_level);

            INSERT INTO role_permissions (role_id, area, access_level, updated_at)
            VALUES (p_role_id, v_area, v_level, timezone('utc', now()))
            ON CONFLICT (role_id, area)
            DO UPDATE SET
                access_level = EXCLUDED.access_level,
                updated_at = EXCLUDED.updated_at
            RETURNING role_id, area, access_level, updated_at
            INTO out_role_id, out_area, out_access_level, out_updated_at;
        END;
        $$;
        """
    )

    # ---------- Set the WHOLE grid (what the Save button calls) ----------
    op.execute(
        """
        CREATE OR REPLACE PROCEDURE sp_set_role_permissions(
            IN p_role_id INTEGER,
            IN p_permissions JSONB,
            OUT out_role_id INTEGER,
            OUT out_changed_count INTEGER
        )
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_key TEXT;
            v_value JSONB;
            v_area permission_area_enum;
            v_clean JSONB := '{}'::jsonb;
        BEGIN
            PERFORM fn_assert_role_permissions_editable(p_role_id);

            IF p_permissions IS NULL THEN
                RAISE EXCEPTION 'Permissions cannot be NULL'
                    USING ERRCODE = '22004';
            END IF;

            IF jsonb_typeof(p_permissions) <> 'object' THEN
                RAISE EXCEPTION 'Permissions must be a JSON object'
                    USING ERRCODE = '22023';
            END IF;

            -- Validate and normalize every entry BEFORE writing anything
            FOR v_key, v_value IN
                SELECT j.key, j.value FROM jsonb_each(p_permissions) AS j
            LOOP
                v_area := fn_parse_permission_area(v_key);

                IF v_clean ->> v_area::text IS NOT NULL THEN
                    RAISE EXCEPTION 'Area "%" is specified more than once', v_area
                        USING ERRCODE = '22023';
                END IF;

                IF jsonb_typeof(v_value) <> 'string' THEN
                    RAISE EXCEPTION 'Access level for area "%" must be a string', v_key
                        USING ERRCODE = '22023';
                END IF;

                v_clean := v_clean || jsonb_build_object(
                    v_area::text,
                    fn_parse_permission_level(v_value #>> '{}')::text
                );
            END LOOP;

            -- Replace the whole grid: areas not provided become 'none'
            INSERT INTO role_permissions (role_id, area, access_level, updated_at)
            SELECT p_role_id,
                   e.area,
                   COALESCE((v_clean ->> e.area::text)::permission_level_enum, 'none'),
                   timezone('utc', now())
            FROM unnest(enum_range(NULL::permission_area_enum)) AS e(area)
            ON CONFLICT (role_id, area)
            DO UPDATE SET
                access_level = EXCLUDED.access_level,
                updated_at = EXCLUDED.updated_at
            WHERE role_permissions.access_level IS DISTINCT FROM EXCLUDED.access_level;

            GET DIAGNOSTICS out_changed_count = ROW_COUNT;
            out_role_id := p_role_id;
        END;
        $$;
        """
    )

    # ---------- Reset (everything back to 'none') ----------
    op.execute(
        """
        CREATE OR REPLACE PROCEDURE sp_reset_role_permissions(
            IN p_role_id INTEGER,
            OUT out_role_id INTEGER,
            OUT out_removed_count INTEGER
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            PERFORM fn_assert_role_permissions_editable(p_role_id);

            -- A missing row means 'none', so deleting the rows resets the role
            DELETE FROM role_permissions WHERE role_id = p_role_id;

            GET DIAGNOSTICS out_removed_count = ROW_COUNT;
            out_role_id := p_role_id;
        END;
        $$;
        """
    )

    # ---------- Get a role's grid (always all 7 areas) ----------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION sp_get_role_permissions(
            p_role_id INTEGER,
            p_area VARCHAR DEFAULT NULL
        )
        RETURNS TABLE (
            role_id INTEGER,
            area permission_area_enum,
            access_level permission_level_enum,
            updated_at TIMESTAMPTZ
        )
        LANGUAGE plpgsql
        STABLE
        AS $$
        DECLARE
            v_area permission_area_enum;
        BEGIN
            IF p_role_id IS NULL OR p_role_id <= 0 THEN
                RAISE EXCEPTION 'Role ID must be a positive integer'
                    USING ERRCODE = '22023';
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM roles r WHERE r.id = p_role_id AND r.deleted_at IS NULL
            ) THEN
                RAISE EXCEPTION 'Role with ID % not found', p_role_id
                    USING ERRCODE = 'P0002';
            END IF;

            IF p_area IS NOT NULL THEN
                v_area := fn_parse_permission_area(p_area);
            END IF;

            RETURN QUERY
            SELECT p_role_id,
                   a.area,
                   COALESCE(rp.access_level, 'none'::permission_level_enum),
                   rp.updated_at
            FROM unnest(enum_range(NULL::permission_area_enum)) AS a(area)
            LEFT JOIN role_permissions rp
                   ON rp.area = a.area AND rp.role_id = p_role_id
            WHERE v_area IS NULL OR a.area = v_area
            ORDER BY a.area;
        END;
        $$;
        """
    )

    # ---------- Role cards: people count + "access to N of 7 areas" ----------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION sp_get_role_permission_summary(
            p_role_id INTEGER DEFAULT NULL,
            p_is_active BOOLEAN DEFAULT NULL
        )
        RETURNS TABLE (
            id INTEGER,
            name VARCHAR(50),
            is_active BOOLEAN,
            is_system BOOLEAN,
            people_count BIGINT,
            areas_with_access BIGINT,
            total_areas BIGINT
        )
        LANGUAGE plpgsql
        STABLE
        AS $$
        DECLARE
            v_total BIGINT := array_length(enum_range(NULL::permission_area_enum), 1);
        BEGIN
            IF p_role_id IS NOT NULL AND p_role_id <= 0 THEN
                RAISE EXCEPTION 'Role ID must be a positive integer'
                    USING ERRCODE = '22023';
            END IF;

            RETURN QUERY
            SELECT r.id,
                   r.name,
                   r.is_active,
                   lower(r.name) = 'admin',
                   (SELECT COUNT(*) FROM employees e
                     WHERE e.role_id = r.id AND e.deleted_at IS NULL),
                   CASE WHEN lower(r.name) = 'admin' THEN v_total
                        ELSE (SELECT COUNT(*) FROM role_permissions rp
                               WHERE rp.role_id = r.id AND rp.access_level <> 'none')
                   END,
                   v_total
            FROM roles r
            WHERE r.deleted_at IS NULL
                AND (p_role_id IS NULL OR r.id = p_role_id)
                AND (p_is_active IS NULL OR r.is_active = p_is_active)
            ORDER BY r.id;
        END;
        $$;
        """
    )

    # ---------- Permission check (for the API guard) ----------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION sp_has_role_permission(
            p_role_id INTEGER,
            p_area VARCHAR,
            p_min_level VARCHAR DEFAULT 'view'
        )
        RETURNS BOOLEAN
        LANGUAGE plpgsql
        STABLE
        AS $$
        DECLARE
            v_area permission_area_enum;
            v_min permission_level_enum;
            v_name VARCHAR(50);
            v_is_active BOOLEAN;
            v_actual permission_level_enum;
        BEGIN
            IF p_role_id IS NULL OR p_role_id <= 0 THEN
                RAISE EXCEPTION 'Role ID must be a positive integer'
                    USING ERRCODE = '22023';
            END IF;

            v_area := fn_parse_permission_area(p_area);
            v_min := fn_parse_permission_level(p_min_level);

            SELECT r.name, r.is_active INTO v_name, v_is_active
            FROM roles r
            WHERE r.id = p_role_id AND r.deleted_at IS NULL;

            -- Unknown, deleted or inactive roles have no access
            IF NOT FOUND OR NOT v_is_active THEN
                RETURN FALSE;
            END IF;

            -- Admin always has full access
            IF lower(v_name) = 'admin' THEN
                RETURN TRUE;
            END IF;

            SELECT rp.access_level INTO v_actual
            FROM role_permissions rp
            WHERE rp.role_id = p_role_id AND rp.area = v_area;

            -- Enums compare by declaration order: none < view < edit < full
            RETURN COALESCE(v_actual, 'none'::permission_level_enum) >= v_min;
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS sp_has_role_permission(INTEGER, VARCHAR, VARCHAR);")
    op.execute("DROP FUNCTION IF EXISTS sp_get_role_permission_summary(INTEGER, BOOLEAN);")
    op.execute("DROP FUNCTION IF EXISTS sp_get_role_permissions(INTEGER, VARCHAR);")
    op.execute("DROP PROCEDURE IF EXISTS sp_reset_role_permissions(INTEGER, INTEGER, INTEGER);")
    op.execute("DROP PROCEDURE IF EXISTS sp_set_role_permissions(INTEGER, JSONB, INTEGER, INTEGER);")
    op.execute(
        "DROP PROCEDURE IF EXISTS sp_set_role_permission(INTEGER, VARCHAR, VARCHAR, INTEGER, permission_area_enum, permission_level_enum, TIMESTAMPTZ);"
    )
    op.execute("DROP FUNCTION IF EXISTS fn_assert_role_permissions_editable(INTEGER);")
    op.execute("DROP FUNCTION IF EXISTS fn_parse_permission_level(TEXT);")
    op.execute("DROP FUNCTION IF EXISTS fn_parse_permission_area(TEXT);")
