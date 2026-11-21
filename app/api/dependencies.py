from fastapi import Depends, Request

from decimal import Decimal

from app.services.control_service import ControlService
from app.services.controls import InvoiceChecker

from app.config import Settings, get_settings
from app.db.connection import Database
from app.services.documents import DocumentService
from app.services.extraction.pipeline import ExtractionPipeline
from app.services.extraction_service import ExtractionService
from app.services.ocr.base import OcrEngine
from app.services.ocr_service import OcrService
from app.services.storage import StorageService


def get_db(request: Request) -> Database:
    return request.app.state.db


def get_ocr_engine(request: Request) -> OcrEngine:
    return request.app.state.ocr_engine


def get_extraction_pipeline(request: Request) -> ExtractionPipeline:
    return request.app.state.extraction_pipeline


def get_storage_service(settings: Settings = Depends(get_settings)) -> StorageService:
    return StorageService(settings.storage_path, settings.max_upload_bytes)


def get_document_service(
    db: Database = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> DocumentService:
    return DocumentService(db, storage)


def get_ocr_service(
    db: Database = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
    engine: OcrEngine = Depends(get_ocr_engine),
) -> OcrService:
    return OcrService(db, storage, engine)


def get_extraction_service(
    db: Database = Depends(get_db),
    pipeline: ExtractionPipeline = Depends(get_extraction_pipeline),
) -> ExtractionService:
    return ExtractionService(db, pipeline)

def get_control_service(
    db: Database = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ControlService:
    checker = InvoiceChecker(
        settings.validation_threshold, Decimal(str(settings.amount_tolerance))
    )
    return ControlService(db, checker)