"""
Sync Operations for Vertex AI Feature Store.

This module provides functions for triggering data synchronization
in Vertex AI Feature Store using the modern vertexai SDK.
"""

import logging
from typing import Dict, Any

from shared_utils import init_aiplatform
from vertexai.resources.preview.feature_store import FeatureOnlineStore, FeatureView
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)

def sync_feature_view(
    project_id: str,
    location: str,
    online_store_name: str,
    feature_view_name: str
) -> Dict[str, Any]:
    """
    Manually triggers a data sync operation for a feature view.

    Args:
        project_id: Your GCP project ID.
        location: The GCP region of the online store.
        online_store_name: The name of the online store containing the feature view.
        feature_view_name: The name of the feature view to sync.

    Returns:
        A dictionary with the status of the sync operation.

    Raises:
        RuntimeError: If initialization or API call fails.
        ValueError: If required parameters are missing.
    """
    if not project_id:
        raise ValueError("project_id is required.")
    if not online_store_name:
        raise ValueError("online_store_name is required.")
    if not feature_view_name:
        raise ValueError("feature_view_name is required.")

    try:
        # Initialize AI Platform
        init_aiplatform(project_id, location)
        
        logger.info(f"Triggering sync for FeatureView '{feature_view_name}'...")
        
        # Get the online store
        fos = FeatureOnlineStore(online_store_name)
        
        # Get the feature view
        fv = FeatureView(feature_view_name, feature_online_store_id=fos.name)
        
        # Trigger sync operation
        sync_response = fv.sync()
        
        logger.info(f"Sync operation triggered for FeatureView '{feature_view_name}'")

        return {
            "status": "success",
            "message": f"Sync operation triggered for FeatureView '{feature_view_name}'.",
            "online_store_name": online_store_name,
            "feature_view_name": feature_view_name,
            "sync_response": sync_response
        }
        
    except google_exceptions.NotFound:
        return {"status": "not_found", "message": f"FeatureView '{feature_view_name}' not found."}
    except google_exceptions.GoogleAPIError as e:
        error_message = f"Google API error triggering sync for FeatureView '{feature_view_name}': {e}"
        logger.error(error_message)
        raise RuntimeError(error_message) from e
    except Exception as e:
        error_message = f"An unexpected error occurred triggering sync for FeatureView '{feature_view_name}': {repr(e)}"
        logger.error(error_message)
        raise RuntimeError(error_message) from e 