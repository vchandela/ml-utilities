"""
Fetch Operations for Vertex AI Feature Store.

This module provides functions for fetching feature values from online stores
in Vertex AI Feature Store using the modern vertexai SDK.
"""

import logging
from typing import Dict, Any, Optional

from shared_utils import init_aiplatform
from vertexai.resources.preview.feature_store import FeatureOnlineStore, FeatureView
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)

def fetch_feature_values(
    project_id: str,
    location: str,
    online_store_name: str,
    feature_view_name: str,
    target_entity_id: str,
    format: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetches feature values for a specific entity ID from an online store.

    Args:
        project_id: Your GCP project ID.
        location: Region where the online store is located.
        online_store_name: The name of the online store.
        feature_view_name: The name of the feature view.
        entity_id: The value of the ID column for the feature record.
        format: Optional format for fetching values (not used in modern SDK).

    Returns:
        A dictionary containing the fetched feature values.

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
    if not target_entity_id:
        raise ValueError("target_entity_id is required.")

    try:
        # Initialize AI Platform
        init_aiplatform(project_id, location)
        
        logger.info(f"Fetching feature values for Entity ID '{target_entity_id}' from FeatureView '{feature_view_name}'...")
        
        # Get the online store
        fos = FeatureOnlineStore(online_store_name)
        
        # Get the feature view
        fv = FeatureView(feature_view_name, feature_online_store_id=fos.name)
        
        # Read data for the entity
        data = fv.read([target_entity_id])
        
        logger.info(f"Successfully fetched feature values for entity '{target_entity_id}'")
        
        return {
            "status": "success",
            "message": f"Successfully fetched feature values for entity ID '{target_entity_id}'.",
            "entity_id": target_entity_id,
            "features": data,
            "online_store_name": online_store_name,
            "feature_view_name": feature_view_name
        }

    except google_exceptions.NotFound:
        return {"status": "not_found", "message": f"FeatureView '{feature_view_name}' or OnlineStore '{online_store_name}' not found."}
    except google_exceptions.InvalidArgument as e:
        error_message = f"Invalid argument for fetching feature values: {e}"
        logger.error(error_message)
        raise RuntimeError(error_message) from e
    except google_exceptions.GoogleAPIError as e:
        error_message = f"Google API error fetching feature values for '{feature_view_name}': {e}"
        logger.error(error_message)
        raise RuntimeError(error_message) from e
    except Exception as e:
        error_message = f"An unexpected error occurred fetching feature values for '{feature_view_name}': {repr(e)}"
        logger.error(error_message)
        raise RuntimeError(error_message) from e 