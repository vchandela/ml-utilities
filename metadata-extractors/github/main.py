# github/main.py
import os
import asyncio
from dotenv import load_dotenv
import json  # For pretty printing results
import logging

# Import the connector
try:
    from .connector import GitHubConnector
except ImportError:
    # Handle direct execution
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from github.connector import GitHubConnector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Main function to orchestrate GitHub metrics collection."""
    load_dotenv()  # Load variables from .env file

    credentials = {
        "access_token": os.getenv("GITHUB_TOKEN"),
        # No refresh token needed for GitHub PATs
    }

    # Validate credentials before proceeding
    connector = GitHubConnector()
    if not await connector.validate_credentials(credentials):
        logger.error("❌ Missing or invalid GitHub credentials.")
        logger.error("   Please set GITHUB_TOKEN in your .env file.")
        logger.error("   Make sure your Personal Access Token has 'repo' scope.")
        return

    # Connect to GitHub
    if not await connector.connect(credentials):
        logger.error("❌ Failed to connect to GitHub.")
        return

    # Fetch aggregated metrics
    logger.info("Fetching GitHub repository metrics...")
    start_time = asyncio.get_event_loop().time()
    
    metrics = await connector.get_repository_metrics()
    
    end_time = asyncio.get_event_loop().time()
    duration = end_time - start_time

    if "error" in metrics:
        logger.error(f"❌ Error fetching GitHub metrics: {metrics['error']}")
        return
        
    logger.info(f"✅ GitHub metrics collection completed in {duration:.2f} seconds!")
    
    # Display results
    global_counts = metrics.get("global_counts", {})
    repo_metrics = metrics.get("repo_metrics", {})

    print("\n" + "="*50)
    print("🔧 GitHub Repository Metrics")
    print("="*50)
    
    # Attempt to get organization name from env or infer from repo data
    org_display = os.getenv("GITHUB_ORG", "N/A")
    if org_display == "N/A" and repo_metrics:
        # Try to infer from first repo's full_name if available
        first_repo_name = next(iter(repo_metrics))
        if '/' in first_repo_name:
            org_display = first_repo_name.split('/')[0]
        else:
            org_display = "UnknownOrganization"
            
    print(f"📁 Organization: {org_display}")
    print(f"⏱️  Processing Time: {duration:.2f} seconds")
    print("-" * 50)
    
    print("📊 Global Counts:")
    print(f"  🏢 Total Repositories: {global_counts.get('repos', 0)}")
    print(f"  📄 Total Files (text, <100MB): {global_counts.get('files', 0)}")
    print(f"  🔀 Total Pull Requests: {global_counts.get('PRs', 0)}")
    print(f"  📝 Total Commits: {global_counts.get('commits', 0)}")
    print("-" * 50)

    if repo_metrics:
        print(f"\n📋 Repository-Level Breakdown ({len(repo_metrics)} repositories):")
        print("-" * 50)
        
        # Sort repositories by total activity (files + PRs + commits) for better display
        sorted_repos = sorted(
            repo_metrics.items(), 
            key=lambda x: (x[1].get('files', 0) + x[1].get('PRs', 0) + x[1].get('commits', 0)) if isinstance(x[1], dict) else 0,
            reverse=True
        )
        
        for repo_name, counts in sorted_repos:
            if isinstance(counts, dict):
                print(f"  📦 {repo_name}:")
                print(f"    📄 Files: {counts.get('files', 0)}")
                print(f"    🔀 PRs: {counts.get('PRs', 0)}")
                print(f"    📝 Commits: {counts.get('commits', 0)}")
                
                # Show any errors or warnings
                if "error" in counts:
                    print(f"    ❌ Error: {counts['error']}")
                if "warning" in counts:
                    print(f"    ⚠️  Warning: {counts['warning']}")
                print()  # Empty line for readability
        
        # Calculate and display summary statistics
        total_repos = len(repo_metrics)
        active_repos = sum(1 for counts in repo_metrics.values() 
                          if isinstance(counts, dict) and 
                          (counts.get('files', 0) > 0 or counts.get('PRs', 0) > 0 or counts.get('commits', 0) > 0))
        
        print("📈 Summary Statistics:")
        print(f"  Active Repositories: {active_repos}/{total_repos} ({(active_repos/max(total_repos,1)*100):.1f}%)")
        
        if global_counts.get('repos', 0) > 0:
            avg_files = global_counts.get('files', 0) / global_counts.get('repos', 1)
            avg_prs = global_counts.get('PRs', 0) / global_counts.get('repos', 1)
            avg_commits = global_counts.get('commits', 0) / global_counts.get('repos', 1)
            
            print(f"  Average Files per Repo: {avg_files:.1f}")
            print(f"  Average PRs per Repo: {avg_prs:.1f}")
            print(f"  Average Commits per Repo: {avg_commits:.1f}")
    else:
        print("\n📋 No repository-level breakdown available.")
    
    print("\n" + "="*50)
    print("✅ GitHub metrics collection completed successfully!")
    print("="*50)
    
    # Close the connector
    connector.close()

if __name__ == "__main__":
    asyncio.run(main()) 