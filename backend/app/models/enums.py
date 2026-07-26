from enum import StrEnum


class FileType(StrEnum):
    """File type enumeration."""

    PDF = "pdf"
    DOCX = "docx"
    AUDIO = "audio"
    VIDEO = "video"
    TXT = "txt"


class ProcessingStatus(StrEnum):
    """Document processing status enumeration."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStage(StrEnum):
    """Document processing stage enumeration.

    Represents the current step in the processing pipeline.
    Separate from ProcessingStatus which represents high-level job status.
    """

    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


class ChatRole(StrEnum):
    """Chat message role enumeration."""

    USER = "user"
    ASSISTANT = "assistant"
