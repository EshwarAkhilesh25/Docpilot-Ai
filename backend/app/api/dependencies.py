from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.providers.groq_provider import GroqLLMProvider
from app.db.session import get_db
from app.db.unit_of_work import IUnitOfWork, SQLAlchemyUnitOfWork
from app.embeddings.interfaces.embedding_provider import EmbeddingProvider
from app.ingestion.factory.processor_factory import ProcessorFactory
from app.ingestion.pipeline.ingestion_pipeline import IngestionPipeline
from app.ingestion.providers.whisper_transcription_provider import (
    WhisperTranscriptionProvider,
)
from app.jobs.dispatchers.in_process_dispatcher import InProcessJobDispatcher
from app.jobs.interfaces.job_dispatcher import JobDispatcher
from app.keyword_search.interfaces.keyword_index_provider import KeywordIndexProvider
from app.models.user import User
from app.retrieval.services.retriever_service import RetrieverService
from app.services.authentication_service import AuthenticationServiceImpl
from app.services.exceptions import InactiveUserException, InvalidCredentialsException
from app.services.interfaces.auth import AuthenticationService
from app.services.interfaces.user import UserService
from app.services.user_service import UserServiceImpl
from app.storage.providers.local_storage_provider import LocalStorageProvider
from app.vectorstore.providers.faiss_provider import FAISSVectorProvider


def get_uow(session: AsyncSession = Depends(get_db)) -> IUnitOfWork:
    """Dependency injection for Unit of Work."""
    return SQLAlchemyUnitOfWork(session)


def get_user_service(uow: IUnitOfWork = Depends(get_uow)) -> UserService:
    """Dependency injection for UserService."""
    return UserServiceImpl(uow)


def get_authentication_service(uow: IUnitOfWork = Depends(get_uow)) -> AuthenticationService:
    """Dependency injection for AuthenticationService."""
    return AuthenticationServiceImpl(uow)


def get_llm_provider(request: Request) -> GroqLLMProvider:
    """Dependency injection for LLM provider from bootstrap."""
    bootstrap = request.app.state.bootstrap
    provider = bootstrap.get_llm_provider()
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM provider not available - check GROQ_API_KEY configuration",
        )
    return provider


def get_embedding_provider(request: Request) -> EmbeddingProvider:
    """Dependency injection for embedding provider from bootstrap application state.

    Shared by API routes including Chat and Document ingestion endpoints.
    """
    bootstrap = request.app.state.bootstrap
    provider = bootstrap.get_embedding_provider()
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding provider not available",
        )
    return provider


def get_transcription_provider(request: Request) -> WhisperTranscriptionProvider:
    """Dependency injection for transcription provider from bootstrap."""
    bootstrap = request.app.state.bootstrap
    provider = bootstrap.get_transcription_provider()
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Transcription provider not available - check GROQ_API_KEY configuration",
        )
    return provider


def get_storage_provider(request: Request) -> LocalStorageProvider:
    """Dependency injection for storage provider from bootstrap."""
    bootstrap = request.app.state.bootstrap
    provider = bootstrap.get_storage_provider()
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage provider not available",
        )
    return provider


def get_vector_index_provider(request: Request) -> FAISSVectorProvider:
    """Dependency injection for vector index provider from bootstrap."""
    bootstrap = request.app.state.bootstrap
    provider = bootstrap.get_vector_index_provider()
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector index provider not available",
        )
    return provider


def get_keyword_index_provider(request: Request) -> KeywordIndexProvider:
    """Dependency injection for keyword index provider from bootstrap."""
    bootstrap = request.app.state.bootstrap
    provider = bootstrap.get_keyword_index_provider()
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Keyword index provider not available",
        )
    return provider


def get_job_dispatcher(request: Request) -> JobDispatcher:
    """Dependency injection for JobDispatcher."""
    bootstrap = request.app.state.bootstrap

    # Get required providers from bootstrap
    embedding_provider = bootstrap.get_embedding_provider()
    transcription_provider = bootstrap.get_transcription_provider()
    keyword_index_provider = bootstrap.get_keyword_index_provider()

    # Create IngestionPipeline dependencies
    processor_factory = ProcessorFactory(transcription_provider)
    ingestion_pipeline = IngestionPipeline(processor_factory)

    from app.core.config import get_settings

    settings = get_settings()

    return InProcessJobDispatcher(
        ingestion_pipeline=ingestion_pipeline,
        embedding_provider=embedding_provider,
        vector_index_path=settings.FAISS_INDEX_PATH,
        transcription_provider=transcription_provider,
        keyword_index_provider=keyword_index_provider,
    )


def get_retriever_service(
    vector_index: FAISSVectorProvider = Depends(get_vector_index_provider),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    keyword_index: KeywordIndexProvider = Depends(get_keyword_index_provider),
) -> RetrieverService:
    """Dependency injection for RetrieverService."""
    from app.db.unit_of_work import UnitOfWorkFactory

    return RetrieverService(
        uow_factory=UnitOfWorkFactory.create,
        embedding_provider=embedding_provider,
        vector_provider=vector_index,
        keyword_index_provider=keyword_index,
    )


# OAuth2PasswordBearer for extracting Bearer token from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthenticationService = Depends(get_authentication_service),
) -> User:
    """Dependency injection for authenticated current user.

    This dependency extracts the Bearer token from the Authorization header,
    validates it using AuthenticationService.verify_token(), and returns
    the authenticated User entity.

    Args:
        token: JWT token from Authorization header.
        auth_service: Authentication service for token verification.

    Returns:
        The authenticated User entity.

    Raises:
        HTTPException: If authentication fails (401) or user is inactive (403).
    """
    try:
        user = await auth_service.verify_token(token)
        return user
    except InvalidCredentialsException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InactiveUserException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )


# Dependency aliases for cleaner code
DatabaseSessionDep = Annotated[AsyncSession, Depends(get_db)]
UnitOfWorkDep = Annotated[IUnitOfWork, Depends(get_uow)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthenticationServiceDep = Annotated[AuthenticationService, Depends(get_authentication_service)]
# CurrentUserDep removed due to FastAPI Annotated processing issue
# Use Depends(get_current_user) directly in endpoints instead
