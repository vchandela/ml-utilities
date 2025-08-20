"""
Simple event publisher for Temporal activities.
Publishes events to Redis without importing FastAPI dependencies.
Separate from SSE module to avoid Temporal sandbox restrictions.
"""
import os
import json
import asyncio
from redis.asyncio import Redis

async def publish_event(task_id: str, payload: dict):
    """Publish real-time event to Redis for SSE streaming."""
    try:
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = Redis.from_url(url)
        channel = f"sse:{task_id}"
        message = json.dumps(payload)
        result = await redis_client.publish(channel, message)
        print(f"[events] Published to {channel}: {message} (subscribers: {result})")
        await redis_client.close()
    except Exception as e:
        print(f"[events] ERROR publishing to Redis: {e}")

# Sync wrapper for backward compatibility
def publish_event_sync(task_id: str, payload: dict):
    """Sync wrapper - creates event loop if needed."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # If we're already in an async context, schedule the coroutine
        asyncio.create_task(publish_event(task_id, payload))
    else:
        # If we're in sync context, run the async function
        loop.run_until_complete(publish_event(task_id, payload))
