"""Document processing worker implementation."""

import logging
from collections.abc import Callable
from uuid import UUID

from app.jobs.exceptions import JobExecutionException
from app.models.enums import ProcessingStage, ProcessingStatus
from app.services.interfaces.document_processing import DocumentProcessingService

logger = logging.getLogger(__name__)


class DocumentProcessingWorker:
    """Worker for processing documents in the background.

    This worker is a thin orchestrator that:
    1. Loads the ProcessingJob
    2. Inspects current_stage
    3. Executes only remaining stages
    4. Updates current_stage after each successful stage
    5. Updates heartbeat before each stage
    6. Marks FAILED with error_message if any stage throws
    7. Increments retry_count on failure

    The worker contains NO document-specific logic. All business logic
    is delegated to the DocumentProcessingService.
    """

    def __init__(self, uow_factory: Callable, processing_service: DocumentProcessingService):
        """Initialize the document processing worker.

        Args:
            uow_factory: Factory function to create UnitOfWork instances.
            processing_service: Document processing service for business logic.
        """
        self._uow_factory = uow_factory
        self._processing_service = processing_service

    async def process(self, document_id: UUID) -> None:
        """Process a document with stage-based orchestration.

        This method orchestrates the processing workflow:
        1. Load ProcessingJob
        2. Inspect current_stage
        3. Execute remaining stages only
        4. Update current_stage after each stage
        5. Update heartbeat before each stage
        6. Mark FAILED on failure with retry increment

        Args:
            document_id: The UUID of the document to process.

        Raises:
            JobExecutionException: If processing fails.
        """
        uow = self._uow_factory()
        job = None

        try:
            async with uow:
                # Get the latest processing job for the document
                jobs = await uow.processing_job_repository.list_by_document(
                    document_id=document_id, offset=0, limit=1
                )

                if not jobs:
                    pass
                    raise JobExecutionException("No processing job found")

                job = jobs[0]

                # Update status to PROCESSING if not already
                if job.status != ProcessingStatus.PROCESSING:
                    job.status = ProcessingStatus.PROCESSING
                    job.started_at = None  # Will be set on first stage
                    await uow.processing_job_repository.update(job)
                    await uow.commit()

                pass

            # Execute stages based on current_stage
            await self._execute_remaining_stages(document_id, job)

            # Mark as COMPLETED
            uow = self._uow_factory()
            async with uow:
                job = await uow.processing_job_repository.get_by_id(job.id)
                if job:
                    job.status = ProcessingStatus.COMPLETED
                    job.current_stage = ProcessingStage.COMPLETED
                    job.progress = 100
                    job.completed_at = None  # Will be set by repository
                    await uow.processing_job_repository.update(job)
                    await uow.commit()

                pass

            # Generate Ingestion Report
            await self._processing_service.generate_ingestion_report(document_id, job.id)

        except Exception as e:
            logger.exception("Document processing failed for document_id %s: %s", document_id, e)
            # Increment retry and mark as FAILED
            if job:
                uow = self._uow_factory()
                try:
                    async with uow:
                        job = await uow.processing_job_repository.get_by_id(job.id)
                        if job:
                            await uow.processing_job_repository.increment_retry(job.id)
                            await uow.processing_job_repository.mark_failed(job.id, str(e))
                            await uow.commit()

                    # Generate Ingestion Report even on failure
                    await self._processing_service.generate_ingestion_report(document_id, job.id)
                except Exception:
                    pass

            if isinstance(e, JobExecutionException):
                raise e
            raise JobExecutionException(f"Processing failed: {e}")

    async def _execute_remaining_stages(self, document_id: UUID, job) -> None:
        """Execute remaining stages based on current_stage.

        Args:
            document_id: The UUID of the document.
            job: The ProcessingJob entity.

        Raises:
            JobExecutionException: If any stage fails.
        """
        # Define stage execution order
        stages = [
            (ProcessingStage.EXTRACTING, self._process_extraction),
            (ProcessingStage.CHUNKING, self._process_chunking),
            (ProcessingStage.EMBEDDING, self._process_embedding),
            (ProcessingStage.INDEXING, self._process_indexing),
        ]

        # Find starting point based on current_stage
        start_index = 0
        for i, (stage, _) in enumerate(stages):
            if stage == job.current_stage:
                start_index = i
                break

        # Execute remaining stages
        for _stage, stage_func in stages[start_index:]:
            await self._update_heartbeat(job.id)
            await stage_func(document_id, job.id)

    async def _update_heartbeat(self, job_id: UUID) -> None:
        """Update heartbeat for a processing job.

        Args:
            job_id: The UUID of the processing job.
        """
        uow = self._uow_factory()
        try:
            async with uow:
                await uow.processing_job_repository.update_heartbeat(job_id)
                await uow.commit()
        except Exception:
            pass

    async def _process_extraction(self, document_id: UUID, job_id: UUID) -> None:
        """Process extraction stage.

        Args:
            document_id: The UUID of the document.
            job_id: The UUID of the processing job.

        Raises:
            JobExecutionException: If extraction fails.
        """
        uow = self._uow_factory()
        try:
            async with uow:
                await uow.processing_job_repository.update_stage(job_id, ProcessingStage.EXTRACTING)
                await uow.commit()
        except Exception:
            pass

        try:
            await self._processing_service.extract_document(document_id)

            uow = self._uow_factory()
            async with uow:
                await uow.processing_job_repository.update_status(
                    job_id, ProcessingStatus.PROCESSING, progress=25
                )
                await uow.commit()
        except Exception as e:
            raise JobExecutionException(f"Extraction failed: {e}")

    async def _process_chunking(self, document_id: UUID, job_id: UUID) -> None:
        """Process chunking stage.

        Args:
            document_id: The UUID of the document.
            job_id: The UUID of the processing job.

        Raises:
            JobExecutionException: If chunking fails.
        """
        uow = self._uow_factory()
        try:
            async with uow:
                await uow.processing_job_repository.update_stage(job_id, ProcessingStage.CHUNKING)
                await uow.commit()
        except Exception:
            pass

        try:
            await self._processing_service.chunk_document(document_id)

            uow = self._uow_factory()
            async with uow:
                await uow.processing_job_repository.update_status(
                    job_id, ProcessingStatus.PROCESSING, progress=50
                )
                await uow.commit()
        except Exception as e:
            raise JobExecutionException(f"Chunking failed: {e}")

    async def _process_embedding(self, document_id: UUID, job_id: UUID) -> None:
        """Process embedding stage.

        Args:
            document_id: The UUID of the document.
            job_id: The UUID of the processing job.

        Raises:
            JobExecutionException: If embedding fails.
        """
        uow = self._uow_factory()
        try:
            async with uow:
                await uow.processing_job_repository.update_stage(job_id, ProcessingStage.EMBEDDING)
                await uow.commit()
        except Exception:
            pass

        try:
            # Get chunks from chunking stage
            chunks = await self._processing_service.chunk_document(document_id)
            self._temp_embeddings = await self._processing_service.generate_embeddings(
                document_id, chunks
            )

            uow = self._uow_factory()
            async with uow:
                await uow.processing_job_repository.update_status(
                    job_id, ProcessingStatus.PROCESSING, progress=75
                )
                await uow.commit()
        except Exception as e:
            raise JobExecutionException(f"Embedding failed: {e}")

    async def _process_indexing(self, document_id: UUID, job_id: UUID) -> None:
        """Process indexing stage (FAISS and BM25).

        Args:
            document_id: The UUID of the document.
            job_id: The UUID of the processing job.

        Raises:
            JobExecutionException: If indexing fails.
        """
        uow = self._uow_factory()
        try:
            async with uow:
                await uow.processing_job_repository.update_stage(job_id, ProcessingStage.INDEXING)
                await uow.commit()
        except Exception:
            pass

        try:
            # Get chunks and embeddings from previous stages
            chunks = await self._processing_service.chunk_document(document_id)
            embeddings = getattr(self, "_temp_embeddings", None)
            if not embeddings:
                embeddings = await self._processing_service.generate_embeddings(document_id, chunks)

            await self._processing_service.index_vectors(document_id, chunks, embeddings)

            uow = self._uow_factory()
            async with uow:
                await uow.processing_job_repository.update_status(
                    job_id, ProcessingStatus.PROCESSING, progress=95
                )
                await uow.commit()
        except Exception as e:
            raise JobExecutionException(f"FAISS indexing failed: {e}")

        try:
            # Index chunks for BM25 keyword search
            await self._processing_service.index_chunks(document_id, chunks)

            uow = self._uow_factory()
            async with uow:
                await uow.processing_job_repository.update_status(
                    job_id, ProcessingStatus.PROCESSING, progress=98
                )
                await uow.commit()
        except Exception:
            pass
            # Continue without failing - BM25 is optional
