"""
Feature Group Operations for Vertex AI Feature Store.

This module provides functions for creating, retrieving, and listing feature groups
in Vertex AI Feature Store using the modern vertexai.resources.preview.feature_store SDK.
"""

import logging
from typing import Dict, List, Any, Optional

from shared_utils import init_aiplatform
from vertexai.resources.preview import feature_store
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)

def create_feature_group(
    project_id: str,
    location: str,
    feature_group_id: str,
    bq_table_uri: str,
    entity_id_columns: List[str],
    description: Optional[str] = None,
    labels: Optional[Dict[str, str]] = None
) -> feature_store.FeatureGroup:
    """
    Creates a new feature group in Vertex AI Feature Store with BigQuery source.

    Args:
        project_id: Your GCP project ID.
        location: Region where the feature group will be created.
        feature_group_id: The name of the new feature group.
        bq_table_uri: The BigQuery source table URI (e.g., "bq://project.dataset.table").
        entity_id_columns: Column(s) in the BigQuery table that contain the entity ID.
        description: A description for the feature group.
        labels: Optional key-value pairs for labeling the feature group.

    Returns:
        A dictionary with the status and details of the created feature group.

    Raises:
        RuntimeError: If initialization or API call fails.
        ValueError: If required parameters are missing or invalid.
    """
    if not project_id:
        raise ValueError("project_id is required for creating a feature group.")
    if not feature_group_id:
        raise ValueError("feature_group_id is required for creating a feature group.")
    if not bq_table_uri:
        raise ValueError("bq_table_uri is required for creating a feature group.")
    if not entity_id_columns:
        raise ValueError("entity_id_columns must be provided.")

    try:
        # Initialize AI Platform
        init_aiplatform(project_id, location)
        
        logger.info(f"Creating FeatureGroup '{feature_group_id}' with BigQuery source '{bq_table_uri}'...")
        
        # Create feature group with BigQuery source
        fg = feature_store.FeatureGroup.create(
            name=feature_group_id,
            source=feature_store.utils.FeatureGroupBigQuerySource(
                uri=bq_table_uri, 
                entity_id_columns=entity_id_columns
            ),
            description=description,
            labels=labels or {}
        )
        
        logger.info(f"FeatureGroup created: {fg.resource_name}")
        
        return fg
    except Exception as e:
        logger.error(f"An unexpected error occurred creating FeatureGroup '{feature_group_id}': {repr(e)}")
        raise RuntimeError(f"An unexpected error occurred creating FeatureGroup '{feature_group_id}': {repr(e)}") from e

def get_feature_group(project_id: str, location: str, feature_group_id: str) -> Dict[str, Any]:
    """
    Retrieves details of a specific feature group.

    Args:
        project_id: Your GCP project ID.
        location: Region of the feature group.
        feature_group_id: The name of the feature group.

    Returns:
        A dictionary containing feature group details on success,
        or raises an exception on failure.
    """
    if not project_id:
        raise ValueError("project_id is required.")
    if not feature_group_id:
        raise ValueError("feature_group_id is required.")

    try:
        # Initialize AI Platform
        init_aiplatform(project_id, location)
        
        logger.info(f"Getting FeatureGroup '{feature_group_id}'...")
        
        # Get the feature group
        fg = feature_store.FeatureGroup(feature_group_id)
        
        return {
            "status": "success",
            "message": f"Successfully retrieved FeatureGroup '{feature_group_id}'.",
            "feature_group_details": {
                "name": fg.resource_name,
                "display_name": getattr(fg, 'display_name', feature_group_id),
                "description": getattr(fg, 'description', None),
                "create_time": getattr(fg, 'create_time', None),
                "update_time": getattr(fg, 'update_time', None),
                "labels": getattr(fg, 'labels', {})
            }
        }
    except google_exceptions.NotFound:
        return {"status": "not_found", "message": f"FeatureGroup '{feature_group_id}' not found."}
    except google_exceptions.GoogleAPIError as e:
        error_message = f"Google API error getting FeatureGroup '{feature_group_id}': {e}"
        logger.error(error_message)
        raise RuntimeError(error_message) from e
    except Exception as e:
        error_message = f"An unexpected error occurred getting FeatureGroup '{feature_group_id}': {repr(e)}"
        logger.error(error_message)
        raise RuntimeError(error_message) from e

def list_feature_groups(project_id: str, location: str) -> List[Dict[str, Any]]:
    """
    Lists all feature groups in a given project and location.

    Args:
        project_id: Your GCP project ID.
        location: The GCP region where the feature groups are located.

    Returns:
        A list of dictionaries, where each dictionary represents a feature group.

    Raises:
        RuntimeError: If initialization or API call fails.
        ValueError: If required parameters are missing.
    """
    if not project_id:
        raise ValueError("project_id is required for listing feature groups.")
    
    try:
        # Initialize AI Platform
        init_aiplatform(project_id, location)
        
        logger.info(f"Listing FeatureGroups in project '{project_id}' location '{location}'...")
        
        # List all feature groups
        feature_groups = feature_store.FeatureGroup.list()
        
        feature_groups_list = []
        for fg in feature_groups:
            feature_groups_list.append({
                "name": fg.resource_name,
                "display_name": getattr(fg, 'display_name', 'N/A'),
                "description": getattr(fg, 'description', None),
                "create_time": getattr(fg, 'create_time', None),
                "update_time": getattr(fg, 'update_time', None), 
                "labels": getattr(fg, 'labels', {})
            })
        
        return feature_groups_list

    except google_exceptions.GoogleAPIError as e:
        error_message = f"Google API error listing FeatureGroups in {project_id}:{location}: {e}"
        logger.error(error_message)
        raise RuntimeError(error_message) from e
    except Exception as e:
        error_message = f"An unexpected error occurred listing FeatureGroups: {repr(e)}"
        logger.error(error_message)
        raise RuntimeError(error_message) from e 