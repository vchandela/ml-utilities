from enum import Enum
from pydantic import BaseModel, HttpUrl

class CodeEngine(str, Enum):
    gemini = "gemini"   # default
    claude = "claude"
    codex  = "codex"
    amp    = "amp"

class Task(BaseModel):
    id: str | None = None
    repo: HttpUrl
    instructions: str = ""  # Default empty - will be auto-loaded from /tasks/task_instructions.md if empty
    branch_base: str = "main"
    engine: CodeEngine = CodeEngine.gemini  # default to Gemini CLI
    callback_url: HttpUrl | None = None 