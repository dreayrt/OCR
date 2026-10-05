import enum
from sqlalchemy import Column, BigInteger, Integer, String, Text, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.database import Base


class ProcessingStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Document(Base):
    __tablename__ = "documents"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    document_uuid = Column(String(36), unique=True, index=True, nullable=False)
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    raw_text = Column(Text, nullable=True)
    processing_status = Column(
        SQLEnum(ProcessingStatus, values_callable=lambda x: [e.value for e in x]),
        default=ProcessingStatus.PENDING,
        nullable=False,
    )
    ocr_engine = Column(String(50), nullable=True)  # 'direct_text' | 'paddleocr'
    ocr_confidence = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # 1 -> N relationship
    fields = relationship(
        "DocumentField",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="joined",
    )


class DocumentField(Base):
    __tablename__ = "document_fields"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, index=True, autoincrement=True)
    document_id = Column(
        BigInteger,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name = Column(String(100), nullable=False, index=True)
    field_value = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document = relationship("Document", back_populates="fields")
