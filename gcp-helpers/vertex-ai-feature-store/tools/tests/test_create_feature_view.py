#!/usr/bin/env python3
"""
Test script for create_feature_view function.
"""

import sys
import os
import json

# Add the tools directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from feature_view_operations import create_feature_view

def test_create_feature_view():
    print("=== Testing create_feature_view ===")
    print()
    
    # Parameters - using default values
    project_id = "ml-tool-playground"
    location = "us-central1"
    online_store_name = "test_online_store"
    feature_view_name = "test_feature_view"

    feature_registry_source = {
        "feature_groups": [
            {
                "feature_group_id": "test_fg",
                "feature_ids": ["test_feature"]
            }
        ]
    }

    sync_config = {
        "cron": "0 0 * * *"
    }
    print("\n" + "="*50)
    print(f"Testing create_feature_view with:")
    print(f"  project_id: {project_id}")
    print(f"  location: {location}")
    print(f"  online_store_name: {online_store_name}")
    print(f"  feature_view_name: {feature_view_name}")
    print(f"  feature_registry_source: {json.dumps(feature_registry_source, indent=2)}")
    print(f"  sync_config: {sync_config}")
    print("="*50)
    print()
    
    try:
        result = create_feature_view(
            project_id=project_id,
            location=location,
            online_store_name=online_store_name,
            feature_view_name=feature_view_name,
            feature_registry_source=feature_registry_source,
            sync_config=sync_config
        )
        print("✅ Function executed successfully!")
        print("Result:")
        for key, value in result.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        print("❌ Function failed with error:")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_create_feature_view() 