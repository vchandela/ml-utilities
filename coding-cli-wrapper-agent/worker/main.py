import os
import sys
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
import time

import redis
import requests
from models import Task, CodeEngine

def log(message):
    """Simple logging with timestamp"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def main():
    """
    Worker internal flow:
    1. Load env → parse TASK_JSON; HSET state=running
    2. Clone repo / checkout branch → git clone + git checkout -b agent-b/{task_id}
    3. Apply engine → run Gemini CLI (default) or selected engine with instructions as prompt
    4. Run tests → pytest (or repo-script). If non-zero exit: state=failed; exit
    5. Push & open PR → git push, then GitHub REST /pulls; capture pr_url
    6. Mark done & callback → HSET state=done pr_url=…; POST result to callback_url if provided
    7. Exit → container auto-removes (--rm)
    """
    
    try:
        # 1. Load env → parse TASK_JSON; HSET state=running
        log("Starting worker...")
        
        task_json = os.getenv("TASK_JSON")
        redis_url = os.getenv("REDIS_URL")
        github_token = os.getenv("GITHUB_TOKEN")
        
        if not task_json:
            log("ERROR: TASK_JSON environment variable not provided")
            sys.exit(1)
            
        if not redis_url:
            log("ERROR: REDIS_URL environment variable not provided")
            sys.exit(1)
            
        if not github_token:
            log("ERROR: GITHUB_TOKEN environment variable not provided")
            sys.exit(1)
            
        # Parse task
        task_data = json.loads(task_json)
        task = Task(**task_data)
        task_id = task.id
        
        # Instructions are now loaded by API from mounted file and passed via TASK_JSON
        log("Using instructions passed from API")
        
        log(f"Processing task {task_id}")
        log(f"Repository: {task.repo}")
        log(f"Instructions: {task.instructions}")
        log(f"Engine: {task.engine}")
        
        # Connect to Redis
        redis_client = redis.from_url(redis_url, decode_responses=True)
        task_key = f"task:{task_id}"
        
        # Update state to running
        redis_client.hset(task_key, "state", "running")
        redis_client.hset(task_key, "started_at", str(int(time.time())))
        log("Task state updated to 'running'")
        
        # 2. Clone repo / checkout branch
        log("Cloning repository...")
        temp_dir = tempfile.mkdtemp()
        repo_dir = Path(temp_dir) / "repo"
        
        try:
            # Clone repository with GitHub token authentication
            repo_url = str(task.repo)
            
            # For GitHub repos, use token authentication for private repos
            if "github.com" in repo_url and github_token:
                # Convert HTTPS URL to use token authentication
                if repo_url.startswith("https://github.com/"):
                    # Extract the path after github.com/
                    repo_path = repo_url.replace("https://github.com/", "")
                    # Create authenticated URL
                    auth_url = f"https://{github_token}@github.com/{repo_path}"
                    clone_cmd = ["git", "clone", auth_url, str(repo_dir)]
                    log("Cloning with GitHub token authentication...")
                else:
                    clone_cmd = ["git", "clone", repo_url, str(repo_dir)]
                    log("Cloning with original URL...")
            else:
                clone_cmd = ["git", "clone", repo_url, str(repo_dir)]
                log("Cloning without authentication...")
            
            result = subprocess.run(clone_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                log(f"ERROR: Failed to clone repository: {result.stderr}")
                redis_client.hset(task_key, "state", "failed")
                redis_client.hset(task_key, "error", f"Clone failed: {result.stderr}")
                sys.exit(1)
                
            log("Repository cloned successfully")
            
            # Create and checkout branch
            branch_name = f"pavo-coding-agent/{task.engine}/{task_id}"
            os.chdir(repo_dir)
            
            # Checkout base branch first
            checkout_base_cmd = ["git", "checkout", task.branch_base]
            result = subprocess.run(checkout_base_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                log(f"WARNING: Could not checkout base branch {task.branch_base}, using current branch")
            
            # Configure git identity before any commits
            subprocess.run(["git", "config", "user.email", "pavo-coding-agent@example.com"], check=True)
            subprocess.run(["git", "config", "user.name", "Pavo Coding Agent"], check=True)
            log("Configured git identity")
            
            # Create new branch
            branch_cmd = ["git", "checkout", "-b", branch_name]
            result = subprocess.run(branch_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                log(f"ERROR: Failed to create branch: {result.stderr}")
                redis_client.hset(task_key, "state", "failed")
                redis_client.hset(task_key, "error", f"Branch creation failed: {result.stderr}")
                sys.exit(1)
                
            log(f"Created and checked out branch: {branch_name}")
            
            # 3. Apply engine
            log(f"Applying {task.engine} engine...")
            engine_start_time = time.time()
            
            if task.engine == CodeEngine.gemini:
                cmd = ["gemini", "-y", "--show_memory_usage", "-d", "-p", task.instructions]
                if not os.getenv("GEMINI_API_KEY"):
                    log("ERROR: GEMINI_API_KEY environment variable not provided")
                    redis_client.hset(task_key, "state", "failed")
                    redis_client.hset(task_key, "error", "GEMINI_API_KEY not provided")
                    sys.exit(1)
            elif task.engine == CodeEngine.claude:
                cmd = ["claude", "-d", "--allowedTools", "Bash,Edit,MultiEdit,NotebookEdit,WebFetch,WebSearch,Write", "-p", task.instructions]
                if not os.getenv("ANTHROPIC_API_KEY"):
                    log("ERROR: ANTHROPIC_API_KEY environment variable not provided")
                    redis_client.hset(task_key, "state", "failed")
                    redis_client.hset(task_key, "error", "ANTHROPIC_API_KEY not provided")
                    sys.exit(1)
            else:  # codex
                cmd = ["codex", "--model", "o3", "--full-auto", "--full-stdout", "-q", task.instructions]
                if not os.getenv("OPENAI_API_KEY"):
                    log("ERROR: OPENAI_API_KEY environment variable not provided")
                    redis_client.hset(task_key, "state", "failed")
                    redis_client.hset(task_key, "error", "OPENAI_API_KEY not provided")
                    sys.exit(1)
            
            try:
                log(f"Running engine command: {' '.join(cmd)}")
                # CLI tools automatically inherit environment variables from container
                subprocess.check_call(cmd, cwd=repo_dir)
                engine_end_time = time.time()
                engine_duration = engine_end_time - engine_start_time
                log(f"Successfully applied {task.engine} engine. Engine took {engine_duration:.2f} seconds")
            except subprocess.CalledProcessError as e:
                log(f"ERROR: {task.engine} engine failed: {e}")
                redis_client.hset(task_key, "state", "failed")
                redis_client.hset(task_key, "error", f"{task.engine} engine failed: {e}")
                sys.exit(1)
            
            # Stage all changes made by the engine
            add_cmd = ["git", "add", "."]
            result = subprocess.run(add_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                log(f"ERROR: Failed to stage changes: {result.stderr}")
                redis_client.hset(task_key, "state", "failed")
                redis_client.hset(task_key, "error", f"Git add failed: {result.stderr}")
                sys.exit(1)
            
            # Commit changes
            commit_msg = f"feat: {task.instructions}\n\nGenerated by Pavo Coding Agent (task: {task_id})"
            commit_cmd = ["git", "commit", "-m", commit_msg]
            result = subprocess.run(commit_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                log(f"ERROR: Failed to commit changes: {result.stderr}")
                redis_client.hset(task_key, "state", "failed")
                redis_client.hset(task_key, "error", f"Git commit failed: {result.stderr}")
                sys.exit(1)
                
            log("Changes committed successfully")
            
            # 4. Run tests (look for common test commands)
            log("Running tests...")
            test_found = False
            test_passed = False
            test_output = ""
            
            # Try common test commands
            test_commands = [
                ["pytest", "-v"],
                ["python", "-m", "pytest", "-v"],
                ["npm", "test"],
                ["make", "test"],
                ["python", "-m", "unittest", "discover"]
            ]
            
            for test_cmd in test_commands:
                if shutil.which(test_cmd[0]):  # Check if command exists
                    test_found = True
                    log(f"Running: {' '.join(test_cmd)}")
                    try:
                        result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=300)
                        test_output = result.stdout + result.stderr
                        
                        if result.returncode == 0:
                            log("Tests passed!")
                            test_passed = True
                            break
                        else:
                            log(f"Tests failed with command {test_cmd[0]}: {result.stderr}")
                    except subprocess.TimeoutExpired:
                        log(f"Tests timed out with command {test_cmd[0]}")
                    except Exception as e:
                        log(f"Error running tests with {test_cmd[0]}: {e}")
                        
            if not test_found:
                log("No test framework found - continuing without running tests")
                redis_client.hset(task_key, "test_status", "no_tests_found")
            elif not test_passed:
                log("Tests failed but continuing with PR creation")
                redis_client.hset(task_key, "test_status", "failed")
                redis_client.hset(task_key, "test_output", test_output)
            else:
                log("Tests passed successfully")
                redis_client.hset(task_key, "test_status", "passed")
            
            # 5. Push & open PR
            log("Pushing branch...")
            
            # Push branch with authentication
            # Set up remote URL with token authentication for pushing
            if "github.com" in repo_url and github_token:
                if repo_url.startswith("https://github.com/"):
                    repo_path = repo_url.replace("https://github.com/", "")
                    auth_url = f"https://{github_token}@github.com/{repo_path}"
                    # Update the remote URL to use token authentication
                    subprocess.run(["git", "remote", "set-url", "origin", auth_url], check=True)
                    log("Updated remote URL for authenticated push")
            
            push_cmd = ["git", "push", "origin", branch_name]
            result = subprocess.run(push_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                log(f"ERROR: Failed to push branch: {result.stderr}")
                redis_client.hset(task_key, "state", "failed")
                redis_client.hset(task_key, "error", f"Git push failed: {result.stderr}")
                sys.exit(1)
                
            log("Branch pushed successfully")
            
            # Create pull request via GitHub API
            log("Creating pull request...")
            
            # Extract owner and repo from URL
            repo_url = str(task.repo)
            if "github.com/" in repo_url:
                repo_path = repo_url.split("github.com/")[1]
                if repo_path.endswith(".git"):
                    repo_path = repo_path[:-4]
                owner, repo_name = repo_path.split("/")
                
                # Create descriptive PR title from first 6 words of instructions
                import re
                words = re.findall(r'\w+', task.instructions.lower())[:6]
                instruction_slug = ' '.join(words).title() if words else 'Task'
                
                # Create PR
                pr_data = {
                    "title": f"feat({task.engine}): {instruction_slug}",
                    "body": f"Automated changes by Pavo Coding Agent.\n\nTask ID: {task_id}\nEngine: {task.engine}\n\nInstructions: {task.instructions}",
                    "head": branch_name,
                    "base": task.branch_base
                }
                
                headers = {
                    "Authorization": f"token {github_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                
                pr_response = requests.post(
                    f"https://api.github.com/repos/{owner}/{repo_name}/pulls",
                    json=pr_data,
                    headers=headers
                )
                
                if pr_response.status_code == 201:
                    pr_url = pr_response.json()["html_url"]
                    log(f"Pull request created: {pr_url}")
                    
                    # 6. Mark done & callback with robust Redis handling
                    try:
                        # Test Redis connection and reconnect if needed
                        redis_client.ping()
                        log("Redis connection verified")
                    except Exception as e:
                        log(f"Redis connection lost, reconnecting: {e}")
                        try:
                            redis_client = redis.from_url(redis_url, decode_responses=True)
                            redis_client.ping()
                            log("Redis reconnected successfully")
                        except Exception as reconnect_error:
                            log(f"CRITICAL: Could not reconnect to Redis: {reconnect_error}")
                            # Still continue - PR was created successfully
                    
                    # Update Redis state with retry logic
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            redis_client.hset(task_key, "state", "done")
                            redis_client.hset(task_key, "pr_url", pr_url)
                            redis_client.hset(task_key, "completed_at", str(int(time.time())))
                            log("Redis state updated successfully")
                            break
                        except Exception as redis_error:
                            log(f"Redis update attempt {attempt + 1} failed: {redis_error}")
                            if attempt == max_retries - 1:
                                log("CRITICAL: All Redis update attempts failed, but PR was created successfully")
                            else:
                                time.sleep(1)  # Wait before retry
                    
                    # Send callback if provided
                    if task.callback_url:
                        callback_data = {
                            "task_id": task_id,
                            "state": "done",
                            "pr_url": pr_url
                        }
                        try:
                            requests.post(task.callback_url, json=callback_data, timeout=10)
                            log("Callback sent successfully")
                        except Exception as e:
                            log(f"WARNING: Callback failed: {e}")
                    
                    log(f"Task {task_id} completed successfully! PR: {pr_url}")
                    
                else:
                    log(f"ERROR: Failed to create PR: {pr_response.status_code} {pr_response.text}")
                    redis_client.hset(task_key, "state", "failed")
                    redis_client.hset(task_key, "error", f"PR creation failed: {pr_response.text}")
                    sys.exit(1)
            else:
                log("ERROR: Only GitHub repositories are supported currently")
                redis_client.hset(task_key, "state", "failed")
                redis_client.hset(task_key, "error", "Only GitHub repositories supported")
                sys.exit(1)
                
        finally:
            # Clean up temp directory
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                log("Cleaned up temporary directory")
                
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        # Try to update Redis if possible
        try:
            if 'redis_client' in locals() and 'task_key' in locals():
                redis_client.hset(task_key, "state", "failed")
                redis_client.hset(task_key, "error", str(e))
        except:
            pass
        sys.exit(1)
    
    # 7. Exit → container auto-removes (--rm)
    log("Worker exiting...")

if __name__ == "__main__":
    main() 