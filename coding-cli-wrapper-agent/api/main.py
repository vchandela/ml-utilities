import os
import json
import uuid
import subprocess
import time
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis

# Import shared models (copied into container)
from models import Task, CodeEngine

app = FastAPI(
    title="Coding Agent API",
    description="Stand-alone coding agent that spawns worker containers for code tasks",
    version="1.0.0"
)

# Settings
class Settings:
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    github_token: str = os.getenv("GITHUB_TOKEN", "")

settings = Settings()

# Redis connection
try:
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    # Test connection
    redis_client.ping()
except Exception as e:
    print(f"Redis connection failed: {e}")
    redis_client = None

class TaskResponse(BaseModel):
    task_id: str
    status: str = "queued"

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Coding Agent API is running", "redis_connected": redis_client is not None}

@app.post("/tasks", response_model=TaskResponse, status_code=202)
async def create_task(task: Task) -> TaskResponse:
    """
    Create a new coding task and spawn worker container
    
    Atomic logic:
    1. Validate incoming JSON against Task model and assign task_id
    2. Read instructions from file if instructions_file is provided
    3. HSET task:{id} state=queued in Redis
    4. Spawn worker container
    5. Return 202 Accepted {"task_id": id}
    """
    
    # 1. Validate and assign task_id
    if not task.id:
        task.id = str(uuid.uuid4())
    
    task_id = task.id
    
    # 2. Auto-load instructions from mounted file if instructions is empty
    if not task.instructions:
        instructions_file_path = "/tasks/task_instructions.md"
        try:
            with open(instructions_file_path, 'r', encoding='utf-8') as f:
                task.instructions = f.read().strip()
            print(f"DEBUG: Auto-loaded instructions from {instructions_file_path}: {task.instructions[:100]}...")
        except Exception as e:
            print(f"ERROR: Failed to read instructions from {instructions_file_path}: {e}")
            raise HTTPException(status_code=400, detail=f"No instructions provided and failed to read from mounted file: {str(e)}")
    
    # Check Redis connection
    if not redis_client:
        raise HTTPException(status_code=500, detail="Redis connection not available")
    
    try:
        # 2. Store task state in Redis
        task_key = f"task:{task_id}"
        redis_client.hset(task_key, mapping={
            "state": "queued",
            "task_json": task.model_dump_json(),
            "created_at": str(int(time.time()))
        })
        
        # 3. Spawn worker container
        task_json = task.model_dump_json()
        # Use docker compose run with explicit compose file (project name set in compose file)
        worker_command = [
            "docker", "compose", "-f", "/workspace/docker-compose.yaml",
            "run",
            "-e", f"TASK_JSON={task_json}",
            "-e", f"REDIS_URL={settings.redis_url}",
            "-e", f"GITHUB_TOKEN={settings.github_token}",
            "-e", f"GEMINI_API_KEY={os.getenv('GEMINI_API_KEY', '')}",
            "-e", f"ANTHROPIC_API_KEY={os.getenv('ANTHROPIC_API_KEY', '')}",
            "-e", f"OPENAI_API_KEY={os.getenv('OPENAI_API_KEY', '')}",
            "-e", f"AMP_API_KEY={os.getenv('AMP_API_KEY', '')}",
            "worker"
        ]
        
        # Start worker process in background
        try:
            process = subprocess.Popen(
                worker_command,
                cwd="/workspace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            # Log the command for debugging
            print(f"DEBUG: Starting worker with command: {' '.join(worker_command)}")
            print(f"DEBUG: Working directory: /workspace")
            print(f"DEBUG: Process PID: {process.pid}")
            
            # Don't wait for completion, but log that it started
            redis_client.hset(task_key, "worker_pid", str(process.pid))
            redis_client.hset(task_key, "worker_started_at", str(int(time.time())))
            
        except Exception as e:
            print(f"ERROR: Failed to start worker: {e}")
            redis_client.hset(task_key, "worker_error", str(e))
            raise HTTPException(status_code=500, detail=f"Failed to start worker: {str(e)}")
        
        # 4. Return task_id
        return TaskResponse(task_id=task_id, status="queued")
        
    except Exception as e:
        # Clean up Redis if something goes wrong
        if redis_client:
            try:
                redis_client.delete(f"task:{task_id}")
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get task status with prominent PR URL display"""
    
    if not redis_client:
        raise HTTPException(status_code=500, detail="Redis connection not available")
    
    task_key = f"task:{task_id}"
    task_data = redis_client.hgetall(task_key)
    
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Create a cleaner response with PR URL prominently displayed
    response = {
        "task_id": task_id,
        "state": task_data.get("state", "unknown"),
        "created_at": task_data.get("created_at"),
    }
    
    # Add timing information
    if "started_at" in task_data:
        response["started_at"] = task_data["started_at"]
    if "completed_at" in task_data:
        response["completed_at"] = task_data["completed_at"]
        
    # Prominently display PR URL for completed tasks
    if task_data.get("state") == "done" and "pr_url" in task_data:
        response["status"] = "✅ COMPLETED SUCCESSFULLY"
        response["pr_url"] = task_data["pr_url"]
        response["github_pr"] = task_data["pr_url"]  # Duplicate for emphasis
    elif task_data.get("state") == "running":
        response["status"] = "🔄 PROCESSING..."
    elif task_data.get("state") == "failed":
        response["status"] = "❌ FAILED"
        response["error"] = task_data.get("error", "Unknown error")
    else:
        response["status"] = "⏳ QUEUED"
        
    # Add test status if available
    if "test_status" in task_data:
        response["test_status"] = task_data["test_status"]
        
    # Add original task details for reference
    if "task_json" in task_data:
        try:
            task_details = json.loads(task_data["task_json"])
            response["instructions"] = task_details.get("instructions")
            response["repo"] = task_details.get("repo")
            response["engine"] = task_details.get("engine")
        except:
            pass
            
    return response

@app.get("/health")
async def health_check():
    """Detailed health check"""
    redis_status = "connected" if redis_client else "disconnected"
    
    if redis_client:
        try:
            redis_client.ping()
            redis_details = "ping successful"
        except Exception as e:
            redis_details = f"ping failed: {e}"
    else:
        redis_details = "no connection"
    
    return {
        "status": "healthy",
        "redis": {
            "status": redis_status,
            "details": redis_details,
            "url": settings.redis_url
        },
        "github_token_configured": bool(settings.github_token)
    } 