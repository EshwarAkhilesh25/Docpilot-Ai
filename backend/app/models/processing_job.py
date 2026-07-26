from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.document import Document


from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.models.enums import ProcessingStage, ProcessingStatus


class ProcessingJob(BaseModel):
    """ProcessingJob model representing document processing jobs."""

    __tablename__ = "processing_jobs"

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=ProcessingStatus.UPLOADED,
        nullable=False,
        index=True,
    )
    current_stage: Mapped[ProcessingStage] = mapped_column(
        Enum(ProcessingStage, values_callable=lambda obj: [e.value for e in obj]),
        default=ProcessingStage.UPLOADED,
        nullable=False,
        index=True,
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingestion_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    # Many-to-one with Document - one document can have many processing jobs
    document: Mapped[Document] = relationship("Document", back_populates="processing_jobs")

    def __repr__(self) -> str:
        return f"<ProcessingJob(id={self.id}, document_id={self.document_id}, status={self.status}, stage={self.current_stage})>"
