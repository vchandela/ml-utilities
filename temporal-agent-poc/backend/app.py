"""
FastAPI application entry point for the Temporal Agent POC.
Main web server that coordinates user authentication, task management, and real-time SSE streaming.
Acts as the bridge between the frontend UI and the Temporal workflow orchestration backend.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes_tasks import router as tasks_router
from .auth import router as auth_router

app = FastAPI(title="Temporal Agent POC")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router, prefix="")
app.include_router(tasks_router, prefix="")

@app.get("/health")
async def health(): return {"ok": True}
