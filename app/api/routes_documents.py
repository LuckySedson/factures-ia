from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status

from app.api.dependencies import get_document_service
from app.api.schemas import ReceptionResponse
from app.config import Settings, get_settings
from app.services.documents import STATUT_RECU, DocumentService
from app.services.errors import FileTooLargeError, UnsupportedFileTypeError

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=ReceptionResponse)
def receive_document(
    response: Response,
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
    settings: Settings = Depends(get_settings),
) -> ReceptionResponse:
    content = file.file.read(settings.max_upload_bytes + 1)
    try:
        result = service.receive(content, file.filename or "")
    except FileTooLargeError as exc:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, str(exc)) from exc
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from exc

    if result.statut == STATUT_RECU:
        response.status_code = status.HTTP_201_CREATED
    return ReceptionResponse.model_validate(result)