"""add employee stored procedure

Revision ID: 088455b114d8
Revises: 01ce553c98f5
Create Date: 2026-11-18 18:28:21.460178

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '088455b114d8'
down_revision: Union[str, Sequence[str], None] = '01ce553c98f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FN_EMPLOYEE_STATUS = r"""
CREATE OR REPLACE FUNCTION fn_employee_status(p_status TEXT)
RETURNS employee_status_enum
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_status IS NULL OR btrim(p_status) = '' THEN
        RAISE EXCEPTION 'status is required' USING ERRCODE = 'EV001';
    END IF;
    RETURN btrim(p_status)::employee_status_enum;
EXCEPTION
    WHEN invalid_text_representation THEN
        RAISE EXCEPTION 'invalid status: %', p_status USING ERRCODE = 'EV001';
END;
$$;
"""

FN_EMPLOYEE_VALIDATE = r"""
CREATE OR REPLACE FUNCTION fn_employee_validate(
    p_employee_id    BIGINT,
    p_first_name     TEXT,
    p_last_name      TEXT,
    p_email          TEXT,
    p_phone          TEXT,
    p_department_id  BIGINT,
    p_job_title      TEXT,
    p_reports_to_id  BIGINT,
    p_hire_date      DATE,
    p_monthly_salary NUMERIC,
    p_role_id        BIGINT
) RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_first_name IS NULL OR btrim(p_first_name) = '' THEN
        RAISE EXCEPTION 'first_name is required' USING ERRCODE = 'EV001';
    END IF;
    IF char_length(btrim(p_first_name)) > 100 THEN
        RAISE EXCEPTION 'first_name must be at most 100 characters' USING ERRCODE = 'EV001';
    END IF;
    IF p_last_name IS NULL OR btrim(p_last_name) = '' THEN
        RAISE EXCEPTION 'last_name is required' USING ERRCODE = 'EV001';
    END IF;
    IF char_length(btrim(p_last_name)) > 100 THEN
        RAISE EXCEPTION 'last_name must be at most 100 characters' USING ERRCODE = 'EV001';
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

    IF p_job_title IS NULL OR btrim(p_job_title) = '' THEN
        RAISE EXCEPTION 'job_title is required' USING ERRCODE = 'EV001';
    END IF;
    IF char_length(btrim(p_job_title)) > 100 THEN
        RAISE EXCEPTION 'job_title must be at most 100 characters' USING ERRCODE = 'EV001';
    END IF;

    IF p_hire_date IS NULL THEN
        RAISE EXCEPTION 'hire_date is required' USING ERRCODE = 'EV001';
    END IF;
    IF p_hire_date > CURRENT_DATE THEN
        RAISE EXCEPTION 'hire_date cannot be in the future' USING ERRCODE = 'EV001';
    END IF;

    IF p_monthly_salary IS NULL THEN
        RAISE EXCEPTION 'monthly_salary is required' USING ERRCODE = 'EV001';
    END IF;
    IF p_monthly_salary < 0 OR p_monthly_salary >= 10000000000 THEN
        RAISE EXCEPTION 'monthly_salary is out of range' USING ERRCODE = 'EV001';
    END IF;

    IF p_department_id IS NULL
       OR NOT EXISTS (SELECT 1 FROM departments WHERE id = p_department_id) THEN
        RAISE EXCEPTION 'department % does not exist', p_department_id USING ERRCODE = 'EV001';
    END IF;
    IF p_role_id IS NULL
       OR NOT EXISTS (SELECT 1 FROM roles WHERE id = p_role_id) THEN
        RAISE EXCEPTION 'role % does not exist', p_role_id USING ERRCODE = 'EV001';
    END IF;

    IF p_reports_to_id IS NOT NULL THEN
        IF NOT EXISTS (SELECT 1 FROM employees
                       WHERE id = p_reports_to_id AND deleted_at IS NULL) THEN
            RAISE EXCEPTION 'manager % does not exist', p_reports_to_id USING ERRCODE = 'EV001';
        END IF;

        IF p_employee_id IS NOT NULL THEN
            IF p_reports_to_id = p_employee_id THEN
                RAISE EXCEPTION 'an employee cannot report to themselves' USING ERRCODE = 'EV001';
            END IF;
            IF EXISTS (
                WITH RECURSIVE chain AS (
                    SELECT id, reports_to_id FROM employees WHERE id = p_reports_to_id
                    UNION
                    SELECT e.id, e.reports_to_id
                    FROM employees e JOIN chain c ON e.id = c.reports_to_id
                )
                SELECT 1 FROM chain WHERE id = p_employee_id
            ) THEN
                RAISE EXCEPTION 'reporting line would create a cycle' USING ERRCODE = 'EV001';
            END IF;
        END IF;
    END IF;
END;
$$;
"""

SP_EMPLOYEE_CREATE = r"""
CREATE OR REPLACE PROCEDURE sp_employee_create(
    INOUT p_id                      BIGINT,
    IN    p_first_name              TEXT,
    IN    p_last_name               TEXT,
    IN    p_email                   TEXT,
    IN    p_phone                   TEXT,
    IN    p_status                  TEXT,
    IN    p_department_id           BIGINT,
    IN    p_job_title               TEXT,
    IN    p_reports_to_id           BIGINT,
    IN    p_hire_date               DATE,
    IN    p_monthly_salary          NUMERIC,
    IN    p_role_id                 BIGINT,
    IN    p_temporary_password_hash TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_email  TEXT := lower(btrim(p_email));
    v_status employee_status_enum := fn_employee_status(p_status);
BEGIN
    PERFORM fn_employee_validate(
        NULL, p_first_name, p_last_name, v_email, p_phone, p_department_id,
        p_job_title, p_reports_to_id, p_hire_date, p_monthly_salary, p_role_id
    );

    IF p_temporary_password_hash IS NULL OR btrim(p_temporary_password_hash) = '' THEN
        RAISE EXCEPTION 'temporary password hash is required' USING ERRCODE = 'EV001';
    END IF;

    IF EXISTS (SELECT 1 FROM employees WHERE email = v_email) THEN
        RAISE EXCEPTION 'email % is already in use', v_email USING ERRCODE = 'EV003';
    END IF;

    INSERT INTO employees (
        first_name, last_name, email, phone, status, department_id, job_title,
        reports_to_id, hire_date, monthly_salary, role_id,
        password, temporary_password, is_temporary_password
    ) VALUES (
        btrim(p_first_name), btrim(p_last_name), v_email,
        NULLIF(btrim(p_phone), ''), v_status, p_department_id, btrim(p_job_title),
        p_reports_to_id, p_hire_date, p_monthly_salary, p_role_id,
        NULL, p_temporary_password_hash, TRUE
    )
    RETURNING id INTO p_id;
EXCEPTION
    WHEN unique_violation THEN
        RAISE EXCEPTION 'email % is already in use', v_email USING ERRCODE = 'EV003';
END;
$$;
"""

SP_EMPLOYEE_UPDATE = r"""
CREATE OR REPLACE PROCEDURE sp_employee_update(
    IN p_id              BIGINT,
    IN p_first_name      TEXT,
    IN p_last_name       TEXT,
    IN p_email           TEXT,
    IN p_phone           TEXT,
    IN p_status          TEXT,
    IN p_department_id   BIGINT,
    IN p_job_title       TEXT,
    IN p_reports_to_id   BIGINT,
    IN p_hire_date       DATE,
    IN p_monthly_salary  NUMERIC,
    IN p_role_id         BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_email  TEXT := lower(btrim(p_email));
    v_status employee_status_enum := fn_employee_status(p_status);
BEGIN
    PERFORM 1 FROM employees WHERE id = p_id AND deleted_at IS NULL FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'employee % not found', p_id USING ERRCODE = 'EV002';
    END IF;

    PERFORM fn_employee_validate(
        p_id, p_first_name, p_last_name, v_email, p_phone, p_department_id,
        p_job_title, p_reports_to_id, p_hire_date, p_monthly_salary, p_role_id
    );

    IF EXISTS (SELECT 1 FROM employees WHERE email = v_email AND id <> p_id) THEN
        RAISE EXCEPTION 'email % is already in use', v_email USING ERRCODE = 'EV003';
    END IF;

    UPDATE employees SET
        first_name     = btrim(p_first_name),
        last_name      = btrim(p_last_name),
        email          = v_email,
        phone          = NULLIF(btrim(p_phone), ''),
        status         = v_status,
        department_id  = p_department_id,
        job_title      = btrim(p_job_title),
        reports_to_id  = p_reports_to_id,
        hire_date      = p_hire_date,
        monthly_salary = p_monthly_salary,
        role_id        = p_role_id,
        updated_at     = now()
    WHERE id = p_id;
EXCEPTION
    WHEN unique_violation THEN
        RAISE EXCEPTION 'email % is already in use', v_email USING ERRCODE = 'EV003';
END;
$$;
"""

SP_EMPLOYEE_CHANGE_STATUS = r"""
CREATE OR REPLACE PROCEDURE sp_employee_change_status(p_id BIGINT, p_status TEXT)
LANGUAGE plpgsql
AS $$
DECLARE
    v_status employee_status_enum := fn_employee_status(p_status);
BEGIN
    UPDATE employees SET status = v_status, updated_at = now()
    WHERE id = p_id AND deleted_at IS NULL;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'employee % not found', p_id USING ERRCODE = 'EV002';
    END IF;
END;
$$;
"""

SP_EMPLOYEE_DELETE = r"""
CREATE OR REPLACE PROCEDURE sp_employee_delete(p_id BIGINT)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM 1 FROM employees WHERE id = p_id AND deleted_at IS NULL FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'employee % not found', p_id USING ERRCODE = 'EV002';
    END IF;

    IF EXISTS (SELECT 1 FROM employees
               WHERE reports_to_id = p_id AND deleted_at IS NULL) THEN
        RAISE EXCEPTION 'employee % still has active subordinates; reassign them first', p_id
            USING ERRCODE = 'EV003';
    END IF;

    UPDATE employees SET deleted_at = now(), updated_at = now() WHERE id = p_id;
END;
$$;
"""

SP_EMPLOYEE_RESTORE = r"""
CREATE OR REPLACE PROCEDURE sp_employee_restore(p_id BIGINT)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE employees SET deleted_at = NULL, updated_at = now()
    WHERE id = p_id AND deleted_at IS NOT NULL;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'deleted employee % not found', p_id USING ERRCODE = 'EV002';
    END IF;
END;
$$;
"""

SP_EMPLOYEE_SET_PASSWORD = r"""
CREATE OR REPLACE PROCEDURE sp_employee_set_password(p_id BIGINT, p_password_hash TEXT)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_password_hash IS NULL OR btrim(p_password_hash) = '' THEN
        RAISE EXCEPTION 'password hash is required' USING ERRCODE = 'EV001';
    END IF;
    UPDATE employees
    SET password = p_password_hash,
        temporary_password = NULL,
        is_temporary_password = FALSE,
        updated_at = now()
    WHERE id = p_id AND deleted_at IS NULL;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'employee % not found', p_id USING ERRCODE = 'EV002';
    END IF;
END;
$$;
"""

SP_EMPLOYEE_RESET_PASSWORD = r"""
CREATE OR REPLACE PROCEDURE sp_employee_reset_password(p_id BIGINT, p_temporary_password_hash TEXT)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_temporary_password_hash IS NULL OR btrim(p_temporary_password_hash) = '' THEN
        RAISE EXCEPTION 'temporary password hash is required' USING ERRCODE = 'EV001';
    END IF;
    UPDATE employees
    SET password = NULL,
        temporary_password = p_temporary_password_hash,
        is_temporary_password = TRUE,
        updated_at = now()
    WHERE id = p_id AND deleted_at IS NULL;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'employee % not found', p_id USING ERRCODE = 'EV002';
    END IF;
END;
$$;
"""

FN_EMPLOYEE_GET = r"""
CREATE OR REPLACE FUNCTION fn_employee_get(p_id BIGINT, p_include_deleted BOOLEAN DEFAULT FALSE)
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

FN_EMPLOYEE_LIST = r"""
CREATE OR REPLACE FUNCTION fn_employee_list(
    p_search          TEXT    DEFAULT NULL,
    p_department_id   BIGINT  DEFAULT NULL,
    p_role_id         BIGINT  DEFAULT NULL,
    p_status          TEXT    DEFAULT NULL,
    p_include_deleted BOOLEAN DEFAULT FALSE,
    p_limit           INT     DEFAULT 50,
    p_offset          INT     DEFAULT 0
)
RETURNS TABLE (
    id BIGINT, first_name VARCHAR, last_name VARCHAR, email VARCHAR, phone VARCHAR,
    status employee_status_enum, department_id BIGINT, job_title VARCHAR,
    reports_to_id BIGINT, hire_date DATE, monthly_salary NUMERIC, role_id BIGINT,
    is_temporary_password BOOLEAN, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ, total_count BIGINT
)
LANGUAGE plpgsql STABLE
AS $$
DECLARE
    v_status employee_status_enum := NULL;
BEGIN
    IF p_limit IS NULL OR p_limit < 1 OR p_limit > 200 THEN
        RAISE EXCEPTION 'limit must be between 1 and 200' USING ERRCODE = 'EV001';
    END IF;
    IF p_offset IS NULL OR p_offset < 0 THEN
        RAISE EXCEPTION 'offset must be >= 0' USING ERRCODE = 'EV001';
    END IF;
    IF p_status IS NOT NULL THEN
        v_status := fn_employee_status(p_status);
    END IF;

    RETURN QUERY
    SELECT e.id, e.first_name, e.last_name, e.email, e.phone, e.status,
           e.department_id::BIGINT, e.job_title, e.reports_to_id, e.hire_date,
           e.monthly_salary, e.role_id::BIGINT, e.is_temporary_password,
           e.created_at, e.updated_at, e.deleted_at,
           COUNT(*) OVER () AS total_count
    FROM employees e
    WHERE (p_include_deleted OR e.deleted_at IS NULL)
      AND (p_department_id IS NULL OR e.department_id = p_department_id)
      AND (p_role_id       IS NULL OR e.role_id       = p_role_id)
      AND (v_status        IS NULL OR e.status        = v_status)
      AND (p_search IS NULL OR p_search = ''
           OR e.first_name ILIKE '%' || p_search || '%'
           OR e.last_name  ILIKE '%' || p_search || '%'
           OR e.email      ILIKE '%' || p_search || '%')
    ORDER BY e.id
    LIMIT p_limit OFFSET p_offset;
END;
$$;
"""

FN_EMPLOYEE_GET_AUTH = r"""
CREATE OR REPLACE FUNCTION fn_employee_get_auth(p_email TEXT)
RETURNS TABLE (
    id BIGINT, email VARCHAR, status employee_status_enum, role_id BIGINT,
    password VARCHAR, temporary_password VARCHAR, is_temporary_password BOOLEAN
)
LANGUAGE sql STABLE
AS $$
    SELECT e.id, e.email, e.status, e.role_id::BIGINT,
           e.password, e.temporary_password, e.is_temporary_password
    FROM employees e
    WHERE e.email = lower(btrim(p_email)) AND e.deleted_at IS NULL;
$$;
"""

# Order matters: helpers first, then the routines that call them.
UPGRADE_STATEMENTS = [
    FN_EMPLOYEE_STATUS,
    FN_EMPLOYEE_VALIDATE,
    SP_EMPLOYEE_CREATE,
    SP_EMPLOYEE_UPDATE,
    SP_EMPLOYEE_CHANGE_STATUS,
    SP_EMPLOYEE_DELETE,
    SP_EMPLOYEE_RESTORE,
    SP_EMPLOYEE_SET_PASSWORD,
    SP_EMPLOYEE_RESET_PASSWORD,
    FN_EMPLOYEE_GET,
    FN_EMPLOYEE_LIST,
    FN_EMPLOYEE_GET_AUTH,
]

DOWNGRADE_STATEMENTS = [
    "DROP FUNCTION IF EXISTS fn_employee_get_auth(TEXT)",
    "DROP FUNCTION IF EXISTS fn_employee_list(TEXT, BIGINT, BIGINT, TEXT, BOOLEAN, INT, INT)",
    "DROP FUNCTION IF EXISTS fn_employee_get(BIGINT, BOOLEAN)",
    "DROP PROCEDURE IF EXISTS sp_employee_reset_password(BIGINT, TEXT)",
    "DROP PROCEDURE IF EXISTS sp_employee_set_password(BIGINT, TEXT)",
    "DROP PROCEDURE IF EXISTS sp_employee_restore(BIGINT)",
    "DROP PROCEDURE IF EXISTS sp_employee_delete(BIGINT)",
    "DROP PROCEDURE IF EXISTS sp_employee_change_status(BIGINT, TEXT)",
    "DROP PROCEDURE IF EXISTS sp_employee_update(BIGINT, TEXT, TEXT, TEXT, TEXT, TEXT, BIGINT, TEXT, BIGINT, DATE, NUMERIC, BIGINT)",
    "DROP PROCEDURE IF EXISTS sp_employee_create(BIGINT, TEXT, TEXT, TEXT, TEXT, TEXT, BIGINT, TEXT, BIGINT, DATE, NUMERIC, BIGINT, TEXT)",
    "DROP FUNCTION IF EXISTS fn_employee_validate(BIGINT, TEXT, TEXT, TEXT, TEXT, BIGINT, TEXT, BIGINT, DATE, NUMERIC, BIGINT)",
    "DROP FUNCTION IF EXISTS fn_employee_status(TEXT)",
]

def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(sa.text(statement))


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(sa.text(statement))
