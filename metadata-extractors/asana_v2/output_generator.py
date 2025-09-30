"""
Output Generator for Phase 3: Final Output Generation

This module handles the conversion of scored tasks into CSV and JSON files
with proper formatting, sorting, and column ordering as specified in the plan.
"""

import pandas as pd
import logging
from typing import List, Dict, Any
import os

logger = logging.getLogger(__name__)


class GoldenTaskOutputGenerator:
    """
    Generates final output files for the Golden Task Ranking System.
    
    Implements Phase 3 requirements:
    - Converts scored tasks to pandas DataFrame
    - Sorts by golden_task_score (desc) then impact_score (desc) as tie-breaker
    - Saves CSV with specific column order and formatting
    - Saves JSON with records format for machine consumption
    - Provides transparent traceability with all component scores
    """
    
    def __init__(self, output_dir: str = "."):
        """
        Initialize the output generator.
        
        Args:
            output_dir: Directory where output files will be saved
        """
        self.output_dir = output_dir
        self.csv_filename = "golden_tasks_output.csv"
        self.json_filename = "golden_tasks_output.json"
        
        # CSV Column Order as specified exactly in the plan
        self.csv_column_order = [
            'id', 'name', 'project_data.name', 'assignee', 'assignee_status', 'golden_task_score', 'impact_score', 'engagement_score',
            'timeliness_recency_score', 'is_completed', 'dependent_count',
            'dependency_count', 'subtask_count', 'comment_count', 'follower_count',
            'due_date', 'last_modified_at', 'custom_fields', 'url'
        ]
    
    def generate_outputs(self, scored_tasks: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Generate both CSV and JSON output files from scored tasks.
        
        This implements the complete Phase 3 workflow as specified in the plan:
        1. Create DataFrame from task dictionaries
        2. Sort by golden_task_score (desc) then impact_score (desc)
        3. Write CSV with proper column order and formatting
        4. Write JSON with records format
        5. Log final summary
        
        Args:
            scored_tasks: List of tasks with golden_task_score and component scores
            
        Returns:
            Dict with file paths of created files
        """
        logger.info("Starting Phase 3: Final Output Generation for %s scored tasks", len(scored_tasks))
        
        if not scored_tasks:
            logger.error("No scored tasks provided for output generation")
            return {}
        
        try:
            # Step 1: Process tasks to extract additional fields
            logger.info("Step 1: Processing tasks and extracting additional fields")
            processed_tasks = self._process_tasks_for_output(scored_tasks)
            
            # Step 2: Create DataFrame
            logger.info("Step 2: Converting task list to pandas DataFrame")
            tasks_df = pd.DataFrame(processed_tasks)
            logger.info("✓ DataFrame created with %s rows and %s columns", len(tasks_df), len(tasks_df.columns))
            
            # Step 3: Sort DataFrame as specified in plan
            logger.info("Step 3: Sorting by golden_task_score (desc) with impact_score tie-breaker")
            tasks_df = tasks_df.sort_values(
                by=['golden_task_score', 'impact_score'], 
                ascending=[False, False]
            )
            logger.info("✓ DataFrame sorted successfully")
            
            # Step 4: Validate CSV columns are available
            missing_columns = [col for col in self.csv_column_order if col not in tasks_df.columns]
            if missing_columns:
                logger.warning("Missing columns for CSV output: %s", missing_columns)
                # Filter to only available columns
                available_columns = [col for col in self.csv_column_order if col in tasks_df.columns]
                logger.info("Using available columns: %s", available_columns)
            else:
                available_columns = self.csv_column_order
                logger.info("✓ All required CSV columns are available")
            
            # Step 5: Write CSV File
            csv_path = self._write_csv_file(tasks_df, available_columns)
            
            # Step 6: Write JSON File  
            json_path = self._write_json_file(tasks_df)
            
            # Step 7: Log Final Summary
            self._log_final_summary(tasks_df, csv_path, json_path)
            
            return {
                'csv_path': csv_path,
                'json_path': json_path,
                'task_count': len(tasks_df)
            }
            
        except Exception as e:
            logger.error("Error during output generation: %s", e)
            raise
    
    def _process_tasks_for_output(self, scored_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process scored tasks to extract additional fields for output.
        
        Extracts:
        - project_data.name (direct field access)
        - assignee and assignee_status
        - formats custom_fields for better readability
        
        Args:
            scored_tasks: List of tasks with scores
            
        Returns:
            List of processed tasks with additional fields
        """
        processed_tasks = []
        
        for task in scored_tasks:
            processed_task = task.copy()
            
            # Extract project_data.name (direct field access as requested)
            project_data = task.get("project_data", {})
            if project_data and isinstance(project_data, dict):
                processed_task["project_data.name"] = project_data.get("name", "")
            else:
                processed_task["project_data.name"] = ""
            
            # Extract assignee information
            assignee = task.get("assignee")
            if assignee and isinstance(assignee, dict):
                processed_task["assignee"] = assignee.get("name", "")
            else:
                processed_task["assignee"] = ""
            
            # Extract assignee_status directly
            processed_task["assignee_status"] = task.get("assignee_status", "")
            
            # Format custom_fields for better readability in CSV/JSON
            custom_fields = task.get("custom_fields", [])
            if custom_fields and isinstance(custom_fields, list):
                # Convert custom fields to a more readable format
                formatted_fields = []
                for field in custom_fields:
                    if isinstance(field, dict):
                        field_name = field.get("name", "Unknown")
                        field_value = field.get("display_value") or field.get("text_value") or field.get("number_value")
                        if field_value is not None:
                            formatted_fields.append(f"{field_name}: {field_value}")
                        else:
                            formatted_fields.append(f"{field_name}: (empty)")
                
                # Join all custom fields into a single string for CSV readability
                processed_task["custom_fields"] = "; ".join(formatted_fields) if formatted_fields else ""
            else:
                processed_task["custom_fields"] = ""
            
            processed_tasks.append(processed_task)
        
        logger.info("✓ Processed %s tasks with additional fields (project_data.name, assignee, assignee_status, custom_fields)", len(processed_tasks))
        return processed_tasks
    
    def _write_csv_file(self, tasks_df: pd.DataFrame, column_order: List[str]) -> str:
        """
        Write CSV file with proper formatting as specified in the plan.
        
        Uses index=False and quoting=1 (QUOTE_ALL) as specified.
        """
        csv_path = os.path.join(self.output_dir, self.csv_filename)
        
        logger.info("Step 5: Writing CSV file to %s", csv_path)
        
        try:
            # Write CSV with exact specifications from plan
            tasks_df[column_order].to_csv(
                csv_path, 
                index=False,  # Prevents pandas from adding unnecessary index column
                quoting=1     # csv.QUOTE_ALL - safely quotes fields with special characters
            )
            
            logger.info("✓ CSV file written successfully")
            logger.info("  - Rows: %s", len(tasks_df))
            logger.info("  - Columns: %s", len(column_order))
            logger.info("  - File size: %s bytes", os.path.getsize(csv_path) if os.path.exists(csv_path) else 0)
            
            return csv_path
            
        except Exception as e:
            logger.error("Error writing CSV file: %s", e)
            raise
    
    def _write_json_file(self, tasks_df: pd.DataFrame) -> str:
        """
        Write JSON file with proper formatting as specified in the plan.
        
        Uses orient='records', indent=2, and date_format='iso' as specified.
        """
        json_path = os.path.join(self.output_dir, self.json_filename)
        
        logger.info("Step 6: Writing JSON file to %s", json_path)
        
        try:
            # Write JSON with exact specifications from plan
            tasks_df.to_json(
                json_path,
                orient='records',    # Produces clean list of JSON objects
                indent=2,           # Makes file human-readable
                date_format='iso'   # ISO format for dates
            )
            
            logger.info("✓ JSON file written successfully")
            logger.info("  - Records: %s", len(tasks_df))
            logger.info("  - Format: List of JSON objects")
            logger.info("  - File size: %s bytes", os.path.getsize(json_path) if os.path.exists(json_path) else 0)
            
            return json_path
            
        except Exception as e:
            logger.error("Error writing JSON file: %s", e)
            raise
    
    def _log_final_summary(self, tasks_df: pd.DataFrame, csv_path: str, json_path: str) -> None:
        """
        Log comprehensive final summary as specified in the plan.
        """
        logger.info("Step 7: Final Summary")
        logger.info("=" * 60)
        logger.info("🎉 Golden Task Ranking System - Output Generation Complete!")
        logger.info("=" * 60)
        
        # File information
        logger.info("📁 Output Files Created:")
        logger.info("  📊 CSV File: %s", csv_path)
        logger.info("  📄 JSON File: %s", json_path)
        
        # Task statistics
        logger.info("📈 Task Statistics:")
        logger.info("  Total tasks processed: %s", len(tasks_df))
        completed_tasks = len(tasks_df[tasks_df['is_completed'] == True])
        incomplete_tasks = len(tasks_df[tasks_df['is_completed'] == False])
        logger.info("  Completed tasks: %s (%.1f%%)", completed_tasks, (completed_tasks/len(tasks_df))*100)
        logger.info("  Incomplete tasks: %s (%.1f%%)", incomplete_tasks, (incomplete_tasks/len(tasks_df))*100)
        
        # Score statistics
        logger.info("🏆 Score Statistics:")
        logger.info("  Highest golden_task_score: %.3f", tasks_df['golden_task_score'].max())
        logger.info("  Lowest golden_task_score: %.3f", tasks_df['golden_task_score'].min())
        logger.info("  Average golden_task_score: %.3f", tasks_df['golden_task_score'].mean())
        
        # Top performer
        top_task = tasks_df.iloc[0]
        logger.info("🥇 Top Golden Task:")
        logger.info("  Name: '%s'", top_task['name'])
        logger.info("  Score: %.3f", top_task['golden_task_score'])
        logger.info("  Impact: %.3f, Engagement: %.3f, Timeliness: %.3f", 
                   top_task['impact_score'], top_task['engagement_score'], top_task['timeliness_recency_score'])
        
        # Component score ranges
        logger.info("📊 Component Score Ranges:")
        logger.info("  Impact scores: %.3f - %.3f (max 5.0)", 
                   tasks_df['impact_score'].min(), tasks_df['impact_score'].max())
        logger.info("  Engagement scores: %.3f - %.3f (max 3.0)", 
                   tasks_df['engagement_score'].min(), tasks_df['engagement_score'].max())
        logger.info("  Timeliness scores: %.3f - %.3f (max 2.0)", 
                   tasks_df['timeliness_recency_score'].min(), tasks_df['timeliness_recency_score'].max())
        
        # Transparency note
        logger.info("🔍 Transparency:")
        logger.info("  All component scores included in output for full traceability")
        logger.info("  CSV format: Human-readable with proper column ordering")
        logger.info("  JSON format: Machine-consumable with complete task data")
        
        logger.info("=" * 60)
        logger.info("✅ Golden Task Ranking System execution complete!")
        logger.info("   Files are ready for analysis and decision-making.")
        logger.info("=" * 60)
    
    def preview_top_tasks(self, scored_tasks: List[Dict[str, Any]], top_n: int = 10) -> None:
        """
        Preview top N tasks without generating files (for quick analysis).
        """
        if not scored_tasks:
            logger.warning("No tasks to preview")
            return
        
        # Sort tasks
        sorted_tasks = sorted(scored_tasks, 
                            key=lambda t: (t['golden_task_score'], t['impact_score']), 
                            reverse=True)
        
        logger.info("🔍 Preview: Top %s Golden Tasks", min(top_n, len(sorted_tasks)))
        logger.info("-" * 100)
        logger.info("%-4s %-8s %-8s %-8s %-8s %-10s %s", 
                   "Rank", "Golden", "Impact", "Engage", "Time", "Complete", "Task Name")
        logger.info("-" * 100)
        
        for i, task in enumerate(sorted_tasks[:top_n], 1):
            completed_str = "✓" if task.get('is_completed') else "○"
            name = task.get('name', 'Unnamed')[:50]
            if len(task.get('name', '')) > 50:
                name += "..."
                
            logger.info("%-4d %-8.3f %-8.3f %-8.3f %-8.3f %-10s %s",
                       i, 
                       task['golden_task_score'],
                       task['impact_score'], 
                       task['engagement_score'],
                       task['timeliness_recency_score'],
                       completed_str,
                       name)
        
        logger.info("-" * 100)
