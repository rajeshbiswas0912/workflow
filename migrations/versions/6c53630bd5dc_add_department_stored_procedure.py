"""add department stored procedure

Revision ID: 6c53630bd5dc
Revises: 088455b114d8
Create Date: 2026-11-18 18:28:46.743297

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c53630bd5dc'
down_revision: Union[str, Sequence[str], None] = '088455b114d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FN_DEPARTMENT_VALIDATE = r"""
CREATE OR REPLACE FUNCTION fn_department_validate(
    p_department_id BIGINT,      -- NULL on create
    p_name          TEXT,
    p_description   TEXT,
    p_head_id       BIGINT
) RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_name IS NULL OR btrim(p_name) = '' THEN
        RAISE EXCEPTION 'name is required' USING ERRCODE = 'EV001';
    END IF;
    IF char_length(btrim(p_name)) > 100 THEN
        RAISE EXCEPTION 'name must be at most 100 characters' USING ERRCODE = 'EV001';
    END IF;

    IF p_description IS NOT NULL AND char_length(p_description) > 2000 THEN
        RAISE EXCEPTION 'description must be at most 2000 characters' USING ERRCODE = 'EV001';
    END IF;

    -- name must be unique among active departments (case-insensitive)
    IF EXISTS (
        SELECT 1 FROM departments d
        WHERE d.deleted_at IS NULL
          AND lower(btrim(d.name)) = lower(btrim(p_name))
          AND (p_department_id IS NULL OR d.id <> p_department_id)
    ) THEN
        RAISE EXCEPTION 'department name % is already in use', btrim(p_name) USING ERRCODE = 'EV003';
    END IF;

    -- department head
    IF p_head_id IS NOT NULL THEN
        IF NOT EXISTS (SELECT 1 FROM employees WHERE id = p_head_id AND deleted_at IS NULL) THEN
            RAISE EXCEPTION 'employee % does not exist', p_head_id USING ERRCODE = 'EV001';
        END IF;
        -- on update, the head must belong to this department
        IF p_department_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM employees
            WHERE id = p_head_id AND department_id = p_department_id AND deleted_at IS NULL
        ) THEN
            RAISE EXCEPTION 'employee % does not belong to department %', p_head_id, p_department_id
                USING ERRCODE = 'EV001';
        END IF;
    END IF;
END;
$$;
"""

SP_DEPARTMENT_CREATE = r"""
CREATE OR REPLACE PROCEDURE sp_department_create(
    INOUT p_id          BIGINT,
    IN    p_name        TEXT,
    IN    p_description TEXT,
    IN    p_head_id     BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM fn_department_validate(NULL, p_name, p_description, p_head_id);

    INSERT INTO departments (name, description, department_head_id)
    VALUES (btrim(p_name), NULLIF(btrim(p_description), ''), p_head_id)
    RETURNING id INTO p_id;
END;
$$;
"""

SP_DEPARTMENT_UPDATE = r"""
CREATE OR REPLACE PROCEDURE sp_department_update(
    IN p_id          BIGINT,
    IN p_name        TEXT,
    IN p_description TEXT,
    IN p_head_id     BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM 1 FROM departments WHERE id = p_id AND deleted_at IS NULL FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'department % not found', p_id USING ERRCODE = 'EV002';
    END IF;

    PERFORM fn_department_validate(p_id, p_name, p_description, p_head_id);

    UPDATE departments SET
        name               = btrim(p_name),
        description        = NULLIF(btrim(p_description), ''),
        department_head_id = p_head_id,
        updated_at         = now()
    WHERE id = p_id;
END;
$$;
"""

SP_DEPARTMENT_SET_HEAD = r"""
CREATE OR REPLACE PROCEDURE sp_department_set_head(p_id BIGINT, p_head_id BIGINT)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM 1 FROM departments WHERE id = p_id AND deleted_at IS NULL FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'department % not found', p_id USING ERRCODE = 'EV002';
    END IF;

    IF p_head_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM employees
        WHERE id = p_head_id AND department_id = p_id AND deleted_at IS NULL
    ) THEN
        RAISE EXCEPTION 'employee % does not exist in department %', p_head_id, p_id
            USING ERRCODE = 'EV001';
    END IF;

    UPDATE departments SET department_head_id = p_head_id, updated_at = now() WHERE id = p_id;
END;
$$;
"""

SP_DEPARTMENT_DELETE = r"""
CREATE OR REPLACE PROCEDURE sp_department_delete(p_id BIGINT)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM 1 FROM departments WHERE id = p_id AND deleted_at IS NULL FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'department % not found', p_id USING ERRCODE = 'EV002';
    END IF;

    IF EXISTS (SELECT 1 FROM employees WHERE department_id = p_id AND deleted_at IS NULL) THEN
        RAISE EXCEPTION 'department % still has active employees; move them first', p_id
            USING ERRCODE = 'EV003';
    END IF;

    UPDATE departments SET deleted_at = now(), updated_at = now() WHERE id = p_id;
END;
$$;
"""

SP_DEPARTMENT_RESTORE = r"""
CREATE OR REPLACE PROCEDURE sp_department_restore(p_id BIGINT)
LANGUAGE plpgsql
AS $$
DECLARE
    v_name TEXT;
BEGIN
    SELECT name INTO v_name FROM departments WHERE id = p_id AND deleted_at IS NOT NULL FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'deleted department % not found', p_id USING ERRCODE = 'EV002';
    END IF;

    IF EXISTS (
        SELECT 1 FROM departments
        WHERE deleted_at IS NULL AND lower(btrim(name)) = lower(btrim(v_name))
    ) THEN
        RAISE EXCEPTION 'department name % is already in use', v_name USING ERRCODE = 'EV003';
    END IF;

    UPDATE departments SET deleted_at = NULL, updated_at = now() WHERE id = p_id;
END;
$$;
"""

FN_DEPARTMENT_GET = r"""
CREATE OR REPLACE FUNCTION fn_department_get(p_id BIGINT, p_include_deleted BOOLEAN DEFAULT FALSE)
RETURNS TABLE (
    id BIGINT, name VARCHAR, description TEXT, department_head_id BIGINT,
    employee_count BIGINT, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
)
LANGUAGE sql STABLE
AS $$
    SELECT d.id::BIGINT, d.name, d.description, d.department_head_id,
           (SELECT COUNT(*) FROM employees e
             WHERE e.department_id = d.id AND e.deleted_at IS NULL)::BIGINT,
           d.created_at, d.updated_at, d.deleted_at
    FROM departments d
    WHERE d.id = p_id AND (p_include_deleted OR d.deleted_at IS NULL);
$$;
"""

FN_DEPARTMENT_LIST = r"""
CREATE OR REPLACE FUNCTION fn_department_list(
    p_search          TEXT    DEFAULT NULL,
    p_include_deleted BOOLEAN DEFAULT FALSE,
    p_limit           INT     DEFAULT 50,
    p_offset          INT     DEFAULT 0
)
RETURNS TABLE (
    id BIGINT, name VARCHAR, description TEXT, department_head_id BIGINT,
    employee_count BIGINT, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ, total_count BIGINT
)
LANGUAGE plpgsql STABLE
AS $$
BEGIN
    IF p_limit IS NULL OR p_limit < 1 OR p_limit > 200 THEN
        RAISE EXCEPTION 'limit must be between 1 and 200' USING ERRCODE = 'EV001';
    END IF;
    IF p_offset IS NULL OR p_offset < 0 THEN
        RAISE EXCEPTION 'offset must be >= 0' USING ERRCODE = 'EV001';
    END IF;

    RETURN QUERY
    SELECT d.id::BIGINT, d.name, d.description, d.department_head_id,
           (SELECT COUNT(*) FROM employees e
             WHERE e.department_id = d.id AND e.deleted_at IS NULL)::BIGINT,
           d.created_at, d.updated_at, d.deleted_at,
           COUNT(*) OVER () AS total_count
    FROM departments d
    WHERE (p_include_deleted OR d.deleted_at IS NULL)
      AND (p_search IS NULL OR p_search = ''
           OR d.name ILIKE '%' || p_search || '%'
           OR d.description ILIKE '%' || p_search || '%')
    ORDER BY d.id
    LIMIT p_limit OFFSET p_offset;
END;
$$;
"""

# Order matters: the validate helper first, then routines that call it.
UPGRADE_STATEMENTS = [
    FN_DEPARTMENT_VALIDATE,
    SP_DEPARTMENT_CREATE,
    SP_DEPARTMENT_UPDATE,
    SP_DEPARTMENT_SET_HEAD,
    SP_DEPARTMENT_DELETE,
    SP_DEPARTMENT_RESTORE,
    FN_DEPARTMENT_GET,
    FN_DEPARTMENT_LIST,
]

DOWNGRADE_STATEMENTS = [
    "DROP FUNCTION IF EXISTS fn_department_list(TEXT, BOOLEAN, INT, INT)",
    "DROP FUNCTION IF EXISTS fn_department_get(BIGINT, BOOLEAN)",
    "DROP PROCEDURE IF EXISTS sp_department_restore(BIGINT)",
    "DROP PROCEDURE IF EXISTS sp_department_delete(BIGINT)",
    "DROP PROCEDURE IF EXISTS sp_department_set_head(BIGINT, BIGINT)",
    "DROP PROCEDURE IF EXISTS sp_department_update(BIGINT, TEXT, TEXT, BIGINT)",
    "DROP PROCEDURE IF EXISTS sp_department_create(BIGINT, TEXT, TEXT, BIGINT)",
    "DROP FUNCTION IF EXISTS fn_department_validate(BIGINT, TEXT, TEXT, BIGINT)",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(sa.text(statement))


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(sa.text(statement))
