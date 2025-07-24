"""
Feature Operations for Vertex AI Feature Store.

This module provides functions for creating and listing features within feature groups
in Vertex AI Feature Store using the modern vertexai.resources.preview.feature_store SDK.
"""

import logging
from typing import Dict, List, Any, Optional

from shared_utils import init_aiplatform
from vertexai.resources.preview import feature_store
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)

def create_feature(
    project_id: str,
    location: str,
    feature_group_id: str,
    feature_id: str,
    version_column_name: str,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a feature within an existing feature group.

    Args:
        project_id: Your GCP project ID.
        location: Region of the feature group.
        feature_group_id: The ID of the parent feature group.
        feature_id: The name of the new feature.
        version_column_name: The column from the BigQuery table or view that you want to associate with the feature.
        description: An optional description for the feature.

    Returns:
        A dictionary with the status and details of the created feature.

    Raises:
        RuntimeError: If initialization or API call fails.
        ValueError: If required parameters are missing or invalid.
    """
    if not project_id:
        raise ValueError("project_id is required.")
    if not feature_group_id:
        raise ValueError("feature_group_id is required.")
    if not feature_id:
        raise ValueError("feature_id is required.")
    if not version_column_name:
        raise ValueError("version_column_name is required.")

    try:
        # Initialize AI Platform
        init_aiplatform(project_id, location)
        
        logger.info(f"Creating Feature '{feature_id}' in FeatureGroup '{feature_group_id}'...")
        
        # Get the existing feature group
        feature_group = feature_store.FeatureGroup(feature_group_id)
        
        # Create feature on the feature group
        feature = feature_group.create_feature(
            name=feature_id,
            version_column_name=version_column_name
        )
        
        logger.info(f"Feature created: {feature.resource_name}")
        
        return {
            "status": "success",
            "message": f"Feature '{feature_id}' created successfully in FeatureGroup '{feature_group_id}'.",
            "feature_name": feature.resource_name,
            "feature_id": feature_id,
            "feature_group_id": feature_group_id,
            "version_column_name": version_column_name
        }

    except google_exceptions.AlreadyExists:
        return {"status": "already_exists", "message": f"Feature '{feature_id}' already exists."}
    except google_exceptions.GoogleAPIError as e:
        error_message = f"Google API error creating Feature '{feature_id}': {e}"
        logger.error(error_message)
        raise RuntimeError(error_message) from e
    except Exception as e:
        error_message = f"An unexpected error occurred creating Feature '{feature_id}': {repr(e)}"
        logger.error(error_message)
        raise RuntimeError(error_message) from e

def list_features(project_id: str, location: str, feature_group_id: str) -> List[Dict[str, Any]]:
    """
    Lists all features within a specific feature group.

    Args:
        project_id: Your GCP project ID.
        location: The GCP region of the feature group.
        feature_group_id: The ID of the parent feature group.

    Returns:
        A list of dictionaries, where each dictionary represents a feature.

    Raises:
        RuntimeError: If initialization or API call fails.
        ValueError: If required parameters are missing.
    """
    if not project_id:
        raise ValueError("project_id is required.")
    if not feature_group_id:
        raise ValueError("feature_group_id is required.")

    try:
        # Initialize AI Platform
        init_aiplatform(project_id, location)
        
        logger.info(f"Listing features for FeatureGroup '{feature_group_id}'...")
        
        # Get the feature group
        feature_group = feature_store.FeatureGroup(feature_group_id)
        
        # List features in the feature group
        features = feature_group.list_features()
        
        features_list = []
        for feature in features:
            features_list.append({
                "name": feature.resource_name,
                "display_name": getattr(feature, 'display_name', 'N/A'),
                "description": getattr(feature, 'description', None),
                "create_time": getattr(feature, 'create_time', None),
                "update_time": getattr(feature, 'update_time', None),
                "labels": getattr(feature, 'labels', {})
            })
        
        return features_list

    except google_exceptions.NotFound:
        error_message = f"FeatureGroup '{feature_group_id}' not found."
        logger.error(error_message)
        raise RuntimeError(error_message)
    except google_exceptions.GoogleAPIError as e:
        error_message = f"Google API error listing Features for '{feature_group_id}': {e}"
        logger.error(error_message)
        raise RuntimeError(error_message) from e
    except Exception as e:
        error_message = f"An unexpected error occurred listing Features for '{feature_group_id}': {repr(e)}"
        logger.error(error_message)
        raise RuntimeError(error_message) from e 