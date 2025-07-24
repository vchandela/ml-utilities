#!/usr/bin/env python3
"""
Test script for create_feature_group function.
"""

import sys
import os

# Add the tools directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from feature_group_operations import create_feature_group

def test_create_feature_group():
    print("=== Testing create_feature_group ===")
    print()
    
    # Parameters - using default values
    project_id = "ml-tool-playground"
    location = "us-central1"
    feature_group_id = "test_fg"
    bq_table_uri = "bq://ml-tool-playground.user_info.user_profile_features"
    entity_id_columns = ["user_id"]
    description = None
    
    # Handle labels input
    labels_input = None
    labels = None
    if labels_input:
        try:
            labels = {}
            for pair in labels_input.split(','):
                key, value = pair.split('=')
                labels[key.strip()] = value.strip()
        except ValueError:
            print("Invalid labels format. Using None.")
            labels = None
    
    print("\n" + "="*50)
    print(f"Testing create_feature_group with:")
    print(f"  project_id: {project_id}")
    print(f"  location: {location}")
    print(f"  feature_group_id: {feature_group_id}")
    print(f"  bq_table_uri: {bq_table_uri}")
    print(f"  entity_id_columns: {entity_id_columns}")
    print(f"  description: {description}")
    print(f"  labels: {labels}")
    print("="*50)
    print()
    
    try:
        result = create_feature_group(
            project_id=project_id,
            location=location,
            feature_group_id=feature_group_id,
            bq_table_uri=bq_table_uri,
            entity_id_columns=entity_id_columns,
            description=description,
            labels=labels
        )
        print("✅ Function executed successfully!")
        print("Result:")
        print(f"  Resource Name: {result.resource_name}")
        print(f"  Display Name: {result.name}")
        print(f"  Labels: {result.labels}")
        print(f"  BigQuery Source: {result.source.uri}")
        print(f"  Entity ID Columns: {result.source.entity_id_columns}")
            
    except Exception as e:
        print("❌ Function failed with error:")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_create_feature_group() 