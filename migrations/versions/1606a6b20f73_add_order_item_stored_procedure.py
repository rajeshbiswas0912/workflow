"""add order item stored procedure

Revision ID: 1606a6b20f73
Revises: 82b1c9a2b4ce
Create Date: 2026-11-19 01:07:33.204529

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1606a6b20f73'
down_revision: Union[str, Sequence[str], None] = '82b1c9a2b4ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SP_ORDER_RECALCULATE_TOTAL = r"""
CREATE OR REPLACE PROCEDURE sp_order_recalculate_total(p_order_id BIGINT)
LANGUAGE plpgsql
AS $$
DECLARE
    v_total NUMERIC;
BEGIN
    SELECT COALESCE(SUM(oi.subtotal), 0) INTO v_total
    FROM order_items oi WHERE oi.order_id = p_order_id;

    IF v_total >= 10000000000 THEN
        RAISE EXCEPTION 'order total exceeds the maximum allowed amount' USING ERRCODE = 'EV001';
    END IF;

    UPDATE orders SET total_amount = v_total, updated_at = now() WHERE id = p_order_id;
END;
$$;
"""

FN_ORDER_ITEM_VALIDATE = r"""
CREATE OR REPLACE FUNCTION fn_order_item_validate(
    p_item_id    BIGINT,      -- NULL on create
    p_order_id   BIGINT,
    p_product_id BIGINT,
    p_quantity   INT,
    p_unit_price NUMERIC
) RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_order_id IS NULL
       OR NOT EXISTS (SELECT 1 FROM orders WHERE id = p_order_id AND deleted_at IS NULL) THEN
        RAISE EXCEPTION 'order % does not exist', p_order_id USING ERRCODE = 'EV002';
    END IF;

    IF p_product_id IS NULL
       OR NOT EXISTS (SELECT 1 FROM products WHERE id = p_product_id) THEN
        RAISE EXCEPTION 'product % does not exist', p_product_id USING ERRCODE = 'EV001';
    END IF;

    IF p_quantity IS NULL OR p_quantity < 1 THEN
        RAISE EXCEPTION 'quantity must be at least 1' USING ERRCODE = 'EV001';
    END IF;
    IF p_quantity > 1000000 THEN
        RAISE EXCEPTION 'quantity must be at most 1000000' USING ERRCODE = 'EV001';
    END IF;

    IF p_unit_price IS NULL THEN
        RAISE EXCEPTION 'unit_price is required' USING ERRCODE = 'EV001';
    END IF;
    IF p_unit_price < 0 OR p_unit_price >= 10000000000 THEN
        RAISE EXCEPTION 'unit_price is out of range' USING ERRCODE = 'EV001';
    END IF;
    IF p_unit_price <> round(p_unit_price, 2) THEN
        RAISE EXCEPTION 'unit_price can have at most 2 decimal places' USING ERRCODE = 'EV001';
    END IF;

    IF p_quantity::NUMERIC * p_unit_price >= 10000000000 THEN
        RAISE EXCEPTION 'subtotal exceeds the maximum allowed amount' USING ERRCODE = 'EV001';
    END IF;

    -- one line per product within an order
    IF EXISTS (
        SELECT 1 FROM order_items oi
        WHERE oi.order_id = p_order_id
          AND oi.product_id = p_product_id
          AND (p_item_id IS NULL OR oi.id <> p_item_id)
    ) THEN
        RAISE EXCEPTION 'product % is already in order %; update that line instead',
            p_product_id, p_order_id USING ERRCODE = 'EV003';
    END IF;
END;
$$;
"""

SP_ORDER_ITEM_CREATE = r"""
CREATE OR REPLACE PROCEDURE sp_order_item_create(
    INOUT p_id         BIGINT,
    IN    p_order_id   BIGINT,
    IN    p_product_id BIGINT,
    IN    p_quantity   INT,
    IN    p_unit_price NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- lock the parent order so concurrent item writes recalculate the total safely
    PERFORM 1 FROM orders WHERE id = p_order_id AND deleted_at IS NULL FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'order % does not exist', p_order_id USING ERRCODE = 'EV002';
    END IF;

    PERFORM fn_order_item_validate(NULL, p_order_id, p_product_id, p_quantity, p_unit_price);

    INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal)
    VALUES (p_order_id, p_product_id, p_quantity, p_unit_price,
            round(p_quantity::NUMERIC * p_unit_price, 2))
    RETURNING id INTO p_id;

    CALL sp_order_recalculate_total(p_order_id);
END;
$$;
"""

SP_ORDER_ITEM_UPDATE = r"""
CREATE OR REPLACE PROCEDURE sp_order_item_update(
    IN p_id         BIGINT,
    IN p_product_id BIGINT,
    IN p_quantity   INT,
    IN p_unit_price NUMERIC
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_order_id BIGINT;
BEGIN
    SELECT oi.order_id INTO v_order_id FROM order_items oi WHERE oi.id = p_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'order item % not found', p_id USING ERRCODE = 'EV002';
    END IF;

    PERFORM 1 FROM orders WHERE id = v_order_id AND deleted_at IS NULL FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'order % does not exist', v_order_id USING ERRCODE = 'EV002';
    END IF;

    PERFORM fn_order_item_validate(p_id, v_order_id, p_product_id, p_quantity, p_unit_price);

    UPDATE order_items SET
        product_id = p_product_id,
        quantity   = p_quantity,
        unit_price = p_unit_price,
        subtotal   = round(p_quantity::NUMERIC * p_unit_price, 2),
        updated_at = now()
    WHERE id = p_id;

    CALL sp_order_recalculate_total(v_order_id);
END;
$$;
"""

SP_ORDER_ITEM_DELETE = r"""
CREATE OR REPLACE PROCEDURE sp_order_item_delete(p_id BIGINT)
LANGUAGE plpgsql
AS $$
DECLARE
    v_order_id BIGINT;
BEGIN
    SELECT oi.order_id INTO v_order_id FROM order_items oi WHERE oi.id = p_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'order item % not found', p_id USING ERRCODE = 'EV002';
    END IF;

    PERFORM 1 FROM orders WHERE id = v_order_id AND deleted_at IS NULL FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'order % does not exist', v_order_id USING ERRCODE = 'EV002';
    END IF;

    DELETE FROM order_items WHERE id = p_id;

    CALL sp_order_recalculate_total(v_order_id);
END;
$$;
"""

FN_ORDER_ITEM_GET = r"""
CREATE OR REPLACE FUNCTION fn_order_item_get(p_id BIGINT)
RETURNS TABLE (
    id BIGINT, order_id BIGINT, product_id BIGINT, quantity INT,
    unit_price NUMERIC, subtotal NUMERIC, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ
)
LANGUAGE sql STABLE
AS $$
    SELECT oi.id, oi.order_id, oi.product_id, oi.quantity,
           oi.unit_price, oi.subtotal, oi.created_at, oi.updated_at
    FROM order_items oi
    WHERE oi.id = p_id;
$$;
"""

FN_ORDER_ITEM_LIST_BY_ORDER = r"""
CREATE OR REPLACE FUNCTION fn_order_item_list_by_order(p_order_id BIGINT)
RETURNS TABLE (
    id BIGINT, order_id BIGINT, product_id BIGINT, quantity INT,
    unit_price NUMERIC, subtotal NUMERIC, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ
)
LANGUAGE plpgsql STABLE
AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM orders o WHERE o.id = p_order_id) THEN
        RAISE EXCEPTION 'order % not found', p_order_id USING ERRCODE = 'EV002';
    END IF;

    RETURN QUERY
    SELECT oi.id, oi.order_id, oi.product_id, oi.quantity,
           oi.unit_price, oi.subtotal, oi.created_at, oi.updated_at
    FROM order_items oi
    WHERE oi.order_id = p_order_id
    ORDER BY oi.id;
END;
$$;
"""

# Order matters: helpers first, then routines that call them.
UPGRADE_STATEMENTS = [
    SP_ORDER_RECALCULATE_TOTAL,
    FN_ORDER_ITEM_VALIDATE,
    SP_ORDER_ITEM_CREATE,
    SP_ORDER_ITEM_UPDATE,
    SP_ORDER_ITEM_DELETE,
    FN_ORDER_ITEM_GET,
    FN_ORDER_ITEM_LIST_BY_ORDER,
]

DOWNGRADE_STATEMENTS = [
    "DROP FUNCTION IF EXISTS fn_order_item_list_by_order(BIGINT)",
    "DROP FUNCTION IF EXISTS fn_order_item_get(BIGINT)",
    "DROP PROCEDURE IF EXISTS sp_order_item_delete(BIGINT)",
    "DROP PROCEDURE IF EXISTS sp_order_item_update(BIGINT, BIGINT, INT, NUMERIC)",
    "DROP PROCEDURE IF EXISTS sp_order_item_create(BIGINT, BIGINT, BIGINT, INT, NUMERIC)",
    "DROP FUNCTION IF EXISTS fn_order_item_validate(BIGINT, BIGINT, BIGINT, INT, NUMERIC)",
    "DROP PROCEDURE IF EXISTS sp_order_recalculate_total(BIGINT)",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(sa.text(statement))


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(sa.text(statement))
