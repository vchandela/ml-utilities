"""
Shared utilities for Vertex AI Feature Store operations.

This module provides common utilities and helper functions for Vertex AI Feature Store operations
using the modern vertexai.resources.preview.feature_store SDK.
"""

import logging
import os
from typing import Any

# Import necessary libraries from Google Cloud AI Platform SDK
try:
    from google.cloud import aiplatform
    from vertexai.resources.preview import feature_store
    from google.api_core import exceptions as google_exceptions
except ImportError:
    # Provide a helpful error message if libraries are not installed
    raise ImportError(
        "Required Google Cloud AI Platform libraries are not installed. "
        "Please install them using: pip install google-cloud-aiplatform"
    )

logger = logging.getLogger(__name__)

# === CONSTANTS ===
DEFAULT_LOCATION = "us-central1"
DEFAULT_BQ_PROJECT_ID = os.getenv("DEFAULT_BQ_PROJECT_ID")
DEFAULT_GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")

# ===============================================================================
# CORE INITIALIZATION
# ===============================================================================

def init_aiplatform(project_id: str, location: str) -> None:
    """
    Initialize AI Platform with project and location.

    Args:
        project_id: The GCP project ID.
        location: The GCP region.
    
    Raises:
        RuntimeError: If initialization fails.
    """
    try:
        aiplatform.init(project=project_id, location=location)
        logger.info(f"AI Platform initialized for project '{project_id}' in location '{location}'")
    except Exception as e:
        logger.error(f"Failed to initialize AI Platform: {e}")
        raise RuntimeError(f"Failed to initialize AI Platform: {e}")

# ===============================================================================
# HELPER FUNCTIONS
# ===============================================================================

def get_default_project_id() -> str:
    """Helper to get default project ID, falling back to environment variable."""
    return DEFAULT_GCP_PROJECT_ID or "your-gcp-project-id"

def get_default_location() -> str:
    """Helper to get default location, falling back to env var or default."""
    return os.getenv("GOOGLE_CLOUD_LOCATION", DEFAULT_LOCATION) 