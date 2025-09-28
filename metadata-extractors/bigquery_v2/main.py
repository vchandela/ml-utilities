#!/usr/bin/env python3
"""
BigQuery Golden Query Feature Extractor - Main Entry Point

Entry point for the Golden Query Feature Extraction PoC.
"""

import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the golden query feature extractor
from query_feature_extractor import main as run_feature_extraction

async def main():
    """Main function to run the Golden Query Feature Extractor"""
    try:
        print("🔄 Starting Golden Query analysis...")
        start_time = datetime.now()
        
        # Run the feature extraction process
        await run_feature_extraction()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"✅ Analysis completed in {duration:.2f} seconds!")
        
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing BIGQUERY_SA_CREDS_JSON: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
