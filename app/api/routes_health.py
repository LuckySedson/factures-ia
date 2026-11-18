from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_db
from app.db.connection import Database

router = APIRouter(tags=["health"])


@router.get("/health")
def health(response: Response, db: Database = Depends(get_db)) -> dict:
    db_ok = db.ping()
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "api": "ok",
        "database": "ok" if db_ok else "indisponible",
    }