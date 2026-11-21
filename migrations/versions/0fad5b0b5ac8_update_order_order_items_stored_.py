"""update order & order items stored procedure

Revision ID: 0fad5b0b5ac8
Revises: 3d7004698d9b
Create Date: 2026-11-21 13:06:03.020297

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0fad5b0b5ac8'
down_revision: Union[str, Sequence[str], None] = '3d7004698d9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


GET_COLUMNS = """
    id BIGINT, order_number VARCHAR, customer_id BIGINT, customer_name VARCHAR,
    customer_email VARCHAR, customer_city VARCHAR,
    handled_by_id BIGINT, handled_by_name TEXT, handled_by_job_title VARCHAR,
    order_date DATE, total_amount NUMERIC, status order_status_enum, notes TEXT,
    item_count BIGINT, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ
"""

FN_ORDER_NEXT_NUMBER = r"""
CREATE OR REPLACE FUNCTION fn_order_next_number()
RETURNS TEXT
LANGUAGE sql
AS $$
    SELECT 'ORD-' || nextval('order_number_seq')::TEXT;
$$;
"""

FN_ORDER_GET = r"""
CREATE FUNCTION fn_order_get(p_id BIGINT, p_include_deleted BOOLEAN DEFAULT FALSE)
RETURNS TABLE (__COLUMNS__)
LANGUAGE sql STABLE
AS $$
    SELECT o.id, o.order_number, o.customer_id, c.name, c.email, c.city,
           o.handled_by_id, e.first_name || ' ' || e.last_name, e.job_title,
           o.order_date, o.total_amount, o.status, o.notes,
           (SELECT COUNT(*) FROM order_items oi WHERE oi.order_id = o.id)::BIGINT,
           o.created_at, o.updated_at, o.deleted_at
    FROM orders o
    JOIN customers c ON c.id = o.customer_id
    JOIN employees e ON e.id = o.handled_by_id
    WHERE o.id = p_id AND (p_include_deleted OR o.deleted_at IS NULL);
$$;
""".replace("__COLUMNS__", GET_COLUMNS)

FN_ORDER_GET_BY_NUMBER = r"""
CREATE FUNCTION fn_order_get_by_number(p_order_number TEXT)
RETURNS TABLE (__COLUMNS__)
LANGUAGE sql STABLE
AS $$
    SELECT g.*
    FROM orders o
    CROSS JOIN LATERAL fn_order_get(o.id) g
    WHERE o.order_number = upper(btrim(p_order_number)) AND o.deleted_at IS NULL;
$$;
""".replace("__COLUMNS__", GET_COLUMNS)

FN_ORDER_LIST = r"""
CREATE FUNCTION fn_order_list(
    p_search          TEXT    DEFAULT NULL,
    p_customer_id     BIGINT  DEFAULT NULL,
    p_handled_by_id   BIGINT  DEFAULT NULL,
    p_status          TEXT    DEFAULT NULL,
    p_date_from       DATE    DEFAULT NULL,
    p_date_to         DATE    DEFAULT NULL,
    p_include_deleted BOOLEAN DEFAULT FALSE,
    p_limit           INT     DEFAULT 50,
    p_offset          INT     DEFAULT 0
)
RETURNS TABLE (
    id BIGINT, order_number VARCHAR, customer_id BIGINT, customer_name VARCHAR,
    handled_by_id BIGINT, handled_by_name TEXT, order_date DATE, total_amount NUMERIC,
    status order_status_enum, notes TEXT, item_count BIGINT,
    created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ,
    total_count BIGINT
)
LANGUAGE plpgsql STABLE
AS $$
DECLARE
    v_status order_status_enum := NULL;
    v_search TEXT := NULLIF(btrim(p_search), '');
BEGIN
    IF p_limit IS NULL OR p_limit < 1 OR p_limit > 200 THEN
        RAISE EXCEPTION 'limit must be between 1 and 200' USING ERRCODE = 'EV001';
    END IF;
    IF p_offset IS NULL OR p_offset < 0 THEN
        RAISE EXCEPTION 'offset must be >= 0' USING ERRCODE = 'EV001';
    END IF;
    IF p_date_from IS NOT NULL AND p_date_to IS NOT NULL AND p_date_from > p_date_to THEN
        RAISE EXCEPTION 'date_from cannot be after date_to' USING ERRCODE = 'EV001';
    END IF;
    IF p_status IS NOT NULL THEN
        v_status := fn_order_status(p_status);
    END IF;

    RETURN QUERY
    SELECT o.id, o.order_number, o.customer_id, c.name,
           o.handled_by_id, e.first_name || ' ' || e.last_name,
           o.order_date, o.total_amount, o.status, o.notes,
           (SELECT COUNT(*) FROM order_items oi WHERE oi.order_id = o.id)::BIGINT,
           o.created_at, o.updated_at, o.deleted_at,
           COUNT(*) OVER ()
    FROM orders o
    JOIN customers c ON c.id = o.customer_id
    JOIN employees e ON e.id = o.handled_by_id
    WHERE (p_include_deleted OR o.deleted_at IS NULL)
      AND (p_customer_id   IS NULL OR o.customer_id   = p_customer_id)
      AND (p_handled_by_id IS NULL OR o.handled_by_id = p_handled_by_id)
      AND (v_status        IS NULL OR o.status        = v_status)
      AND (p_date_from     IS NULL OR o.order_date   >= p_date_from)
      AND (p_date_to       IS NULL OR o.order_date   <= p_date_to)
      AND (v_search IS NULL
           OR o.order_number ILIKE '%' || v_search || '%'
           OR o.notes        ILIKE '%' || v_search || '%'
           OR c.name         ILIKE '%' || v_search || '%')
    ORDER BY o.order_date DESC, o.id DESC
    LIMIT p_limit OFFSET p_offset;
END;
$$;
"""

# Counts for the status chips: honours search/customer/handler/date, ignores the status filter
FN_ORDER_STATUS_COUNTS = r"""
CREATE FUNCTION fn_order_status_counts(
    p_search        TEXT   DEFAULT NULL,
    p_customer_id   BIGINT DEFAULT NULL,
    p_handled_by_id BIGINT DEFAULT NULL,
    p_date_from     DATE   DEFAULT NULL,
    p_date_to       DATE   DEFAULT NULL
)
RETURNS TABLE (status order_status_enum, order_count BIGINT)
LANGUAGE sql STABLE
AS $$
    SELECT s.status, COUNT(x.id)::BIGINT
    FROM unnest(enum_range(NULL::order_status_enum)) AS s(status)
    LEFT JOIN (
        SELECT o.id, o.status
        FROM orders o
        JOIN customers c ON c.id = o.customer_id
        WHERE o.deleted_at IS NULL
          AND (p_customer_id   IS NULL OR o.customer_id   = p_customer_id)
          AND (p_handled_by_id IS NULL OR o.handled_by_id = p_handled_by_id)
          AND (p_date_from     IS NULL OR o.order_date   >= p_date_from)
          AND (p_date_to       IS NULL OR o.order_date   <= p_date_to)
          AND (NULLIF(btrim(p_search), '') IS NULL
               OR o.order_number ILIKE '%' || btrim(p_search) || '%'
               OR o.notes        ILIKE '%' || btrim(p_search) || '%'
               OR c.name         ILIKE '%' || btrim(p_search) || '%')
    ) x ON x.status = s.status
    GROUP BY s.status
    ORDER BY s.status;
$$;
"""

FN_ORDER_ITEM_GET = r"""
CREATE FUNCTION fn_order_item_get(p_id BIGINT)
RETURNS TABLE (
    id BIGINT, order_id BIGINT, product_id BIGINT, product_name VARCHAR, product_sku VARCHAR,
    quantity INT, unit_price NUMERIC, subtotal NUMERIC,
    created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ
)
LANGUAGE sql STABLE
AS $$
    SELECT oi.id, oi.order_id, oi.product_id, p.name, p.sku,
           oi.quantity, oi.unit_price, oi.subtotal, oi.created_at, oi.updated_at
    FROM order_items oi
    JOIN products p ON p.id = oi.product_id
    WHERE oi.id = p_id;
$$;
"""

FN_ORDER_ITEM_LIST_BY_ORDER = r"""
CREATE FUNCTION fn_order_item_list_by_order(p_order_id BIGINT)
RETURNS TABLE (
    id BIGINT, order_id BIGINT, product_id BIGINT, product_name VARCHAR, product_sku VARCHAR,
    quantity INT, unit_price NUMERIC, subtotal NUMERIC,
    created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ
)
LANGUAGE plpgsql STABLE
AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM orders o WHERE o.id = p_order_id) THEN
        RAISE EXCEPTION 'order % not found', p_order_id USING ERRCODE = 'EV002';
    END IF;

    RETURN QUERY
    SELECT oi.id, oi.order_id, oi.product_id, p.name, p.sku,
           oi.quantity, oi.unit_price, oi.subtotal, oi.created_at, oi.updated_at
    FROM order_items oi
    JOIN products p ON p.id = oi.product_id
    WHERE oi.order_id = p_order_id
    ORDER BY oi.id;
END;
$$;
"""

# Total = sum of line subtotals + GST, which is how your existing order totals are stored
SP_ORDER_RECALCULATE_TOTAL = r"""
CREATE OR REPLACE PROCEDURE sp_order_recalculate_total(p_order_id BIGINT)
LANGUAGE plpgsql
AS $$
DECLARE
    v_gst_rate NUMERIC := 0.18;      -- keep in sync with GST_RATE in the API
    v_subtotal NUMERIC;
    v_total    NUMERIC;
BEGIN
    SELECT COALESCE(SUM(oi.subtotal), 0) INTO v_subtotal
    FROM order_items oi WHERE oi.order_id = p_order_id;

    v_total := round(v_subtotal * (1 + v_gst_rate), 2);

    IF v_total >= 10000000000 THEN
        RAISE EXCEPTION 'order total exceeds the maximum allowed amount' USING ERRCODE = 'EV001';
    END IF;

    UPDATE orders SET total_amount = v_total, updated_at = now() WHERE id = p_order_id;
END;
$$;
"""


def upgrade() -> None:
    for stmt in (
        "DROP FUNCTION IF EXISTS fn_order_item_list_by_order(BIGINT)",
        "DROP FUNCTION IF EXISTS fn_order_item_get(BIGINT)",
        "DROP FUNCTION IF EXISTS fn_order_list(TEXT, BIGINT, BIGINT, TEXT, DATE, DATE, BOOLEAN, INT, INT)",
        "DROP FUNCTION IF EXISTS fn_order_get_by_number(TEXT)",
        "DROP FUNCTION IF EXISTS fn_order_get(BIGINT, BOOLEAN)",
    ):
        op.execute(sa.text(stmt))

    # order numbers: continue after the highest existing ORD-<number>
    op.execute(sa.text("CREATE SEQUENCE IF NOT EXISTS order_number_seq"))
    op.execute(sa.text("""
        SELECT setval('order_number_seq', GREATEST(1000, COALESCE(
            (SELECT MAX(substring(order_number from '^ORD-([0-9]+)$')::INT) FROM orders), 1000)))
    """))

    for stmt in (
        FN_ORDER_NEXT_NUMBER,
        FN_ORDER_GET,
        FN_ORDER_GET_BY_NUMBER,
        FN_ORDER_LIST,
        FN_ORDER_STATUS_COUNTS,
        FN_ORDER_ITEM_GET,
        FN_ORDER_ITEM_LIST_BY_ORDER,
        SP_ORDER_RECALCULATE_TOTAL,
    ):
        op.execute(sa.text(stmt))


def downgrade() -> None:
    for stmt in (
        "DROP FUNCTION IF EXISTS fn_order_status_counts(TEXT, BIGINT, BIGINT, DATE, DATE)",
        "DROP FUNCTION IF EXISTS fn_order_item_list_by_order(BIGINT)",
        "DROP FUNCTION IF EXISTS fn_order_item_get(BIGINT)",
        "DROP FUNCTION IF EXISTS fn_order_list(TEXT, BIGINT, BIGINT, TEXT, DATE, DATE, BOOLEAN, INT, INT)",
        "DROP FUNCTION IF EXISTS fn_order_get_by_number(TEXT)",
        "DROP FUNCTION IF EXISTS fn_order_get(BIGINT, BOOLEAN)",
        "DROP FUNCTION IF EXISTS fn_order_next_number()",
        "DROP SEQUENCE IF EXISTS order_number_seq",
    ):
        op.execute(sa.text(stmt))
