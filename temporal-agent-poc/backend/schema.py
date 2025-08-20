"""
Pydantic schemas for API request/response validation.
Defines data structures for task creation, feedback management, and document status actions.
"""
from pydantic import BaseModel, Field
from typing import Optional

class TaskCreate(BaseModel):
    title: str
    agent_type: Optional[str] = Field("intern", description="intern | tribal_search")

class FeedbackCreate(BaseModel):
    body: str

class FeedbackUpdate(BaseModel):
    body: str

class DocumentStatusAction(BaseModel):
    action: str  # expect "done_reviewing"
