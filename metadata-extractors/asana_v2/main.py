"""
Main Script for Asana Golden Task Ranking System

This script implements the complete 3-phase system as outlined in the plan:
- Phase 1: Foundational Layer - High-Performance Data Extraction
- Phase 2: Golden Task Scoring Logic  
- Phase 3: Final Output Generation

Usage:
    python main.py

Requirements:
    - Set ASANA_ACCESS_TOKEN environment variable
    - Optionally set ASANA_REFRESH_TOKEN environment variable
"""

import asyncio
import logging
import os
import sys
import time
from typing import Dict, Any

# Import all components
from connector import AsanaConnector
from golden_task_scorer import GoldenTaskScorer
from output_generator import GoldenTaskOutputGenerator

# Set up comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('golden_task_ranking.log')
    ]
)
logger = logging.getLogger(__name__)


class AsanaGoldenTaskRankingSystem:
    """
    Complete Golden Task Ranking System orchestrator.
    
    Executes all three phases in sequence:
    1. Data extraction from Asana with full metadata
    2. Golden task scoring with transparent components
    3. Output generation to CSV and JSON files
    """
    
    def __init__(self, output_dir: str = ".", task_concurrency: int = 5):
        """
        Initialize the complete system.
        
        Args:
            output_dir: Directory for output files (default: current directory)
            task_concurrency: Maximum number of tasks to process concurrently per project (default: 5)
        """
        self.output_dir = output_dir
        self.task_concurrency = task_concurrency
        self.connector = None
        self.scorer = GoldenTaskScorer()
        self.output_generator = GoldenTaskOutputGenerator(output_dir)
        
    async def run_complete_system(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """
        Execute the complete 3-phase Golden Task Ranking System.
        
        Args:
            credentials: Asana API credentials
            
        Returns:
            Dict with execution results and statistics
        """
        start_time = time.time()
        
        logger.info("🚀 Starting Asana Golden Task Ranking System")
        logger.info("=" * 70)
        
        try:
            # Phase 1: High-Performance Data Extraction
            logger.info("📡 PHASE 1: High-Performance Data Extraction")
            logger.info("-" * 50)
            
            enriched_tasks = await self._execute_phase_1(credentials)
            
            if not enriched_tasks:
                logger.error("❌ Phase 1 failed - no tasks extracted")
                return {"success": False, "error": "No tasks extracted"}
            
            phase_1_time = time.time()
            logger.info("✅ Phase 1 Complete: %s tasks extracted in %.2f seconds", 
                       len(enriched_tasks), phase_1_time - start_time)
            
            # Phase 2: Golden Task Scoring Logic
            logger.info("\n🏆 PHASE 2: Golden Task Scoring Logic")
            logger.info("-" * 50)
            
            scored_tasks = self._execute_phase_2(enriched_tasks)
            
            phase_2_time = time.time()
            logger.info("✅ Phase 2 Complete: %s tasks scored in %.2f seconds", 
                       len(scored_tasks), phase_2_time - phase_1_time)
            
            # Phase 3: Final Output Generation
            logger.info("\n📊 PHASE 3: Final Output Generation")
            logger.info("-" * 50)
            
            output_results = self._execute_phase_3(scored_tasks)
            
            phase_3_time = time.time()
            logger.info("✅ Phase 3 Complete: Output files generated in %.2f seconds",
                       phase_3_time - phase_2_time)
            
            # Final Results
            total_time = time.time() - start_time
            
            results = {
                "success": True,
                "total_time": total_time,
                "tasks_processed": len(scored_tasks),
                "output_files": output_results,
                "phase_times": {
                    "phase_1": phase_1_time - start_time,
                    "phase_2": phase_2_time - phase_1_time,
                    "phase_3": phase_3_time - phase_2_time
                }
            }
            
            self._log_final_system_summary(results)
            
            return results
            
        except Exception as e:
            logger.error("❌ System execution failed: %s", e)
            return {"success": False, "error": str(e)}
            
        finally:
            # Cleanup
            if self.connector:
                await self.connector.close()
    
    async def _execute_phase_1(self, credentials: Dict[str, str]) -> list:
        """
        Execute Phase 1: High-Performance Data Extraction
        
        - Establishes secure connection with automatic token refresh
        - Discovers all accessible workspaces
        - Spawns parallel tasks for concurrent extraction
        - Processes every task with process_task_with_details
        """
        logger.info("🔗 Establishing secure connection to Asana...")
        
        self.connector = AsanaConnector()
        
        # Connect and automatically discover workspaces
        is_connected = await self.connector.connect(credentials)
        if not is_connected:
            raise Exception("Failed to establish connection to Asana")
        
        logger.info("✓ Connected successfully to %s workspaces", len(self.connector.workspaces))
        
        # Display workspace information
        logger.info("📋 Accessible Workspaces:")
        for i, workspace in enumerate(self.connector.workspaces, 1):
            logger.info("  %s. %s (%s)", i, workspace.get('name', 'Unknown'), workspace.get('gid'))
        
        logger.info("⚡ Starting concurrent data extraction...")
        logger.info("  - Parallel workspace processing")
        logger.info("  - Concurrent project and task fetching") 
        logger.info("  - Task concurrency: %s tasks per project", self.task_concurrency)
        logger.info("  - Full metadata extraction (dependencies, comments, subtasks)")
        
        # Extract enriched tasks using streaming approach (configurable limit for testing)
        enriched_tasks = []
        task_count = 0
        max_tasks = int(os.getenv("ASANA_MAX_TASKS", "100"))
        
        if max_tasks > 0:
            logger.info("  🎯 Limiting extraction to %s tasks for faster processing", max_tasks)
        else:
            logger.info("  🌊 No task limit set - extracting ALL tasks (this may take a long time)")
        
        async for task_data in self.connector.workspace_data(task_concurrency=self.task_concurrency):
            enriched_tasks.append(task_data)
            task_count += 1
            
            if task_count % 25 == 0:
                logger.info("  📥 Extracted %s tasks so far...", task_count)
            
            # Stop after reaching the limit (if limit is set)
            # if max_tasks > 0 and task_count >= max_tasks:
            #     logger.info("  🛑 Reached limit of %s tasks, stopping extraction", max_tasks)
            #     break
        
        logger.info("✅ Data extraction complete!")
        logger.info("  Total tasks: %s", len(enriched_tasks))
        
        # Log extraction statistics
        self._log_phase_1_statistics(enriched_tasks)
        
        return enriched_tasks
    
    def _execute_phase_2(self, enriched_tasks: list) -> list:
        """
        Execute Phase 2: Golden Task Scoring Logic
        
        - Raw feature assembly from all tasks
        - Component score calculation (Impact, Engagement, Timeliness)
        - Final golden_task_score calculation with completion penalty
        """
        logger.info("🧮 Starting comprehensive task scoring...")
        logger.info("  Components: Impact (5 pts) + Engagement (3 pts) + Timeliness (2 pts)")
        logger.info("  Completion penalty: 0.2x multiplier for completed tasks")
        
        # Apply golden task scoring
        scored_tasks = self.scorer.process_all_tasks(enriched_tasks)
        
        logger.info("✅ Scoring complete!")
        
        # Preview top tasks
        self.output_generator.preview_top_tasks(scored_tasks, top_n=5)
        
        return scored_tasks
    
    def _execute_phase_3(self, scored_tasks: list) -> Dict[str, Any]:
        """
        Execute Phase 3: Final Output Generation
        
        - Convert to pandas DataFrame with proper sorting
        - Generate CSV with specified column order and formatting
        - Generate JSON with records format for machine consumption
        - Provide complete transparency with all component scores
        """
        logger.info("💾 Generating final output files...")
        logger.info("  CSV: Human-readable format with logical column ordering")
        logger.info("  JSON: Machine-consumable format with complete data")
        
        # Generate both output files
        output_results = self.output_generator.generate_outputs(scored_tasks)
        
        return output_results
    
    def _log_phase_1_statistics(self, enriched_tasks: list) -> None:
        """Log detailed Phase 1 extraction statistics"""
        if not enriched_tasks:
            return
        
        tasks_with_deps = sum(1 for t in enriched_tasks if t.get("dependencies"))
        tasks_with_dependents = sum(1 for t in enriched_tasks if t.get("dependents"))
        tasks_with_comments = sum(1 for t in enriched_tasks if t.get("comments"))
        tasks_with_subtasks = sum(1 for t in enriched_tasks if t.get("recursive_subtasks"))
        
        logger.info("📊 Phase 1 Data Quality Statistics:")
        logger.info("  Tasks with dependencies: %s (%.1f%%)", 
                   tasks_with_deps, (tasks_with_deps/len(enriched_tasks))*100)
        logger.info("  Tasks with dependents: %s (%.1f%%)", 
                   tasks_with_dependents, (tasks_with_dependents/len(enriched_tasks))*100)
        logger.info("  Tasks with comments: %s (%.1f%%)", 
                   tasks_with_comments, (tasks_with_comments/len(enriched_tasks))*100)
        logger.info("  Tasks with subtasks: %s (%.1f%%)", 
                   tasks_with_subtasks, (tasks_with_subtasks/len(enriched_tasks))*100)
    
    def _log_final_system_summary(self, results: Dict[str, Any]) -> None:
        """Log comprehensive final system summary"""
        logger.info("\n" + "=" * 70)
        logger.info("🎯 ASANA GOLDEN TASK RANKING SYSTEM - EXECUTION SUMMARY")
        logger.info("=" * 70)
        
        logger.info("⏱️  Execution Time:")
        logger.info("   Phase 1 (Data Extraction): %.2f seconds", results["phase_times"]["phase_1"])
        logger.info("   Phase 2 (Task Scoring): %.2f seconds", results["phase_times"]["phase_2"])
        logger.info("   Phase 3 (Output Generation): %.2f seconds", results["phase_times"]["phase_3"])
        logger.info("   Total Execution Time: %.2f seconds", results["total_time"])
        
        logger.info("📈 Processing Results:")
        logger.info("   Tasks Processed: %s", results["tasks_processed"])
        logger.info("   CSV Output: %s", results["output_files"]["csv_path"])
        logger.info("   JSON Output: %s", results["output_files"]["json_path"])
        
        logger.info("🏗️  System Architecture:")
        logger.info("   ✓ API-First Approach: Non-intrusive, secure, maintainable")
        logger.info("   ✓ Impact & Activity Proxies: Objective measures of task value")
        logger.info("   ✓ Actionable & Transparent Output: Complete component traceability")
        
        logger.info("🔍 Algorithm Components:")
        logger.info("   ✓ Impact Score: Dependencies/dependents analysis (max 5 pts)")
        logger.info("   ✓ Engagement Score: Subtasks/comments/followers (max 3 pts)")
        logger.info("   ✓ Timeliness Score: Urgency + recency decay (max 2 pts)")
        logger.info("   ✓ Completion Penalty: 0.2x multiplier for completed tasks")
        
        logger.info("=" * 70)
        logger.info("✨ SUCCESS: Golden Task Ranking System execution complete!")
        logger.info("   Your ranked tasks are ready for data-driven decision making.")
        logger.info("=" * 70)


def get_credentials_from_environment() -> Dict[str, str]:
    """Get Asana credentials from environment variables"""
    access_token = os.getenv("ASANA_ACCESS_TOKEN")
    refresh_token = os.getenv("ASANA_REFRESH_TOKEN")
    
    if not access_token:
        raise ValueError("ASANA_ACCESS_TOKEN environment variable is required")
    
    credentials = {"access_token": access_token}
    if refresh_token:
        credentials["refresh_token"] = refresh_token
        logger.info("✓ Using access token with refresh token")
    else:
        logger.warning("⚠️  No refresh token provided - token refresh will not be available")
    
    return credentials


async def main():
    """Main entry point for the Golden Task Ranking System"""
    
    print("🚀 Asana Golden Task Ranking System")
    print("=" * 50)
    print("This system implements a complete 3-phase automated workflow:")
    print("1. High-performance data extraction from Asana")
    print("2. Golden task scoring with transparent components")  
    print("3. Ranked output generation in CSV and JSON formats")
    print("=" * 50)
    print()
    
    try:
        # Get credentials
        logger.info("🔑 Loading Asana credentials...")
        credentials = get_credentials_from_environment()
        logger.info("✓ Credentials loaded successfully")
        
        # Initialize and run system
        output_dir = os.getenv("OUTPUT_DIR", ".")
        task_concurrency = int(os.getenv("ASANA_TASK_CONCURRENCY", "5"))
        system = AsanaGoldenTaskRankingSystem(output_dir, task_concurrency)
        
        results = await system.run_complete_system(credentials)
        
        if results["success"]:
            print("\n✅ System execution completed successfully!")
            print(f"📊 Processed {results['tasks_processed']} tasks in {results['total_time']:.1f} seconds")
            print(f"📁 Output files saved to: {output_dir}")
            return 0
        else:
            print(f"\n❌ System execution failed: {results.get('error', 'Unknown error')}")
            return 1
            
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\nRequired environment variables:")
        print("  ASANA_ACCESS_TOKEN - Your Asana Personal Access Token")
        print("  ASANA_REFRESH_TOKEN - Your Asana refresh token (optional)")
        print("  OUTPUT_DIR - Output directory path (optional, defaults to current directory)")
        print("  ASANA_TASK_CONCURRENCY - Max concurrent tasks per project (optional, defaults to 5)")
        print("  ASANA_MAX_TASKS - Max total tasks to extract (optional, defaults to 100)")
        return 1
        
    except Exception as e:
        logger.exception("Unexpected error during system execution")
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
