#!/usr/bin/env python3
"""
Test script for fetch_feature_values function.
"""

import sys
import os

# Add the tools directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fetch_operations import fetch_feature_values

def test_fetch_feature_values():
    print("=== Testing fetch_feature_values ===")
    print()
    
    # Parameters - using default values
    project_id = "ml-tool-playground"
    location = "us-central1"
    online_store_name = "user_profile_serving"
    feature_view_name = "	v_user_profile_features_v2"
    target_entity_id = "user_89"
    format_value = "KEY_VALUE"
    
    print("\n" + "="*50)
    print(f"Testing fetch_feature_values with:")
    print(f"  project_id: {project_id}")
    print(f"  location: {location}")
    print(f"  online_store_name: {online_store_name}")
    print(f"  feature_view_name: {feature_view_name}")
    print(f"  target_entity_id: {target_entity_id}")
    print(f"  format: {format_value}")
    print("="*50)
    print()
    
    try:
        result = fetch_feature_values(
            project_id=project_id,
            location=location,
            online_store_name=online_store_name,
            feature_view_name=feature_view_name,
            target_entity_id=target_entity_id,
            format=format_value
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
    test_fetch_feature_values() 