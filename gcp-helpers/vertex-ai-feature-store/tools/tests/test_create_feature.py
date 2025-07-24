#!/usr/bin/env python3
"""
Test script for create_feature function.
"""

import sys
import os

# Add the tools directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from feature_operations import create_feature

def test_create_feature():
    print("=== Testing create_feature ===")
    print()
    
    # Parameters - using default values
    project_id = "ml-tool-playground"
    location = "us-central1"
    feature_group_id = "test_fg"
    feature_id = "test_feature"
    version_column_name = "gender"
    description = None
    
    print("\n" + "="*50)
    print(f"Testing create_feature with:")
    print(f"  project_id: {project_id}")
    print(f"  location: {location}")
    print(f"  feature_group_id: {feature_group_id}")
    print(f"  feature_id: {feature_id}")
    print(f"  version_column_name: {version_column_name}")
    print(f"  description: {description}")
    print("="*50)
    print()
    
    try:
        result = create_feature(
            project_id=project_id,
            location=location,
            feature_group_id=feature_group_id,
            feature_id=feature_id,
            version_column_name=version_column_name,
            description=description
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
    test_create_feature() 