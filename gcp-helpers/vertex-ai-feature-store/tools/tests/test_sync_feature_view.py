#!/usr/bin/env python3
"""
Test script for sync_feature_view function.
"""

import sys
import os

# Add the tools directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sync_operations import sync_feature_view

def test_sync_feature_view():
    print("=== Testing sync_feature_view ===")
    print()
    
    # Parameters - using default values
    project_id = "ml-tool-playground"
    location = "us-central1"
    online_store_name = "test_online_store"
    feature_view_name = "test_feature_view"
    
    print("\n" + "="*50)
    print(f"Testing sync_feature_view with:")
    print(f"  project_id: {project_id}")
    print(f"  location: {location}")
    print(f"  online_store_name: {online_store_name}")
    print(f"  feature_view_name: {feature_view_name}")
    print("="*50)
    print()
    
    try:
        result = sync_feature_view(
            project_id=project_id,
            location=location,
            online_store_name=online_store_name,
            feature_view_name=feature_view_name
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
    test_sync_feature_view() 