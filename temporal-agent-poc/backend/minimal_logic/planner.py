"""
Plan generation and persistence functionality.
Creates structured plans using task context and tribal search results.
Saves generated plans to database as TaskDocument records for user review.
"""
from uuid import UUID
from ..db import SessionLocal
from ..models import Task, TaskDocument
from .tribal_search import search

def plan_v1(task_id: str) -> str:
    """Simulates generating the first version of a plan."""
    with SessionLocal() as db:
        task = db.get(Task, UUID(task_id))
        title = task.title if task else "Untitled Task"
    
    hits = search(task_id)
    bullets = "\\n".join([f"- Use context: {h['title']}" for h in hits]) or "- No context found."
    return f"# Plan v1 for: {title}\\n\\n## Steps\\n1. Analyze requirements.\\n2. Gather context.\\n   {bullets}\\n3. Produce report."

def plan_v2_with_feedback(task_id: str, feedback: str) -> str:
    """Generates plan v2 incorporating user feedback."""
    with SessionLocal() as db:
        task = db.get(Task, UUID(task_id))
        title = task.title if task else "Untitled Task"
    
    # Get previous plan for context (optional enhancement)
    hits = search(task_id)
    bullets = "\n".join([f"- Use context: {h['title']}" for h in hits]) or "- No context found."
    
    # Incorporate feedback into revised plan
    feedback_section = f"\n\n## Feedback Incorporated\n- {feedback}\n\n## Revised Approach"
    
    return f"""# Plan v2 for: {title} (Revised)

## Steps
1. Analyze requirements with focus on user feedback.
2. Gather enhanced context based on feedback.
   {bullets}
3. Address specific feedback: "{feedback}"
4. Produce comprehensive report with requested improvements.{feedback_section}
- Enhanced data source analysis 
- More detailed methodology section
- Expanded validation criteria"""

def persist_plan(task_id: str, body: str, version: int = 1) -> str:
    """Saves the generated plan to the database."""
    with SessionLocal() as db:
        doc = TaskDocument(task_id=UUID(task_id), kind="PLAN", body=body, status="REVIEW", version=str(version))
        db.add(doc)
        db.commit()
        return str(doc.id)
