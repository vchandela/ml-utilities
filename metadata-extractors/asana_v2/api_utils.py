"""
API utilities for Asana data extraction

This module contains all the functions needed for Phase 1.2:
High-Performance, Concurrent Task Extraction
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Set
try:
    from .connection import AsanaConnection
except ImportError:
    from connection import AsanaConnection

logger = logging.getLogger(__name__)


async def fetch_workspaces(connection: AsanaConnection) -> Optional[Dict[str, Any]]:
    """Fetch all workspaces available to the authenticated user"""
    try:
        response = await connection.make_authenticated_request(
            "GET", 
            connection.base_url + "/workspaces"
        )
        
        if response.status_code == 200:
            logger.info("Successfully fetched workspaces")
            return response.json()
        else:
            logger.error("Failed to fetch workspaces: %s - %s", response.status_code, response.text)
            return None
            
    except Exception as e:
        logger.error("Exception while fetching workspaces: %s", e)
        return None


async def fetch_workspace_projects(connection: AsanaConnection, workspace_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch all projects in a workspace with pagination"""
    projects = []
    url = connection.base_url + "/projects"
    params = {
        "workspace": workspace_id,
        "limit": limit,
        "opt_fields": "gid,name,notes,archived,public,owner,current_status,due_date,start_on,created_at,modified_at,team,workspace,members,followers,custom_fields"
    }
    
    try:
        while url:
            if url == connection.base_url + "/projects":
                response = await connection.make_authenticated_request("GET", url, params=params)
            else:
                response = await connection.make_authenticated_request("GET", url)
            
            if response.status_code == 200:
                data = response.json()
                projects.extend(data.get("data", []))
                
                # Handle pagination
                next_page = data.get("next_page")
                if next_page and next_page.get("uri"):
                    url = next_page["uri"]
                    params = None  # URL already contains parameters
                else:
                    break
            else:
                logger.error("Failed to fetch projects: %s - %s", response.status_code, response.text)
                break
                
        logger.info("Fetched %s projects from workspace %s", len(projects), workspace_id)
        return projects
        
    except Exception as e:
        logger.error("Exception while fetching projects: %s", e)
        return []


async def fetch_project_tasks(connection: AsanaConnection, project_gid: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch all tasks in a project with pagination"""
    tasks = []
    url = connection.base_url + "/tasks"
    params = {
        "project": project_gid,
        "limit": limit,
        "opt_fields": "gid,name,notes,html_notes,completed,assignee.name,assignee_status,completed_at,due_on,due_at,start_on,start_at,created_at,modified_at,workspace.name,projects.name,parent,tags,followers,custom_fields,permalink_url,attachments.name"
    }
    
    try:
        while url:
            if url == connection.base_url + "/tasks":
                response = await connection.make_authenticated_request("GET", url, params=params)
            else:
                response = await connection.make_authenticated_request("GET", url)
            
            if response.status_code == 200:
                data = response.json()
                tasks.extend(data.get("data", []))
                
                # Handle pagination
                next_page = data.get("next_page")
                if next_page and next_page.get("uri"):
                    url = next_page["uri"]
                    params = None  # URL already contains parameters
                else:
                    break
            else:
                logger.error("Failed to fetch tasks from project %s: %s - %s", project_gid, response.status_code, response.text)
                break
                
        logger.info("Fetched %s tasks from project %s", len(tasks), project_gid)
        return tasks
        
    except Exception as e:
        logger.error("Exception while fetching tasks from project %s: %s", project_gid, e)
        return []


async def fetch_task_details(connection: AsanaConnection, task_gid: str) -> Optional[Dict[str, Any]]:
    """
    Fetch detailed information about a specific task.
    
    This is the KEY function for Phase 1.2 as mentioned in the plan.
    It gets core fields including dependencies and dependents.
    """
    try:
        params = {
            "opt_fields": "gid,name,notes,html_notes,completed,assignee,assignee_status,completed_at,due_on,due_at,start_on,start_at,created_at,modified_at,workspace,projects,parent,tags,followers,custom_fields,permalink_url,attachments,dependencies,dependents"
        }
        
        response = await connection.make_authenticated_request(
            "GET", 
            connection.base_url + "/tasks/" + task_gid, 
            params=params
        )
        
        if response.status_code == 200:
            logger.debug("Successfully fetched details for task %s", task_gid)
            return response.json().get("data")
        else:
            logger.error("Failed to fetch task %s: %s - %s", task_gid, response.status_code, response.text)
            return None
            
    except Exception as e:
        logger.error("Exception while fetching task %s: %s", task_gid, e)
        return None


async def fetch_task_comments(connection: AsanaConnection, task_gid: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch comments (stories) for a given task with pagination"""
    comments = []
    url = connection.base_url + "/tasks/" + task_gid + "/stories"
    params = {
        "limit": limit,
        "opt_fields": "gid,text,html_text,created_at,created_by,resource_type,type,is_pinned"
    }
    
    try:
        while url:
            if url == connection.base_url + "/tasks/" + task_gid + "/stories":
                response = await connection.make_authenticated_request("GET", url, params=params)
            else:
                response = await connection.make_authenticated_request("GET", url)
            
            if response.status_code == 200:
                data = response.json()
                stories = data.get("data", [])
                
                # Filter for actual comments (stories with type 'comment')
                task_comments = [story for story in stories if story.get("type") == "comment"]
                comments.extend(task_comments)
                
                # Handle pagination
                next_page = data.get("next_page")
                if next_page and next_page.get("uri"):
                    url = next_page["uri"]
                    params = None  # URL already contains parameters
                else:
                    break
            else:
                logger.error("Failed to fetch comments for task %s: %s - %s", task_gid, response.status_code, response.text)
                break
                
        logger.debug("Fetched %s comments for task %s", len(comments), task_gid)
        return comments
        
    except Exception as e:
        logger.error("Exception while fetching comments for task %s: %s", task_gid, e)
        return []


async def fetch_task_subtasks(connection: AsanaConnection, task_gid: str) -> List[Dict[str, Any]]:
    """Fetch direct subtasks for a given task"""
    try:
        params = {
            "opt_fields": "gid,name,completed,assignee,due_on"
        }
        
        response = await connection.make_authenticated_request(
            "GET", 
            connection.base_url + "/tasks/" + task_gid + "/subtasks", 
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            subtasks = data.get("data", [])
            logger.debug("Fetched %s subtasks for task %s", len(subtasks), task_gid)
            return subtasks
        else:
            logger.error("Failed to fetch subtasks for task %s: %s - %s", task_gid, response.status_code, response.text)
            return []
            
    except Exception as e:
        logger.error("Exception while fetching subtasks for task %s: %s", task_gid, e)
        return []


async def fetch_task_subtasks_recursive(connection: AsanaConnection, task_gid: str, visited_tasks: Set[str] = None, max_depth: int = 10, current_depth: int = 0) -> List[Dict[str, Any]]:
    """
    Fetch all subtasks for a given task recursively with cycle detection.
    
    This is one of the KEY functions for Phase 1.2 as mentioned in the plan.
    It gets a flattened list of all nested subtasks, no matter how deep.
    
    Args:
        connection: Asana connection object
        task_gid: The task GID to fetch subtasks for
        visited_tasks: Set of task GIDs already visited to prevent cycles
        max_depth: Maximum recursion depth to prevent infinite recursion
        current_depth: Current recursion depth
        
    Returns:
        List of all subtasks (including nested subtasks) as task data dictionaries
    """
    if visited_tasks is None:
        visited_tasks = set()
    
    # Prevent infinite recursion
    if current_depth >= max_depth:
        logger.warning("Maximum recursion depth (%s) reached for task %s", max_depth, task_gid)
        return []
    
    # Prevent cycles
    if task_gid in visited_tasks:
        logger.warning("Cycle detected: task %s already visited", task_gid)
        return []
    
    visited_tasks.add(task_gid)
    all_subtasks = []
    
    try:
        # Fetch direct subtasks
        direct_subtasks = await fetch_task_subtasks(connection, task_gid)
        
        for subtask in direct_subtasks:
            subtask_gid = subtask.get("gid")
            if not subtask_gid:
                continue
            
            # Fetch detailed information about the subtask
            detailed_subtask = await fetch_task_details(connection, subtask_gid)
            if detailed_subtask:
                all_subtasks.append(detailed_subtask)
                
                # Recursively fetch subtasks of this subtask
                # Pass the same visited_tasks set to maintain cycle detection across all branches
                nested_subtasks = await fetch_task_subtasks_recursive(
                    connection, 
                    subtask_gid, 
                    visited_tasks,  # Use same set for global cycle detection
                    max_depth, 
                    current_depth + 1
                )
                all_subtasks.extend(nested_subtasks)
                
        logger.debug("Fetched %s total subtasks (recursive) for task %s", len(all_subtasks), task_gid)
        return all_subtasks
        
    except Exception as e:
        logger.error("Exception while fetching recursive subtasks for task %s: %s", task_gid, e)
        return []


async def process_task_with_details(connection: AsanaConnection, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a task with all its details including comments and recursive subtasks.
    
    This is the KEY orchestration function mentioned in Phase 1.2 of the plan.
    It aggregates all necessary information by making parallel calls to:
    - fetch_task_details: To get core fields like dependencies and dependents
    - fetch_task_comments: To get all comment stories
    - fetch_task_subtasks_recursive: To get flattened list of nested subtasks
    """
    task_id = task_data.get("gid")
    if not task_id:
        return task_data
    
    try:
        # Make parallel calls to fetch all task details
        logger.debug("Processing task with details: %s", task_id)
        
        detailed_task, comments, recursive_subtasks = await asyncio.gather(
            fetch_task_details(connection, task_id),
            fetch_task_comments(connection, task_id),
            fetch_task_subtasks_recursive(connection, task_id),
            return_exceptions=True
        )
        
        # Start with the original task data
        enriched_task = task_data.copy()
        
        # Merge detailed task information
        if isinstance(detailed_task, dict):
            enriched_task.update(detailed_task)
        elif isinstance(detailed_task, Exception):
            logger.error("Error fetching task details for %s: %s", task_id, detailed_task)
        
        # Add comments
        if isinstance(comments, list):
            enriched_task["comments"] = comments
        elif isinstance(comments, Exception):
            logger.error("Error fetching comments for task %s: %s", task_id, comments)
            enriched_task["comments"] = []
        
        # Add recursive subtasks
        if isinstance(recursive_subtasks, list):
            enriched_task["recursive_subtasks"] = recursive_subtasks
        elif isinstance(recursive_subtasks, Exception):
            logger.error("Error fetching recursive subtasks for task %s: %s", task_id, recursive_subtasks)
            enriched_task["recursive_subtasks"] = []
        
        logger.debug("Completed processing task with details: %s", task_id)
        return enriched_task
        
    except Exception as e:
        logger.error("Exception while processing task with details %s: %s", task_id, e)
        return task_data
