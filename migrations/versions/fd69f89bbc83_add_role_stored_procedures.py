"""add role stored procedures

Revision ID: fd69f89bbc83
Revises: 2159522270d9
Create Date: 2026-11-17 02:00:59.893126

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fd69f89bbc83'
down_revision: Union[str, Sequence[str], None] = '2159522270d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE PROCEDURE sp_create_role(
            IN p_name VARCHAR(50),
            IN p_is_active BOOLEAN,
            OUT out_id INTEGER,
            OUT out_name VARCHAR(50),
            OUT out_is_active BOOLEAN,
            OUT out_created_at TIMESTAMPTZ,
            OUT out_updated_at TIMESTAMPTZ,
            OUT out_deleted_at TIMESTAMPTZ
        )
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_clean_name VARCHAR(50);
        BEGIN
            -- Validate p_name
            IF p_name IS NULL OR length(trim(p_name)) < 2 THEN
                RAISE EXCEPTION 'Role name must be at least 2 characters long'
                    USING ERRCODE = '22023'; -- invalid_parameter_value
            END IF;

            v_clean_name := trim(p_name);

            IF length(v_clean_name) > 50 THEN
                RAISE EXCEPTION 'Role name cannot exceed 50 characters'
                    USING ERRCODE = '22001'; -- string_data_right_truncation
            END IF;

            -- Validate p_is_active
            IF p_is_active IS NULL THEN
                RAISE EXCEPTION 'is_active cannot be NULL'
                    USING ERRCODE = '22004'; -- null_value_not_allowed
            END IF;

            -- Prevent duplicate active role names (case-insensitive)
            IF EXISTS (
                SELECT 1 FROM roles
                WHERE lower(name) = lower(v_clean_name)
                    AND deleted_at IS NULL
            ) THEN
                RAISE EXCEPTION 'Role with name "%" already exists', v_clean_name
                    USING ERRCODE = '23505'; -- unique_violation
            END IF;

            INSERT INTO roles (name, is_active, created_at, updated_at)
            VALUES (
                v_clean_name,
                p_is_active,
                timezone('utc', now()),
                timezone('utc', now())
            )
            RETURNING id, name, is_active, created_at, updated_at, deleted_at
            INTO out_id, out_name, out_is_active, out_created_at, out_updated_at, out_deleted_at;
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE PROCEDURE sp_update_role(
            IN p_id INTEGER,
            IN p_name VARCHAR(50),
            IN p_is_active BOOLEAN,
            OUT out_id INTEGER,
            OUT out_name VARCHAR(50),
            OUT out_is_active BOOLEAN,
            OUT out_created_at TIMESTAMPTZ,
            OUT out_updated_at TIMESTAMPTZ,
            OUT out_deleted_at TIMESTAMPTZ
        )
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_clean_name VARCHAR(50);
        BEGIN
            -- Validate p_id
            IF p_id IS NULL OR p_id <= 0 THEN
                RAISE EXCEPTION 'Role ID must be a positive integer'
                    USING ERRCODE = '22023';
            END IF;

            -- Ensure at least one field is provided
            IF p_name IS NULL AND p_is_active IS NULL THEN
                RAISE EXCEPTION 'At least one field (name or is_active) must be provided for update'
                    USING ERRCODE = '22023';
            END IF;

            -- Ensure role exists and is not soft-deleted
            IF NOT EXISTS (
                SELECT 1 FROM roles WHERE id = p_id AND deleted_at IS NULL
            ) THEN
                RAISE EXCEPTION 'Role with ID % not found', p_id
                    USING ERRCODE = 'P0002'; -- no_data_found
            END IF;

            -- Validate p_name if provided
            IF p_name IS NOT NULL THEN
                v_clean_name := trim(p_name);

                IF length(v_clean_name) < 2 OR length(v_clean_name) > 50 THEN
                    RAISE EXCEPTION 'Role name must be between 2 and 50 characters'
                        USING ERRCODE = '22023';
                END IF;

                -- Prevent duplicate name on another active role
                IF EXISTS (
                    SELECT 1 FROM roles
                    WHERE lower(name) = lower(v_clean_name)
                        AND id <> p_id
                        AND deleted_at IS NULL
                ) THEN
                    RAISE EXCEPTION 'Another role with name "%" already exists', v_clean_name
                        USING ERRCODE = '23505';
                END IF;
            END IF;

            -- Prevent deactivating the core Admin role
            IF p_is_active IS FALSE AND EXISTS (
                SELECT 1 FROM roles WHERE id = p_id AND lower(name) = 'admin'
            ) THEN
                RAISE EXCEPTION 'The Admin role cannot be deactivated'
                    USING ERRCODE = '22023';
            END IF;

            UPDATE roles
            SET
                name = COALESCE(v_clean_name, name),
                is_active = COALESCE(p_is_active, is_active),
                updated_at = timezone('utc', now())
            WHERE id = p_id
                AND deleted_at IS NULL
            RETURNING id, name, is_active, created_at, updated_at, deleted_at
            INTO out_id, out_name, out_is_active, out_created_at, out_updated_at, out_deleted_at;
        END;
        $$;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION sp_get_roles(
            p_id INTEGER DEFAULT NULL,
            p_is_active BOOLEAN DEFAULT NULL,
            p_limit INTEGER DEFAULT 50,
            p_offset INTEGER DEFAULT 0
        )
        RETURNS TABLE (
            id INTEGER,
            name VARCHAR(50),
            is_active BOOLEAN,
            created_at TIMESTAMPTZ,
            updated_at TIMESTAMPTZ,
            deleted_at TIMESTAMPTZ
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN
            -- Validate p_id if provided
            IF p_id IS NOT NULL AND p_id <= 0 THEN
                RAISE EXCEPTION 'Role ID must be a positive integer'
                    USING ERRCODE = '22023';
            END IF;

            -- Validate pagination bounds
            IF p_limit IS NULL OR p_limit < 1 OR p_limit > 100 THEN
                RAISE EXCEPTION 'Limit must be between 1 and 100'
                    USING ERRCODE = '22023';
            END IF;

            IF p_offset IS NULL OR p_offset < 0 THEN
                RAISE EXCEPTION 'Offset cannot be negative'
                    USING ERRCODE = '22023';
            END IF;

            RETURN QUERY
            SELECT r.id, r.name, r.is_active, r.created_at, r.updated_at, r.deleted_at
            FROM roles r
            WHERE r.deleted_at IS NULL
                AND (p_id IS NULL OR r.id = p_id)
                AND (p_is_active IS NULL OR r.is_active = p_is_active)
            ORDER BY r.id DESC
            LIMIT p_limit OFFSET p_offset;
        END;
        $$;
        """
    )

def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS sp_get_roles(INTEGER, BOOLEAN, INTEGER, INTEGER);")
    op.execute(
        "DROP PROCEDURE IF EXISTS sp_update_role(INTEGER, VARCHAR, BOOLEAN, INTEGER, VARCHAR, BOOLEAN, TIMESTAMPTZ, TIMESTAMPTZ, TIMESTAMPTZ);"
    )
    op.execute(
        "DROP PROCEDURE IF EXISTS sp_create_role(VARCHAR, BOOLEAN, INTEGER, VARCHAR, BOOLEAN, TIMESTAMPTZ, TIMESTAMPTZ, TIMESTAMPTZ);"
    )
