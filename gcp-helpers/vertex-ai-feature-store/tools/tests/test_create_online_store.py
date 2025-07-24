#!/usr/bin/env python3
"""
Test script for create_online_store function.
"""

import sys
import os

# Add the tools directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from online_store_operations import create_online_store

def test_create_online_store():
    print("=== Testing create_online_store ===")
    print()
    
    # Parameters - using default values
    project_id = "ml-tool-playground"
    location = "us-central1"
    online_store_id = "test_online_store"
    
    print("\n" + "="*50)
    print(f"Testing create_online_store with:")
    print(f"  project_id: {project_id}")
    print(f"  location: {location}")
    print(f"  online_store_id: {online_store_id}")
    print("  optimized: True (always)")
    print("  public_endpoint: True (always)")
    print("="*50)
    print()
    
    try:
        result = create_online_store(
            project_id=project_id,
            location=location,
            online_store_id=online_store_id
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
    test_create_online_store() 