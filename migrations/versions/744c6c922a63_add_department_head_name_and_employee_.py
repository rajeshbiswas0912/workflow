"""add department head name and employee totals stored procedure

Revision ID: 744c6c922a63
Revises: e1294e646441
Create Date: 2026-11-20 18:16:14.463285

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '744c6c922a63'
down_revision: Union[str, Sequence[str], None] = 'e1294e646441'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FN_DEPARTMENT_GET = r"""
CREATE FUNCTION fn_department_get(p_id BIGINT, p_include_deleted BOOLEAN DEFAULT FALSE)
RETURNS TABLE (
    id BIGINT, name VARCHAR, description TEXT, department_head_id BIGINT, head_name TEXT,
    employee_count BIGINT, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
)
LANGUAGE sql STABLE
AS $$
    SELECT d.id::BIGINT, d.name, d.description, d.department_head_id,
           (h.first_name || ' ' || h.last_name)::TEXT,
           (SELECT COUNT(*) FROM employees e
             WHERE e.department_id = d.id AND e.deleted_at IS NULL)::BIGINT,
           d.created_at, d.updated_at, d.deleted_at
    FROM departments d
    LEFT JOIN employees h ON h.id = d.department_head_id AND h.deleted_at IS NULL
    WHERE d.id = p_id AND (p_include_deleted OR d.deleted_at IS NULL);
$$;
"""

FN_DEPARTMENT_LIST = r"""
CREATE FUNCTION fn_department_list(
    p_search          TEXT    DEFAULT NULL,
    p_include_deleted BOOLEAN DEFAULT FALSE,
    p_limit           INT     DEFAULT 50,
    p_offset          INT     DEFAULT 0
)
RETURNS TABLE (
    id BIGINT, name VARCHAR, description TEXT, department_head_id BIGINT, head_name TEXT,
    employee_count BIGINT, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ, total_count BIGINT, total_employees BIGINT
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
    WITH base AS (
        SELECT d.id::BIGINT AS b_id, d.name AS b_name, d.description AS b_description,
               d.department_head_id AS b_head_id,
               (h.first_name || ' ' || h.last_name)::TEXT AS b_head_name,
               (SELECT COUNT(*) FROM employees e
                 WHERE e.department_id = d.id AND e.deleted_at IS NULL)::BIGINT AS b_count,
               d.created_at AS b_created_at, d.updated_at AS b_updated_at,
               d.deleted_at AS b_deleted_at
        FROM departments d
        LEFT JOIN employees h ON h.id = d.department_head_id AND h.deleted_at IS NULL
        WHERE (p_include_deleted OR d.deleted_at IS NULL)
          AND (p_search IS NULL OR p_search = ''
               OR d.name ILIKE '%' || p_search || '%'
               OR d.description ILIKE '%' || p_search || '%')
    )
    SELECT b.b_id, b.b_name, b.b_description, b.b_head_id, b.b_head_name, b.b_count,
           b.b_created_at, b.b_updated_at, b.b_deleted_at,
           COUNT(*) OVER (),
           COALESCE(SUM(b.b_count) OVER (), 0)::BIGINT
    FROM base b
    ORDER BY b.b_id
    LIMIT p_limit OFFSET p_offset;
END;
$$;
"""

FN_DEPARTMENT_GET_OLD = r"""
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

FN_DEPARTMENT_LIST_OLD = r"""
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

def upgrade() -> None:
    op.execute(sa.text("DROP FUNCTION IF EXISTS fn_department_list(TEXT, BOOLEAN, INT, INT)"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS fn_department_get(BIGINT, BOOLEAN)"))
    op.execute(sa.text(FN_DEPARTMENT_GET))
    op.execute(sa.text(FN_DEPARTMENT_LIST))


def downgrade() -> None:
    op.execute(sa.text("DROP FUNCTION IF EXISTS fn_department_list(TEXT, BOOLEAN, INT, INT)"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS fn_department_get(BIGINT, BOOLEAN)"))
    op.execute(sa.text(FN_DEPARTMENT_GET_OLD))
    op.execute(sa.text(FN_DEPARTMENT_LIST_OLD))
