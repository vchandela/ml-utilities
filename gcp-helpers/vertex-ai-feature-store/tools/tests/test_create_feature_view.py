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
    online_store_name = "user_serving_store"
    feature_view_name = "user_engagements_live_view"

    feature_group_ids = ["seekho_user_engagements_group_v2"]
    feature_ids_list = [["age_group"]]
    sync_cron = "0 0 * * *"
    print("\n" + "="*50)
    print(f"Testing create_feature_view with:")
    print(f"  project_id: {project_id}")
    print(f"  location: {location}")
    print(f"  online_store_name: {online_store_name}")
    print(f"  feature_view_name: {feature_view_name}")
    print(f"  feature_group_ids: {feature_group_ids}")
    print(f"  feature_ids_list: {feature_ids_list}")
    print(f"  sync_cron: {sync_cron}")
    print("="*50)
    print()
    
    try:
        result = create_feature_view(
            project_id=project_id,
            location=location,
            online_store_name=online_store_name,
            feature_view_name=feature_view_name,
            feature_group_ids=feature_group_ids,
            feature_ids_list=feature_ids_list,
            sync_cron=sync_cron
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