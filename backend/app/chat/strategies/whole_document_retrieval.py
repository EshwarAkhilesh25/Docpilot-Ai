"""Retrieval Strategy that fetches the entire document sequentially."""

import logging
from uuid import UUID

from app.chat.interfaces.retrieval_strategy import RetrievalStrategy
from app.models.document_chunk import DocumentChunk

logger = logging.getLogger(__name__)


class WholeDocumentRetrievalStrategy(RetrievalStrategy):
    """Retrieves all chunks of the specified documents in chronological order.

    Useful for summarization or full document extraction where semantic
    similarity to the prompt is irrelevant.
    """

    async def retrieve(
        self,
        question: str,
        document_ids: list[UUID] | None,
        vector_index_service,
        embedding_service,
        uow,
        **kwargs,
    ) -> list[DocumentChunk]:
        """Perform full document retrieval."""

        if not document_ids:
            logger.warning(
                "WholeDocumentRetrievalStrategy received empty document_ids — returning 0 chunks. "
                "Ensure document_ids are resolved before invoking this strategy."
            )
            return []

        max_chunks = kwargs.get("max_chunks", 100)  # Prevents blowing up context window

        logger.info(
            "WholeDocumentRetrievalStrategy retrieving chunks for %d document(s): %s",
            len(document_ids),
            [str(d) for d in document_ids],
        )

        chunks = []
        async with uow:
            for doc_id in document_ids:
                doc_chunks = await uow.document_chunk_repository.list_by_document(doc_id)

                # Sort chronologically by chunk index
                doc_chunks.sort(key=lambda c: getattr(c, "chunk_index", 0))
                chunks.extend(doc_chunks)

        # Limit chunks if document is too large
        return chunks[:max_chunks]
