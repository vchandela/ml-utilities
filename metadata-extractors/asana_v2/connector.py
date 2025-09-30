"""
Asana Connector for Phase 1.2: High-Performance, Concurrent Task Extraction

This module contains the AsanaConnector class that orchestrates the entire
data extraction process as outlined in the plan.
"""

import asyncio
import logging
from typing import List, Dict, Any, AsyncIterator
try:
    from .connection import AsanaConnection
    from .api_utils import (
        fetch_workspaces,
        fetch_workspace_projects,
        fetch_project_tasks,
        process_task_with_details
    )
except ImportError:
    from connection import AsanaConnection
    from api_utils import (
        fetch_workspaces,
        fetch_workspace_projects,
        fetch_project_tasks,
        process_task_with_details
    )

logger = logging.getLogger(__name__)


class AsanaConnector:
    """
    Asana connector for fetching project management data.
    
    This class implements Phase 1.2 of the plan:
    - Automatically discovers all workspaces
    - Spawns parallel tasks for each workspace
    - Concurrently fetches projects and tasks within projects
    - Uses process_task_with_details for every single task
    """
    
    def __init__(self):
        self.connection: AsanaConnection = None
        self.workspaces = None
        self._credentials = None
        
    async def connect(self, credentials: Dict[str, str]) -> bool:
        """
        Establish a connection to Asana and automatically discover workspaces.
        
        Args:
            credentials: Dictionary containing 'access_token' and optionally 'refresh_token'
            
        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            logger.info("Connecting to Asana...")
            
            if not credentials.get("access_token"):
                logger.error("Missing access_token in credentials")
                return False
                
            self._credentials = credentials.copy()
            self.connection = AsanaConnection(credentials)
            
            # Test the connection first
            if not await self.connection.test_connection():
                logger.error("Connection test failed")
                return False
            
            # Fetch workspaces to validate access (this also serves as workspace discovery)
            workspaces_data = await fetch_workspaces(self.connection)
            if not workspaces_data or not workspaces_data.get("data"):
                logger.error("No workspaces found or accessible - connection failed")
                return False
                
            self.workspaces = workspaces_data.get("data", [])
            logger.info("Successfully connected to Asana. Found %s workspaces.", len(self.workspaces))
            
            return True
            
        except Exception as e:
            logger.error("Error connecting to Asana: %s", e)
            if self.connection:
                await self.connection.close()
                self.connection = None
            return False
    
    async def workspace_data(self, task_concurrency: int = 5) -> AsyncIterator[Dict[str, Any]]:
        """
        Asynchronously fetch and yield all tasks with their detailed metadata.
        
        This implements the core Phase 1.2 functionality:
        - Spawns parallel tasks for each workspace
        - Within each workspace, concurrently fetches projects and tasks
        - For every single task, uses process_task_with_details
        
        Args:
            task_concurrency: Maximum number of tasks to process concurrently per project (default: 5)
        
        Yields:
            Dict[str, Any]: Enriched task data with all metadata
        """
        if not self.connection:
            logger.error("Not connected to Asana. Call connect() first.")
            return
            
        if not self.workspaces:
            logger.warning("No workspaces available to process.")
            return
            
        logger.info("Starting Asana workspace_data stream for %s workspaces...", len(self.workspaces))
        
        # Create workspace processing tasks for parallel execution
        workspace_tasks = []
        for workspace in self.workspaces:
            workspace_id = workspace.get("gid")
            workspace_name = workspace.get("name", "Unknown")
            
            if not workspace_id:
                logger.warning("Skipping workspace without GID: %s", workspace)
                continue
                
            logger.info("Adding workspace %s (%s) to processing queue", workspace_name, workspace_id)
            workspace_task = self._process_workspace_data(workspace_id, workspace_name, task_concurrency)
            workspace_tasks.append(workspace_task)
        
        if not workspace_tasks:
            logger.warning("No valid workspaces to process.")
            return
            
        # Process workspaces concurrently and yield results
        processed_count = 0
        try:
            async for task_data in self._merge_async_iterators(workspace_tasks):
                processed_count += 1
                yield task_data
                
                if processed_count % 50 == 0:
                    logger.info("Yielded %s enriched tasks so far...", processed_count)
                    
        except Exception as e:
            logger.error("Error during workspace data processing: %s", e)
            
        logger.info("Finished Asana workspace_data stream. Yielded %s total enriched tasks.", processed_count)
    
    async def _process_workspace_data(self, workspace_id: str, workspace_name: str, task_concurrency: int) -> AsyncIterator[Dict[str, Any]]:
        """Process all data from a single workspace"""
        logger.info("Starting to process data for workspace %s (%s)", workspace_name, workspace_id)
        
        try:
            # Fetch all projects in this workspace
            logger.info("Fetching projects for workspace %s", workspace_name)
            projects_data = await fetch_workspace_projects(self.connection, workspace_id)
            
            # Create project processing tasks for parallel execution
            project_tasks = []
            for project_data in projects_data:
                project_task = self._process_project_data(project_data, workspace_id, task_concurrency)
                project_tasks.append(project_task)
            
            # Process projects concurrently
            if project_tasks:
                logger.info("Processing %s projects concurrently in workspace %s", len(project_tasks), workspace_name)
                async for task_data in self._merge_async_iterators(project_tasks):
                    yield task_data
                    
        except Exception as e:
            logger.error("Error processing workspace %s (%s): %s", workspace_name, workspace_id, e)
    
    async def _process_project_data(self, project_data: Dict[str, Any], workspace_id: str, task_concurrency: int) -> AsyncIterator[Dict[str, Any]]:
        """Process all tasks from a single project"""
        project_id = project_data.get("gid")
        project_name = project_data.get("name", "Unknown")
        
        if not project_id:
            logger.warning("Skipping project without GID: %s", project_data)
            return
        
        try:
            # Fetch all tasks in this project
            logger.info("Fetching tasks for project %s (%s)", project_name, project_id)
            tasks_data = await fetch_project_tasks(self.connection, project_id)
            
            if not tasks_data:
                logger.info("No tasks found in project %s", project_name)
                return
            
            logger.info("Processing %s tasks from project %s", len(tasks_data), project_name)
            
            # Process tasks with controlled concurrency
            # This is where the KEY function process_task_with_details is called for every single task
            task_semaphore = asyncio.Semaphore(task_concurrency)  # Limit concurrent tasks
            
            async def process_single_task(task_data):
                """Process a single task with concurrency control"""
                async with task_semaphore:
                    try:
                        # Add workspace and project context to task
                        task_data["workspace_id"] = workspace_id
                        task_data["project_data"] = project_data
                        
                        # Process task with all its details (dependencies, comments, subtasks)
                        # Each task still makes 3 parallel API calls internally
                        enriched_task = await process_task_with_details(self.connection, task_data)
                        return enriched_task
                        
                    except Exception as e:
                        logger.error("Error processing task %s in project %s: %s", 
                                   task_data.get('gid', 'unknown'), project_name, e)
                        return None
            
            # Create tasks for concurrent processing
            task_processing_coroutines = [
                process_single_task(task_data) for task_data in tasks_data
            ]
            
            # Process tasks in parallel (controlled by semaphore)
            logger.info("Processing %s tasks with max %s concurrent tasks", len(task_processing_coroutines), task_concurrency)
            
            for coro in asyncio.as_completed(task_processing_coroutines):
                try:
                    enriched_task = await coro
                    if enriched_task is not None:
                        yield enriched_task
                except Exception as e:
                    logger.error("Error in concurrent task processing: %s", e)
                    continue
                    
        except Exception as e:
            logger.error("Error processing project %s: %s", project_name, e)
    
    async def _merge_async_iterators(self, iterators: List[AsyncIterator]) -> AsyncIterator[Dict[str, Any]]:
        """
        Merge multiple async iterators, yielding items as they become available.
        Handles exceptions within iterators gracefully.
        """
        if not iterators:
            return

        pending_tasks = set()
        iterator_map = {}  # Map task back to its iterator

        # Initialize: Create a task for the first item of each iterator
        for i, iterator in enumerate(iterators):
            try:
                # Get the __anext__ coroutine
                anext_coro = iterator.__anext__()
                # Create task and add to pending set
                task = asyncio.create_task(anext_coro)
                pending_tasks.add(task)
                iterator_map[task] = iterator  # Map task to its origin iterator
            except Exception as init_e:
                logger.error("Error initializing Asana data iterator %s: %s", i, init_e)
                # Don't add this iterator if initialization fails

        while pending_tasks:
            # Wait for the next task to complete
            done, pending_tasks = await asyncio.wait(pending_tasks, return_when=asyncio.FIRST_COMPLETED)

            for task in done:
                origin_iterator = iterator_map.pop(task)  # Get the iterator this task belonged to
                try:
                    # Get the next item from the iterator
                    item = task.result()
                    yield item
                    # Get the next item from the iterator
                    anext_coro = origin_iterator.__anext__()
                    # Create task and add to pending set
                    task = asyncio.create_task(anext_coro)
                    pending_tasks.add(task)
                    iterator_map[task] = origin_iterator
                except StopAsyncIteration:
                    # This iterator is finished, do nothing more with it
                    logger.debug("Asana data iterator finished.")
                except Exception as e:
                    logger.error("Error getting next item from Asana data iterator: %s", e)
                    # Stop processing this specific iterator
    
    async def close(self) -> None:
        """Close the connection to Asana and clean up resources."""
        logger.info("Closing AsanaConnector connection.")
        if self.connection:
            await self.connection.close()
            self.connection = None
        self.workspaces = None
        self._credentials = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
