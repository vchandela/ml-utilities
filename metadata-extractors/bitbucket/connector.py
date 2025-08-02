# bitbucket/connector.py
# Import necessary functions from client.py and data_processor.py
from .client import (
    fetch_workspaces, fetch_repos, count_pull_requests_for_repo, fetch_commit_count,
    clone_repo_into_fs, get_local_repo_path, _async_request_with_retries, MAX_REPOS_PER_WORKSPACE_LIMIT
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
BitbucketMetadataItem = Dict[str, Any] 

class BitbucketConnector:
    def __init__(self):
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.workspace_name: Optional[str] = None
        self.repos: Optional[List[Dict[str, Any]]] = None
        self.credentials: Dict[str, Any] = {}
        logger.debug("BitbucketConnector initialized.")

    async def validate_credentials(self, credentials: Dict[str, Any]) -> bool:
        """Validates Bitbucket credentials."""
        is_valid = bool(credentials.get("access_token") and credentials.get("refresh_token"))
        if not is_valid:
            logger.error("Bitbucket credentials validation failed. Missing 'access_token' or 'refresh_token'.")
        return is_valid

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Connects to Bitbucket by storing credentials and performing an initial check."""
        logger.info("Connecting to Bitbucket...")
        if not await self.validate_credentials(credentials):
            return False
        
        self.credentials = credentials.copy()
        # Validate token by attempting a simple API call
        if not await self._check_connection():
            logger.error("Failed to establish Bitbucket connection or validate tokens.")
            return False
        
        logger.info("Bitbucket connection established successfully.")
        return True

    async def _check_connection(self) -> bool:
        """Checks Bitbucket connection validity and refreshes token if necessary."""
        logger.debug("Checking Bitbucket connection status...")
        try:
            # Use a simple API call to verify token validity
            user_info = await _async_request_with_retries("https://api.bitbucket.org/2.0/user", "GET", {}, self.credentials)
            if user_info is not None:
                logger.debug("Bitbucket connection check successful.")
                # Store the refreshed credentials for later use
                self.credentials = self.credentials.copy()  # Ensure we have the latest tokens
                return True
            else:
                logger.error("Bitbucket connection check failed: API request returned None.")
                return False
        except Exception as e:
            logger.error(f"Error during Bitbucket connection check: {str(e)}", exc_info=True)
            return False

    async def get_repository_metrics(self) -> Dict[str, Any]:
        """Fetches aggregate counts of repos, files, PRs, and commits for the workspace."""
        logger.info("Starting Bitbucket repository metrics aggregation...")
        
        if not self.credentials:
            logger.error("Bitbucket connector is not connected. Call connect() first.")
            return {"error": "Not connected"}
        
        # 1. Fetch Workspaces and Repos
        workspaces_data = await fetch_workspaces(self.credentials)
        if not workspaces_data or not workspaces_data.get("values"):
            return {"error": "Failed to fetch workspaces. Check credentials/permissions."}
        
        workspace = workspaces_data["values"][0]  # Process only the first workspace
        workspace_name = workspace.get("slug") or workspace.get("name")
        if not workspace_name:
            return {"error": "Could not determine workspace name."}
        
        logger.info(f"Processing metrics for first workspace: '{workspace_name}'")
        repos = await fetch_repos(workspace_name, self.credentials, limit=MAX_REPOS_PER_WORKSPACE_LIMIT)
        if not repos:
            logger.warning(f"No repositories found in workspace '{workspace_name}'. Returning empty metrics.")
            return {"global_counts": {"repos": 0, "files": 0, "PRs": 0, "commits": 0}, "repo_metrics": {}}
        
        # 2. Prepare concurrent tasks for processing each repository's counts
        repo_metric_tasks = []
        for repo in repos:
            repo_name = repo.get("slug") or repo.get("name") or repo.get("full_name", "").split("/")[-1]
            if not repo_name:
                continue  # Skip repo if name is missing
            
            default_branch = repo.get("mainbranch", {}).get("name", "main")  # Default to 'main'
            
            task = asyncio.create_task(
                self._process_single_repo_counts(workspace_name, repo_name, default_branch, self.credentials)
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
        
        logger.info(f"Finished aggregating metrics for workspace '{workspace_name}'.")
        return {
            "global_counts": global_counts,
            "repo_metrics": all_repo_metrics
        }

    async def _process_single_repo_counts(self, workspace_name: str, repo_name: str, default_branch: str, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Fetches counts for files, PRs, and commits for a single repo."""
        logger.info(f"Fetching counts for repo: {workspace_name}/{repo_name}...")
        repo_counts = {"repo": 1, "files": 0, "PRs": 0, "commits": 0}  # Default counts
        
        try:
            # Clone the repository once for all local operations
            logger.debug(f"Cloning repo {workspace_name}/{repo_name} for local operations...")
            cloned_path = await clone_repo_into_fs(workspace_name, repo_name, credentials)
            
            # Fetch counts concurrently (PR count doesn't need cloning, others use the cloned repo)
            # Use the latest credentials from the connector to ensure we have fresh tokens
            fresh_credentials = self.credentials.copy()
            
            if cloned_path:
                file_count_task = count_files_in_repo(workspace_name, repo_name, default_branch, fresh_credentials, cloned_path)
                commit_count_task = fetch_commit_count(workspace_name, repo_name, fresh_credentials, cloned_path)
            else:
                # If cloning failed, return zero for operations that need local access
                logger.warning(f"Cloning failed for {workspace_name}/{repo_name}, skipping file and commit counts")
                file_count_task = asyncio.create_task(asyncio.sleep(0, result=0))
                commit_count_task = asyncio.create_task(asyncio.sleep(0, result=0))
            
            pr_count_task = count_pull_requests_for_repo(workspace_name, repo_name, fresh_credentials)
            
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
            
            logger.info(f"Counts for {workspace_name}/{repo_name}: Files={repo_counts['files']}, PRs={repo_counts['PRs']}, Commits={repo_counts['commits']}")
            return repo_counts
            
        except Exception as e:
            logger.error(f"Failed to get counts for repo {workspace_name}/{repo_name}: {str(e)}", exc_info=True)
            # Return partial counts with an error indicator
            return {
                "repo": 1, "files": repo_counts.get("files", 0),
                "PRs": repo_counts.get("PRs", 0), "commits": repo_counts.get("commits", 0),
                "error": str(e)
            }

    def close(self) -> None:
        """Close the Bitbucket connection and clear tokens."""
        logger.info("Closing BitbucketConnector connection.")
        self.access_token = None
        self.refresh_token = None
        self.workspace_name = None
        self.repos = None
        self.credentials = {}

    def __del__(self):
        self.close() 