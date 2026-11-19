from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.db.connection import Database
from app.services.documents import DocumentService
from app.services.storage import StorageService


def get_db(request: Request) -> Database:
    return request.app.state.db


def get_storage_service(settings: Settings = Depends(get_settings)) -> StorageService:
    return StorageService(settings.storage_path, settings.max_upload_bytes)


def get_document_service(
    db: Database = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> DocumentService:
    return DocumentService(db, storage)