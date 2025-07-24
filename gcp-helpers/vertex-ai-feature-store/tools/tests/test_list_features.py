#!/usr/bin/env python3
"""
Test script for list_features function.
"""

import sys
import os

# Add the tools directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from feature_operations import list_features

def test_list_features():
    print("=== Testing list_features ===")
    print()
    
    # Parameters - using default values
    project_id = "ml-tool-playground"
    location = "us-central1"
    feature_group_id = "test_fg"
    
    print("\n" + "="*50)
    print(f"Testing list_features with:")
    print(f"  project_id: {project_id}")
    print(f"  location: {location}")
    print(f"  feature_group_id: {feature_group_id}")
    print("="*50)
    print()
    
    try:
        result = list_features(
            project_id=project_id,
            location=location,
            feature_group_id=feature_group_id
        )
        print("✅ Function executed successfully!")
        print(f"Found {len(result)} features:")
        for i, feature in enumerate(result, 1):
            print(f"\n{i}. Feature:")
            for key, value in feature.items():
                print(f"   {key}: {value}")
            
    except Exception as e:
        print("❌ Function failed with error:")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_list_features() 