"""
User authentication and task listing API.
Provides /me_v2 endpoint for user login/registration and retrieving user's tasks.
Supports both email-based and user-id-based authentication via HTTP headers.
"""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from uuid import UUID, uuid4
from .db import SessionLocal, init_db
from .models import User, Task

router = APIRouter()

class MeResponse(BaseModel):
    user_id: str
    email: str
    tasks: list[dict]

@router.get("/me_v2", response_model=MeResponse)
def me_v2(x_user_id: str = Header(None), x_user_email: str = Header(None)):
    init_db()
    with SessionLocal() as db:
        user = None
        if x_user_id:
            try: user = db.get(User, UUID(x_user_id))
            except Exception: raise HTTPException(status_code=400, detail="Invalid X-User-Id")
        if not user:
            if not x_user_email: x_user_email = f"anon-{uuid4().hex[:8]}@example.com"
            user = db.query(User).filter(User.email == x_user_email).first() or User(email=x_user_email)
            db.add(user); db.commit()
        tasks = db.query(Task).filter(Task.user_id == user.id).order_by(Task.created_at.desc()).limit(50).all()
        return MeResponse(user_id=str(user.id), email=user.email,
                          tasks=[{"id": str(t.id), "title": t.title, "agent_type": t.agent_type,
                                  "stage": t.stage, "stage_status": t.stage_status} for t in tasks])
