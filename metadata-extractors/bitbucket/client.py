# bitbucket/client.py
from typing import Optional, Dict, Any, List
import requests
import time
import subprocess
from requests.auth import HTTPBasicAuth
import shutil
import os
import asyncio
from requests.adapters import HTTPAdapter, Retry
import re
import mimetypes
import logging
import aiohttp

# Configure logging
logger = logging.getLogger(__name__)

# --- Configuration Constants ---
BITBUCKET_MAX_PARALLEL: int = 20  # Default, can be overridden by .env
MAX_REPOS_PER_WORKSPACE_LIMIT = 1000

# --- Semaphore for Concurrency Control ---
def _get_http_semaphore() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    attr_name = "_bitbucket_http_semaphore"
    sem = getattr(loop, attr_name, None)
    if sem is None:
        sem = asyncio.Semaphore(BITBUCKET_MAX_PARALLEL)
        setattr(loop, attr_name, sem)
    return sem

# --- Shared Requests Session ---
def _create_shared_session() -> requests.Session:
    sess = requests.Session()
    retries = Retry(
        total=3, backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(pool_connections=50, pool_maxsize=50, max_retries=retries)
    sess.mount("https://", adapter)
    sess.mount("http://", adapter)
    logger.info("Bitbucket shared requests.Session initialised with pool_maxsize=50")
    return sess

_SESSION: requests.Session = _create_shared_session()

# --- Credential Handling ---

def get_client_credentials() -> tuple[Optional[str], Optional[str]]:
    """Get Bitbucket client ID and secret from environment variables."""
    import os
    client_id = os.getenv("BITBUCKET_CLIENT_ID")
    client_secret = os.getenv("BITBUCKET_CLIENT_SECRET")
    return client_id, client_secret

async def refresh_credentials_async(credentials: Dict[str, Any]) -> Dict[str, Any]:
    """Asynchronously refreshes the access token using client credentials from environment."""
    logger.info("Attempting to refresh Bitbucket access token...")
    url = "https://bitbucket.org/site/oauth2/access_token"
    
    # Get client credentials from environment
    client_id, client_secret = get_client_credentials()
    if not client_id or not client_secret:
        raise ValueError("BITBUCKET_CLIENT_ID and BITBUCKET_CLIENT_SECRET must be set in environment variables")
    
    try:
        response = await asyncio.to_thread(
            requests.post, url,
            data={"grant_type": "refresh_token", "refresh_token": credentials['refresh_token']},
            auth=HTTPBasicAuth(client_id, client_secret),
            timeout=30
        )
        response.raise_for_status()  # Raise for 4xx/5xx
        
        token_data = response.json()
        new_access_token = token_data.get("access_token")
        new_refresh_token = token_data.get("refresh_token")

        if not new_access_token:
            raise ValueError("'access_token' not found in refresh response.")
        
        credentials["access_token"] = new_access_token
        if new_refresh_token:
            credentials["refresh_token"] = new_refresh_token
        
        logger.info("Successfully refreshed Bitbucket access token.")
        return credentials
    except requests.exceptions.RequestException as e:
        logger.error(f"Error refreshing Bitbucket token: {str(e)}", exc_info=True)
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Status: {e.response.status_code}, Response: {e.response.text[:500]}")
        raise
    except (ValueError, Exception) as e:
        logger.error(f"Error refreshing Bitbucket token: {str(e)}", exc_info=True)
        raise

async def _async_request_with_retries(url: str, method: str, headers: Dict[str, str], credentials: Dict[str, Any], max_retries: int = 3):
    """Non-blocking wrapper for requests with retries and token refresh."""
    hdrs = headers.copy()
    attempt = 0
    while attempt < max_retries:
        attempt += 1
        try:
            if not credentials.get("access_token"):
                await refresh_credentials_async(credentials)
            hdrs["Authorization"] = f"Bearer {credentials['access_token']}"
            hdrs["Content-Type"] = "application/json"  # Add Content-Type header like in curl
            
            async with _get_http_semaphore():
                response = await asyncio.to_thread(_SESSION.request, method, url, headers=hdrs, timeout=30)

            if response.status_code == 200:
                return response
            elif response.status_code == 401:
                logger.info(f"Received 401 for {url}, attempting token refresh and retry.")
                await refresh_credentials_async(credentials)
            elif response.status_code == 404:
                logger.warning(f"[404] Resource not found at {url}")
                return None
            else:
                response.raise_for_status()  # Raise for other errors
        except (requests.exceptions.RequestException, asyncio.TimeoutError) as exc:
            logger.warning(f"HTTP request exception for {method} {url} (Attempt {attempt}/{max_retries}): {str(exc)}")
        except Exception as exc:
            logger.error(f"Unexpected error during Bitbucket API request {method} {url}: {str(exc)}", exc_info=True)
            raise
        
        if attempt < max_retries:
            await asyncio.sleep(min(2 ** attempt, 5))
    
    logger.error(f"All {max_retries} attempts failed for {method} {url}")
    return None

# --- Functions for fetching Lists ---
async def fetch_workspaces(credentials: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Fetches workspaces, handling pagination and retries."""
    url = "https://api.bitbucket.org/2.0/workspaces"
    logger.info(f"Fetching Bitbucket workspaces...")
    try:
        response = await _async_request_with_retries(url, "GET", {}, credentials)
        if response is None:
            raise ConnectionError("API request returned None.")
        
        result = response.json()
        all_workspaces = result.get("values", [])
        next_url = result.get("next")
        while next_url:
            response = await _async_request_with_retries(next_url, "GET", {}, credentials)
            if response is None:
                break
            result = response.json()
            all_workspaces.extend(result.get("values", []))
            next_url = result.get("next")

        if all_workspaces:
            logger.info(f"Successfully fetched {len(all_workspaces)} workspace(s).")
            return {"values": all_workspaces}
        else:
            logger.error("Bitbucket workspaces API returned empty or invalid response.")
            return None
    except Exception as e:
        logger.error(f"Failed to fetch workspaces: {str(e)}", exc_info=True)
        return None

async def fetch_repos(workspace: str, credentials: Dict[str, Any], limit: int = 1000) -> Optional[List[Dict[str, Any]]]:
    """Fetches repositories for a given workspace, handling pagination and retries."""
    url = f"https://api.bitbucket.org/2.0/repositories/{workspace}"
    logger.info(f"Fetching repos for workspace '{workspace}' (limit: {limit})...")
    repos = []
    try:
        current_url = url
        while len(repos) < limit:
            response = await _async_request_with_retries(current_url, "GET", {}, credentials)
            if response is None:
                break
            res_json = response.json()
            page_values = res_json.get("values", [])
            repos.extend(page_values[:limit - len(repos)])
            current_url = res_json.get("next")
            if not current_url or len(repos) >= limit:
                break
        
        logger.info(f"Fetched {len(repos)} repositories for workspace '{workspace}'.")
        return repos
    except Exception as e:
        logger.error(f"Failed to fetch repos for workspace '{workspace}': {str(e)}", exc_info=True)
        return None

# --- Functions for Counting ---

def _is_valid_pr(pr_data: Dict[str, Any]) -> bool:
    """Check if PR has required fields."""
    return bool(pr_data.get("id") and pr_data.get("title") and
                pr_data.get("links", {}).get("html", {}).get("href") and
                pr_data.get("author", {}).get("display_name") and
                pr_data.get("source") and pr_data.get("destination"))

async def _count_valid_prs_threaded(values: List[Dict[str, Any]]) -> int:
    """Count valid PRs in a separate thread to keep event loop responsive."""
    return await asyncio.to_thread(lambda: sum(1 for v in values if _is_valid_pr(v)))

async def _fetch_pr_page(session, url: str, headers: Dict[str, str], semaphore: asyncio.Semaphore) -> tuple[int, Optional[str]]:
    """Fetch a single PR page and return (count, next_url)."""
    async with semaphore:
        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    count = await _count_valid_prs_threaded(data.get("values", []))
                    return count, data.get("next")  # Return count and next URL
                else:
                    logger.warning(f"Failed to fetch page, status: {resp.status}")
                    return 0, None
        except Exception as e:
            logger.warning(f"Error fetching PR page: {e}")
            return 0, None

async def count_pull_requests_for_repo(workspace: str, repo: str, credentials: Dict[str, Any]) -> int:
    """Counts valid pull requests using optimized aiohttp with field filtering and parallel fetching."""
    import aiohttp
    
    base_url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo}/pullrequests"
    logger.info(f"Counting PRs for {workspace}/{repo}...")
    
    # Define required fields to minimize payload size  
    # Note: Some Bitbucket instances may not support all field filtering
    FIELDS = "values.id,values.title,values.links.html.href,values.author.display_name,values.source,values.destination,next,size"
    
    headers = {
        "Authorization": f"Bearer {credentials['access_token']}",
        "Content-Type": "application/json"
    }
    
    try:
        # Use existing semaphore system from the module
        semaphore = _get_http_semaphore()
        total_count = 0
        
        async with aiohttp.ClientSession() as session:
            
            # Always validate PR fields - try with field filtering first, fallback if needed
            first_params = {
                "state": "ALL",
                "pagelen": 50,  # Conservative page size (Bitbucket may not support 100)
                "fields": FIELDS
            }
            
            # Get first page with full validation
            async with semaphore:
                async with session.get(base_url, params=first_params, headers=headers) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        logger.warning(f"PR API with fields returned status {response.status}: {response_text[:200]}")
                        logger.info("Retrying without field filtering...")
                        
                        # Fallback: try without fields parameter
                        simple_params = {"state": "ALL", "pagelen": 50}
                        async with session.get(base_url, params=simple_params, headers=headers) as fallback_response:
                            if fallback_response.status != 200:
                                fallback_text = await fallback_response.text()
                                logger.error(f"PR API fallback also failed with status {fallback_response.status}: {fallback_text[:200]}")
                                return 0
                            response = fallback_response  # Use fallback response
                    
                    page_data = await response.json()
                    total_count += await _count_valid_prs_threaded(page_data.get("values", []))
                    next_url = page_data.get("next")
                    expected_total = page_data.get("size")
            
            if not next_url:
                logger.info(f"Found {total_count} valid PRs for {workspace}/{repo} (1 page only).")
                return total_count
            
            # Collect remaining pages and fetch in parallel
            logger.info(f"Fetching remaining pages in parallel (expected ~{expected_total or 'unknown'} total PRs)...")
            
            # Start with first next_url
            active_tasks = set()
            processed_pages = 1  # Already processed first page
            pages_with_prs = 1 if total_count > 0 else 0  # Track pages that contain PRs
            max_concurrent = 10  # Reasonable limit to avoid rate limiting
            
            # Add first task
            if next_url:
                task = asyncio.create_task(_fetch_pr_page(session, next_url, headers, semaphore))
                active_tasks.add(task)
            
            while active_tasks:
                # Wait for at least one task to complete
                done, pending = await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)
                active_tasks = pending
                
                for task in done:
                    try:
                        count, next_link = await task
                        total_count += count
                        processed_pages += 1
                        if count > 0:
                            pages_with_prs += 1
                        
                        # Add next task if there's a next link and we haven't hit limits
                        if next_link and len(active_tasks) < max_concurrent and processed_pages < 200:
                            new_task = asyncio.create_task(_fetch_pr_page(session, next_link, headers, semaphore))
                            active_tasks.add(new_task)
                            
                    except Exception as e:
                        logger.warning(f"Exception in page task: {e}")
            
            logger.info(f"Found {total_count} valid PRs for {workspace}/{repo} and {processed_pages} total pages")
            return total_count
            
    except Exception as e:
        logger.error(f"Failed to count PRs for {workspace}/{repo}: {str(e)}", exc_info=True)
        return 0

# --- Git Operations ---

def get_local_repo_path(workspace: str, repo: str) -> str:
    """Constructs the local path for a cloned repository."""
    local_dir_base = os.getenv("LOCAL_REPO_DIR", "./cloned_repos")  # Default path if not in env
    return os.path.join(local_dir_base, workspace, repo)

async def clone_repo_into_fs(workspace_name: str, repo_name: str, credentials: Dict[str, Any]) -> Optional[str]:
    """Clones a repo locally if it doesn't exist. Returns local path."""
    repo_local_path = get_local_repo_path(workspace_name, repo_name)
    
    if os.path.exists(repo_local_path):
        # Verify it's a valid git repository
        if os.path.exists(os.path.join(repo_local_path, '.git')):
            logger.debug(f"Repo '{repo_name}' already exists locally at '{repo_local_path}'.")
            return repo_local_path
        else:
            # Directory exists but is not a git repo, remove it
            logger.warning(f"Directory '{repo_local_path}' exists but is not a git repo. Removing...")
            shutil.rmtree(repo_local_path)
    
    logger.info(f"Cloning repo '{workspace_name}/{repo_name}' into '{repo_local_path}'...")
    url = f"https://x-token-auth:{credentials['access_token']}@bitbucket.org/{workspace_name}/{repo_name}.git"
    
    try:
        os.makedirs(os.path.dirname(repo_local_path), exist_ok=True)
        result = await asyncio.to_thread(
            subprocess.run, ["git", "clone", url, repo_local_path],
            capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            logger.info(f"Successfully cloned repo '{workspace_name}/{repo_name}'.")
            return repo_local_path
        else:
            logger.error(f"Failed to clone repo '{workspace_name}/{repo_name}'. Git error:\n{result.stderr}")
            return None
    except Exception as e:
        logger.error(f"Exception during git clone for '{workspace_name}/{repo_name}': {str(e)}", exc_info=True)
        return None

async def fetch_commit_count(workspace: str, repo: str, credentials: Dict[str, Any], cloned_path: Optional[str] = None) -> int:
    """Fetches the commit count for a repository's default branch using git rev-list."""
    logger.info(f"Fetching commit count for {workspace}/{repo}...")
    
    if not cloned_path:
        logger.error(f"Cannot fetch commit count for {workspace}/{repo}: Repo cloning failed.")
        return 0
    
    try:
        cmd = ["git", "-C", cloned_path, "rev-list", "--count", "HEAD"]
        result = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            commit_count = int(result.stdout.strip())
            logger.info(f"Found {commit_count} commits for {workspace}/{repo}.")
            return commit_count
        else:
            logger.error(f"Failed to get commit count for {workspace}/{repo}. Git error:\n{result.stderr}")
            return 0
    except (ValueError, Exception) as e:
        logger.error(f"Error fetching commit count for {workspace}/{repo}: {str(e)}", exc_info=True)
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

async def count_files_in_repo(workspace: str, repo: str, branch: str, credentials: Dict[str, Any]) -> int:
    """Counts files adhering to filters using local filesystem walk."""
    logger.info(f"Counting files in {workspace}/{repo} (branch: {branch})...")
    file_count = 0
    
    cloned_path = await clone_repo_into_fs(workspace, repo, credentials)
    if not cloned_path:
        logger.error(f"Cannot count files for {workspace}/{repo}: Repo cloning failed.")
        return 0
    
    try:
        for root, dirs, files in os.walk(cloned_path):
            if '.git' in dirs:
                dirs.remove('.git')  # Exclude .git directory
            if root.startswith(os.path.join(cloned_path, '.git')):
                continue

            for fname in files:
                abs_path = os.path.join(root, fname)
                try:
                    if not os.path.isfile(abs_path):
                        continue
                    file_size = os.path.getsize(abs_path)
                    if file_size > MAX_FILE_SIZE:
                        continue
                    if not _is_probably_text(abs_path):
                        continue
                    file_count += 1
                except (FileNotFoundError, PermissionError, Exception) as e:
                    logger.warning(f"Error processing file {abs_path} for count: {e}")
        
        logger.info(f"Counted {file_count} valid files for {workspace}/{repo}.")
        return file_count
    except Exception as e:
        logger.error(f"Unexpected error counting files for {workspace}/{repo}: {str(e)}", exc_info=True)
        return 0 