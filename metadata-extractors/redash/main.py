#!/usr/bin/env python3
"""
Redash Metadata Extractor - Main Entry Point

Simple script to extract Redash metadata using environment variables.
"""

import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the metadata extractor
from metadata import extract_metadata

async def main():
    """Main function to extract Redash metadata"""
    try:
        # Load credentials from environment variables
        api_url = os.getenv('REDASH_API_URL')
        api_key = os.getenv('REDASH_API_KEY')
        
        if not all([api_url, api_key]):
            print("❌ Missing required environment variables:")
            print("   Please set REDASH_API_URL and REDASH_API_KEY")
            print("   in your .env file or environment variables.")
            return
        
        credentials = {
            'api_url': api_url,
            'api_key': api_key
        }
        
        print("🔧 Redash Metadata Extractor")
        print("="*40)
        print(f"🌐 Redash URL: {credentials['api_url']}")
        api_key_display = credentials['api_key']
        if api_key_display and len(api_key_display) > 4:
            api_key_display = '*' * (len(api_key_display) - 4) + api_key_display[-4:]
        print(f"🔑 API Key: {api_key_display}")
        print()
        
        print("🔄 Extracting metadata...")
        start_time = datetime.now()
        
        # Call the extract_metadata function
        metadata = await extract_metadata(credentials)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if "error" in metadata:
            print(f"❌ {metadata['error']}")
            return
            
        print(f"✅ Extraction completed in {duration:.2f} seconds!")
        
        # Print the summary
        counts = metadata.get('counts', {})
        print(f"\n📊 Results:")
        print(f"   - Dashboards: {counts.get('dashboards', 0)}")
        print(f"   - Widgets: {counts.get('widgets', 0)}")
        print(f"   - Saved Queries: {counts.get('saved_queries', 0)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 