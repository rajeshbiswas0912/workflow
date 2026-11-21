"""update products stored procedure

Revision ID: 3d7004698d9b
Revises: 142e9daa1466
Create Date: 2026-11-21 02:05:27.227145

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d7004698d9b'
down_revision: Union[str, Sequence[str], None] = '142e9daa1466'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FN_PRODUCT_SALES = r"""
CREATE OR REPLACE FUNCTION fn_product_sales(p_product_id BIGINT DEFAULT NULL)
RETURNS TABLE (product_id BIGINT, units_sold BIGINT, total_sales NUMERIC)
LANGUAGE sql STABLE
AS $$
    SELECT oi.product_id::BIGINT,
           COALESCE(SUM(oi.quantity), 0)::BIGINT,
           COALESCE(SUM(oi.quantity * oi.unit_price), 0)::NUMERIC
    FROM order_items oi
    JOIN orders o ON o.id = oi.order_id
    WHERE o.deleted_at IS NULL
      AND o.status::text <> 'cancelled'
      AND (p_product_id IS NULL OR oi.product_id = p_product_id)
    GROUP BY oi.product_id;
$$;
"""

# Reuses the spelling already in the catalogue ("seating" becomes "Seating")
FN_PRODUCT_CATEGORY_CANONICAL = r"""
CREATE OR REPLACE FUNCTION fn_product_category_canonical(p_category TEXT)
RETURNS TEXT
LANGUAGE sql STABLE
AS $$
    SELECT COALESCE(
        (SELECT p.category FROM products p
          WHERE lower(p.category) = lower(btrim(p_category))
          ORDER BY p.id LIMIT 1),
        NULLIF(btrim(p_category), '')
    );
$$;
"""

FN_PRODUCT_VALIDATE = r"""
CREATE OR REPLACE FUNCTION fn_product_validate(
    p_product_id     BIGINT,    -- NULL on create
    p_name           TEXT,
    p_sku            TEXT,      -- already upper-cased/trimmed
    p_category       TEXT,      -- already trimmed / canonical spelling
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

    IF p_sku IS NULL THEN
        RAISE EXCEPTION 'sku is required' USING ERRCODE = 'EV001';
    END IF;
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

    IF p_category IS NULL THEN
        RAISE EXCEPTION 'category is required' USING ERRCODE = 'EV001';
    END IF;
    IF char_length(p_category) > 100 THEN
        RAISE EXCEPTION 'category must be at most 100 characters' USING ERRCODE = 'EV001';
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
    IN    p_category       TEXT,
    IN    p_description    TEXT,
    IN    p_unit_price     NUMERIC,
    IN    p_stock_quantity INT,
    IN    p_is_active      BOOLEAN
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_sku      TEXT := NULLIF(upper(btrim(p_sku)), '');
    v_category TEXT := fn_product_category_canonical(p_category);
BEGIN
    IF p_stock_quantity IS NULL THEN
        RAISE EXCEPTION 'stock_quantity is required' USING ERRCODE = 'EV001';
    END IF;
    IF p_is_active IS NULL THEN
        RAISE EXCEPTION 'is_active is required' USING ERRCODE = 'EV001';
    END IF;

    PERFORM fn_product_validate(NULL, p_name, v_sku, v_category, p_description, p_unit_price, p_stock_quantity);

    INSERT INTO products (name, sku, category, description, unit_price, stock_quantity, is_active)
    VALUES (btrim(p_name), v_sku, v_category, NULLIF(btrim(p_description), ''),
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
    IN p_category    TEXT,
    IN p_description TEXT,
    IN p_unit_price  NUMERIC,
    IN p_is_active   BOOLEAN
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_sku      TEXT := NULLIF(upper(btrim(p_sku)), '');
    v_category TEXT := fn_product_category_canonical(p_category);
BEGIN
    IF p_is_active IS NULL THEN
        RAISE EXCEPTION 'is_active is required' USING ERRCODE = 'EV001';
    END IF;

    PERFORM 1 FROM products WHERE id = p_id AND deleted_at IS NULL FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'product % not found', p_id USING ERRCODE = 'EV002';
    END IF;

    PERFORM fn_product_validate(p_id, p_name, v_sku, v_category, p_description, p_unit_price, NULL);

    UPDATE products SET
        name        = btrim(p_name),
        sku         = v_sku,
        category    = v_category,
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

FN_PRODUCT_GET = r"""
CREATE OR REPLACE FUNCTION fn_product_get(p_id BIGINT, p_include_deleted BOOLEAN DEFAULT FALSE)
RETURNS TABLE (
    id BIGINT, name VARCHAR, sku VARCHAR, category VARCHAR, description TEXT, unit_price NUMERIC,
    stock_quantity INT, is_active BOOLEAN, units_sold BIGINT, total_sales NUMERIC,
    created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ
)
LANGUAGE sql STABLE
AS $$
    SELECT p.id, p.name, p.sku, p.category, p.description, p.unit_price,
           p.stock_quantity, p.is_active,
           COALESCE(s.units_sold, 0)::BIGINT, COALESCE(s.total_sales, 0)::NUMERIC,
           p.created_at, p.updated_at, p.deleted_at
    FROM products p
    LEFT JOIN LATERAL fn_product_sales(p.id) s ON TRUE
    WHERE p.id = p_id AND (p_include_deleted OR p.deleted_at IS NULL);
$$;
"""

FN_PRODUCT_GET_BY_SKU = r"""
CREATE OR REPLACE FUNCTION fn_product_get_by_sku(p_sku TEXT)
RETURNS TABLE (
    id BIGINT, name VARCHAR, sku VARCHAR, category VARCHAR, description TEXT, unit_price NUMERIC,
    stock_quantity INT, is_active BOOLEAN, units_sold BIGINT, total_sales NUMERIC,
    created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ
)
LANGUAGE sql STABLE
AS $$
    SELECT p.id, p.name, p.sku, p.category, p.description, p.unit_price,
           p.stock_quantity, p.is_active,
           COALESCE(s.units_sold, 0)::BIGINT, COALESCE(s.total_sales, 0)::NUMERIC,
           p.created_at, p.updated_at, p.deleted_at
    FROM products p
    LEFT JOIN LATERAL fn_product_sales(p.id) s ON TRUE
    WHERE p.sku = upper(btrim(p_sku)) AND p.deleted_at IS NULL;
$$;
"""

FN_PRODUCT_LIST = r"""
CREATE OR REPLACE FUNCTION fn_product_list(
    p_search          TEXT    DEFAULT NULL,
    p_category        TEXT    DEFAULT NULL,
    p_is_active       BOOLEAN DEFAULT NULL,
    p_min_price       NUMERIC DEFAULT NULL,
    p_max_price       NUMERIC DEFAULT NULL,
    p_in_stock_only   BOOLEAN DEFAULT FALSE,
    p_include_deleted BOOLEAN DEFAULT FALSE,
    p_limit           INT     DEFAULT 50,
    p_offset          INT     DEFAULT 0
)
RETURNS TABLE (
    id BIGINT, name VARCHAR, sku VARCHAR, category VARCHAR, description TEXT, unit_price NUMERIC,
    stock_quantity INT, is_active BOOLEAN, units_sold BIGINT, total_sales NUMERIC,
    created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ,
    total_count BIGINT
)
LANGUAGE plpgsql STABLE
AS $$
DECLARE
    v_search   TEXT := NULLIF(btrim(p_search), '');
    v_category TEXT := NULLIF(btrim(p_category), '');
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
    SELECT p.id, p.name, p.sku, p.category, p.description, p.unit_price,
           p.stock_quantity, p.is_active,
           COALESCE(s.units_sold, 0)::BIGINT, COALESCE(s.total_sales, 0)::NUMERIC,
           p.created_at, p.updated_at, p.deleted_at,
           COUNT(*) OVER ()
    FROM products p
    LEFT JOIN fn_product_sales() s ON s.product_id = p.id
    WHERE (p_include_deleted OR p.deleted_at IS NULL)
      AND (v_category IS NULL OR lower(p.category) = lower(v_category))
      AND (p_is_active IS NULL OR p.is_active = p_is_active)
      AND (p_min_price IS NULL OR p.unit_price >= p_min_price)
      AND (p_max_price IS NULL OR p.unit_price <= p_max_price)
      AND (NOT COALESCE(p_in_stock_only, FALSE) OR p.stock_quantity > 0)
      AND (v_search IS NULL
           OR p.name        ILIKE '%' || v_search || '%'
           OR p.sku         ILIKE '%' || v_search || '%'
           OR p.description ILIKE '%' || v_search || '%')
    ORDER BY p.id
    LIMIT p_limit OFFSET p_offset;
END;
$$;
"""

FN_PRODUCT_SUMMARY = r"""
CREATE OR REPLACE FUNCTION fn_product_summary(p_low_stock_threshold INT DEFAULT 10)
RETURNS TABLE (
    total_count BIGINT, active_count BIGINT, discontinued_count BIGINT,
    low_stock_count BIGINT, stock_value NUMERIC,
    best_seller_id BIGINT, best_seller_name VARCHAR,
    best_seller_units BIGINT, best_seller_sales NUMERIC
)
LANGUAGE plpgsql STABLE
AS $$
BEGIN
    IF p_low_stock_threshold IS NULL OR p_low_stock_threshold < 1
       OR p_low_stock_threshold > 1000000 THEN
        RAISE EXCEPTION 'low stock threshold must be between 1 and 1000000' USING ERRCODE = 'EV001';
    END IF;

    RETURN QUERY
    WITH stats AS (
        SELECT COUNT(*) AS c_total,
               COUNT(*) FILTER (WHERE p.is_active) AS c_active,
               COUNT(*) FILTER (WHERE NOT p.is_active) AS c_disc,
               COUNT(*) FILTER (WHERE p.is_active AND p.stock_quantity < p_low_stock_threshold) AS c_low,
               COALESCE(SUM(p.unit_price * p.stock_quantity) FILTER (WHERE p.is_active), 0) AS c_value
        FROM products p
        WHERE p.deleted_at IS NULL
    ), best AS (
        SELECT p.id AS b_id, p.name AS b_name, s.units_sold AS b_units, s.total_sales AS b_sales
        FROM products p
        JOIN fn_product_sales() s ON s.product_id = p.id
        WHERE p.deleted_at IS NULL AND s.total_sales > 0
        ORDER BY s.total_sales DESC, p.id
        LIMIT 1
    )
    SELECT st.c_total, st.c_active, st.c_disc, st.c_low, st.c_value::NUMERIC,
           b.b_id::BIGINT, b.b_name, b.b_units, b.b_sales
    FROM stats st
    LEFT JOIN best b ON TRUE;
END;
$$;
"""

# Options for the Category dropdown and filter
FN_PRODUCT_CATEGORIES = r"""
CREATE OR REPLACE FUNCTION fn_product_categories()
RETURNS TABLE (category VARCHAR, product_count BIGINT)
LANGUAGE sql STABLE
AS $$
    SELECT p.category, COUNT(*)::BIGINT
    FROM products p
    WHERE p.deleted_at IS NULL AND p.category IS NOT NULL
    GROUP BY p.category
    ORDER BY p.category;
$$;
"""

OLD_SIGNATURES = [
    "DROP FUNCTION IF EXISTS fn_product_summary(INT)",
    "DROP FUNCTION IF EXISTS fn_product_list(TEXT, BOOLEAN, NUMERIC, NUMERIC, BOOLEAN, BOOLEAN, INT, INT)",
    "DROP FUNCTION IF EXISTS fn_product_get_by_sku(TEXT)",
    "DROP FUNCTION IF EXISTS fn_product_get(BIGINT, BOOLEAN)",
    "DROP PROCEDURE IF EXISTS sp_product_update(BIGINT, TEXT, TEXT, TEXT, NUMERIC, BOOLEAN)",
    "DROP PROCEDURE IF EXISTS sp_product_create(BIGINT, TEXT, TEXT, TEXT, NUMERIC, INT, BOOLEAN)",
    "DROP FUNCTION IF EXISTS fn_product_validate(BIGINT, TEXT, TEXT, TEXT, NUMERIC, INT)",
]

# Order matters: helpers first, then the routines that call them.
UPGRADE_STATEMENTS = [
    FN_PRODUCT_SALES,
    FN_PRODUCT_CATEGORY_CANONICAL,
    FN_PRODUCT_VALIDATE,
    SP_PRODUCT_CREATE,
    SP_PRODUCT_UPDATE,
    FN_PRODUCT_GET,
    FN_PRODUCT_GET_BY_SKU,
    FN_PRODUCT_LIST,
    FN_PRODUCT_SUMMARY,
    FN_PRODUCT_CATEGORIES,
]

NEW_SIGNATURES = [
    "DROP FUNCTION IF EXISTS fn_product_categories()",
    "DROP FUNCTION IF EXISTS fn_product_summary(INT)",
    "DROP FUNCTION IF EXISTS fn_product_list(TEXT, TEXT, BOOLEAN, NUMERIC, NUMERIC, BOOLEAN, BOOLEAN, INT, INT)",
    "DROP FUNCTION IF EXISTS fn_product_get_by_sku(TEXT)",
    "DROP FUNCTION IF EXISTS fn_product_get(BIGINT, BOOLEAN)",
    "DROP PROCEDURE IF EXISTS sp_product_update(BIGINT, TEXT, TEXT, TEXT, TEXT, NUMERIC, BOOLEAN)",
    "DROP PROCEDURE IF EXISTS sp_product_create(BIGINT, TEXT, TEXT, TEXT, TEXT, NUMERIC, INT, BOOLEAN)",
    "DROP FUNCTION IF EXISTS fn_product_validate(BIGINT, TEXT, TEXT, TEXT, TEXT, NUMERIC, INT)",
    "DROP FUNCTION IF EXISTS fn_product_category_canonical(TEXT)",
    "DROP FUNCTION IF EXISTS fn_product_sales(BIGINT)",
]


def upgrade() -> None:
    for statement in OLD_SIGNATURES:
        op.execute(sa.text(statement))
    for statement in UPGRADE_STATEMENTS:
        op.execute(sa.text(statement))

def downgrade() -> None:
    for statement in NEW_SIGNATURES:
        op.execute(sa.text(statement))
