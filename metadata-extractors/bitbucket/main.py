# bitbucket/main.py
import os
import asyncio
from dotenv import load_dotenv
import json  # For pretty printing results
import logging

# Import the connector
try:
    from .connector import BitbucketConnector
except ImportError:
    # Handle direct execution
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from bitbucket.connector import BitbucketConnector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Main function to orchestrate Bitbucket metrics collection."""
    load_dotenv()  # Load variables from .env file

    credentials = {
        "access_token": os.getenv("BITBUCKET_ACCESS_TOKEN"),
        "refresh_token": os.getenv("BITBUCKET_REFRESH_TOKEN"),
    }

    # Validate credentials before proceeding
    connector = BitbucketConnector()
    if not await connector.validate_credentials(credentials):
        logger.error("❌ Missing or invalid Bitbucket credentials.")
        logger.error("   Please set BITBUCKET_ACCESS_TOKEN and BITBUCKET_REFRESH_TOKEN in your .env file.")
        return

    # Connect to Bitbucket
    if not await connector.connect(credentials):
        logger.error("❌ Failed to connect to Bitbucket.")
        return

    # Fetch aggregated metrics
    logger.info("Fetching Bitbucket repository metrics...")
    start_time = asyncio.get_event_loop().time()
    
    metrics = await connector.get_repository_metrics()
    
    end_time = asyncio.get_event_loop().time()
    duration = end_time - start_time

    if "error" in metrics:
        logger.error(f"❌ Error fetching Bitbucket metrics: {metrics['error']}")
        return
        
    logger.info(f"✅ Bitbucket metrics collection completed in {duration:.2f} seconds!")
    
    # Display results
    global_counts = metrics.get("global_counts", {})
    repo_metrics = metrics.get("repo_metrics", {})

    print("\n--- Bitbucket Workspace Metrics ---")
    # Attempt to get workspace name from env or found repo data for clarity
    workspace_display = os.getenv("BITBUCKET_WORKSPACE", "N/A (Workspace name not set in env)")
    if not workspace_display or workspace_display == "N/A":
        # Try to infer from repo_metrics if available
        if repo_metrics:
            first_repo_name = next(iter(repo_metrics))
            workspace_display = first_repo_name.split('/')[0] if '/' in first_repo_name else "UnknownWorkspace"
            
    print(f"Workspace: {workspace_display}")
    print("----------------------------------")
    print("Global Counts:")
    print(f"  Total Repositories: {global_counts.get('repos', 0)}")
    print(f"  Total Files (text, <100MB): {global_counts.get('files', 0)}")
    print(f"  Total Pull Requests: {global_counts.get('PRs', 0)}")
    print(f"  Total Commits: {global_counts.get('commits', 0)}")
    print("----------------------------------")

    if repo_metrics:
        print("\nRepository-Level Breakdown:")
        for repo_name, counts in repo_metrics.items():
            print(f"  Repo: {repo_name}")
            print(f"    Files: {counts.get('files', 0)}")
            print(f"    PRs: {counts.get('PRs', 0)}")
            print(f"    Commits: {counts.get('commits', 0)}")
            if "error" in counts:
                print(f"    Error: {counts['error']}")
            if "warning" in counts:
                print(f"    Warning: {counts['warning']}")
    else:
        print("\nNo repository-level breakdown available.")
        
if __name__ == "__main__":
    asyncio.run(main()) 