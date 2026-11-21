from contextlib import contextmanager

from sqlalchemy.exc import DBAPIError

from app.utils.exceptions import BadRequestError, ConflictError, NotFoundError


def _translate(e: DBAPIError) -> Exception:
    orig = e.orig
    code = getattr(orig, "sqlstate", None)
    msg = getattr(getattr(orig, "diag", None), "message_primary", None) or "Database error"
    if code in {"P0002", "EV002"}:
        return NotFoundError(msg)
    if code in {"23505", "EV003"}:
        return ConflictError(msg)
    if code in {"22023", "22004", "22001", "22P02", "EV001"}:
        return BadRequestError(msg)
    return e


@contextmanager
def db_errors(db):
    try:
        yield
    except DBAPIError as e:
        db.rollback()
        mapped = _translate(e)
        if mapped is e:
            raise
        raise mapped from e
