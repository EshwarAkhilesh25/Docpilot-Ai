import logging
import traceback
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi import status as http_status
from fastapi.responses import StreamingResponse

from app.api.dependencies import (
    get_current_user,
    get_job_dispatcher,
    get_keyword_index_provider,
    get_storage_provider,
    get_uow,
    get_vector_index_provider,
)
from app.db.unit_of_work import IUnitOfWork, UnitOfWorkFactory
from app.jobs.interfaces.job_dispatcher import JobDispatcher
from app.keyword_search.interfaces.keyword_index_provider import KeywordIndexProvider
from app.models.document import Document
from app.models.enums import FileType, ProcessingStatus
from app.models.processing_job import ProcessingJob
from app.models.user import User
from app.schemas.document import DocumentDetailsResponse, DocumentListResponse
from app.schemas.upload import UploadDocumentResponse
from app.services.document_download_service import DocumentDownloadServiceImpl
from app.services.document_service import DocumentServiceImpl
from app.services.processing_status_service import ProcessingStatusServiceImpl
from app.storage.interfaces.storage_provider import StorageProvider
from app.vectorstore.interfaces.vector_index_provider import VectorIndexProvider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# File upload configuration
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".mp3", ".wav", ".mp4", ".txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB in bytes

# Extension to FileType mapping
EXTENSION_TO_FILE_TYPE = {
    ".pdf": FileType.PDF,
    ".docx": FileType.DOCX,
    ".mp3": FileType.AUDIO,
    ".wav": FileType.AUDIO,
    ".mp4": FileType.VIDEO,
    ".txt": FileType.TXT,
}


def get_document_service(
    storage_provider: StorageProvider = Depends(get_storage_provider),
    vector_provider: VectorIndexProvider = Depends(get_vector_index_provider),
    keyword_index_provider: KeywordIndexProvider = Depends(get_keyword_index_provider),
) -> DocumentServiceImpl:
    """Dependency injection for document service."""
    return DocumentServiceImpl(
        uow_factory=UnitOfWorkFactory.create,
        storage_provider=storage_provider,
        vector_provider=vector_provider,
        keyword_index_provider=keyword_index_provider,
    )


def get_processing_status_service() -> ProcessingStatusServiceImpl:
    """Dependency injection for processing status service."""
    return ProcessingStatusServiceImpl(
        uow_factory=UnitOfWorkFactory.create,
    )


def get_document_download_service(
    storage_provider: StorageProvider = Depends(get_storage_provider),
) -> DocumentDownloadServiceImpl:
    """Dependency injection for document download service."""
    return DocumentDownloadServiceImpl(
        uow_factory=UnitOfWorkFactory.create,
        storage_provider=storage_provider,
    )


async def validate_file(file: UploadFile) -> FileType:
    """Validate uploaded file.

    Args:
        file: The uploaded file.

    Returns:
        The FileType enum value.

    Raises:
        HTTPException: If file is invalid.
    """
    # Check file extension
    if not file.filename:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Check file size
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    return EXTENSION_TO_FILE_TYPE[ext]


@router.post(
    "/upload",
    response_model=UploadDocumentResponse,
    status_code=http_status.HTTP_202_ACCEPTED,
    summary="Upload a document",
    description="Upload a document for processing. Returns immediately with document and processing job IDs.",
)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    storage_provider: StorageProvider = Depends(get_storage_provider),
    dispatcher: JobDispatcher = Depends(get_job_dispatcher),
    uow: IUnitOfWork = Depends(get_uow),
) -> UploadDocumentResponse:
    """Upload a document.

    Args:
        file: The uploaded file.
        current_user: Authenticated user from JWT token.
        storage_provider: Storage provider for file storage.

    Returns:
        UploadDocumentResponse with document_id, processing_job_id, and status.

    Raises:
        HTTPException: If upload fails.
    """
    pass
    pass
    pass

    # Validate file
    file_type = await validate_file(file)

    # Generate document UUID
    document_id = uuid4()
    job_id = uuid4()

    # Generate storage path
    storage_path = storage_provider.generate_storage_path(
        user_id=str(current_user.id),
        document_id=str(document_id),
        filename=file.filename or "unnamed",
    )

    # Stream file to storage
    try:
        # Use streaming upload - pass file object directly to avoid loading into memory
        await storage_provider.save(storage_path, file.file)

        pass

    except Exception:
        pass
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file",
        )

    # Create Document and ProcessingJob records
    try:
        async with uow:
            # Create Document
            document = Document(
                id=document_id,
                user_id=current_user.id,
                original_filename=file.filename or "unnamed",
                stored_filename=file.filename or "unnamed",
                file_type=file_type,
                processing_status=ProcessingStatus.UPLOADED,
                storage_path=storage_path,
                file_size=file.size or 0,
                mime_type=file.content_type,
            )

            await uow.document_repository.create(document)

            # Create ProcessingJob
            processing_job = ProcessingJob(
                id=job_id,
                document_id=document_id,
                status=ProcessingStatus.UPLOADED,
                progress=0,
            )

            await uow.processing_job_repository.create(processing_job)

            await uow.commit()

            # Dispatch the background job to process the document
            await dispatcher.enqueue_document_processing(document_id)

            pass

    except Exception as e:
        pass

        # Print complete traceback to console
        traceback.print_exc()

        # Clean up stored file if database operation fails
        try:
            await storage_provider.delete(storage_path)
        except Exception:
            pass

        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create document record: {str(e)}",
        )

    return UploadDocumentResponse(
        document_id=document_id,
        processing_job_id=processing_job.id,
        status=ProcessingStatus.UPLOADED,
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List documents",
    description="List documents for the authenticated user with pagination and filtering.",
)
async def list_documents(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page (max 100)"),
    search: str | None = Query(None, description="Search term for filename filtering"),
    status: str | None = Query(None, description="Filter by processing status"),
    current_user: User = Depends(get_current_user),
    document_service: DocumentServiceImpl = Depends(get_document_service),
) -> DocumentListResponse:
    """List documents for the authenticated user.

    Args:
        page: Page number (1-indexed).
        page_size: Number of items per page.
        search: Optional search term for filename filtering.
        status: Optional processing status filter.
        current_user: Authenticated user from JWT token.
        document_service: Document service for business logic.

    Returns:
        DocumentListResponse with paginated document summaries.

    Raises:
        HTTPException: If listing fails.
    """
    try:
        status_filter = ProcessingStatus(status) if status else None
        return await document_service.list_documents(
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            search=search,
            status=status_filter,
        )
    except Exception:
        pass
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list documents",
        )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailsResponse,
    summary="Get document details",
    description="Get detailed information about a specific document.",
)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    document_service: DocumentServiceImpl = Depends(get_document_service),
) -> DocumentDetailsResponse:
    """Get document details.

    Args:
        document_id: The UUID of the document.
        current_user: Authenticated user from JWT token.
        document_service: Document service for business logic.

    Returns:
        DocumentDetailsResponse with document details.

    Raises:
        HTTPException: If document not found or access denied.
    """
    try:
        from uuid import UUID

        doc_uuid = UUID(document_id)
        return await document_service.get_document(doc_uuid, current_user.id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format",
        )
    except Exception as e:
        if "not found" in str(e).lower() or "access denied" in str(e).lower():
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        pass
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get document",
        )


@router.delete(
    "/{document_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Delete document",
    description="Delete a document and all its associated data.",
)
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    document_service: DocumentServiceImpl = Depends(get_document_service),
) -> None:
    """Delete a document.

    Args:
        document_id: The UUID of the document.
        current_user: Authenticated user from JWT token.
        document_service: Document service for business logic.

    Raises:
        HTTPException: If document not found, access denied, or deletion fails.
    """
    try:
        from uuid import UUID

        doc_uuid = UUID(document_id)
        await document_service.delete_document(doc_uuid, current_user.id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format",
        )
    except Exception as e:
        if "not found" in str(e).lower() or "access denied" in str(e).lower():
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        pass

        # Print complete traceback to console
        traceback.print_exc()

        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document",
        )


@router.get(
    "/{document_id}/summary",
    summary="Get document summary",
    description="Get the AI-generated summary of a document if available.",
)
async def get_document_summary(
    document_id: str,
    current_user: User = Depends(get_current_user),
    document_service: DocumentServiceImpl = Depends(get_document_service),
) -> dict:
    """Get document summary.

    Args:
        document_id: The UUID of the document.
        current_user: Authenticated user from JWT token.
        document_service: Document service for business logic.

    Returns:
        Dictionary containing the summary or null if not available.

    Raises:
        HTTPException: If document not found or access denied.
    """
    try:
        from uuid import UUID

        doc_uuid = UUID(document_id)
        summary = await document_service.get_document_summary(doc_uuid, current_user.id)
        return summary or {"summary": None}
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format",
        )
    except Exception as e:
        if "not found" in str(e).lower() or "access denied" in str(e).lower():
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        pass
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get document summary",
        )


@router.get(
    "/{document_id}/processing-status",
    summary="Get document processing status",
    description="Get the current processing status and progress of a document.",
)
async def get_processing_status(
    document_id: str,
    current_user: User = Depends(get_current_user),
    processing_status_service: ProcessingStatusServiceImpl = Depends(get_processing_status_service),
) -> dict:
    """Get document processing status.

    Args:
        document_id: The UUID of the document.
        current_user: Authenticated user from JWT token.
        processing_status_service: Processing status service for business logic.

    Returns:
        Dictionary containing the processing status information.

    Raises:
        HTTPException: If document not found or access denied.
    """
    try:
        from uuid import UUID

        doc_uuid = UUID(document_id)
        status_response = await processing_status_service.get_processing_status(
            doc_uuid, current_user.id
        )
        return status_response.model_dump()
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format",
        )
    except Exception as e:
        if "not found" in str(e).lower() or "access denied" in str(e).lower():
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        pass
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get processing status",
        )


@router.get(
    "/{document_id}/download",
    summary="Download document",
    description="Download the original uploaded document file.",
)
async def download_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    document_download_service: DocumentDownloadServiceImpl = Depends(get_document_download_service),
) -> StreamingResponse:
    """Download document file.

    Args:
        document_id: The UUID of the document.
        current_user: Authenticated user from JWT token.
        document_download_service: Document download service for business logic.

    Returns:
        StreamingResponse with the file content.

    Raises:
        HTTPException: If document not found, access denied, or file missing.
    """
    try:
        from uuid import UUID

        doc_uuid = UUID(document_id)
        download_info = await document_download_service.download_document(doc_uuid, current_user.id)

        return StreamingResponse(
            download_info["file_stream"],
            media_type=download_info["mime_type"],
            headers={"Content-Disposition": f'attachment; filename="{download_info["filename"]}"'},
        )
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format",
        )
    except Exception as e:
        if "not found" in str(e).lower() or "access denied" in str(e).lower():
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        pass

        # Print complete traceback to console
        traceback.print_exc()

        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download document",
        )
