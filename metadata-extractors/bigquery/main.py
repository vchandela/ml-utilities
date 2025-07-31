#!/usr/bin/env python3
"""
BigQuery Metadata Counter - Main Entry Point

Simple script to count BigQuery resources using environment variables.
"""

import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the metadata counter
from metadata import extract_metadata

async def main():
    """Main function to extract BigQuery metadata counts"""
    try:
        # Load credentials from environment variables
        sa_creds_json = os.getenv('BIGQUERY_SA_CREDS_JSON')
        project_id = os.getenv('BIGQUERY_PROJECT_ID')
        client_email = os.getenv('BIGQUERY_CLIENT_EMAIL')
        # Read the env var for query history
        query_days_back = int(os.getenv('QUERY_DAYS_BACK', 800))
        
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
        
        print("🔧 BigQuery Metadata Counter")
        print("="*40)
        print(f"📁 Project: {credentials['project_id']}")
        print(f"👤 Service Account: {credentials['client_email']}")
        print(f"🗓️ Query History: Last {query_days_back} days")
        print()
        
        print("🔄 Counting resources...")
        start_time = datetime.now()
        
        # Call the updated extract_metadata function
        metadata = await extract_metadata(credentials, query_days_back=query_days_back)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if "error" in metadata:
            print(f"❌ {metadata['error']}")
            return
            
        print(f"✅ Counting completed in {duration:.2f} seconds!")
        
        # Print the new, simplified summary
        counts = metadata.get('counts', {})
        print(f"\n📊 Results:")
        print(f"   - Datasets: {counts.get('datasets', 0)}")
        print(f"   - Logical Tables: {counts.get('logical_tables', 0)}")
        print(f"   - Unique Queries (last {query_days_back} days): {counts.get('unique_queries', 0)}")
        
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing BIGQUERY_SA_CREDS_JSON: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 