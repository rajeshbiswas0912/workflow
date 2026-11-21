"""add dshboard stored procedure

Revision ID: 9fc07c115edf
Revises: 0fad5b0b5ac8
Create Date: 2026-11-21 13:57:16.549250

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9fc07c115edf'
down_revision: Union[str, Sequence[str], None] = '0fad5b0b5ac8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FN_DASHBOARD_EMPLOYEES = r"""
CREATE OR REPLACE FUNCTION fn_dashboard_employees()
RETURNS TABLE (employee_count BIGINT, department_count BIGINT)
LANGUAGE sql STABLE
AS $$
    SELECT (SELECT COUNT(*) FROM employees e   WHERE e.deleted_at IS NULL)::BIGINT,
           (SELECT COUNT(*) FROM departments d WHERE d.deleted_at IS NULL)::BIGINT;
$$;
"""

FN_DASHBOARD_CUSTOMERS = r"""
CREATE OR REPLACE FUNCTION fn_dashboard_customers()
RETURNS TABLE (customer_count BIGINT)
LANGUAGE sql STABLE
AS $$
    SELECT COUNT(*)::BIGINT FROM customers c WHERE c.deleted_at IS NULL;
$$;
"""

# Revenue for the month containing p_month_start: all orders except cancelled ones
FN_DASHBOARD_REVENUE = r"""
CREATE OR REPLACE FUNCTION fn_dashboard_revenue(p_month_start DATE)
RETURNS TABLE (revenue NUMERIC, order_count BIGINT)
LANGUAGE sql STABLE
AS $$
    SELECT COALESCE(SUM(o.total_amount), 0)::NUMERIC, COUNT(o.id)::BIGINT
    FROM orders o
    WHERE o.deleted_at IS NULL
      AND o.status::text <> 'cancelled'
      AND o.order_date >= date_trunc('month', p_month_start::TIMESTAMP)::DATE
      AND o.order_date <  (date_trunc('month', p_month_start::TIMESTAMP) + INTERVAL '1 month')::DATE;
$$;
"""

# One row per month for the last p_months months, ending with the month of p_end_month. Empty months are 0.
FN_DASHBOARD_SALES_BY_MONTH = r"""
CREATE OR REPLACE FUNCTION fn_dashboard_sales_by_month(p_end_month DATE, p_months INT DEFAULT 6)
RETURNS TABLE (month_start DATE, total_sales NUMERIC, order_count BIGINT)
LANGUAGE plpgsql STABLE
AS $$
BEGIN
    IF p_end_month IS NULL THEN
        RAISE EXCEPTION 'end month is required' USING ERRCODE = 'EV001';
    END IF;
    IF p_months IS NULL OR p_months < 1 OR p_months > 24 THEN
        RAISE EXCEPTION 'months must be between 1 and 24' USING ERRCODE = 'EV001';
    END IF;

    RETURN QUERY
    SELECT m.month_start::DATE,
           COALESCE(SUM(o.total_amount), 0)::NUMERIC,
           COUNT(o.id)::BIGINT
    FROM generate_series(
             date_trunc('month', p_end_month::TIMESTAMP) - ((p_months - 1) * INTERVAL '1 month'),
             date_trunc('month', p_end_month::TIMESTAMP),
             INTERVAL '1 month'
         ) AS m(month_start)
    LEFT JOIN orders o
           ON o.order_date >= m.month_start::DATE
          AND o.order_date <  (m.month_start + INTERVAL '1 month')::DATE
          AND o.deleted_at IS NULL
          AND o.status::text <> 'cancelled'
    GROUP BY m.month_start
    ORDER BY m.month_start;
END;
$$;
"""

UPGRADE_STATEMENTS = [
    FN_DASHBOARD_EMPLOYEES,
    FN_DASHBOARD_CUSTOMERS,
    FN_DASHBOARD_REVENUE,
    FN_DASHBOARD_SALES_BY_MONTH,
]

DOWNGRADE_STATEMENTS = [
    "DROP FUNCTION IF EXISTS fn_dashboard_sales_by_month(DATE, INT)",
    "DROP FUNCTION IF EXISTS fn_dashboard_revenue(DATE)",
    "DROP FUNCTION IF EXISTS fn_dashboard_customers()",
    "DROP FUNCTION IF EXISTS fn_dashboard_employees()",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(sa.text(statement))


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(sa.text(statement))
