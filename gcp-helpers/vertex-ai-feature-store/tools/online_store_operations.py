"""
Online Store Operations for Vertex AI Feature Store.

This module provides functions for creating and retrieving online stores
in Vertex AI Feature Store using the modern vertexai SDK.
"""

import logging
from typing import Dict, Any, Optional

from shared_utils import init_aiplatform
from vertexai.resources.preview import feature_store
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)

def create_online_store(
    project_id: str,
    location: str,
    online_store_id: str
) -> Dict[str, Any]:
    """
    Creates an optimized online serving store with public endpoint.

    Args:
        project_id: Your GCP project ID.
        location: Region where the online store will be created.
        online_store_id: The name of the new FeatureOnlineStore instance.

    Returns:
        A dictionary with the status and details of the created online store.

    Raises:
        RuntimeError: If initialization or API call fails.
        ValueError: If required parameters are missing.
    """
    if not project_id:
        raise ValueError("project_id is required.")
    if not online_store_id:
        raise ValueError("online_store_id is required.")

    try:
        # Initialize AI Platform
        init_aiplatform(project_id, location)
        
        logger.info(f"Creating optimized OnlineStore '{online_store_id}' in project '{project_id}'...")
        
        # Create optimized online store with public endpoint
        fos = feature_store.FeatureOnlineStore.create_optimized_store(online_store_id)
        
        # Handle response
        if fos and hasattr(fos, 'resource_name'):
            logger.info(f"OnlineStore created: {fos.resource_name}")
            online_store_name = fos.resource_name
        else:
            logger.info(f"OnlineStore creation initiated for: {online_store_id}")
            online_store_name = f"projects/{project_id}/locations/{location}/featureOnlineStores/{online_store_id}"
        
        return {
            "status": "success",
            "message": f"Optimized OnlineStore '{online_store_id}' created successfully with public endpoint.",
            "online_store_name": online_store_name,
            "online_store_id": online_store_id,
            "optimized": True,
            "public_endpoint": True
        }
        
    except google_exceptions.AlreadyExists:
        return {"status": "already_exists", "message": f"OnlineStore '{online_store_id}' already exists."}
    except google_exceptions.GoogleAPIError as e:
        error_message = f"Google API error creating OnlineStore '{online_store_id}': {e}"
        logger.error(error_message)
        raise RuntimeError(error_message) from e
    except Exception as e:
        error_message = f"An unexpected error occurred creating OnlineStore '{online_store_id}': {repr(e)}"
        logger.error(error_message)
        raise RuntimeError(error_message) from e

def get_online_store(project_id: str, location: str, online_store_name: str) -> Dict[str, Any]:
    """
    Retrieves details of a specific online store.

    Args:
        project_id: Your GCP project ID.
        location: The GCP region of the online store.
        online_store_name: The name of the online store instance.

    Returns:
        A dictionary containing online store details on success.

    Raises:
        RuntimeError: If initialization or API call fails.
        ValueError: If required parameters are missing.
    """
    if not project_id:
        raise ValueError("project_id is required.")
    if not online_store_name:
        raise ValueError("online_store_name is required.")

    try:
        # Initialize AI Platform
        init_aiplatform(project_id, location)
        
        logger.info(f"Getting OnlineStore '{online_store_name}'...")
        
        # Get the online store
        fos = feature_store.FeatureOnlineStore(online_store_name)
        
        return {
            "status": "success", 
            "message": f"Successfully retrieved OnlineStore '{online_store_name}'.",
            "online_store_details": {
                "name": fos.resource_name,
                "display_name": getattr(fos, 'display_name', online_store_name),
                "create_time": getattr(fos, 'create_time', None),
                "update_time": getattr(fos, 'update_time', None),
                "labels": getattr(fos, 'labels', {}),
                "optimized": True  # Assuming optimized for modern stores
            }
        }
        
    except google_exceptions.NotFound:
        return {"status": "not_found", "message": f"OnlineStore '{online_store_name}' not found."}
    except google_exceptions.GoogleAPIError as e:
        error_message = f"Google API error getting OnlineStore '{online_store_name}': {e}"
        logger.error(error_message)
        raise RuntimeError(error_message) from e
    except Exception as e:
        error_message = f"An unexpected error occurred getting OnlineStore '{online_store_name}': {repr(e)}"
        logger.error(error_message)
        raise RuntimeError(error_message) from e 