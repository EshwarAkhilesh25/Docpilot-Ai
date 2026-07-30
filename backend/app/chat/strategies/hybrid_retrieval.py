import logging
import traceback
from uuid import UUID

from app.chat.interfaces.retrieval_strategy import RetrievalStrategy
from app.models.document_chunk import DocumentChunk

logger = logging.getLogger(__name__)


class HybridRetrievalStrategy(RetrievalStrategy):
    """Retrieves document chunks using semantic similarity."""

    async def retrieve(
        self,
        question: str,
        document_ids: list[UUID] | None,
        vector_index_service,
        embedding_service,
        uow,
        **kwargs,
    ) -> list[DocumentChunk]:
        """Perform semantic retrieval."""
        top_k = kwargs.get("top_k", 5)

        logger.info(
            f"[TRACE DEBUG] HybridRetrievalStrategy.retrieve() called for question: '{question}' | doc_ids: {document_ids}"
        )

        try:
            # 1. Generate query embedding
            query_embedding = await embedding_service.generate_embeddings([question])
            if not query_embedding or len(query_embedding) == 0:
                logger.warning(
                    "[TRACE DEBUG] HybridRetrievalStrategy: generate_embeddings returned empty list!"
                )
                return []

            vector = query_embedding[0]
            vector_shape = getattr(vector, "shape", "unknown")
            logger.info(
                f"[TRACE DEBUG] HybridRetrievalStrategy: Query embedding generated successfully. Shape: {vector_shape} | Dtype: {getattr(vector, 'dtype', 'unknown')}"
            )

            # 2. Search vector index (FAISS)
            logger.info(
                f"[TRACE DEBUG] HybridRetrievalStrategy: Passing vector (shape {vector_shape}) to FAISS vector_index_service.search..."
            )
            semantic_results = await vector_index_service.search(
                vector, top_k=kwargs.get("search_k", 20)
            )

            if not semantic_results:
                logger.warning(
                    "[TRACE DEBUG] HybridRetrievalStrategy: FAISS search returned 0 semantic results!"
                )
                return []

            logger.info(
                f"[TRACE DEBUG] HybridRetrievalStrategy: FAISS search returned {len(semantic_results)} semantic result(s)."
            )

            # 3. Get matching chunks
            vector_ids = [result.vector_id for result in semantic_results]
            logger.info(
                f"[TRACE DEBUG] HybridRetrievalStrategy: Fetching document chunks for FAISS vector_ids: {vector_ids}"
            )

            async with uow:
                chunks = await uow.document_chunk_repository.get_by_vector_ids(vector_ids)

            logger.info(
                f"[TRACE DEBUG] HybridRetrievalStrategy: Repository returned {len(chunks)} chunk(s) from database."
            )

            # 4. Filter by document IDs if specified
            if document_ids:
                doc_id_strs = [str(did) for did in document_ids]
                chunks = [chunk for chunk in chunks if str(chunk.document_id) in doc_id_strs]
                logger.info(
                    f"[TRACE DEBUG] HybridRetrievalStrategy: Filtered chunks by document scope {doc_id_strs} -> {len(chunks)} chunk(s) remaining."
                )

            # 5. Sort by relevance and take top_k
            chunk_map = {chunk.vector_id: chunk for chunk in chunks}
            sorted_chunks = []
            for result in semantic_results:
                if result.vector_id in chunk_map:
                    chunk = chunk_map[result.vector_id]
                    # Attach similarity_score for orchestrator
                    chunk.similarity_score = getattr(result, "score", 0.0)
                    if hasattr(result, "similarity_score"):
                        chunk.similarity_score = result.similarity_score
                    sorted_chunks.append(chunk)

            logger.info(
                f"[TRACE DEBUG] HybridRetrievalStrategy: Returning final top {len(sorted_chunks[:top_k])} chunk(s)."
            )
            return sorted_chunks[:top_k]

        except Exception as e:
            logger.error(
                f"[TRACE DEBUG] HybridRetrievalStrategy EXCEPTION: {e}\nFull Traceback:\n{traceback.format_exc()}"
            )
            raise
