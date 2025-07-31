#!/usr/bin/env python3
"""
Test script for get_feature_group function.
"""

import sys
import os

# Add the tools directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from feature_group_operations import get_feature_group

def test_get_feature_group():
    print("=== Testing get_feature_group ===")
    print()
    
    # Parameters - using default values
    project_id = "ml-tool-playground"
    location = "us-central1"
    feature_group_id = "seekho_user_engagements_fg"
    
    print("\n" + "="*50)
    print(f"Testing get_feature_group with:")
    print(f"  project_id: {project_id}")
    print(f"  location: {location}")
    print(f"  feature_group_id: {feature_group_id}")
    print("="*50)
    print()
    
    try:
        result = get_feature_group(
            project_id=project_id,
            location=location,
            feature_group_id=feature_group_id
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
    test_get_feature_group() 