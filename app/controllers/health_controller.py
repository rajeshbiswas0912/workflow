from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from fastapi.responses import JSONResponse

from app.config.database import get_db

router = APIRouter(tags=["Health"])

@router.get("/health", summary="Liveness + database check")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={"success": False, "data": {}, "message": "Service unavailable"},
        )
    return {"success": True, "data": {"status": "healthy"}, "message": "Service is healthy"}
