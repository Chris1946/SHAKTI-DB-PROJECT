from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.models.metrics import Base


class UserMemory(Base):
    """
    Stores user preferences for explanations.
    """
    __tablename__ = "user_memory"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SystemMemory(Base):
    """
    Stores static and semi-static System Intelligence Profile per host.
    Replaces MetricMetadata.
    """
    __tablename__ = "system_memory"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    hostname: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    
    # OS
    os_name: Mapped[Optional[str]] = mapped_column(String(255))
    os_version: Mapped[Optional[str]] = mapped_column(String(255))
    kernel_version: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Hardware
    architecture: Mapped[Optional[str]] = mapped_column(String(50))
    cpu_model: Mapped[Optional[str]] = mapped_column(String(255))
    cpu_cores: Mapped[Optional[int]] = mapped_column(BigInteger)
    cpu_threads: Mapped[Optional[int]] = mapped_column(BigInteger)
    total_memory: Mapped[Optional[int]] = mapped_column(BigInteger)
    
    # Features
    ebpf_support: Mapped[Optional[bool]] = mapped_column()
    
    # Extensible Profile (Docker, NUMA, capabilities, etc)
    profile: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class IncidentMemory(Base):
    """
    Historical incidents with resolutions and embeddings for RAG.
    """
    __tablename__ = "incident_memory"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    alert_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    hostname: Mapped[str] = mapped_column(String(255), index=True)
    
    facts_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    explanation: Mapped[str] = mapped_column(Text)
    root_cause: Mapped[Optional[str]] = mapped_column(Text)
    resolution: Mapped[Optional[str]] = mapped_column(Text)
    
    # Vector embedding of the explanation and root cause (dimensions match sentence-transformers or Groq)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(384))
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class KnowledgeMemory(Base):
    """
    Technical documentation for RAG.
    """
    __tablename__ = "knowledge_memory"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(255), index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Vector embedding of the content (dimensions match sentence-transformers or Groq)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(384))
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
