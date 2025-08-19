"""
Server-Sent Events (SSE) implementation for real-time workflow updates.
Provides live streaming of Temporal workflow events to the frontend via Redis pub/sub.
Used by Temporal activities to publish progress updates and stage changes.
"""
import os, json
from typing import AsyncGenerator
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
router = APIRouter()

def _format_sse(data: dict) -> bytes:
    return f"data: {json.dumps(data)}\n\n".encode("utf-8")

async def _stream_channel(channel: str) -> AsyncGenerator[bytes, None]:
    redis = Redis.from_url(REDIS_URL, decode_responses=False)
    try:
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        print(f"[sse] Subscribed to Redis channel: {channel}")
        
        async for msg in pubsub.listen():
            print(f"[sse] Received message: {msg}")
            if msg and msg.get("type") == "message":
                payload = msg.get("data")
                if isinstance(payload, (bytes, bytearray)):
                    yield b"data: " + payload + b"\n\n"
                else:
                    yield _format_sse(payload)
    except Exception as e:
        print(f"[sse] ERROR in stream: {e}")
        yield _format_sse({"error": str(e)})
    finally:
        await redis.close(close_connection_pool=True)

@router.get("/tasks/{task_id}/stream")
async def stream_task(task_id: str):
    channel = f"sse:{task_id}"
    return StreamingResponse(_stream_channel(channel), media_type="text/event-stream")

# publisher utility - import from events module to avoid duplication
from .events import publish_event
