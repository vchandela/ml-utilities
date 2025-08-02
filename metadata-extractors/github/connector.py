# github/connector.py
# Import necessary functions from client.py and data_processor.py
from .client import (
    fetch_organizations, fetch_repos, count_pull_requests_for_repo, fetch_commit_count,
    clone_repo_into_fs, get_local_repo_path, GitHubApiHandler, _SESSION
)
from .data_processor import count_files_in_repo

import logging
import asyncio
import os
from typing import Dict, Any, List, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Placeholder for the Union type, as we're focusing on counts (Dict[str, int])
# If detailed artifacts were needed, this would be more complex.
GitHubMetadataItem = Dict[str, Any] 

class GitHubConnector:
    def __init__(self):
        self.access_token: Optional[str] = None
        self.org_name: Optional[str] = None
        self.repos: Optional[List[Dict[str, Any]]] = None
        self.credentials: Dict[str, Any] = {}
        logger.debug("GitHubConnector initialized.")

    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """Validates GitHub credentials."""
        is_valid = bool(credentials.get("access_token"))
        if not is_valid:
            logger.error("GitHub credentials validation failed. Missing 'access_token'.")
        return is_valid

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Connects to GitHub by storing credentials and performing an initial check."""
        logger.info("Connecting to GitHub...")
        if not await self.validate_credentials(credentials):
            return False
        
        self.credentials = credentials.copy()
        # Validate token by attempting a simple API call
        if not await self._check_connection():
            logger.error("Failed to establish GitHub connection or validate token.")
            return False
        
        logger.info("GitHub connection established successfully.")
        return True

    async def _check_connection(self) -> bool:
        """Checks GitHub connection validity."""
        logger.debug("Checking GitHub connection status...")
        try:
            # Create API handler
            headers = {
                "Authorization": f"Bearer {self.credentials['access_token']}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "GitHub-Metadata-Extractor"
            }
            api_handler = GitHubApiHandler(_SESSION, headers)
            
            # Use a simple API call to verify token validity
            response = await api_handler.request_with_retries("GET", "https://api.github.com/user")
            if response and response.status_code == 200:
                logger.debug("GitHub connection check successful.")
                return True
            else:
                logger.error("GitHub connection check failed: Invalid API response.")
                return False
        except Exception as e:
            logger.error(f"Error during GitHub connection check: {str(e)}", exc_info=True)
            return False

    async def get_repository_metrics(self) -> Dict[str, Any]:
        """Fetches aggregate counts of repos, files, PRs, and commits for the organization."""
        logger.info("Starting GitHub repository metrics aggregation...")
        
        if not self.credentials:
            logger.error("GitHub connector is not connected. Call connect() first.")
            return {"error": "Not connected"}
        
        # 1. Fetch Organizations and Repos
        orgs_data = await fetch_organizations(self.credentials)
        if not orgs_data:
            return {"error": "Failed to fetch organizations. Check token/permissions."}
        
        org = orgs_data[0]  # Process only the first organization
        org_name = org.get("login") or org.get("name")
        if not org_name:
            return {"error": "Could not determine organization name."}
        
        logger.info(f"Processing metrics for first organization: '{org_name}'")
        repos = await fetch_repos(org_name, self.credentials, limit=1000)
        if not repos:
            logger.warning(f"No repositories found in organization '{org_name}'. Returning empty metrics.")
            return {"global_counts": {"repos": 0, "files": 0, "PRs": 0, "commits": 0}, "repo_metrics": {}}
        
        # 2. Prepare concurrent tasks for processing each repository's counts
        repo_metric_tasks = []
        for repo in repos:
            repo_name = repo.get("name")
            if not repo_name:
                continue  # Skip repo if name is missing
            
            default_branch = repo.get("default_branch", "main")  # Default to 'main'
            
            task = asyncio.create_task(
                self._process_single_repo_counts(org_name, repo_name, default_branch, self.credentials)
            )
            repo_metric_tasks.append((repo_name, task))
        
        # Execute tasks concurrently
        logger.info(f"Launching {len(repo_metric_tasks)} concurrent tasks for repository metrics...")
        results = await asyncio.gather(*(task for _, task in repo_metric_tasks), return_exceptions=True)
        
        # 3. Aggregate Results
        all_repo_metrics = {}
        global_counts = {"repos": 0, "files": 0, "PRs": 0, "commits": 0}
        
        for i, result in enumerate(results):
            repo_name, _ = repo_metric_tasks[i]
            
            if isinstance(result, Exception):
                logger.error(f"Error processing metrics for repo '{repo_name}': {str(result)}", exc_info=True)
                repo_metrics_data = {"repo": 1, "files": 0, "PRs": 0, "commits": 0, "error": str(result)}
            elif result is None:  # Handle cases where a function returned None explicitly (e.g., cloning failed)
                logger.warning(f"Metric processing returned None for repo '{repo_name}'.")
                repo_metrics_data = {"repo": 1, "files": 0, "PRs": 0, "commits": 0, "warning": "Metric calculation failed."}
            else:  # Successfully got metrics for this repo
                repo_metrics_data = result
            
            all_repo_metrics[repo_name] = repo_metrics_data
            # Add to global counts (only for valid dictionary results)
            if isinstance(repo_metrics_data, dict):
                repo_val = repo_metrics_data.get("repo", 0)
                files_val = repo_metrics_data.get("files", 0)
                prs_val = repo_metrics_data.get("PRs", 0)
                commits_val = repo_metrics_data.get("commits", 0)
                
                global_counts["repos"] += repo_val if isinstance(repo_val, int) else 0
                global_counts["files"] += files_val if isinstance(files_val, int) else 0
                global_counts["PRs"] += prs_val if isinstance(prs_val, int) else 0
                global_counts["commits"] += commits_val if isinstance(commits_val, int) else 0
        
        logger.info(f"Finished aggregating metrics for organization '{org_name}'.")
        return {
            "global_counts": global_counts,
            "repo_metrics": all_repo_metrics
        }

    async def _process_single_repo_counts(self, org_name: str, repo_name: str, default_branch: str, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Fetches counts for files, PRs, and commits for a single repo."""
        logger.info(f"Fetching counts for repo: {org_name}/{repo_name}...")
        repo_counts = {"repo": 1, "files": 0, "PRs": 0, "commits": 0}  # Default counts
        
        try:
            # Create API handler for this repo's operations
            headers = {
                "Authorization": f"Bearer {credentials['access_token']}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "GitHub-Metadata-Extractor"
            }
            api_handler = GitHubApiHandler(_SESSION, headers)
            
            # Fetch counts concurrently
            # File count uses GitHub API (efficient), PR count uses API, commit count needs cloning
            file_count_task = count_files_in_repo(org_name, repo_name, default_branch, credentials)
            pr_count_task = count_pull_requests_for_repo(api_handler, org_name, repo_name)
            commit_count_task = fetch_commit_count(org_name, repo_name, credentials)
            
            file_count, pr_count, commit_count = await asyncio.gather(
                file_count_task, pr_count_task, commit_count_task,
                return_exceptions=True  # Catch errors for individual counts
            )
            
            repo_counts["files"] = file_count if isinstance(file_count, int) else 0
            repo_counts["PRs"] = pr_count if isinstance(pr_count, int) else 0
            repo_counts["commits"] = commit_count if isinstance(commit_count, int) else 0
            
            # Log errors for specific counts if they occurred
            if isinstance(file_count, Exception):
                logger.error(f"Error getting file count for {repo_name}: {file_count}")
            if isinstance(pr_count, Exception):
                logger.error(f"Error getting PR count for {repo_name}: {pr_count}")
            if isinstance(commit_count, Exception):
                logger.error(f"Error getting commit count for {repo_name}: {commit_count}")
            
            logger.info(f"Counts for {org_name}/{repo_name}: Files={repo_counts['files']}, PRs={repo_counts['PRs']}, Commits={repo_counts['commits']}")
            return repo_counts
            
        except Exception as e:
            logger.error(f"Failed to get counts for repo {org_name}/{repo_name}: {str(e)}", exc_info=True)
            # Return partial counts with an error indicator
            return {
                "repo": 1, "files": repo_counts.get("files", 0),
                "PRs": repo_counts.get("PRs", 0), "commits": repo_counts.get("commits", 0),
                "error": str(e)
            }

    def close(self) -> None:
        """Close the GitHub connection and clear tokens."""
        logger.info("Closing GitHubConnector connection.")
        self.access_token = None
        self.org_name = None
        self.repos = None
        self.credentials = {}

    def __del__(self):
        self.close() 