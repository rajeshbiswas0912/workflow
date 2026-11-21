"""update employee list stored procedure

Revision ID: ef773702b784
Revises: 744c6c922a63
Create Date: 2026-11-20 20:58:38.086762

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef773702b784'
down_revision: Union[str, Sequence[str], None] = '744c6c922a63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FN_EMPLOYEE_LIST_NEW = r"""
CREATE OR REPLACE FUNCTION fn_employee_list(
    p_search          TEXT    DEFAULT NULL,
    p_department_id   BIGINT  DEFAULT NULL,
    p_role_id         BIGINT  DEFAULT NULL,
    p_status          TEXT    DEFAULT NULL,
    p_include_deleted BOOLEAN DEFAULT FALSE,
    p_limit           INT     DEFAULT 50,
    p_offset          INT     DEFAULT 0
)
RETURNS TABLE (
    id BIGINT, first_name VARCHAR, last_name VARCHAR, email VARCHAR, phone VARCHAR,
    status employee_status_enum, department_id BIGINT, department_name VARCHAR,
    job_title VARCHAR, reports_to_id BIGINT, hire_date DATE, monthly_salary NUMERIC,
    role_id BIGINT, role_name VARCHAR, is_temporary_password BOOLEAN,
    created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ,
    total_count BIGINT, department_count BIGINT
)
LANGUAGE plpgsql STABLE
AS $$
DECLARE
    v_status employee_status_enum := NULL;
BEGIN
    IF p_limit IS NULL OR p_limit < 1 OR p_limit > 200 THEN
        RAISE EXCEPTION 'limit must be between 1 and 200' USING ERRCODE = 'EV001';
    END IF;
    IF p_offset IS NULL OR p_offset < 0 THEN
        RAISE EXCEPTION 'offset must be >= 0' USING ERRCODE = 'EV001';
    END IF;
    IF p_status IS NOT NULL AND btrim(p_status) <> '' THEN
        v_status := fn_employee_status(p_status);
    END IF;

    RETURN QUERY
    SELECT e.id, e.first_name, e.last_name, e.email, e.phone, e.status,
           e.department_id::BIGINT, d.name AS department_name, e.job_title,
           e.reports_to_id, e.hire_date, e.monthly_salary,
           e.role_id::BIGINT, r.name AS role_name, e.is_temporary_password,
           e.created_at, e.updated_at, e.deleted_at,
           COUNT(*) OVER () AS total_count,
           (SELECT COUNT(DISTINCT e2.department_id)
            FROM employees e2
            WHERE (p_include_deleted OR e2.deleted_at IS NULL)) AS department_count
    FROM employees e
    LEFT JOIN departments d ON d.id = e.department_id
    LEFT JOIN roles r       ON r.id = e.role_id
    WHERE (p_include_deleted OR e.deleted_at IS NULL)
      AND (p_department_id IS NULL OR e.department_id = p_department_id)
      AND (p_role_id       IS NULL OR e.role_id       = p_role_id)
      AND (v_status        IS NULL OR e.status        = v_status)
      AND (p_search IS NULL OR btrim(p_search) = ''
           OR e.first_name ILIKE '%' || btrim(p_search) || '%'
           OR e.last_name  ILIKE '%' || btrim(p_search) || '%'
           OR (e.first_name || ' ' || e.last_name) ILIKE '%' || btrim(p_search) || '%'
           OR e.email      ILIKE '%' || btrim(p_search) || '%'
           OR e.job_title  ILIKE '%' || btrim(p_search) || '%')
    ORDER BY e.id
    LIMIT p_limit OFFSET p_offset;
END;
$$;
"""


FN_EMPLOYEE_LIST_OLD = r"""
CREATE OR REPLACE FUNCTION fn_employee_list(
    p_search          TEXT    DEFAULT NULL,
    p_department_id   BIGINT  DEFAULT NULL,
    p_role_id         BIGINT  DEFAULT NULL,
    p_status          TEXT    DEFAULT NULL,
    p_include_deleted BOOLEAN DEFAULT FALSE,
    p_limit           INT     DEFAULT 50,
    p_offset          INT     DEFAULT 0
)
RETURNS TABLE (
    id BIGINT, first_name VARCHAR, last_name VARCHAR, email VARCHAR, phone VARCHAR,
    status employee_status_enum, department_id BIGINT, job_title VARCHAR,
    reports_to_id BIGINT, hire_date DATE, monthly_salary NUMERIC, role_id BIGINT,
    is_temporary_password BOOLEAN, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ, total_count BIGINT
)
LANGUAGE plpgsql STABLE
AS $$
DECLARE
    v_status employee_status_enum := NULL;
BEGIN
    IF p_limit IS NULL OR p_limit < 1 OR p_limit > 200 THEN
        RAISE EXCEPTION 'limit must be between 1 and 200' USING ERRCODE = 'EV001';
    END IF;
    IF p_offset IS NULL OR p_offset < 0 THEN
        RAISE EXCEPTION 'offset must be >= 0' USING ERRCODE = 'EV001';
    END IF;
    IF p_status IS NOT NULL THEN
        v_status := fn_employee_status(p_status);
    END IF;

    RETURN QUERY
    SELECT e.id, e.first_name, e.last_name, e.email, e.phone, e.status,
           e.department_id::BIGINT, e.job_title, e.reports_to_id, e.hire_date,
           e.monthly_salary, e.role_id::BIGINT, e.is_temporary_password,
           e.created_at, e.updated_at, e.deleted_at,
           COUNT(*) OVER () AS total_count
    FROM employees e
    WHERE (p_include_deleted OR e.deleted_at IS NULL)
      AND (p_department_id IS NULL OR e.department_id = p_department_id)
      AND (p_role_id       IS NULL OR e.role_id       = p_role_id)
      AND (v_status        IS NULL OR e.status        = v_status)
      AND (p_search IS NULL OR p_search = ''
           OR e.first_name ILIKE '%' || p_search || '%'
           OR e.last_name  ILIKE '%' || p_search || '%'
           OR e.email      ILIKE '%' || p_search || '%')
    ORDER BY e.id
    LIMIT p_limit OFFSET p_offset;
END;
$$;
"""

def upgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS fn_employee_list(TEXT, BIGINT, BIGINT, TEXT, BOOLEAN, INT, INT)")
    op.execute(FN_EMPLOYEE_LIST_NEW)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS fn_employee_list(TEXT, BIGINT, BIGINT, TEXT, BOOLEAN, INT, INT)")
    op.execute(FN_EMPLOYEE_LIST_OLD)
