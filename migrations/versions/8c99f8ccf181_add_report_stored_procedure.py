"""add report stored procedure

Revision ID: 8c99f8ccf181
Revises: 9fc07c115edf
Create Date: 2026-11-21 14:19:34.599877

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c99f8ccf181'
down_revision: Union[str, Sequence[str], None] = '9fc07c115edf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FN_REPORT_TOP_CUSTOMERS = r"""
CREATE OR REPLACE FUNCTION fn_report_top_customers(
    p_date_from DATE, p_date_to DATE, p_limit INT DEFAULT 5
)
RETURNS TABLE (customer_id BIGINT, customer_name VARCHAR, total_spent NUMERIC, order_count BIGINT)
LANGUAGE plpgsql STABLE
AS $$
BEGIN
    IF p_date_from IS NULL OR p_date_to IS NULL THEN
        RAISE EXCEPTION 'date_from and date_to are required' USING ERRCODE = 'EV001';
    END IF;
    IF p_date_from > p_date_to THEN
        RAISE EXCEPTION 'date_from cannot be after date_to' USING ERRCODE = 'EV001';
    END IF;
    IF p_limit IS NULL OR p_limit < 1 OR p_limit > 50 THEN
        RAISE EXCEPTION 'limit must be between 1 and 50' USING ERRCODE = 'EV001';
    END IF;

    RETURN QUERY
    SELECT c.id::BIGINT, c.name, SUM(o.total_amount)::NUMERIC, COUNT(o.id)::BIGINT
    FROM orders o
    JOIN customers c ON c.id = o.customer_id
    WHERE o.deleted_at IS NULL
      AND o.status::text <> 'cancelled'
      AND o.order_date >= p_date_from
      AND o.order_date <= p_date_to
    GROUP BY c.id, c.name
    ORDER BY SUM(o.total_amount) DESC, c.id
    LIMIT p_limit;
END;
$$;
"""

FN_REPORT_ORDERS_PER_EMPLOYEE = r"""
CREATE OR REPLACE FUNCTION fn_report_orders_per_employee(
    p_date_from DATE, p_date_to DATE, p_limit INT DEFAULT 5
)
RETURNS TABLE (employee_id BIGINT, employee_name TEXT, order_count BIGINT, total_sales NUMERIC)
LANGUAGE plpgsql STABLE
AS $$
BEGIN
    IF p_date_from IS NULL OR p_date_to IS NULL THEN
        RAISE EXCEPTION 'date_from and date_to are required' USING ERRCODE = 'EV001';
    END IF;
    IF p_date_from > p_date_to THEN
        RAISE EXCEPTION 'date_from cannot be after date_to' USING ERRCODE = 'EV001';
    END IF;
    IF p_limit IS NULL OR p_limit < 1 OR p_limit > 50 THEN
        RAISE EXCEPTION 'limit must be between 1 and 50' USING ERRCODE = 'EV001';
    END IF;

    RETURN QUERY
    SELECT e.id::BIGINT, e.first_name || ' ' || e.last_name,
           COUNT(o.id)::BIGINT, SUM(o.total_amount)::NUMERIC
    FROM orders o
    JOIN employees e ON e.id = o.handled_by_id
    WHERE o.deleted_at IS NULL
      AND o.status::text <> 'cancelled'
      AND o.order_date >= p_date_from
      AND o.order_date <= p_date_to
    GROUP BY e.id, e.first_name, e.last_name
    ORDER BY COUNT(o.id) DESC, SUM(o.total_amount) DESC, e.id
    LIMIT p_limit;
END;
$$;
"""

FN_REPORT_DEPARTMENT_SUMMARY = r"""
CREATE OR REPLACE FUNCTION fn_report_department_summary()
RETURNS TABLE (
    department_id BIGINT, department_name VARCHAR, employee_count BIGINT,
    average_salary NUMERIC, monthly_payroll NUMERIC
)
LANGUAGE sql STABLE
AS $$
    SELECT d.id::BIGINT, d.name,
           COUNT(e.id)::BIGINT,
           COALESCE(ROUND(AVG(e.monthly_salary), 2), 0)::NUMERIC,
           COALESCE(SUM(e.monthly_salary), 0)::NUMERIC
    FROM departments d
    LEFT JOIN employees e ON e.department_id = d.id AND e.deleted_at IS NULL
    WHERE d.deleted_at IS NULL
    GROUP BY d.id, d.name
    ORDER BY d.id;
$$;
"""


def upgrade() -> None:
    for statement in (FN_REPORT_TOP_CUSTOMERS, FN_REPORT_ORDERS_PER_EMPLOYEE, FN_REPORT_DEPARTMENT_SUMMARY):
        op.execute(sa.text(statement))


def downgrade() -> None:
    for statement in (
        "DROP FUNCTION IF EXISTS fn_report_department_summary()",
        "DROP FUNCTION IF EXISTS fn_report_orders_per_employee(DATE, DATE, INT)",
        "DROP FUNCTION IF EXISTS fn_report_top_customers(DATE, DATE, INT)",
    ):
        op.execute(sa.text(statement))
