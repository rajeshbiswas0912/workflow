"""employee get with relations

Revision ID: 9541050ea067
Revises: 55cee651257f
Create Date: 2026-11-20 00:52:29.810833

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9541050ea067'
down_revision: Union[str, Sequence[str], None] = '55cee651257f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FN_NEW = r"""
CREATE FUNCTION fn_employee_get(p_id BIGINT, p_include_deleted BOOLEAN DEFAULT FALSE)
RETURNS TABLE (
    id BIGINT, first_name VARCHAR, last_name VARCHAR, email VARCHAR, phone VARCHAR,
    status employee_status_enum, department_id BIGINT, job_title VARCHAR,
    reports_to_id BIGINT, hire_date DATE, monthly_salary NUMERIC, role_id BIGINT,
    is_temporary_password BOOLEAN, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    department JSONB, role JSONB, manager JSONB, subordinates JSONB
)
LANGUAGE sql STABLE
AS $$
    SELECT e.id, e.first_name, e.last_name, e.email, e.phone, e.status,
           e.department_id::BIGINT, e.job_title, e.reports_to_id, e.hire_date,
           e.monthly_salary, e.role_id::BIGINT, e.is_temporary_password,
           e.created_at, e.updated_at, e.deleted_at,

           CASE WHEN d.id IS NULL THEN NULL ELSE to_jsonb(d) END,
           CASE WHEN r.id IS NULL THEN NULL ELSE to_jsonb(r) END,

           CASE WHEN m.id IS NULL THEN NULL ELSE jsonb_build_object(
               'id', m.id,
               'first_name', m.first_name,
               'last_name', m.last_name,
               'email', m.email,
               'job_title', m.job_title
           ) END,

           COALESCE((
               SELECT jsonb_agg(
                          jsonb_build_object(
                              'id', s.id,
                              'first_name', s.first_name,
                              'last_name', s.last_name,
                              'email', s.email,
                              'job_title', s.job_title,
                              'status', s.status
                          )
                          ORDER BY s.first_name, s.last_name
                      )
               FROM employees s
               WHERE s.reports_to_id = e.id AND s.deleted_at IS NULL
           ), '[]'::jsonb)
    FROM employees e
    LEFT JOIN departments d ON d.id = e.department_id
    LEFT JOIN roles r       ON r.id = e.role_id
    LEFT JOIN employees m   ON m.id = e.reports_to_id AND m.deleted_at IS NULL
    WHERE e.id = p_id AND (p_include_deleted OR e.deleted_at IS NULL);
$$;
"""

FN_OLD = r"""
CREATE FUNCTION fn_employee_get(p_id BIGINT, p_include_deleted BOOLEAN DEFAULT FALSE)
RETURNS TABLE (
    id BIGINT, first_name VARCHAR, last_name VARCHAR, email VARCHAR, phone VARCHAR,
    status employee_status_enum, department_id BIGINT, job_title VARCHAR,
    reports_to_id BIGINT, hire_date DATE, monthly_salary NUMERIC, role_id BIGINT,
    is_temporary_password BOOLEAN, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
)
LANGUAGE sql STABLE
AS $$
    SELECT e.id, e.first_name, e.last_name, e.email, e.phone, e.status,
           e.department_id::BIGINT, e.job_title, e.reports_to_id, e.hire_date,
           e.monthly_salary, e.role_id::BIGINT, e.is_temporary_password,
           e.created_at, e.updated_at, e.deleted_at
    FROM employees e
    WHERE e.id = p_id AND (p_include_deleted OR e.deleted_at IS NULL);
$$;
"""


def upgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS fn_employee_get(BIGINT, BOOLEAN)")
    op.execute(FN_NEW)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS fn_employee_get(BIGINT, BOOLEAN)")
    op.execute(FN_OLD)
