from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.document_chunk import DocumentChunk
    from app.models.document_content import DocumentContent
    from app.models.processing_job import ProcessingJob
    from app.models.user import User


from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.models.enums import FileType, ProcessingStatus
from app.models.file_metadata import FileMetadataMixin


class Document(BaseModel, FileMetadataMixin):
    """Document model representing uploaded files."""

    __tablename__ = "documents"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Override stored_filename to use 'filename' column name for schema compatibility
    stored_filename: Mapped[str] = mapped_column("filename", String(255), nullable=False)
    file_type: Mapped[FileType] = mapped_column(
        Enum(FileType, values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=ProcessingStatus.UPLOADED,
        nullable=False,
        index=True,
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="documents")
    chunks: Mapped[list[DocumentChunk]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )
    processing_jobs: Mapped[list[ProcessingJob]] = relationship(
        "ProcessingJob",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="ProcessingJob.created_at.desc()",
    )
    content: Mapped[DocumentContent] = relationship(
        "DocumentContent", back_populates="document", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, stored_filename={self.stored_filename}, file_type={self.file_type})>"
