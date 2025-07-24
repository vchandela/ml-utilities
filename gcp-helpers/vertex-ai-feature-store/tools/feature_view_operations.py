"""
Feature View Operations for Vertex AI Feature Store.

This module provides functions for creating and listing feature views
in Vertex AI Feature Store using the modern vertexai SDK.
"""

import logging
import requests
import json
import subprocess
from typing import Dict, List, Any, Optional

from shared_utils import init_aiplatform
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)

def create_feature_view(
    project_id: str,
    location: str,
    online_store_name: str,
    feature_view_name: str,
    feature_registry_source: Dict[str, Any],
    sync_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Creates a feature view, linking feature groups and an online store.

    Args:
        project_id: Your GCP project ID.
        location: Region of the feature view.
        online_store_name: The name of the online store to associate with.
        feature_view_name: The name for the new feature view.
        feature_registry_source: Dictionary containing feature_registry_source with feature_groups.
                                Example: {"feature_groups": [{"feature_group_id": "fg_1", "feature_ids": ["feat_a", "feat_b"]}]}
        sync_config: Optional configuration for data synchronization.
                    Example: {"cron": "0 0 * * *"}

    Returns:
        A dictionary with the status and details of the created feature view.
    """
    if not project_id or not online_store_name or not feature_view_name or not feature_registry_source:
        raise ValueError("All required parameters must be provided.")

    try:
        init_aiplatform(project_id, location)
        
        logger.info(f"Creating FeatureView '{feature_view_name}' for OnlineStore '{online_store_name}'...")
        
        # Get access token using gcloud
        try:
            access_token = subprocess.check_output(
                ["gcloud", "auth", "print-access-token"], 
                text=True, 
                stderr=subprocess.PIPE
            ).strip()
        except subprocess.CalledProcessError as e:
            error_message = f"Failed to get access token: {e.stderr}"
            logger.error(error_message)
            raise RuntimeError(error_message)
        
        # Construct the API URL
        api_url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/featureOnlineStores/{online_store_name}/featureViews?feature_view_id={feature_view_name}"
        
        # Prepare the request body
        request_body = {
            "feature_registry_source": feature_registry_source
        }
        
        # Add sync config if provided
        if sync_config:
            request_body["sync_config"] = sync_config
        
        logger.info(f"API URL: {api_url}")
        logger.info(f"Request body: {json.dumps(request_body, indent=2)}")
        
        # Make the POST request
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        response = requests.post(api_url, headers=headers, json=request_body)
        
        if response.status_code == 200:
            response_data = response.json()
            logger.info(f"FeatureView created successfully: {response_data.get('name', 'N/A')}")
        else:
            error_message = f"API request failed with status {response.status_code}: {response.text}"
            logger.error(error_message)
            raise RuntimeError(error_message)
        
        return {
            "status": "success",
            "message": f"FeatureView '{feature_view_name}' created successfully.",
            "feature_view_name": response_data.get('name', f"{online_store_name}/featureViews/{feature_view_name}"),
            "online_store_name": online_store_name,
            "feature_registry_source": feature_registry_source,
            "sync_config": sync_config,
            "response_data": response_data
        }
        
    except google_exceptions.AlreadyExists:
        return {"status": "already_exists", "message": f"FeatureView '{feature_view_name}' already exists."}
    except Exception as e:
        error_message = f"An unexpected error occurred creating FeatureView '{feature_view_name}': {repr(e)}"
        logger.error(error_message)
        raise RuntimeError(error_message) from e

def list_feature_views(project_id: str, location: str, online_store_name: str) -> List[Dict[str, Any]]:
    """
    Lists all feature views for a given online store.

    Args:
        project_id: Your GCP project ID.
        location: The GCP region of the online store.
        online_store_name: The name of the online store.

    Returns:
        A list of dictionaries, where each dictionary represents a feature view.
    """
    if not project_id or not online_store_name:
        raise ValueError("project_id and online_store_name are required.")

    try:
        init_aiplatform(project_id, location)
        
        logger.info(f"Listing FeatureViews for OnlineStore '{online_store_name}'...")
        
        # Get access token using gcloud
        try:
            access_token = subprocess.check_output(
                ["gcloud", "auth", "print-access-token"], 
                text=True, 
                stderr=subprocess.PIPE
            ).strip()
        except subprocess.CalledProcessError as e:
            error_message = f"Failed to get access token: {e.stderr}"
            logger.error(error_message)
            raise RuntimeError(error_message)
        
        # Construct the API URL
        api_url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/featureOnlineStores/{online_store_name}/featureViews"
        
        # Make the GET request
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            response_data = response.json()
            feature_views_list = []
            
            for fv in response_data.get('featureViews', []):
                feature_views_list.append({
                    "name": fv.get('name', 'N/A'),
                    "display_name": fv.get('displayName', 'N/A'),
                    "create_time": fv.get('createTime', None),
                    "update_time": fv.get('updateTime', None),
                    "labels": fv.get('labels', {}),
                    "sync_config": fv.get('syncConfig', None),
                    "feature_registry_source": fv.get('featureRegistrySource', {})
                })
            
            return feature_views_list
        else:
            error_message = f"API request failed with status {response.status_code}: {response.text}"
            logger.error(error_message)
            raise RuntimeError(error_message)

    except Exception as e:
        error_message = f"An unexpected error occurred listing FeatureViews for '{online_store_name}': {repr(e)}"
        logger.error(error_message)
        raise RuntimeError(error_message) from e 