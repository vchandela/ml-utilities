"""
GitHub Metadata Extractor

This module provides functionality to extract metadata from GitHub including:
- Repository counts (total repositories in organization)
- File counts (text files only, with size limits, excluding .git)
- Pull Request counts (all valid PRs with essential fields)
- Commit counts (using git operations on cloned repositories)

Authentication is handled via GitHub Personal Access Tokens (PAT).
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import the main connector
from .connector import GitHubConnector

# Configure logging
logger = logging.getLogger(__name__)


class GitHubMetadataExtractor:
    """Main class for extracting metadata from GitHub repositories"""
    
    def __init__(self, credentials: Dict[str, Any]):
        """
        Initialize GitHub metadata extractor
        
        Args:
            credentials: Dictionary containing:
                - access_token: GitHub Personal Access Token (PAT)
        """
        self.credentials = credentials
        self.access_token = credentials.get('access_token')
        self.connector: Optional[GitHubConnector] = None
        
        self._validate_credentials()

    def _validate_credentials(self):
        """Validate required credentials"""
        if not self.access_token:
            raise ValueError("GitHub access_token is required")
        
        logger.info("GitHub credentials validated successfully")

    async def connect(self) -> bool:
        """Establish connection to GitHub"""
        logger.info("Connecting to GitHub API...")
        
        self.connector = GitHubConnector()
        connected = await self.connector.connect(self.credentials)
        
        if connected:
            logger.info("Successfully connected to GitHub")
        else:
            logger.error("Failed to connect to GitHub")
            
        return connected

    async def extract_repository_counts(self) -> Dict[str, Any]:
        """
        Extract repository counts from GitHub organization
        
        Returns:
            Dictionary containing:
                - global_counts: Aggregate counts across all repositories
                - repo_metrics: Per-repository breakdown of counts
        
        Raises:
            RuntimeError: If not connected to GitHub
        """
        if not self.connector:
            raise RuntimeError("Not connected to GitHub. Call connect() first.")
        
        logger.info("Starting GitHub repository count extraction...")
        start_time = datetime.now()
        
        try:
            metrics = await self.connector.get_repository_metrics()
            
            if "error" in metrics:
                logger.error(f"Error extracting repository counts: {metrics['error']}")
                return metrics
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Add extraction metadata
            metrics["extraction_metadata"] = {
                "extraction_time": start_time.isoformat(),
                "duration_seconds": duration,
                "extractor_version": "1.0.0",
                "source": "github_api_and_git"
            }
            
            global_counts = metrics.get("global_counts", {})
            repo_count = len(metrics.get("repo_metrics", {}))
            
            logger.info(f"Successfully extracted GitHub repository counts in {duration:.2f}s:")
            logger.info(f"  - Total Organizations Processed: 1")
            logger.info(f"  - Total Repositories: {global_counts.get('repos', 0)}")
            logger.info(f"  - Total Files: {global_counts.get('files', 0)}")
            logger.info(f"  - Total Pull Requests: {global_counts.get('PRs', 0)}")
            logger.info(f"  - Total Commits: {global_counts.get('commits', 0)}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to extract repository counts: {str(e)}", exc_info=True)
            return {"error": f"Extraction failed: {str(e)}"}

    async def get_organization_summary(self) -> Dict[str, Any]:
        """
        Get a high-level summary of the GitHub organization
        
        Returns:
            Dictionary with organization summary information
        """
        if not self.connector:
            raise RuntimeError("Not connected to GitHub. Call connect() first.")
        
        try:
            metrics = await self.connector.get_repository_metrics()
            
            if "error" in metrics:
                return {"error": metrics["error"]}
            
            global_counts = metrics.get("global_counts", {})
            repo_metrics = metrics.get("repo_metrics", {})
            
            # Calculate additional summary statistics
            repos_with_files = sum(1 for repo_data in repo_metrics.values() 
                                 if isinstance(repo_data, dict) and repo_data.get("files", 0) > 0)
            repos_with_prs = sum(1 for repo_data in repo_metrics.values() 
                               if isinstance(repo_data, dict) and repo_data.get("PRs", 0) > 0)
            repos_with_commits = sum(1 for repo_data in repo_metrics.values() 
                                   if isinstance(repo_data, dict) and repo_data.get("commits", 0) > 0)
            
            avg_files_per_repo = (global_counts.get("files", 0) / max(global_counts.get("repos", 1), 1))
            avg_prs_per_repo = (global_counts.get("PRs", 0) / max(global_counts.get("repos", 1), 1))
            avg_commits_per_repo = (global_counts.get("commits", 0) / max(global_counts.get("repos", 1), 1))
            
            summary = {
                "organization_totals": global_counts,
                "repository_statistics": {
                    "total_repositories": global_counts.get("repos", 0),
                    "repositories_with_files": repos_with_files,
                    "repositories_with_pull_requests": repos_with_prs,
                    "repositories_with_commits": repos_with_commits,
                },
                "average_metrics": {
                    "avg_files_per_repository": round(avg_files_per_repo, 2),
                    "avg_pull_requests_per_repository": round(avg_prs_per_repo, 2),
                    "avg_commits_per_repository": round(avg_commits_per_repo, 2),
                },
                "summary_generated_at": datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate organization summary: {str(e)}", exc_info=True)
            return {"error": f"Summary generation failed: {str(e)}"}

    def export_metrics_to_json(self, metrics: Dict[str, Any], output_file: str) -> bool:
        """
        Export metrics to a JSON file
        
        Args:
            metrics: The metrics dictionary to export
            output_file: Path to the output JSON file
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            with open(output_file, 'w') as f:
                json.dump(metrics, f, indent=2, default=str)
            
            logger.info(f"Successfully exported metrics to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export metrics to {output_file}: {str(e)}", exc_info=True)
            return False

    def close(self):
        """Close the GitHub connection"""
        if self.connector:
            self.connector.close()
            self.connector = None
        logger.info("GitHub metadata extractor connection closed")

    def __del__(self):
        """Cleanup on object destruction"""
        self.close()

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self.close()


# Convenience function for quick extraction
async def extract_github_repository_counts(credentials: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to extract GitHub repository counts
    
    Args:
        credentials: Dictionary with 'access_token' key
        
    Returns:
        Dictionary with repository counts and metrics
    """
    async with GitHubMetadataExtractor(credentials) as extractor:
        return await extractor.extract_repository_counts()


# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    async def main():
        load_dotenv()
        
        credentials = {
            "access_token": os.getenv("GITHUB_TOKEN")
        }
        
        if not credentials["access_token"]:
            print("Error: GITHUB_TOKEN not found in environment")
            return
        
        async with GitHubMetadataExtractor(credentials) as extractor:
            metrics = await extractor.extract_repository_counts()
            print(json.dumps(metrics, indent=2, default=str))
    
    asyncio.run(main()) 