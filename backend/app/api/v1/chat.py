from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.chat.services.chat_pipeline_service import ChatPipelineService


"""Chat API endpoints for RAG-based document Q&A."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_current_user,
    get_embedding_provider,
    get_llm_provider,
)
from app.chat.interfaces.llm_provider import LLMProvider
from app.db.session import get_db
from app.db.unit_of_work import UnitOfWorkFactory
from app.models.user import User
from app.repositories.sqlalchemy.chat_message_repository import SQLAlchemyChatMessageRepository
from app.repositories.sqlalchemy.chat_session_repository import SQLAlchemyChatSessionRepository
from app.schemas.chat import ConversationDetail, ConversationListItem, ConversationUpdate
from app.services.conversation_service import ConversationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# Request/Response Schemas
class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""

    question: str = Field(..., min_length=1, description="The user's question")
    session_id: UUID | None = Field(
        None, description="Optional session ID for conversation continuity"
    )
    document_ids: list[UUID] | None = Field(
        None, description="Optional list of document IDs to filter retrieval"
    )
    intent: str | None = Field(None, description="Explicit intent to route to a specific workflow")
    workflow_params: dict | None = Field(None, description="Optional parameters for the workflow")
    # Legacy parameters, can be removed once frontend is fully migrated
    top_k: int = Field(5, ge=1, le=20, description="Number of chunks to return after deduplication")
    search_k: int = Field(
        20, ge=1, le=100, description="Number of chunks to retrieve before deduplication"
    )


class CitationResponse(BaseModel):
    """Response schema for a citation."""

    document_id: str
    chunk_id: str
    chunk_index: int
    page_number: int | None = None
    similarity_score: float


class ChatResponseSchema(BaseModel):
    """Response schema for chat endpoint."""

    answer: str
    sources: list[dict]
    citations: list[CitationResponse] | None = None
    session_id: UUID

    @classmethod
    def from_chat_response(cls, response: dict, session_id: UUID) -> ChatResponseSchema:
        """Create schema from pipeline response."""
        sources = response.get("sources", [])

        # Backward compatibility for old format (list of UUID strings)
        if sources and isinstance(sources[0], str):
            # deduplicate
            list(dict.fromkeys(sources))
            parsed_sources = [{"chunk_id": s} for s in sources]  # Keep all for sources
            citations = None
        else:
            # Deduplicate by chunk_id for citations only
            seen = set()
            unique_citations = []
            for s in sources:
                chunk_id = s.get("chunk_id")
                if chunk_id not in seen:
                    seen.add(chunk_id)
                    unique_citations.append(s)

            parsed_sources = sources
            citations = None
            if sources:
                citations = []
                for s in unique_citations:
                    citations.append(
                        CitationResponse(
                            document_id=s.get("document_id"),
                            chunk_id=s.get("chunk_id"),
                            chunk_index=s.get("chunk_index", 0),
                            page_number=s.get("start_page") or s.get("page_number"),
                            similarity_score=s.get("similarity_score", 0.0),
                        )
                    )

        return cls(
            answer=response.get("answer", ""),
            sources=parsed_sources,
            citations=citations,
            session_id=session_id,
        )


from app.api.dependencies import get_vector_index_provider
from app.embeddings.interfaces.embedding_provider import EmbeddingProvider
from app.vectorstore.providers.faiss_provider import FAISSVectorProvider


def get_chat_pipeline_service(
    llm_provider: LLMProvider = Depends(get_llm_provider),
    vector_index_provider: FAISSVectorProvider = Depends(get_vector_index_provider),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
) -> ChatPipelineService:
    """Dependency injection for chat pipeline service."""
    from app.chat.classification.rule_based_classifier import RuleBasedClassifier
    from app.chat.pipeline.orchestrator import ChatPipelineService

    return ChatPipelineService(
        uow_factory=UnitOfWorkFactory.create,
        llm_provider=llm_provider,
        vector_index_service=vector_index_provider,
        embedding_service=embedding_provider,
        intent_classifier=RuleBasedClassifier(),
    )


def get_conversation_service(
    session: AsyncSession = Depends(get_db),
) -> ConversationService:
    """Dependency injection for conversation service."""
    session_repo = SQLAlchemyChatSessionRepository(session)
    message_repo = SQLAlchemyChatMessageRepository(session)
    return ConversationService(session_repo, message_repo)


@router.get(
    "/conversations",
    response_model=list[ConversationListItem],
    status_code=status.HTTP_200_OK,
    summary="List all conversations",
    description="Returns all chat conversations for the authenticated user, ordered by updated_at DESC.",
)
async def list_conversations(
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationListItem]:
    """List all conversations for the authenticated user.

    Args:
        current_user: Authenticated user from JWT token.
        conversation_service: Conversation service for business logic.

    Returns:
        List of ConversationListItem with session metadata.

    Raises:
        HTTPException: If listing fails.
    """
    try:
        conversations = await conversation_service.list_conversations(current_user.id)
        return [ConversationListItem(**conv) for conv in conversations]

    except Exception as e:
        pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list conversations: {str(e)}",
        )


@router.get(
    "/conversations/{session_id}",
    response_model=ConversationDetail,
    status_code=status.HTTP_200_OK,
    summary="Get conversation details",
    description="Returns conversation metadata and complete message history for a specific session.",
)
async def get_conversation(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationDetail:
    """Get a conversation with its message history.

    Args:
        session_id: The UUID of the conversation session.
        current_user: Authenticated user from JWT token.
        conversation_service: Conversation service for business logic.

    Returns:
        ConversationDetail with session metadata and messages.

    Raises:
        HTTPException: If conversation not found or access is unauthorized.
    """
    try:
        conversation = await conversation_service.get_conversation(session_id, current_user.id)
        return ConversationDetail(**conversation)

    except Exception as e:
        pass
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
                if "not found" in str(e).lower()
                else status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(e),
        )


@router.patch(
    "/conversations/{session_id}",
    response_model=ConversationDetail,
    status_code=status.HTTP_200_OK,
    summary="Update a conversation",
    description="Updates conversation title and/or document scope.",
)
async def update_conversation(
    session_id: UUID,
    update_data: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationDetail:
    """Update a conversation's details.

    Args:
        session_id: The UUID of the conversation session.
        update_data: Data to update (title, document_ids).
        current_user: Authenticated user from JWT token.
        conversation_service: Conversation service for business logic.

    Returns:
        Updated ConversationDetail.
    """
    try:
        conversation = await conversation_service.update_conversation(
            session_id=session_id,
            user_id=current_user.id,
            document_ids=update_data.document_ids,
            title=update_data.title,
        )
        return ConversationDetail(**conversation)

    except Exception as e:
        pass
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
                if "not found" in str(e).lower()
                else status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(e),
        )


@router.delete(
    "/conversations/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
    description="Deletes a conversation and all its messages. Does not affect documents, vectors, or chunks.",
)
async def delete_conversation(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> None:
    """Delete a conversation.

    Args:
        session_id: The UUID of the conversation session.
        current_user: Authenticated user from JWT token.
        conversation_service: Conversation service for business logic.

    Raises:
        HTTPException: If conversation not found or access is unauthorized.
    """
    try:
        await conversation_service.delete_conversation(session_id, current_user.id)

    except Exception as e:
        pass
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
                if "not found" in str(e).lower()
                else status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(e),
        )


@router.post(
    "/",
    response_model=ChatResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Ask a question about documents",
    description="Ask a question about uploaded documents using RAG. Returns answer with sources.",
)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    chat_pipeline_service: ChatPipelineService = Depends(get_chat_pipeline_service),
) -> ChatResponseSchema:
    """Process a chat request.

    Args:
        request: The chat request with question and optional parameters.
        current_user: Authenticated user from JWT token.
        chat_pipeline_service: Chat pipeline service for RAG processing.

    Returns:
        ChatResponseSchema with answer and sources.

    Raises:
        HTTPException: If chat processing fails.
    """
    try:
        import uuid

        # Default session ID if not provided
        session_id = request.session_id or uuid.uuid4()

        pass
        response = await chat_pipeline_service.execute_pipeline(
            question=request.question,
            session_id=session_id,
            user_id=current_user.id,
            document_ids=request.document_ids,
            explicit_intent=request.intent,
        )

        return ChatResponseSchema.from_chat_response(response, session_id)

    except Exception as e:
        import traceback

        logger.error(f"Chat request failed with exception: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat request failed: {str(e)}",
        )
