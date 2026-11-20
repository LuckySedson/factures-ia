from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_ocr_service
from app.api.schemas import OcrResponse
from app.services.errors import DocumentNotFoundError, OcrError
from app.services.ocr_service import OcrService

router = APIRouter(prefix="/documents", tags=["ocr"])


@router.post("/{document_id}/ocr", response_model=OcrResponse)
def run_ocr(
    document_id: int,
    force: bool = False,
    service: OcrService = Depends(get_ocr_service),
) -> OcrResponse:
    try:
        outcome = service.run(document_id, force=force)
    except DocumentNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except OcrError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return OcrResponse.model_validate(outcome)