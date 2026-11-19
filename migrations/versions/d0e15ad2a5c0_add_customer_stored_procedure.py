"""add customer stored procedure

Revision ID: d0e15ad2a5c0
Revises: da2a013cdf33
Create Date: 2026-11-19 00:51:12.898330

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0e15ad2a5c0'
down_revision: Union[str, Sequence[str], None] = 'da2a013cdf33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FN_CUSTOMER_VALIDATE = r"""
CREATE OR REPLACE FUNCTION fn_customer_validate(
    p_customer_id BIGINT,     -- NULL on create
    p_name        TEXT,
    p_email       TEXT,       -- already lower-cased and trimmed
    p_phone       TEXT,
    p_city        TEXT,
    p_address     TEXT
) RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_name IS NULL OR btrim(p_name) = '' THEN
        RAISE EXCEPTION 'name is required' USING ERRCODE = 'EV001';
    END IF;
    IF char_length(btrim(p_name)) > 100 THEN
        RAISE EXCEPTION 'name must be at most 100 characters' USING ERRCODE = 'EV001';
    END IF;

    IF p_email IS NULL OR btrim(p_email) = '' THEN
        RAISE EXCEPTION 'email is required' USING ERRCODE = 'EV001';
    END IF;
    IF char_length(btrim(p_email)) > 255
       OR btrim(p_email) !~ '^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$' THEN
        RAISE EXCEPTION 'email is not valid' USING ERRCODE = 'EV001';
    END IF;

    IF p_phone IS NOT NULL AND btrim(p_phone) <> '' THEN
        IF char_length(btrim(p_phone)) > 20
           OR btrim(p_phone) !~ '^\+?[0-9][0-9 ()\-]{6,18}$' THEN
            RAISE EXCEPTION 'phone is not valid' USING ERRCODE = 'EV001';
        END IF;
    END IF;

    IF p_city IS NOT NULL AND char_length(btrim(p_city)) > 100 THEN
        RAISE EXCEPTION 'city must be at most 100 characters' USING ERRCODE = 'EV001';
    END IF;

    IF p_address IS NOT NULL AND char_length(p_address) > 2000 THEN
        RAISE EXCEPTION 'address must be at most 2000 characters' USING ERRCODE = 'EV001';
    END IF;

    -- email is unique across ALL rows (including soft-deleted ones)
    IF EXISTS (
        SELECT 1 FROM customers c
        WHERE c.email = btrim(p_email)
          AND (p_customer_id IS NULL OR c.id <> p_customer_id)
    ) THEN
        RAISE EXCEPTION 'email % is already in use', btrim(p_email) USING ERRCODE = 'EV003';
    END IF;
END;
$$;
"""

SP_CUSTOMER_CREATE = r"""
CREATE OR REPLACE PROCEDURE sp_customer_create(
    INOUT p_id      BIGINT,
    IN    p_name    TEXT,
    IN    p_email   TEXT,
    IN    p_phone   TEXT,
    IN    p_city    TEXT,
    IN    p_address TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_email TEXT := lower(btrim(p_email));
BEGIN
    PERFORM fn_customer_validate(NULL, p_name, v_email, p_phone, p_city, p_address);

    INSERT INTO customers (name, email, phone, city, address)
    VALUES (
        btrim(p_name), v_email, NULLIF(btrim(p_phone), ''),
        NULLIF(btrim(p_city), ''), NULLIF(btrim(p_address), '')
    )
    RETURNING id INTO p_id;
EXCEPTION
    WHEN unique_violation THEN
        RAISE EXCEPTION 'email % is already in use', v_email USING ERRCODE = 'EV003';
END;
$$;
"""

SP_CUSTOMER_UPDATE = r"""
CREATE OR REPLACE PROCEDURE sp_customer_update(
    IN p_id      BIGINT,
    IN p_name    TEXT,
    IN p_email   TEXT,
    IN p_phone   TEXT,
    IN p_city    TEXT,
    IN p_address TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_email TEXT := lower(btrim(p_email));
BEGIN
    PERFORM 1 FROM customers WHERE id = p_id AND deleted_at IS NULL FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'customer % not found', p_id USING ERRCODE = 'EV002';
    END IF;

    PERFORM fn_customer_validate(p_id, p_name, v_email, p_phone, p_city, p_address);

    UPDATE customers SET
        name       = btrim(p_name),
        email      = v_email,
        phone      = NULLIF(btrim(p_phone), ''),
        city       = NULLIF(btrim(p_city), ''),
        address    = NULLIF(btrim(p_address), ''),
        updated_at = now()
    WHERE id = p_id;
EXCEPTION
    WHEN unique_violation THEN
        RAISE EXCEPTION 'email % is already in use', v_email USING ERRCODE = 'EV003';
END;
$$;
"""

SP_CUSTOMER_DELETE = r"""
CREATE OR REPLACE PROCEDURE sp_customer_delete(p_id BIGINT)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE customers SET deleted_at = now(), updated_at = now()
    WHERE id = p_id AND deleted_at IS NULL;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'customer % not found', p_id USING ERRCODE = 'EV002';
    END IF;
END;
$$;
"""

SP_CUSTOMER_RESTORE = r"""
CREATE OR REPLACE PROCEDURE sp_customer_restore(p_id BIGINT)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE customers SET deleted_at = NULL, updated_at = now()
    WHERE id = p_id AND deleted_at IS NOT NULL;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'deleted customer % not found', p_id USING ERRCODE = 'EV002';
    END IF;
END;
$$;
"""

FN_CUSTOMER_GET = r"""
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

FN_CUSTOMER_GET_BY_EMAIL = r"""
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

FN_CUSTOMER_LIST = r"""
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

# Order matters: the validate helper first, then routines that call it.
UPGRADE_STATEMENTS = [
    FN_CUSTOMER_VALIDATE,
    SP_CUSTOMER_CREATE,
    SP_CUSTOMER_UPDATE,
    SP_CUSTOMER_DELETE,
    SP_CUSTOMER_RESTORE,
    FN_CUSTOMER_GET,
    FN_CUSTOMER_GET_BY_EMAIL,
    FN_CUSTOMER_LIST,
]

DOWNGRADE_STATEMENTS = [
    "DROP FUNCTION IF EXISTS fn_customer_list(TEXT, TEXT, BOOLEAN, INT, INT)",
    "DROP FUNCTION IF EXISTS fn_customer_get_by_email(TEXT)",
    "DROP FUNCTION IF EXISTS fn_customer_get(BIGINT, BOOLEAN)",
    "DROP PROCEDURE IF EXISTS sp_customer_restore(BIGINT)",
    "DROP PROCEDURE IF EXISTS sp_customer_delete(BIGINT)",
    "DROP PROCEDURE IF EXISTS sp_customer_update(BIGINT, TEXT, TEXT, TEXT, TEXT, TEXT)",
    "DROP PROCEDURE IF EXISTS sp_customer_create(BIGINT, TEXT, TEXT, TEXT, TEXT, TEXT)",
    "DROP FUNCTION IF EXISTS fn_customer_validate(BIGINT, TEXT, TEXT, TEXT, TEXT, TEXT)",
]


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(sa.text(statement))


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(sa.text(statement))
