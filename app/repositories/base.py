from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

Row = dict[str, Any]


def fetch_one(db: Session, sql: str, params: dict[str, Any] | None = None) -> Row | None:
    row = db.execute(text(sql), params or {}).mappings().first()
    return dict(row) if row is not None else None


def fetch_all(db: Session, sql: str, params: dict[str, Any] | None = None) -> list[Row]:
    result = db.execute(text(sql), params or {}).mappings().all()
    return [dict(row) for row in result]


def fetch_scalar(db: Session, sql: str, params: dict[str, Any] | None = None) -> Any:
    """Return the first column of the single row the procedure produced."""
    return db.execute(text(sql), params or {}).scalar_one()
