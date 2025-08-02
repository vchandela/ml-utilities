# github/data_processor.py
import asyncio
import os
import mimetypes
import logging
from typing import Optional, Dict, Any, List

# Import necessary client functions
from .client import GitHubApiHandler, _SESSION

# Configure logging
logger = logging.getLogger(__name__)

# Constants for file filtering
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# Helper to check if a file is likely text-based
def _is_probably_text(path: str) -> bool:
    """Return True if the file appears to be text."""
    mime, _ = mimetypes.guess_type(path)
    if mime and (mime.startswith("text/") or mime in {"application/json", "application/xml"}):
        return True
    try:
        with open(path, "rb") as fh:
            sample = fh.read(512)
            if b"\x00" in sample:
                return False  # Null bytes often indicate binary
            printable = sum(32 <= b < 127 or b in (9, 10, 13) for b in sample)
            return printable / max(len(sample), 1) > 0.9  # 90% printable heuristic
    except Exception:
        return False  # Assume not text if any error occurs (e.g., permissions)

async def fetch_repo_tree(api_handler: GitHubApiHandler, org: str, repo: str, branch: str) -> List[Dict[str, Any]]:
    """Fetches the recursive tree structure from GitHub API."""
    try:
        url = f"https://api.github.com/repos/{org}/{repo}/git/trees/{branch}"
        params = {"recursive": "1"}  # Get recursive tree
        
        response = await api_handler.request_with_retries("GET", url, params=params)
        data = response.json()
        
        return data.get("tree", [])
    except Exception as e:
        logger.debug(f"Could not fetch tree for {org}/{repo} branch {branch}: {str(e)}")
        return []

async def count_files_in_repo(org: str, repo: str, branch: str, credentials: Dict[str, Any]) -> int:
    """Counts files adhering to filters using GitHub API's tree endpoint."""
    logger.info(f"Counting files in {org}/{repo} (branch: {branch})...")
    file_count = 0
    
    # Create API handler
    headers = {
        "Authorization": f"Bearer {credentials['access_token']}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Metadata-Extractor"
    }
    api_handler = GitHubApiHandler(_SESSION, headers)
    
    try:
        # Fetch the recursive tree from GitHub API
        tree_items = await fetch_repo_tree(api_handler, org, repo, branch)
        
        if not tree_items:
            logger.warning(f"No tree items found for {org}/{repo} branch '{branch}'. File count will be 0.")
            return 0

        for item in tree_items:
            if item.get("type") == "blob":  # Process only files
                file_size = item.get("size")
                file_path = item.get("path")
                
                if file_path and file_size is not None:
                    # Skip .git files
                    if file_path.startswith(".git/") or "/.git/" in file_path:
                        continue
                    
                    # Apply size filter
                    if file_size > MAX_FILE_SIZE:
                        logger.debug(f"Skipping file {file_path} in {org}/{repo}: too large ({file_size} bytes).")
                        continue
                    
                    # For counting via API, we'll include all files that pass size and .git filters
                    # Text check would require downloading content, which is inefficient for counting
                    # We rely on the assumption that most code repository files are text-based
                    file_count += 1
                else:
                    logger.debug(f"Skipping item with missing path/size in {org}/{repo}: {item}")
        
        logger.info(f"Counted {file_count} files (within size limits) for {org}/{repo}.")
        return file_count
        
    except Exception as e:
        logger.error(f"Unexpected error counting files for {org}/{repo}: {str(e)}", exc_info=True)
        return 0

async def count_files_in_repo_local(org: str, repo: str, cloned_path: str) -> int:
    """Alternative method: Counts files using local filesystem walk (if repo is cloned)."""
    logger.info(f"Counting files in {org}/{repo} using local filesystem...")
    file_count = 0
    
    if not cloned_path or not os.path.exists(cloned_path):
        logger.error(f"Cannot count files for {org}/{repo}: Invalid or missing cloned path.")
        return 0
    
    try:
        # Walk the repository filesystem
        for root, dirs, files in os.walk(cloned_path):
            # Exclude .git directories by removing them from dirs list *before* recursion
            if '.git' in dirs:
                dirs.remove('.git')
            # Also skip if we are already inside a .git directory
            if root.startswith(os.path.join(cloned_path, '.git')):
                continue

            for fname in files:
                abs_path = os.path.join(root, fname)
                try:
                    # Basic checks: is it a file, within size limit, and likely text?
                    if not os.path.isfile(abs_path):
                        continue  # Skip if not a regular file
                    file_size = os.path.getsize(abs_path)
                    if file_size > MAX_FILE_SIZE:
                        continue  # Skip if too large
                    if not _is_probably_text(abs_path):
                        continue  # Skip if not text
                    
                    file_count += 1  # Increment count if all checks pass
                    
                except (FileNotFoundError, PermissionError, Exception) as e:
                    logger.warning(f"Error processing file {abs_path} for count: {e}")
        
        logger.info(f"Counted {file_count} valid files (local) for {org}/{repo}.")
        return file_count
    except Exception as e:
        logger.error(f"Unexpected error counting files locally for {org}/{repo}: {str(e)}", exc_info=True)
        return 0

def validate_repository_data(repo_data: Dict[str, Any]) -> bool:
    """Validates that repository data contains essential fields."""
    required_fields = ["name", "full_name", "html_url"]
    return bool(all(repo_data.get(field) for field in required_fields))

def validate_pull_request_data(pr_data: Dict[str, Any]) -> bool:
    """Validates that pull request data contains essential fields."""
    return bool(pr_data.get("id") and pr_data.get("title") and
                pr_data.get("html_url") and
                pr_data.get("user", {}).get("login") and
                pr_data.get("head", {}) and pr_data.get("base", {}))

def extract_repo_size_info(repo_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts size-related information from repository data."""
    return {
        "size_kb": repo_data.get("size", 0),  # GitHub returns size in KB
        "is_fork": repo_data.get("fork", False),
        "is_private": repo_data.get("private", False),
        "is_archived": repo_data.get("archived", False),
        "default_branch": repo_data.get("default_branch", "main")
    }

# Note: count_pull_requests_for_repo and fetch_commit_count are implemented
# in client.py and can be imported from there when needed by the connector. 