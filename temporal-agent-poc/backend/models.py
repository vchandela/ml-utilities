"""
Database models for the Temporal Agent POC.
Defines User, Task, TaskDocument, Feedback, and TribalCorpus tables.
Task model includes workflow_id field to link database state with Temporal workflow execution.
"""
from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.sql import func, expression
from sqlalchemy.orm import relationship
from uuid import uuid4
from .db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    email = Column(String, unique=True, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class Task(Base):
    __tablename__ = "tasks"
    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(Text, nullable=False)
    agent_type = Column(String, nullable=False, default="intern")
    stage = Column(String, nullable=False, server_default=expression.literal("INIT"))
    stage_status = Column(String, nullable=False, server_default=expression.literal("PENDING"))
    workflow_id = Column(String, nullable=True, index=True) # Link to Temporal execution
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    user = relationship("User", lazy="joined")

class TaskDocument(Base):
    __tablename__ = "task_documents"
    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    task_id = Column(PGUUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    version = Column(String, nullable=False, default="1")
    kind = Column(String, nullable=False, default="PLAN") # e.g., PLAN, REPORT
    body = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="DRAFT") # DRAFT, REVIEW, LOCKED
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    document_id = Column(PGUUID(as_uuid=True), ForeignKey("task_documents.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class TribalCorpus(Base): # For simulating tribal search
    __tablename__ = "tribal_corpus"
    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    tenant = Column(String, nullable=False, default="default")
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
