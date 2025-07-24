#!/usr/bin/env python3
"""
Test script for list_feature_groups function.
"""

import sys
import os

# Add the tools directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from feature_group_operations import list_feature_groups

def test_list_feature_groups():
    print("=== Testing list_feature_groups ===")
    print()
    
    # Parameters - using default values
    project_id = "ml-tool-playground"
    location = "us-central1"
    
    print("\n" + "="*50)
    print(f"Testing list_feature_groups with:")
    print(f"  project_id: {project_id}")
    print(f"  location: {location}")
    print("="*50)
    print()
    
    try:
        result = list_feature_groups(
            project_id=project_id,
            location=location
        )
        print("✅ Function executed successfully!")
        print(f"Found {len(result)} feature groups:")
        for i, fg in enumerate(result, 1):
            print(f"\n{i}. Feature Group:")
            for key, value in fg.items():
                print(f"   {key}: {value}")
            
    except Exception as e:
        print("❌ Function failed with error:")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_list_feature_groups() 