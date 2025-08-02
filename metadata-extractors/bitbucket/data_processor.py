# bitbucket/data_processor.py
import asyncio
import os
import mimetypes
import logging
from typing import Optional, Dict, Any

# Import necessary client functions
from .client import get_local_repo_path, clone_repo_into_fs

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

async def count_files_in_repo(workspace: str, repo: str, branch: str, credentials: Dict[str, Any], cloned_path: Optional[str] = None) -> int:
    """Counts files adhering to filters using local filesystem walk."""
    logger.info(f"Counting files in {workspace}/{repo} (branch: {branch})...")
    file_count = 0
    
    if not cloned_path:
        logger.error(f"Cannot count files for {workspace}/{repo}: Repo cloning failed.")
        return 0
    
    try:
        # Walk the repository filesystem
        for root, dirs, files in os.walk(cloned_path):
            # Exclude .git directories by removing them from dirs list *before* recursion
            if '.git' in dirs:
                dirs.remove('.git')
            # Also skip if we are already inside a .git directory (though previous step should prevent this)
            if root.startswith(os.path.join(cloned_path, '.git')):
                continue

            for fname in files:
                abs_path = os.path.join(root, fname)
                rel_path = os.path.relpath(abs_path, cloned_path)
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
        
        logger.info(f"Counted {file_count} valid files for {workspace}/{repo}.")
        return file_count
    except Exception as e:
        logger.error(f"Unexpected error counting files for {workspace}/{repo}: {str(e)}", exc_info=True)
        return 0

# Note: count_pull_requests_for_repo and fetch_commit_count are assumed to be
# defined or imported from client.py for reuse by the connector. 