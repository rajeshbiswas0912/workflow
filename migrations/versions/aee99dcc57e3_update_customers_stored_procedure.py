"""update customers stored procedure

Revision ID: aee99dcc57e3
Revises: a88fb64da2d3
Create Date: 2026-11-21 01:26:46.763254

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aee99dcc57e3'
down_revision: Union[str, Sequence[str], None] = 'a88fb64da2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FN_CUSTOMER_GET = r"""
CREATE FUNCTION fn_customer_get(p_id BIGINT, p_include_deleted BOOLEAN DEFAULT FALSE)
RETURNS TABLE (
    id BIGINT, name VARCHAR, email VARCHAR, phone VARCHAR, city VARCHAR, address TEXT,
    order_count BIGINT, total_spent NUMERIC,
    created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ
)
LANGUAGE sql STABLE
AS $$
    SELECT c.id, c.name, c.email, c.phone, c.city, c.address,
           COALESCE(s.o_count, 0)::BIGINT,
           COALESCE(s.o_spent, 0)::NUMERIC,
           c.created_at, c.updated_at, c.deleted_at
    FROM customers c
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS o_count,
               SUM(o.total_amount) FILTER (WHERE o.status::text <> 'cancelled') AS o_spent
        FROM orders o
        WHERE o.customer_id = c.id AND o.deleted_at IS NULL
    ) s ON TRUE
    WHERE c.id = p_id AND (p_include_deleted OR c.deleted_at IS NULL);
$$;
"""

FN_CUSTOMER_GET_BY_EMAIL = r"""
CREATE FUNCTION fn_customer_get_by_email(p_email TEXT)
RETURNS TABLE (
    id BIGINT, name VARCHAR, email VARCHAR, phone VARCHAR, city VARCHAR, address TEXT,
    order_count BIGINT, total_spent NUMERIC,
    created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ
)
LANGUAGE sql STABLE
AS $$
    SELECT c.id, c.name, c.email, c.phone, c.city, c.address,
           COALESCE(s.o_count, 0)::BIGINT,
           COALESCE(s.o_spent, 0)::NUMERIC,
           c.created_at, c.updated_at, c.deleted_at
    FROM customers c
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS o_count,
               SUM(o.total_amount) FILTER (WHERE o.status::text <> 'cancelled') AS o_spent
        FROM orders o
        WHERE o.customer_id = c.id AND o.deleted_at IS NULL
    ) s ON TRUE
    WHERE c.email = lower(btrim(p_email)) AND c.deleted_at IS NULL;
$$;
"""

FN_CUSTOMER_LIST = r"""
CREATE FUNCTION fn_customer_list(
    p_search          TEXT    DEFAULT NULL,
    p_city            TEXT    DEFAULT NULL,
    p_include_deleted BOOLEAN DEFAULT FALSE,
    p_limit           INT     DEFAULT 50,
    p_offset          INT     DEFAULT 0
)
RETURNS TABLE (
    id BIGINT, name VARCHAR, email VARCHAR, phone VARCHAR, city VARCHAR, address TEXT,
    order_count BIGINT, total_spent NUMERIC,
    created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ,
    total_count BIGINT
)
LANGUAGE plpgsql STABLE
AS $$
DECLARE
    v_search TEXT := NULLIF(btrim(p_search), '');
BEGIN
    IF p_limit IS NULL OR p_limit < 1 OR p_limit > 200 THEN
        RAISE EXCEPTION 'limit must be between 1 and 200' USING ERRCODE = 'EV001';
    END IF;
    IF p_offset IS NULL OR p_offset < 0 THEN
        RAISE EXCEPTION 'offset must be >= 0' USING ERRCODE = 'EV001';
    END IF;

    RETURN QUERY
    SELECT c.id, c.name, c.email, c.phone, c.city, c.address,
           COALESCE(s.o_count, 0)::BIGINT,
           COALESCE(s.o_spent, 0)::NUMERIC,
           c.created_at, c.updated_at, c.deleted_at,
           COUNT(*) OVER ()
    FROM customers c
    LEFT JOIN LATERAL (
        SELECT COUNT(*) AS o_count,
               SUM(o.total_amount) FILTER (WHERE o.status::text <> 'cancelled') AS o_spent
        FROM orders o
        WHERE o.customer_id = c.id AND o.deleted_at IS NULL
    ) s ON TRUE
    WHERE (p_include_deleted OR c.deleted_at IS NULL)
      AND (p_city IS NULL OR p_city = '' OR lower(c.city) = lower(btrim(p_city)))
      AND (v_search IS NULL
           OR c.name  ILIKE '%' || v_search || '%'
           OR c.email ILIKE '%' || v_search || '%'
           OR c.phone ILIKE '%' || v_search || '%'
           OR c.city  ILIKE '%' || v_search || '%')
    ORDER BY c.id
    LIMIT p_limit OFFSET p_offset;
END;
$$;
"""

FN_CUSTOMER_LIST_OLD = r"""
CREATE OR REPLACE FUNCTION fn_customer_list(
    p_search          TEXT    DEFAULT NULL,
    p_city            TEXT    DEFAULT NULL,
    p_include_deleted BOOLEAN DEFAULT FALSE,
    p_limit           INT     DEFAULT 50,
    p_offset          INT     DEFAULT 0
)
RETURNS TABLE (
    id BIGINT, name VARCHAR, email VARCHAR, phone VARCHAR, city VARCHAR, address TEXT,
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

    RETURN QUERY
    SELECT c.id, c.name, c.email, c.phone, c.city, c.address,
           c.created_at, c.updated_at, c.deleted_at,
           COUNT(*) OVER () AS total_count
    FROM customers c
    WHERE (p_include_deleted OR c.deleted_at IS NULL)
      AND (p_city IS NULL OR p_city = '' OR lower(c.city) = lower(btrim(p_city)))
      AND (p_search IS NULL OR p_search = ''
           OR c.name  ILIKE '%' || p_search || '%'
           OR c.email ILIKE '%' || p_search || '%'
           OR c.phone ILIKE '%' || p_search || '%')
    ORDER BY c.id
    LIMIT p_limit OFFSET p_offset;
END;
$$;
"""

FN_CUSTOMER_GET_BY_EMAIL_OLD = r"""
CREATE OR REPLACE FUNCTION fn_customer_get_by_email(p_email TEXT)
RETURNS TABLE (
    id BIGINT, name VARCHAR, email VARCHAR, phone VARCHAR, city VARCHAR, address TEXT,
    created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ
)
LANGUAGE sql STABLE
AS $$
    SELECT c.id, c.name, c.email, c.phone, c.city, c.address,
           c.created_at, c.updated_at, c.deleted_at
    FROM customers c
    WHERE c.email = lower(btrim(p_email)) AND c.deleted_at IS NULL;
$$;
"""

FN_CUSTOMER_GET_OLD = r"""
CREATE OR REPLACE FUNCTION fn_customer_get(p_id BIGINT, p_include_deleted BOOLEAN DEFAULT FALSE)
RETURNS TABLE (
    id BIGINT, name VARCHAR, email VARCHAR, phone VARCHAR, city VARCHAR, address TEXT,
    created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ
)
LANGUAGE sql STABLE
AS $$
    SELECT c.id, c.name, c.email, c.phone, c.city, c.address,
           c.created_at, c.updated_at, c.deleted_at
    FROM customers c
    WHERE c.id = p_id AND (p_include_deleted OR c.deleted_at IS NULL);
$$;
"""

def upgrade() -> None:
    op.execute(sa.text("DROP FUNCTION IF EXISTS fn_customer_list(TEXT, TEXT, BOOLEAN, INT, INT)"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS fn_customer_get_by_email(TEXT)"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS fn_customer_get(BIGINT, BOOLEAN)"))
    op.execute(sa.text(FN_CUSTOMER_GET))
    op.execute(sa.text(FN_CUSTOMER_GET_BY_EMAIL))
    op.execute(sa.text(FN_CUSTOMER_LIST))


def downgrade() -> None:
    op.execute(sa.text("DROP FUNCTION IF EXISTS fn_customer_list(TEXT, TEXT, BOOLEAN, INT, INT)"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS fn_customer_get_by_email(TEXT)"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS fn_customer_get(BIGINT, BOOLEAN)"))
    op.execute(sa.text(FN_CUSTOMER_GET_OLD))
    op.execute(sa.text(FN_CUSTOMER_GET_BY_EMAIL_OLD))
    op.execute(sa.text(FN_CUSTOMER_LIST_OLD))
