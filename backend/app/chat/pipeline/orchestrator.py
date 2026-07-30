"""Chat Pipeline Orchestrator."""

import logging
import time
from collections.abc import Callable
from uuid import UUID

from app.chat.interfaces.intent_classifier import IntentClassifier
from app.chat.interfaces.llm_provider import LLMProvider
from app.chat.workflows.registry import registry as workflow_registry
from app.db.unit_of_work import IUnitOfWork
from app.embeddings.interfaces.embedding_provider import EmbeddingProvider
from app.models.chat_message import ChatMessage
from app.models.enums import ChatRole
from app.vectorstore.interfaces.vector_index_provider import VectorIndexProvider

logger = logging.getLogger(__name__)


class ChatPipelineService:
    """Orchestrates the modular RAG pipeline."""

    def __init__(
        self,
        uow_factory: Callable,
        llm_provider: LLMProvider,
        vector_index_service: VectorIndexProvider,
        embedding_service: EmbeddingProvider,
        intent_classifier: IntentClassifier,
    ):
        self._uow_factory = uow_factory
        self._llm_provider = llm_provider
        self._vector_index_service = vector_index_service
        self._embedding_service = embedding_service
        self._intent_classifier = intent_classifier

    async def execute_pipeline(
        self,
        question: str,
        session_id: UUID,
        user_id: UUID,
        document_ids: list[UUID] | None = None,
        explicit_intent: str | None = None,
    ):
        """Executes the pipeline and returns the full response (non-streaming)."""

        start_time = time.time()
        pipeline_log = {
            "session_id": str(session_id),
            "question": question,
        }

        uow = self._uow_factory()

        try:
            # 1. Intent Classification
            intent = explicit_intent
            if not intent:
                intent = await self._intent_classifier.classify(question)
            pipeline_log["intent"] = intent

            # 2. Workflow Registry
            workflow = workflow_registry.get_workflow(intent)
            pipeline_log["workflow"] = workflow.__class__.__name__

            # 3. Document Scope & Profiles
            document_profiles = []
            async with uow:
                session = await uow.chat_session_repository.get_by_id(session_id)
                if session:
                    # Existing conversation: enforce its document scope
                    document_ids = session.document_ids or []

                if document_ids:
                    num_docs = len(document_ids)
                    for did in document_ids:
                        doc = await uow.document_content_repository.get_by_document_id(did)
                        if doc and doc.content_metadata:
                            document_profiles.append(doc.content_metadata)
                else:
                    num_docs = 0

            # Workflow Preconditions
            is_valid, err_msg = workflow.validate_preconditions(num_docs)
            if not is_valid:
                err_response = self._format_error(err_msg, pipeline_log)
                await self._persist_conversation(
                    uow, session_id, user_id, question, err_response["answer"], document_ids
                )
                return err_response

            # 4. Conversation Context Builder
            history = []
            if workflow.requires_history:
                async with uow:
                    session = await uow.chat_session_repository.get_by_id(session_id)
                    if session:
                        # Get last 5 messages for context
                        messages = await uow.chat_message_repository.list_by_session(session_id)
                        recent = messages[-5:]
                        for m in recent:
                            role_val = m.role.value if hasattr(m.role, "value") else m.role
                            history.append({"role": str(role_val).lower(), "content": m.content})

            # 5. Retrieval Strategy & Retriever
            retrieval_strategy = workflow.get_retrieval_strategy()
            retrieval_params = workflow.get_retrieval_params(question)

            t0 = time.time()
            chunks = await retrieval_strategy.retrieve(
                question=question,
                document_ids=document_ids,
                vector_index_service=self._vector_index_service,
                embedding_service=self._embedding_service,
                uow=uow,
                **retrieval_params,
            )
            pipeline_log["retrieval_time_ms"] = (time.time() - t0) * 1000  # type: ignore
            pipeline_log["retrieved_chunks"] = len(chunks)  # type: ignore

            if not chunks:
                err_response = self._format_error(
                    "No relevant context found in documents.", pipeline_log
                )
                await self._persist_conversation(
                    uow, session_id, user_id, question, err_response["answer"], document_ids
                )
                return err_response

            # Format context
            context_text = self._format_context(chunks)

            # 6. Prompt Builder
            sys_prompt, user_prompt = workflow.build_prompt(
                question=question,
                context=context_text,
                history=history,
                document_profiles=document_profiles,
            )

            # 7. LLM Invocation
            t0 = time.time()
            messages = [{"role": "system", "content": sys_prompt}]
            messages.extend(history)
            messages.append({"role": "user", "content": user_prompt})

            raw_response = await self._llm_provider.generate_with_history(messages)
            pipeline_log["llm_time_ms"] = (time.time() - t0) * 1000  # type: ignore

            # 8. Response Formatter
            formatter = workflow.get_response_formatter()
            if formatter:
                final_response = formatter.format(raw_response)
            else:
                final_response = raw_response

            sources_data = [
                {
                    "document_id": str(c.document_id),
                    "chunk_id": str(c.id),
                    "chunk_index": c.chunk_index,
                    "start_page": c.page_number,
                    "end_page": c.page_number,
                    "similarity_score": float(getattr(c, "similarity_score", 0.0)),
                }
                for c in chunks
            ]

            # 10. Persistence
            await self._persist_conversation(
                uow, session_id, user_id, question, final_response, document_ids
            )

            # Log Observability
            pipeline_log["status"] = "SUCCESS"
            pipeline_log["total_time_ms"] = (time.time() - start_time) * 1000  # type: ignore

            return {"answer": final_response, "sources": sources_data}

        except Exception as e:
            import traceback

            full_trace = traceback.format_exc()
            logger.error(
                f"[TRACE DEBUG] Chat Orchestrator Exception: {e}\nFull Traceback:\n{full_trace}"
            )

            pipeline_log["status"] = "FAILED"
            pipeline_log["error"] = str(e)

            # Don't throw 500 for LLM rate limits or other generation errors; return a fallback response
            if "429" in str(e):
                err_msg = "I'm currently experiencing high traffic and hit an API rate limit. Please try again in a few moments."
            else:
                err_msg = (
                    "I encountered an error while trying to generate a response. Please try again."
                )

            err_response = self._format_error(err_msg, pipeline_log)

            # Persist the fallback conversation so the user sees it in their history
            await self._persist_conversation(
                uow, session_id, user_id, question, err_response["answer"], document_ids
            )
            return err_response

    def _format_error(self, message: str, log_dict: dict):
        log_dict["status"] = "FALLBACK"
        log_dict["reason"] = message
        pass
        return {"answer": message, "sources": []}

    def _format_context(self, chunks: list) -> str:
        parts = []
        for i, chunk in enumerate(chunks, 1):
            text = chunk.text
            page = getattr(chunk, "page_number", None)
            if page is not None:
                parts.append(f"[Source {i}, Page {page}]\n{text}")
            else:
                parts.append(f"[Source {i}]\n{text}")
        return "\n\n".join(parts)

    async def _persist_conversation(
        self,
        uow: IUnitOfWork,
        session_id: UUID,
        user_id: UUID,
        question: str,
        answer: str,
        document_ids: list[UUID] | None,
    ):
        async with uow:
            session = await uow.chat_session_repository.get_by_id(session_id)
            if not session:
                # Create session (importing ChatSession dynamically to avoid circular issues)
                from app.models.chat_session import ChatSession

                # Convert UUIDs to strings for JSON serialization
                str_document_ids = [str(did) for did in document_ids] if document_ids else None
                session = ChatSession(
                    id=session_id,
                    user_id=user_id,
                    title=question[:50],
                    document_ids=str_document_ids,
                )
                await uow.chat_session_repository.create(session)

            user_msg = ChatMessage(session_id=session_id, role=ChatRole.USER, content=question)
            ai_msg = ChatMessage(session_id=session_id, role=ChatRole.ASSISTANT, content=answer)

            await uow.chat_message_repository.create(user_msg)
            await uow.chat_message_repository.create(ai_msg)
            await uow.commit()
