"""add product stored procedure

Revision ID: 55cee651257f
Revises: 1606a6b20f73
Create Date: 2026-11-19 01:11:14.717417

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '55cee651257f'
down_revision: Union[str, Sequence[str], None] = '1606a6b20f73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FN_PRODUCT_VALIDATE = r"""
CREATE OR REPLACE FUNCTION fn_product_validate(
    p_product_id     BIGINT,    -- NULL on create
    p_name           TEXT,
    p_sku            TEXT,      -- already upper-cased/trimmed, NULL when not provided
    p_description    TEXT,
    p_unit_price     NUMERIC,
    p_stock_quantity INT        -- NULL = not being changed, skip the check
) RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_name IS NULL OR btrim(p_name) = '' THEN
        RAISE EXCEPTION 'name is required' USING ERRCODE = 'EV001';
    END IF;
    IF char_length(btrim(p_name)) > 150 THEN
        RAISE EXCEPTION 'name must be at most 150 characters' USING ERRCODE = 'EV001';
    END IF;

    IF p_sku IS NOT NULL THEN
        IF char_length(p_sku) > 100 OR p_sku !~ '^[A-Za-z0-9][A-Za-z0-9\-_./]*$' THEN
            RAISE EXCEPTION 'sku is not valid (letters, digits, - _ . / only, max 100)'
                USING ERRCODE = 'EV001';
        END IF;
        -- unique across ALL rows (including soft-deleted ones)
        IF EXISTS (
            SELECT 1 FROM products p
            WHERE p.sku = p_sku
              AND (p_product_id IS NULL OR p.id <> p_product_id)
        ) THEN
            RAISE EXCEPTION 'sku % is already in use', p_sku USING ERRCODE = 'EV003';
        END IF;
    END IF;

    IF p_description IS NOT NULL AND char_length(p_description) > 5000 THEN
        RAISE EXCEPTION 'description must be at most 5000 characters' USING ERRCODE = 'EV001';
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

    IF p_stock_quantity IS NOT NULL
       AND (p_stock_quantity < 0 OR p_stock_quantity > 1000000000) THEN
        RAISE EXCEPTION 'stock_quantity must be between 0 and 1000000000' USING ERRCODE = 'EV001';
    END IF;
END;
$$;
"""

SP_PRODUCT_CREATE = r"""
CREATE OR REPLACE PROCEDURE sp_product_create(
    INOUT p_id             BIGINT,
    IN    p_name           TEXT,
    IN    p_sku            TEXT,
    IN    p_description    TEXT,
    IN    p_unit_price     NUMERIC,
    IN    p_stock_quantity INT,
    IN    p_is_active      BOOLEAN
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_sku TEXT := NULLIF(upper(btrim(p_sku)), '');
BEGIN
    IF p_stock_quantity IS NULL THEN
        RAISE EXCEPTION 'stock_quantity is required' USING ERRCODE = 'EV001';
    END IF;
    IF p_is_active IS NULL THEN
        RAISE EXCEPTION 'is_active is required' USING ERRCODE = 'EV001';
    END IF;

    PERFORM fn_product_validate(NULL, p_name, v_sku, p_description, p_unit_price, p_stock_quantity);

    INSERT INTO products (name, sku, description, unit_price, stock_quantity, is_active)
    VALUES (btrim(p_name), v_sku, NULLIF(btrim(p_description), ''),
            p_unit_price, p_stock_quantity, p_is_active)
    RETURNING id INTO p_id;
EXCEPTION
    WHEN unique_violation THEN
        RAISE EXCEPTION 'sku % is already in use', v_sku USING ERRCODE = 'EV003';
END;
$$;
"""

SP_PRODUCT_UPDATE = r"""
CREATE OR REPLACE PROCEDURE sp_product_update(
    IN p_id          BIGINT,
    IN p_name        TEXT,
    IN p_sku         TEXT,
    IN p_description TEXT,
    IN p_unit_price  NUMERIC,
    IN p_is_active   BOOLEAN
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_sku TEXT := NULLIF(upper(btrim(p_sku)), '');
BEGIN
    IF p_is_active IS NULL THEN
        RAISE EXCEPTION 'is_active is required' USING ERRCODE = 'EV001';
    END IF;

    PERFORM 1 FROM products WHERE id = p_id AND deleted_at IS NULL FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'product % not found', p_id USING ERRCODE = 'EV002';
    END IF;

    PERFORM fn_product_validate(p_id, p_name, v_sku, p_description, p_unit_price, NULL);

    UPDATE products SET
        name        = btrim(p_name),
        sku         = v_sku,
        description = NULLIF(btrim(p_description), ''),
        unit_price  = p_unit_price,
        is_active   = p_is_active,
        updated_at  = now()
    WHERE id = p_id;
EXCEPTION
    WHEN unique_violation THEN
        RAISE EXCEPTION 'sku % is already in use', v_sku USING ERRCODE = 'EV003';
END;
$$;
"""

SP_PRODUCT_SET_ACTIVE = r"""
CREATE OR REPLACE PROCEDURE sp_product_set_active(p_id BIGINT, p_is_active BOOLEAN)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_is_active IS NULL THEN
        RAISE EXCEPTION 'is_active is required' USING ERRCODE = 'EV001';
    END IF;
    UPDATE products SET is_active = p_is_active, updated_at = now()
    WHERE id = p_id AND deleted_at IS NULL;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'product % not found', p_id USING ERRCODE = 'EV002';
    END IF;
END;
$$;
"""

SP_PRODUCT_SET_STOCK = r"""
CREATE OR REPLACE PROCEDURE sp_product_set_stock(p_id BIGINT, p_stock_quantity INT)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_stock_quantity IS NULL OR p_stock_quantity < 0 OR p_stock_quantity > 1000000000 THEN
        RAISE EXCEPTION 'stock_quantity must be between 0 and 1000000000' USING ERRCODE = 'EV001';
    END IF;
    UPDATE products SET stock_quantity = p_stock_quantity, updated_at = now()
    WHERE id = p_id AND deleted_at IS NULL;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'product % not found', p_id USING ERRCODE = 'EV002';
    END IF;
END;
$$;
"""

SP_PRODUCT_ADJUST_STOCK = r"""
CREATE OR REPLACE PROCEDURE sp_product_adjust_stock(p_id BIGINT, p_delta INT)
LANGUAGE plpgsql
AS $$
DECLARE
    v_current INT;
    v_new     BIGINT;
BEGIN
    IF p_delta IS NULL OR p_delta = 0 THEN
        RAISE EXCEPTION 'delta must be a non-zero number' USING ERRCODE = 'EV001';
    END IF;
    IF abs(p_delta) > 1000000000 THEN
        RAISE EXCEPTION 'delta is out of range' USING ERRCODE = 'EV001';
    END IF;

    SELECT p.stock_quantity INTO v_current
    FROM products p WHERE p.id = p_id AND p.deleted_at IS NULL FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'product % not found', p_id USING ERRCODE = 'EV002';
    END IF;

    v_new := v_current::BIGINT + p_delta;
    IF v_new < 0 THEN
        RAISE EXCEPTION 'insufficient stock for product %: have %, requested %',
            p_id, v_current, abs(p_delta) USING ERRCODE = 'EV003';
    END IF;
    IF v_new > 1000000000 THEN
        RAISE EXCEPTION 'stock_quantity would exceed 1000000000' USING ERRCODE = 'EV001';
    END IF;

    UPDATE products SET stock_quantity = v_new::INT, updated_at = now() WHERE id = p_id;
END;
$$;
"""

SP_PRODUCT_DELETE = r"""
CREATE OR REPLACE PROCEDURE sp_product_delete(p_id BIGINT)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE products SET deleted_at = now(), updated_at = now()
    WHERE id = p_id AND deleted_at IS NULL;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'product % not found', p_id USING ERRCODE = 'EV002';
    END IF;
END;
$$;
"""

SP_PRODUCT_RESTORE = r"""
CREATE OR REPLACE PROCEDURE sp_product_restore(p_id BIGINT)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE products SET deleted_at = NULL, updated_at = now()
    WHERE id = p_id AND deleted_at IS NOT NULL;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'deleted product % not found', p_id USING ERRCODE = 'EV002';
    END IF;
END;
$$;
"""

FN_PRODUCT_GET = r"""
CREATE OR REPLACE FUNCTION fn_product_get(p_id BIGINT, p_include_deleted BOOLEAN DEFAULT FALSE)
RETURNS TABLE (
    id BIGINT, name VARCHAR, sku VARCHAR, description TEXT, unit_price NUMERIC,
    stock_quantity INT, is_active BOOLEAN,
    created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ
)
LANGUAGE sql STABLE
AS $$
    SELECT p.id, p.name, p.sku, p.description, p.unit_price,
           p.stock_quantity, p.is_active, p.created_at, p.updated_at, p.deleted_at
    FROM products p
    WHERE p.id = p_id AND (p_include_deleted OR p.deleted_at IS NULL);
$$;
"""

FN_PRODUCT_GET_BY_SKU = r"""
CREATE OR REPLACE FUNCTION fn_product_get_by_sku(p_sku TEXT)
RETURNS TABLE (
    id BIGINT, name VARCHAR, sku VARCHAR, description TEXT, unit_price NUMERIC,
    stock_quantity INT, is_active BOOLEAN,
    created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ
)
LANGUAGE sql STABLE
AS $$
    SELECT p.id, p.name, p.sku, p.description, p.unit_price,
           p.stock_quantity, p.is_active, p.created_at, p.updated_at, p.deleted_at
    FROM products p
    WHERE p.sku = upper(btrim(p_sku)) AND p.deleted_at IS NULL;
$$;
"""

FN_PRODUCT_LIST = r"""
CREATE OR REPLACE FUNCTION fn_product_list(
    p_search          TEXT    DEFAULT NULL,
    p_is_active       BOOLEAN DEFAULT NULL,
    p_min_price       NUMERIC DEFAULT NULL,
    p_max_price       NUMERIC DEFAULT NULL,
    p_in_stock_only   BOOLEAN DEFAULT FALSE,
    p_include_deleted BOOLEAN DEFAULT FALSE,
    p_limit           INT     DEFAULT 50,
    p_offset          INT     DEFAULT 0
)
RETURNS TABLE (
    id BIGINT, name VARCHAR, sku VARCHAR, description TEXT, unit_price NUMERIC,
    stock_quantity INT, is_active BOOLEAN,
    created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ,
    total_count BIGINT
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
    IF (p_min_price IS NOT NULL AND p_min_price < 0)
       OR (p_max_price IS NOT NULL AND p_max_price < 0) THEN
        RAISE EXCEPTION 'prices cannot be negative' USING ERRCODE = 'EV001';
    END IF;
    IF p_min_price IS NOT NULL AND p_max_price IS NOT NULL AND p_min_price > p_max_price THEN
        RAISE EXCEPTION 'min_price cannot be greater than max_price' USING ERRCODE = 'EV001';
    END IF;

    RETURN QUERY
    SELECT p.id, p.name, p.sku, p.description, p.unit_price,
           p.stock_quantity, p.is_active, p.created_at, p.updated_at, p.deleted_at,
           COUNT(*) OVER () AS total_count
    FROM products p
    WHERE (p_include_deleted OR p.deleted_at IS NULL)
      AND (p_is_active IS NULL OR p.is_active = p_is_active)
      AND (p_min_price IS NULL OR p.unit_price >= p_min_price)
      AND (p_max_price IS NULL OR p.unit_price <= p_max_price)
      AND (NOT COALESCE(p_in_stock_only, FALSE) OR p.stock_quantity > 0)
      AND (p_search IS NULL OR p_search = ''
           OR p.name        ILIKE '%' || p_search || '%'
           OR p.sku         ILIKE '%' || p_search || '%'
           OR p.description ILIKE '%' || p_search || '%')
    ORDER BY p.id
    LIMIT p_limit OFFSET p_offset;
END;
$$;
"""

# Order matters: the validate helper first, then routines that call it.
UPGRADE_STATEMENTS = [
    FN_PRODUCT_VALIDATE,
    SP_PRODUCT_CREATE,
    SP_PRODUCT_UPDATE,
    SP_PRODUCT_SET_ACTIVE,
    SP_PRODUCT_SET_STOCK,
    SP_PRODUCT_ADJUST_STOCK,
    SP_PRODUCT_DELETE,
    SP_PRODUCT_RESTORE,
    FN_PRODUCT_GET,
    FN_PRODUCT_GET_BY_SKU,
    FN_PRODUCT_LIST,
]

DOWNGRADE_STATEMENTS = [
    "DROP FUNCTION IF EXISTS fn_product_list(TEXT, BOOLEAN, NUMERIC, NUMERIC, BOOLEAN, BOOLEAN, INT, INT)",
    "DROP FUNCTION IF EXISTS fn_product_get_by_sku(TEXT)",
    "DROP FUNCTION IF EXISTS fn_product_get(BIGINT, BOOLEAN)",
    "DROP PROCEDURE IF EXISTS sp_product_restore(BIGINT)",
    "DROP PROCEDURE IF EXISTS sp_product_delete(BIGINT)",
    "DROP PROCEDURE IF EXISTS sp_product_adjust_stock(BIGINT, INT)",
    "DROP PROCEDURE IF EXISTS sp_product_set_stock(BIGINT, INT)",
    "DROP PROCEDURE IF EXISTS sp_product_set_active(BIGINT, BOOLEAN)",
    "DROP PROCEDURE IF EXISTS sp_product_update(BIGINT, TEXT, TEXT, TEXT, NUMERIC, BOOLEAN)",
    "DROP PROCEDURE IF EXISTS sp_product_create(BIGINT, TEXT, TEXT, TEXT, NUMERIC, INT, BOOLEAN)",
    "DROP FUNCTION IF EXISTS fn_product_validate(BIGINT, TEXT, TEXT, TEXT, NUMERIC, INT)",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(sa.text(statement))


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(sa.text(statement))
