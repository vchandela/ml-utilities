"""
Golden Task Scorer for Phase 2: Golden Task Scoring Logic

This module implements the complete scoring system outlined in the plan:
- Raw Feature Assembly (Phase 2.1)
- Component Score Calculation (Phase 2.2)
- Final Score Calculation and Storage (Phase 2.3)
"""

import math
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class GoldenTaskScorer:
    """
    Calculates golden_task_score and its individual components for tasks.
    
    Scoring Components:
    1. Impact Score (max 5 points) - based on dependencies and dependents
    2. Engagement Score (max 3 points) - based on subtasks, comments, followers  
    3. Timeliness & Recency Score (max 2 points) - based on due dates and activity
    
    Final golden_task_score = sum of components × completion penalty (0.2 if completed)
    """
    
    def __init__(self):
        self.max_log_dependent_count = 0
        self.max_log_dependency_count = 0
        self.max_log_subtask_count = 0
        self.max_log_comment_count = 0
        self.max_log_follower_count = 0
        
    def process_all_tasks(self, enriched_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process all tasks to calculate golden_task_score and components.
        
        This implements the complete Phase 2 workflow:
        1. Raw Feature Assembly for all tasks
        2. Calculate normalization factors (max values)
        3. Component Score Calculation for each task
        4. Final Score Calculation and Storage
        
        Args:
            enriched_tasks: List of tasks from Phase 1.2 extraction
            
        Returns:
            List of tasks with golden_task_score and all component scores
        """
        logger.info("Starting Phase 2: Golden Task Scoring for %s tasks", len(enriched_tasks))
        
        if not enriched_tasks:
            logger.warning("No tasks provided for scoring")
            return []
        
        # Phase 2.1: Raw Feature Assembly
        logger.info("Phase 2.1: Assembling raw features for all tasks")
        feature_rich_tasks = []
        for task in enriched_tasks:
            feature_task = self._assemble_raw_features(task)
            feature_rich_tasks.append(feature_task)
        
        logger.info("✓ Raw features assembled for %s tasks", len(feature_rich_tasks))
        
        # Calculate normalization factors (max log values across entire dataset)
        logger.info("Calculating normalization factors across dataset")
        self._calculate_normalization_factors(feature_rich_tasks)
        
        logger.info("✓ Normalization factors calculated:")
        logger.info("  Max log dependent count: %.3f", self.max_log_dependent_count)
        logger.info("  Max log dependency count: %.3f", self.max_log_dependency_count)
        logger.info("  Max log subtask count: %.3f", self.max_log_subtask_count)
        logger.info("  Max log comment count: %.3f", self.max_log_comment_count)
        logger.info("  Max log follower count: %.3f", self.max_log_follower_count)
        
        # Phase 2.2 & 2.3: Component Score Calculation and Final Score
        logger.info("Phase 2.2 & 2.3: Calculating component scores and final golden_task_score")
        scored_tasks = []
        for task in feature_rich_tasks:
            scored_task = self._calculate_all_scores(task)
            scored_tasks.append(scored_task)
        
        logger.info("✓ Golden task scoring complete for %s tasks", len(scored_tasks))
        
        # Log scoring statistics
        self._log_scoring_statistics(scored_tasks)
        
        return scored_tasks
    
    def _assemble_raw_features(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 2.1: Raw Feature Assembly
        
        Create a single, feature-rich dictionary containing the raw numbers 
        needed for scoring as specified in the plan.
        """
        # Start with the original task data
        feature_task = task_data.copy()
        
        # Identity fields
        feature_task["id"] = task_data.get("gid", "")
        feature_task["name"] = task_data.get("name", "")
        feature_task["url"] = task_data.get("permalink_url", "")
        
        # Status fields
        feature_task["is_completed"] = task_data.get("completed", False)
        feature_task["due_date"] = task_data.get("due_on") or task_data.get("due_at")
        feature_task["last_modified_at"] = task_data.get("modified_at")
        
        # Impact Counts (from dependencies and dependents)
        dependencies = task_data.get("dependencies", [])
        dependents = task_data.get("dependents", [])
        feature_task["dependent_count"] = len(dependents) if dependents else 0
        feature_task["dependency_count"] = len(dependencies) if dependencies else 0
        
        # Engagement Counts
        recursive_subtasks = task_data.get("recursive_subtasks", [])
        comments = task_data.get("comments", [])
        followers = task_data.get("followers", [])
        
        feature_task["subtask_count"] = len(recursive_subtasks) if recursive_subtasks else 0
        feature_task["comment_count"] = len(comments) if comments else 0
        feature_task["follower_count"] = len(followers) if followers else 0
        
        logger.debug("Assembled features for task %s: deps=%s, dependents=%s, subtasks=%s, comments=%s, followers=%s",
                    feature_task["id"], feature_task["dependency_count"], feature_task["dependent_count"],
                    feature_task["subtask_count"], feature_task["comment_count"], feature_task["follower_count"])
        
        return feature_task
    
    def _calculate_normalization_factors(self, feature_tasks: List[Dict[str, Any]]) -> None:
        """
        Calculate maximum log-transformed values across the entire dataset.
        These are used for normalizing scores to 0-1 range as specified in the plan.
        """
        max_log_dependent = 0
        max_log_dependency = 0
        max_log_subtask = 0
        max_log_comment = 0
        max_log_follower = 0
        
        for task in feature_tasks:
            # Log-transform counts (1 + count to avoid log(0))
            log_dependent = math.log(1 + task["dependent_count"])
            log_dependency = math.log(1 + task["dependency_count"])
            log_subtask = math.log(1 + task["subtask_count"])
            log_comment = math.log(1 + task["comment_count"])
            log_follower = math.log(1 + task["follower_count"])
            
            # Track maximums
            max_log_dependent = max(max_log_dependent, log_dependent)
            max_log_dependency = max(max_log_dependency, log_dependency)
            max_log_subtask = max(max_log_subtask, log_subtask)
            max_log_comment = max(max_log_comment, log_comment)
            max_log_follower = max(max_log_follower, log_follower)
        
        # Store for normalization (avoid division by zero)
        self.max_log_dependent_count = max(max_log_dependent, 0.001)
        self.max_log_dependency_count = max(max_log_dependency, 0.001)
        self.max_log_subtask_count = max(max_log_subtask, 0.001)
        self.max_log_comment_count = max(max_log_comment, 0.001)
        self.max_log_follower_count = max(max_log_follower, 0.001)
    
    def _calculate_all_scores(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate all component scores and final golden_task_score for a single task.
        
        This implements Phase 2.2 (Component Score Calculation) and 
        Phase 2.3 (Final Score Calculation and Storage).
        """
        scored_task = task.copy()
        
        # Phase 2.2: Calculate individual component scores
        impact_score = self._calculate_impact_score(task)
        engagement_score = self._calculate_engagement_score(task)
        timeliness_score = self._calculate_timeliness_recency_score(task)
        
        # Phase 2.3: Final Score Calculation
        golden_task_score = impact_score + engagement_score + timeliness_score
        
        # Apply penalty for completed tasks (multiply by 0.2)
        if task["is_completed"]:
            golden_task_score *= 0.2
            logger.debug("Applied completion penalty to task %s", task["id"])
        
        # Store all scores in the task's feature dictionary (as required by plan)
        scored_task["golden_task_score"] = golden_task_score
        scored_task["impact_score"] = impact_score
        scored_task["engagement_score"] = engagement_score
        scored_task["timeliness_recency_score"] = timeliness_score
        
        logger.debug("Scored task %s: golden=%.3f (impact=%.3f, engagement=%.3f, timeliness=%.3f)",
                    task["id"], golden_task_score, impact_score, engagement_score, timeliness_score)
        
        return scored_task
    
    def _calculate_impact_score(self, task: Dict[str, Any]) -> float:
        """
        Component 1: Upstream/Downstream Impact Score (Max: 5 points)
        
        Based on dependencies and dependents with log-transformation.
        dependent_count weighted 70%, dependency_count weighted 30%.
        """
        # Log-transform counts
        log_dependent_count = math.log(1 + task["dependent_count"])
        log_dependency_count = math.log(1 + task["dependency_count"])
        
        # Normalize to 0-1 range
        norm_log_dependent = log_dependent_count / self.max_log_dependent_count
        norm_log_dependency = log_dependency_count / self.max_log_dependency_count
        
        # Calculate weighted score (max 5 points)
        impact_score = 5 * ((0.7 * norm_log_dependent) + (0.3 * norm_log_dependency))
        
        return impact_score
    
    def _calculate_engagement_score(self, task: Dict[str, Any]) -> float:
        """
        Component 2: Engagement & Complexity Score (Max: 3 points)
        
        Based on subtasks (50%), comments (30%), and followers (20%).
        """
        # Log-transform counts
        log_subtask_count = math.log(1 + task["subtask_count"])
        log_comment_count = math.log(1 + task["comment_count"])
        log_follower_count = math.log(1 + task["follower_count"])
        
        # Normalize to 0-1 range
        norm_log_subtask = log_subtask_count / self.max_log_subtask_count
        norm_log_comment = log_comment_count / self.max_log_comment_count
        norm_log_follower = log_follower_count / self.max_log_follower_count
        
        # Calculate weighted score (max 3 points)
        engagement_score = 3 * ((0.5 * norm_log_subtask) + (0.3 * norm_log_comment) + (0.2 * norm_log_follower))
        
        return engagement_score
    
    def _calculate_timeliness_recency_score(self, task: Dict[str, Any]) -> float:
        """
        Component 3: Timeliness & Recency Score (Max: 2 points)
        
        Sum of urgency sub-score (due dates) and recency sub-score (activity).
        """
        urgency_score = self._calculate_urgency_subscore(task)
        recency_score = self._calculate_recency_subscore(task)
        
        return urgency_score + recency_score
    
    def _calculate_urgency_subscore(self, task: Dict[str, Any]) -> float:
        """
        Urgency Sub-Score (Max 1 point) based on due_date.
        
        - 1.0 if overdue
        - 0.5 if due within 7 days
        - 0.0 otherwise
        """
        due_date = task.get("due_date")
        if not due_date:
            return 0.0
        
        try:
            # Parse due date
            if "T" in due_date:
                # Full datetime
                due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
            else:
                # Date only - assume end of day
                due_dt = datetime.strptime(due_date, '%Y-%m-%d').replace(
                    hour=23, minute=59, second=59, tzinfo=timezone.utc
                )
            
            now = datetime.now(timezone.utc)
            days_until_due = (due_dt - now).days
            
            if days_until_due < 0:  # Overdue
                return 1.0
            elif days_until_due <= 7:  # Due within 7 days
                return 0.5
            else:
                return 0.0
                
        except (ValueError, TypeError) as e:
            logger.debug("Error parsing due date '%s' for task %s: %s", due_date, task.get("id", "unknown"), e)
            return 0.0
    
    def _calculate_recency_subscore(self, task: Dict[str, Any]) -> float:
        """
        Recency Sub-Score (Max 1 point) based on last_modified_at.
        
        Uses exponential decay function: 1 * exp(-0.02 * days_since_modified)
        """
        last_modified = task.get("last_modified_at")
        if not last_modified:
            return 0.0
        
        try:
            # Parse last modified date
            if "T" in last_modified:
                modified_dt = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
            else:
                modified_dt = datetime.strptime(last_modified, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            days_since_modified = (now - modified_dt).days
            
            # Exponential decay function
            recency_score = 1.0 * math.exp(-0.02 * days_since_modified)
            
            return recency_score
            
        except (ValueError, TypeError) as e:
            logger.debug("Error parsing modified date '%s' for task %s: %s", last_modified, task.get("id", "unknown"), e)
            return 0.0
    
    def _log_scoring_statistics(self, scored_tasks: List[Dict[str, Any]]) -> None:
        """Log statistics about the scoring results"""
        if not scored_tasks:
            return
        
        scores = [task["golden_task_score"] for task in scored_tasks]
        impact_scores = [task["impact_score"] for task in scored_tasks]
        engagement_scores = [task["engagement_score"] for task in scored_tasks]
        timeliness_scores = [task["timeliness_recency_score"] for task in scored_tasks]
        
        logger.info("📊 Golden Task Scoring Statistics:")
        logger.info("  Golden Task Scores - Min: %.3f, Max: %.3f, Avg: %.3f", 
                   min(scores), max(scores), sum(scores) / len(scores))
        logger.info("  Impact Scores - Min: %.3f, Max: %.3f, Avg: %.3f", 
                   min(impact_scores), max(impact_scores), sum(impact_scores) / len(impact_scores))
        logger.info("  Engagement Scores - Min: %.3f, Max: %.3f, Avg: %.3f", 
                   min(engagement_scores), max(engagement_scores), sum(engagement_scores) / len(engagement_scores))
        logger.info("  Timeliness Scores - Min: %.3f, Max: %.3f, Avg: %.3f", 
                   min(timeliness_scores), max(timeliness_scores), sum(timeliness_scores) / len(timeliness_scores))
        
        # Count completed vs incomplete tasks
        completed_count = sum(1 for task in scored_tasks if task["is_completed"])
        logger.info("  Completed tasks: %s/%s (%.1f%% received completion penalty)", 
                   completed_count, len(scored_tasks), (completed_count / len(scored_tasks)) * 100)
        
        # Show top 5 scoring tasks
        top_tasks = sorted(scored_tasks, key=lambda t: t["golden_task_score"], reverse=True)[:5]
        logger.info("  🏆 Top 5 Golden Tasks:")
        for i, task in enumerate(top_tasks, 1):
            logger.info("    %s. '%s' (Score: %.3f)", i, task["name"][:50], task["golden_task_score"])
