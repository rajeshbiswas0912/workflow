"""add order stored procedure

Revision ID: 82b1c9a2b4ce
Revises: d0e15ad2a5c0
Create Date: 2026-11-19 01:01:27.484593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '82b1c9a2b4ce'
down_revision: Union[str, Sequence[str], None] = 'd0e15ad2a5c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FN_ORDER_STATUS = r"""
CREATE OR REPLACE FUNCTION fn_order_status(p_status TEXT)
RETURNS order_status_enum
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_status IS NULL OR btrim(p_status) = '' THEN
        RAISE EXCEPTION 'status is required' USING ERRCODE = 'EV001';
    END IF;
    RETURN btrim(p_status)::order_status_enum;
EXCEPTION
    WHEN invalid_text_representation THEN
        RAISE EXCEPTION 'invalid status: %', p_status USING ERRCODE = 'EV001';
END;
$$;
"""

FN_ORDER_VALIDATE = r"""
CREATE OR REPLACE FUNCTION fn_order_validate(
    p_order_id      BIGINT,      -- NULL on create
    p_order_number  TEXT,        -- already upper-cased and trimmed
    p_customer_id   BIGINT,
    p_handled_by_id BIGINT,
    p_order_date    DATE,
    p_total_amount  NUMERIC,
    p_notes         TEXT
) RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_order_number IS NULL OR btrim(p_order_number) = '' THEN
        RAISE EXCEPTION 'order_number is required' USING ERRCODE = 'EV001';
    END IF;
    IF char_length(btrim(p_order_number)) > 50
       OR btrim(p_order_number) !~ '^[A-Za-z0-9][A-Za-z0-9\-_/]*$' THEN
        RAISE EXCEPTION 'order_number is not valid (letters, digits, - _ / only, max 50)'
            USING ERRCODE = 'EV001';
    END IF;

    -- unique across ALL rows (including soft-deleted ones)
    IF EXISTS (
        SELECT 1 FROM orders o
        WHERE o.order_number = btrim(p_order_number)
          AND (p_order_id IS NULL OR o.id <> p_order_id)
    ) THEN
        RAISE EXCEPTION 'order number % is already in use', btrim(p_order_number)
            USING ERRCODE = 'EV003';
    END IF;

    IF p_customer_id IS NULL
       OR NOT EXISTS (SELECT 1 FROM customers WHERE id = p_customer_id AND deleted_at IS NULL) THEN
        RAISE EXCEPTION 'customer % does not exist', p_customer_id USING ERRCODE = 'EV001';
    END IF;

    IF p_handled_by_id IS NULL
       OR NOT EXISTS (SELECT 1 FROM employees WHERE id = p_handled_by_id AND deleted_at IS NULL) THEN
        RAISE EXCEPTION 'employee % does not exist', p_handled_by_id USING ERRCODE = 'EV001';
    END IF;

    IF p_order_date IS NULL THEN
        RAISE EXCEPTION 'order_date is required' USING ERRCODE = 'EV001';
    END IF;
    -- +1 day tolerance so time-zone differences don't reject "today"
    IF p_order_date > CURRENT_DATE + 1 THEN
        RAISE EXCEPTION 'order_date cannot be in the future' USING ERRCODE = 'EV001';
    END IF;

    IF p_total_amount IS NULL THEN
        RAISE EXCEPTION 'total_amount is required' USING ERRCODE = 'EV001';
    END IF;
    IF p_total_amount < 0 OR p_total_amount >= 10000000000 THEN
        RAISE EXCEPTION 'total_amount is out of range' USING ERRCODE = 'EV001';
    END IF;

    IF p_notes IS NOT NULL AND char_length(p_notes) > 2000 THEN
        RAISE EXCEPTION 'notes must be at most 2000 characters' USING ERRCODE = 'EV001';
    END IF;
END;
$$;
"""

SP_ORDER_CREATE = r"""
CREATE OR REPLACE PROCEDURE sp_order_create(
    INOUT p_id            BIGINT,
    IN    p_order_number  TEXT,
    IN    p_customer_id   BIGINT,
    IN    p_handled_by_id BIGINT,
    IN    p_order_date    DATE,
    IN    p_total_amount  NUMERIC,
    IN    p_status        TEXT,
    IN    p_notes         TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_number TEXT := upper(btrim(p_order_number));
    v_status order_status_enum := fn_order_status(p_status);
BEGIN
    PERFORM fn_order_validate(
        NULL, v_number, p_customer_id, p_handled_by_id, p_order_date, p_total_amount, p_notes
    );

    INSERT INTO orders (
        order_number, customer_id, handled_by_id, order_date, total_amount, status, notes
    ) VALUES (
        v_number, p_customer_id, p_handled_by_id, p_order_date, p_total_amount, v_status,
        NULLIF(btrim(p_notes), '')
    )
    RETURNING id INTO p_id;
EXCEPTION
    WHEN unique_violation THEN
        RAISE EXCEPTION 'order number % is already in use', v_number USING ERRCODE = 'EV003';
END;
$$;
"""

SP_ORDER_UPDATE = r"""
CREATE OR REPLACE PROCEDURE sp_order_update(
    IN p_id            BIGINT,
    IN p_order_number  TEXT,
    IN p_customer_id   BIGINT,
    IN p_handled_by_id BIGINT,
    IN p_order_date    DATE,
    IN p_total_amount  NUMERIC,
    IN p_notes         TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_number TEXT := upper(btrim(p_order_number));
BEGIN
    PERFORM 1 FROM orders WHERE id = p_id AND deleted_at IS NULL FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'order % not found', p_id USING ERRCODE = 'EV002';
    END IF;

    PERFORM fn_order_validate(
        p_id, v_number, p_customer_id, p_handled_by_id, p_order_date, p_total_amount, p_notes
    );

    UPDATE orders SET
        order_number  = v_number,
        customer_id   = p_customer_id,
        handled_by_id = p_handled_by_id,
        order_date    = p_order_date,
        total_amount  = p_total_amount,
        notes         = NULLIF(btrim(p_notes), ''),
        updated_at    = now()
    WHERE id = p_id;
EXCEPTION
    WHEN unique_violation THEN
        RAISE EXCEPTION 'order number % is already in use', v_number USING ERRCODE = 'EV003';
END;
$$;
"""

SP_ORDER_CHANGE_STATUS = r"""
CREATE OR REPLACE PROCEDURE sp_order_change_status(p_id BIGINT, p_status TEXT)
LANGUAGE plpgsql
AS $$
DECLARE
    v_status order_status_enum := fn_order_status(p_status);
BEGIN
    UPDATE orders SET status = v_status, updated_at = now()
    WHERE id = p_id AND deleted_at IS NULL;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'order % not found', p_id USING ERRCODE = 'EV002';
    END IF;
END;
$$;
"""

SP_ORDER_SET_TOTAL = r"""
CREATE OR REPLACE PROCEDURE sp_order_set_total(p_id BIGINT, p_total_amount NUMERIC)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_total_amount IS NULL OR p_total_amount < 0 OR p_total_amount >= 10000000000 THEN
        RAISE EXCEPTION 'total_amount is out of range' USING ERRCODE = 'EV001';
    END IF;
    UPDATE orders SET total_amount = p_total_amount, updated_at = now()
    WHERE id = p_id AND deleted_at IS NULL;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'order % not found', p_id USING ERRCODE = 'EV002';
    END IF;
END;
$$;
"""

SP_ORDER_DELETE = r"""
CREATE OR REPLACE PROCEDURE sp_order_delete(p_id BIGINT)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE orders SET deleted_at = now(), updated_at = now()
    WHERE id = p_id AND deleted_at IS NULL;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'order % not found', p_id USING ERRCODE = 'EV002';
    END IF;
END;
$$;
"""

SP_ORDER_RESTORE = r"""
CREATE OR REPLACE PROCEDURE sp_order_restore(p_id BIGINT)
LANGUAGE plpgsql
AS $$
DECLARE
    v_customer_id BIGINT;
BEGIN
    SELECT customer_id INTO v_customer_id
    FROM orders WHERE id = p_id AND deleted_at IS NOT NULL FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'deleted order % not found', p_id USING ERRCODE = 'EV002';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM customers WHERE id = v_customer_id AND deleted_at IS NULL) THEN
        RAISE EXCEPTION 'cannot restore order %: its customer is deleted', p_id
            USING ERRCODE = 'EV003';
    END IF;

    UPDATE orders SET deleted_at = NULL, updated_at = now() WHERE id = p_id;
END;
$$;
"""

FN_ORDER_GET = r"""
CREATE OR REPLACE FUNCTION fn_order_get(p_id BIGINT, p_include_deleted BOOLEAN DEFAULT FALSE)
RETURNS TABLE (
    id BIGINT, order_number VARCHAR, customer_id BIGINT, customer_name VARCHAR,
    handled_by_id BIGINT, handled_by_name TEXT, order_date DATE, total_amount NUMERIC,
    status order_status_enum, notes TEXT,
    created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ
)
LANGUAGE sql STABLE
AS $$
    SELECT o.id, o.order_number, o.customer_id, c.name,
           o.handled_by_id, e.first_name || ' ' || e.last_name,
           o.order_date, o.total_amount, o.status, o.notes,
           o.created_at, o.updated_at, o.deleted_at
    FROM orders o
    JOIN customers c ON c.id = o.customer_id
    JOIN employees e ON e.id = o.handled_by_id
    WHERE o.id = p_id AND (p_include_deleted OR o.deleted_at IS NULL);
$$;
"""

FN_ORDER_GET_BY_NUMBER = r"""
CREATE OR REPLACE FUNCTION fn_order_get_by_number(p_order_number TEXT)
RETURNS TABLE (
    id BIGINT, order_number VARCHAR, customer_id BIGINT, customer_name VARCHAR,
    handled_by_id BIGINT, handled_by_name TEXT, order_date DATE, total_amount NUMERIC,
    status order_status_enum, notes TEXT,
    created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ
)
LANGUAGE sql STABLE
AS $$
    SELECT o.id, o.order_number, o.customer_id, c.name,
           o.handled_by_id, e.first_name || ' ' || e.last_name,
           o.order_date, o.total_amount, o.status, o.notes,
           o.created_at, o.updated_at, o.deleted_at
    FROM orders o
    JOIN customers c ON c.id = o.customer_id
    JOIN employees e ON e.id = o.handled_by_id
    WHERE o.order_number = upper(btrim(p_order_number)) AND o.deleted_at IS NULL;
$$;
"""

FN_ORDER_LIST = r"""
CREATE OR REPLACE FUNCTION fn_order_list(
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
    status order_status_enum, notes TEXT,
    created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ,
    total_count BIGINT
)
LANGUAGE plpgsql STABLE
AS $$
DECLARE
    v_status order_status_enum := NULL;
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
           o.created_at, o.updated_at, o.deleted_at,
           COUNT(*) OVER () AS total_count
    FROM orders o
    JOIN customers c ON c.id = o.customer_id
    JOIN employees e ON e.id = o.handled_by_id
    WHERE (p_include_deleted OR o.deleted_at IS NULL)
      AND (p_customer_id   IS NULL OR o.customer_id   = p_customer_id)
      AND (p_handled_by_id IS NULL OR o.handled_by_id = p_handled_by_id)
      AND (v_status        IS NULL OR o.status        = v_status)
      AND (p_date_from     IS NULL OR o.order_date   >= p_date_from)
      AND (p_date_to       IS NULL OR o.order_date   <= p_date_to)
      AND (p_search IS NULL OR p_search = ''
           OR o.order_number ILIKE '%' || p_search || '%'
           OR o.notes        ILIKE '%' || p_search || '%'
           OR c.name         ILIKE '%' || p_search || '%')
    ORDER BY o.order_date DESC, o.id DESC
    LIMIT p_limit OFFSET p_offset;
END;
$$;
"""

# Order matters: helpers first, then routines that call them.
UPGRADE_STATEMENTS = [
    FN_ORDER_STATUS,
    FN_ORDER_VALIDATE,
    SP_ORDER_CREATE,
    SP_ORDER_UPDATE,
    SP_ORDER_CHANGE_STATUS,
    SP_ORDER_SET_TOTAL,
    SP_ORDER_DELETE,
    SP_ORDER_RESTORE,
    FN_ORDER_GET,
    FN_ORDER_GET_BY_NUMBER,
    FN_ORDER_LIST,
]

DOWNGRADE_STATEMENTS = [
    "DROP FUNCTION IF EXISTS fn_order_list(TEXT, BIGINT, BIGINT, TEXT, DATE, DATE, BOOLEAN, INT, INT)",
    "DROP FUNCTION IF EXISTS fn_order_get_by_number(TEXT)",
    "DROP FUNCTION IF EXISTS fn_order_get(BIGINT, BOOLEAN)",
    "DROP PROCEDURE IF EXISTS sp_order_restore(BIGINT)",
    "DROP PROCEDURE IF EXISTS sp_order_delete(BIGINT)",
    "DROP PROCEDURE IF EXISTS sp_order_set_total(BIGINT, NUMERIC)",
    "DROP PROCEDURE IF EXISTS sp_order_change_status(BIGINT, TEXT)",
    "DROP PROCEDURE IF EXISTS sp_order_update(BIGINT, TEXT, BIGINT, BIGINT, DATE, NUMERIC, TEXT)",
    "DROP PROCEDURE IF EXISTS sp_order_create(BIGINT, TEXT, BIGINT, BIGINT, DATE, NUMERIC, TEXT, TEXT)",
    "DROP FUNCTION IF EXISTS fn_order_validate(BIGINT, TEXT, BIGINT, BIGINT, DATE, NUMERIC, TEXT)",
    "DROP FUNCTION IF EXISTS fn_order_status(TEXT)",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(sa.text(statement))


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(sa.text(statement))
