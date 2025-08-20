"""
Simulated tribal knowledge search functionality.
Provides mock knowledge base search for agent context gathering.
Creates dummy tribal knowledge entries if none exist in the database.
"""
from sqlalchemy import select
from ..db import SessionLocal
from ..models import TribalCorpus, Task
from uuid import UUID

def search(task_id: str) -> list[dict]:
    """Simulates searching tribal knowledge. Returns a few dummy rows."""
    with SessionLocal() as db:
        task = db.get(Task, UUID(task_id))
        if not task:
            return []
        # Create dummy data if it doesn't exist
        if db.query(TribalCorpus).count() == 0:
            db.add_all([
                TribalCorpus(title="Onboarding Guide", content="..."),
                TribalCorpus(title="SQL Style Guide", content="..."),
            ])
            db.commit()
        rows = db.execute(select(TribalCorpus).limit(2)).scalars().all()
        return [{"id": str(r.id), "title": r.title} for r in rows]
