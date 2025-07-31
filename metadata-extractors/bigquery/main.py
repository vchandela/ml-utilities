#!/usr/bin/env python3
"""
BigQuery Metadata Extractor - Main Entry Point

Simple script to extract BigQuery metadata using environment variables.
"""

import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the metadata extractor
from metadata import extract_metadata

async def main():
    """Main function to extract BigQuery metadata"""
    try:
        # Load credentials from environment variables
        sa_creds_json = os.getenv('BIGQUERY_SA_CREDS_JSON')
        project_id = os.getenv('BIGQUERY_PROJECT_ID')
        client_email = os.getenv('BIGQUERY_CLIENT_EMAIL')
        region = os.getenv('BIGQUERY_REGION', 'US')  # Default to 'US' if not set
        
        if not all([sa_creds_json, project_id, client_email]):
            print("❌ Missing required environment variables:")
            print("   Please set BIGQUERY_SA_CREDS_JSON, BIGQUERY_PROJECT_ID, and BIGQUERY_CLIENT_EMAIL")
            print("   in your .env file or environment variables.")
            return
        
        credentials = {
            'sa_creds_json': json.loads(sa_creds_json) if sa_creds_json else {},
            'project_id': project_id,
            'client_email': client_email
        }
        
        print("🔧 BigQuery Metadata Extractor")
        print("="*40)
        print(f"📁 Project: {credentials['project_id']}")
        print(f"👤 Service Account: {credentials['client_email']}")
        print(f"🌍 Region: {region}")
        print()
        
        print("🔄 Extracting metadata...")
        start_time = datetime.now()
        
        # Extract all metadata
        metadata = await extract_metadata(credentials, region=region)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"✅ Extraction completed in {duration:.2f} seconds!")
        
        # Print summary
        counts = metadata.get('document_counts', {})
        print(f"\n📊 Summary:")
        print(f"   Datasets: {counts.get('datasets', 0)}")
        print(f"   Tables: {counts.get('tables', 0)}")
        print(f"   Views: {counts.get('views', 0)}")
        print(f"   Queries: {len(metadata.get('queries', []))}")
        
        # Print full results
        print(f"\n📄 Full Results:")
        print(json.dumps(metadata, indent=2, default=str))
        
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing BIGQUERY_SA_CREDS_JSON: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 