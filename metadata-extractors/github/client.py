# github/client.py
import asyncio
import requests
import requests.exceptions
from requests.adapters import HTTPAdapter, Retry
from tenacity import (
    retry, stop_after_attempt, wait_exponential_jitter,
    before_sleep_log, retry_if_exception
)
import logging
import os
import subprocess
import shutil
import mimetypes
from typing import Optional, Dict, List, Any
import urllib.parse

# Configure logging
logger = logging.getLogger(__name__)

# --- Constants ---
GITHUB_MAX_PARALLEL: int = 20  # Default, can be overridden
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
RETRY_ATTEMPTS = 3
BACKOFF_FACTOR = 0.5

# --- Retry Logic ---
def should_retry_github_error(exception: BaseException) -> bool:
    if isinstance(exception, requests.exceptions.HTTPError):
        response = getattr(exception, 'response', None)
        if response is not None:
            return response.status_code in RETRYABLE_STATUS_CODES
    if isinstance(exception, requests.exceptions.ConnectionError):
        return True
    return False

# --- Semaphore for Concurrency ---
def _get_github_http_semaphore() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    attr_name = "_github_http_semaphore"
    sem = getattr(loop, attr_name, None)
    if sem is None:
        sem = asyncio.Semaphore(GITHUB_MAX_PARALLEL)
        setattr(loop, attr_name, sem)
    return sem

# --- Shared Requests Session ---
def _create_github_shared_session() -> requests.Session:
    sess = requests.Session()
    retries = Retry(
        total=RETRY_ATTEMPTS, backoff_factor=BACKOFF_FACTOR,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(pool_connections=50, pool_maxsize=50, max_retries=retries)
    sess.mount("https://", adapter)
    sess.mount("http://", adapter)
    logger.info("GitHub shared requests.Session initialised with pool_maxsize=50")
    return sess

_SESSION: requests.Session = _create_github_shared_session()

# --- API Request Handler ---
class GitHubApiHandler:
    def __init__(self, session: requests.Session, headers: Dict[str, str]):
        self.session = session
        self.headers = headers
        logger.debug("GitHubApiHandler initialized.")

    @retry(
        reraise=True, stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential_jitter(initial=0.5, max=10, exp_base=2),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        retry=retry_if_exception(should_retry_github_error)
    )
    async def request_with_retries(self, method: str, url: str, **kwargs) -> requests.Response:
        """Performs an HTTP request asynchronously with retries."""
        logger.debug(f"Making {method} request to {url}")
        request_headers = self.headers.copy()
        if 'headers' in kwargs: 
            request_headers.update(kwargs.pop('headers'))
        timeout = kwargs.pop('timeout', 20)

        def _sync_request():
            try:
                response = self.session.request(method, url, timeout=timeout, headers=request_headers, **kwargs)
                response.raise_for_status()
                logger.debug(f"Request to {url} successful with status {response.status_code}")
                return response
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request to {url} failed: {e}")
                raise  # Let tenacity handle retries
        
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(None, _sync_request)
            return response
        except Exception as e:
            logger.debug(f"Request to {url} failed: {str(e)}")  
            raise

    async def get_paginated_data(self, url: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Fetches all pages for a given GitHub API endpoint using Link header."""
        results = []
        current_url: Optional[str] = url
        if params:
            current_url = f"{url}?{urllib.parse.urlencode(params)}"
        page_num = 1
        logger.info(f"Starting pagination for {url}")
        
        while current_url:
            logger.debug(f"Fetching page {page_num} from {current_url}")
            try:
                response = await self.request_with_retries("GET", current_url)
                if response is None: 
                    break  # Stop if request fails after retries
                
                data = response.json()
                # GitHub API returns data directly as a list for most endpoints
                page_items = data if isinstance(data, list) else data.get("items", [])
                if not isinstance(page_items, list):
                    logger.error(f"Unexpected data format from {current_url}: Expected list, got {type(page_items)}. Stopping.")
                    break
                
                results.extend(page_items)
                logger.debug(f"Page {page_num}: Received {len(page_items)} items. Total: {len(results)}")

                # Get next page URL from Link header
                next_link = response.links.get("next")
                current_url = next_link["url"] if next_link else None
                page_num += 1
                
            except Exception as e:
                logger.error(f"Error during pagination for {current_url} (Page {page_num}): {e}", exc_info=True)
                break

        logger.info(f"Finished pagination for {url}. Fetched {len(results)} items.")
        return results

# --- Functions for GitHub API interactions ---

async def fetch_organizations(credentials: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetches organizations accessible to the authenticated user."""
    headers = {
        "Authorization": f"Bearer {credentials['access_token']}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Metadata-Extractor"
    }
    
    api_handler = GitHubApiHandler(_SESSION, headers)
    
    try:
        # First try to get user's organizations
        orgs = await api_handler.get_paginated_data("https://api.github.com/user/orgs")
        
        # If no orgs, get user info (for personal account)
        if not orgs:
            logger.info("No organizations found, fetching user account info...")
            response = await api_handler.request_with_retries("GET", "https://api.github.com/user")
            user_data = response.json()
            return [user_data] if user_data else []
        
        return orgs
    except Exception as e:
        logger.error(f"Failed to fetch organizations: {str(e)}", exc_info=True)
        return []

async def fetch_repos(org_name: str, credentials: Dict[str, Any], limit: int = 1000) -> List[Dict[str, Any]]:
    """Fetches repositories for a given organization."""
    headers = {
        "Authorization": f"Bearer {credentials['access_token']}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Metadata-Extractor"
    }
    
    api_handler = GitHubApiHandler(_SESSION, headers)
    
    try:
        # GitHub API endpoint for organization repos
        url = f"https://api.github.com/orgs/{org_name}/repos"
        params = {"per_page": 100, "type": "all"}  # Get all repo types
        
        repos = await api_handler.get_paginated_data(url, params)
        
        # Apply limit
        if limit and len(repos) > limit:
            repos = repos[:limit]
            logger.info(f"Limited repositories to {limit} for organization {org_name}")
        
        logger.info(f"Fetched {len(repos)} repositories for organization {org_name}")
        return repos
        
    except Exception as e:
        logger.error(f"Failed to fetch repositories for {org_name}: {str(e)}", exc_info=True)
        return []

async def count_pull_requests_for_repo(api_handler: GitHubApiHandler, org: str, repo: str, state: str = "all") -> int:
    """Counts valid pull requests for a specific repository."""
    url = f"https://api.github.com/repos/{org}/{repo}/pulls"
    params = {"state": state, "per_page": 100}  # Request 100 per page for efficiency
    logger.info(f"Counting PRs for {org}/{repo}...")
    pr_count = 0
    
    try:
        # Use get_paginated_data which internally handles retries and pagination
        pr_list = await api_handler.get_paginated_data(url, params)
        
        if not isinstance(pr_list, list):
            logger.error(f"Unexpected PR data format for {org}/{repo}.")
            return 0

        for pr_data in pr_list:
            # Validate essential fields for a PR
            if (pr_data.get("id") and pr_data.get("title") and
                pr_data.get("html_url") and
                pr_data.get("user", {}).get("login") and
                pr_data.get("head", {}) and pr_data.get("base", {})):
                pr_count += 1
            else:
                logger.debug(f"Skipping PR with missing essential fields in {org}/{repo}: {pr_data.get('id', 'N/A')}")
        
        logger.info(f"Found {pr_count} valid PRs for {org}/{repo}.")
        return pr_count
        
    except Exception as e:
        logger.error(f"Failed to count PRs for {org}/{repo}: {str(e)}", exc_info=True)
        return 0

# --- Git Operations ---

def get_local_repo_path(org_name: str, repo_name: str) -> str:
    """Returns the local path where a repo should be cloned."""
    local_repo_dir = os.getenv("LOCAL_REPO_DIR", "./cloned_repos")
    return os.path.join(local_repo_dir, "github", org_name, repo_name)

async def clone_repo_into_fs(org_name: str, repo_name: str, credentials: Dict[str, Any]) -> Optional[str]:
    """Clones a repo locally if it doesn't exist. Returns local path."""
    repo_local_path = get_local_repo_path(org_name, repo_name)
    if os.path.exists(repo_local_path): 
        return repo_local_path
    
    logger.info(f"Cloning repo '{org_name}/{repo_name}' into '{repo_local_path}'...")
    # Construct GitHub clone URL using token
    url = f"https://{credentials['access_token']}@github.com/{org_name}/{repo_name}.git"
    
    try:
        os.makedirs(os.path.dirname(repo_local_path), exist_ok=True)
        result = await asyncio.to_thread(
            subprocess.run, ["git", "clone", url, repo_local_path],
            capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            logger.info(f"Successfully cloned repo '{org_name}/{repo_name}'.")
            return repo_local_path
        else:
            logger.error(f"Failed to clone repo '{org_name}/{repo_name}'. Git error:\n{result.stderr}")
            return None
    except Exception as e:
        logger.error(f"Exception during git clone for '{org_name}/{repo_name}': {str(e)}", exc_info=True)
        return None

async def fetch_commit_count(org_name: str, repo_name: str, credentials: Dict[str, Any]) -> int:
    """Fetches the commit count for a repository's default branch using git rev-list."""
    logger.info(f"Fetching commit count for {org_name}/{repo_name}...")
    cloned_path = await clone_repo_into_fs(org_name, repo_name, credentials)
    if not cloned_path:
        logger.error(f"Cannot fetch commit count for {org_name}/{repo_name}: Repo cloning failed.")
        return 0
    
    try:
        # Use HEAD to get commit count from default branch
        cmd = ["git", "-C", cloned_path, "rev-list", "--count", "HEAD"]
        result = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            count = int(result.stdout.strip())
            logger.info(f"Found {count} commits for {org_name}/{repo_name}.")
            return count
        else:
            logger.error(f"Failed to get commit count for {org_name}/{repo_name}. Git error:\n{result.stderr}")
            return 0
    except (ValueError, Exception) as e:
        logger.error(f"Error fetching commit count for {org_name}/{repo_name}: {str(e)}", exc_info=True)
        return 0

# --- Helper for file processing ---
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

def _is_probably_text(path: str) -> bool:
    """Return True if the file appears to be text."""
    mime, _ = mimetypes.guess_type(path)
    if mime and (mime.startswith("text/") or mime in {"application/json", "application/xml"}): 
        return True
    try:
        with open(path, "rb") as fh:
            sample = fh.read(512)
            if b"\x00" in sample: 
                return False
            printable = sum(32 <= b < 127 or b in (9, 10, 13) for b in sample)
            return printable / max(len(sample), 1) > 0.9
    except Exception: 
        return False

 