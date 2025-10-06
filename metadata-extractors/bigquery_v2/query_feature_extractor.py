#!/usr/bin/env python3
"""
Golden Query Feature Extractor (Proof of Concept)

This script implements a detailed feature extraction process for BigQuery queries
to support the "Golden Queries" ranking initiative.

**Objective of this Analysis:**
To extract a rich set of features for ALL query patterns in the last 180 days.
The output will be JSON and CSV files that can be analyzed to refine the 
final query scoring logic.

**Workflow:**
1.  **Connect & Configure:** Establishes a connection to BigQuery using
    service account credentials.
2.  **Raw Job Ingestion:** Fetches the full history of query jobs from the
    last 180 days across all active regions in the project.
3.  **Normalization & Grouping:** For all jobs, normalizes the SQL
    text to create a canonical "query shape" and groups all executions
    of the same shape together.
4.  **Feature Extraction:** For each unique query shape, calculates a
    comprehensive set of features across several categories:
    - Execution & Usage
    - Authorship & Ownership
    - Lineage & Asset Interaction
    - Structural Complexity
5.  **Output:** Writes the final list of feature-rich query shape objects
    to JSON and CSV files for analysis.
"""

import os
import sys
import json
import asyncio
import hashlib
import logging
import time
from datetime import datetime, timezone, timedelta
from collections import Counter
from statistics import stdev
from typing import Dict, List, Any, Tuple, Optional

# Add the parent directory to the path to import from bigquery module
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Third-party libraries. Add to your requirements.txt:
# pandas>=2.0.0
# sqlglot>=18.5.1  
# google-cloud-bigquery (already in use)
import pandas as pd
import sqlglot
from sqlglot import exp
from dotenv import load_dotenv

# Import the base extractor from the existing codebase
from bigquery.metadata import BigQueryMetadataExtractor

# Import BigQuery client for query configuration and Storage API for fast downloads
from google.cloud import bigquery

try:
    from google.cloud import bigquery_storage
    STORAGE_API_AVAILABLE = True
except ImportError:
    bigquery_storage = None
    STORAGE_API_AVAILABLE = False

# --- Configuration ---
# Load environment variables from .env file
load_dotenv()

# Configure logging to be informative
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Column names for consistent DataFrame structure
JOB_COLS = [
    "user_email", "query", "creation_time", "start_time", "end_time",
    "statement_type", "referenced_tables", "destination_table", "job_id"
]


class GoldenQueryFeatureExtractor(BigQueryMetadataExtractor):
    """
    Extends the BigQueryMetadataExtractor to perform detailed feature extraction
    on query jobs for the Golden Query PoC.
    """

    def __init__(self, credentials: Dict[str, Any]):
        """Initialize the Golden Query Feature Extractor"""
        super().__init__(credentials)
        logger.info("Initialized GoldenQueryFeatureExtractor")


    async def _fetch_raw_jobs_for_region(self, region: str, start_date: datetime) -> pd.DataFrame:
        """
        Queries a single BigQuery region to fetch detailed job history.

        Args:
            region: The BigQuery region to query (e.g., 'US', 'EU').
            start_date: The earliest creation time for jobs to fetch.

        Returns:
            A pandas DataFrame containing raw job records with optimized memory usage.
        """
        # Fixed SQL with correct INFORMATION_SCHEMA path and parameterized query
        sql = """
            SELECT
          user_email, query, creation_time, start_time, end_time,
          statement_type, referenced_tables, destination_table, job_id
        FROM `region-{}`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
        WHERE project_id = @project_id
          AND job_type = 'QUERY'
                AND state = 'DONE'
          AND start_time >= @start_time
        """.format(region)

        # Use parameterized queries for security and correctness
        cfg = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("project_id", "STRING", self.project_id),
                bigquery.ScalarQueryParameter("start_time", "TIMESTAMP", start_date),
            ]
        )

        def fetch_sync():
            """Storage API sync function - runs in background thread for optimal speed and memory usage"""
            # Run query
            job = self.client.query(sql, job_config=cfg)
            
            total_processed = 0
            start_time = time.time()
            last_milestone_time = start_time
            last_logged_milestone = 0
            chunks = []
            
            if STORAGE_API_AVAILABLE:
                try:
                    # Get the RowIterator (this is where to_dataframe_iterable lives!)
                    row_iter = job.result()
                    
                    if hasattr(row_iter, 'to_dataframe_iterable'):
                        # Use Storage API for fast binary downloads via RowIterator
                        bqs = bigquery_storage.BigQueryReadClient()
                        logger.info("Starting Storage API download for region %s...", region)
                        
                        for chunk_num, df_chunk in enumerate(
                            row_iter.to_dataframe_iterable(
                                bqstorage_client=bqs,
                                max_stream_count=4  # Allow parallel streams
                            ), start=1
                        ):
                            # Ensure consistent column order
                            df_chunk = df_chunk.reindex(columns=JOB_COLS, fill_value=None)
                            chunks.append(df_chunk)
                            total_processed += len(df_chunk)
                            
                            # Log chunk info
                            logger.info("Region %s: Chunk %d - %d records (cumulative: %d)", 
                                      region, chunk_num, len(df_chunk), total_processed)
                            
                            # Log progress every 10,000 records
                            current_milestone = (total_processed // 10000) * 10000
                            if current_milestone > last_logged_milestone and current_milestone > 0:
                                current_time = time.time()
                                batch_time = current_time - last_milestone_time
                                total_elapsed = current_time - start_time
                                total_elapsed_minutes = total_elapsed / 60.0
                                logger.info("Region %s: Processed %d records via Storage API - Batch: %.1fs, Total: %.1fm", 
                                          region, current_milestone, batch_time, total_elapsed_minutes)
                                last_milestone_time = current_time
                                last_logged_milestone = current_milestone
                                
                        logger.info("Region %s: Storage API download complete - %d records across %d chunks", 
                                   region, total_processed, len(chunks))
                    else:
                        logger.info("RowIterator doesn't have to_dataframe_iterable, using fallback...")
                        chunks = []  # Trigger fallback
                        
                except Exception as e:
                    logger.warning("Storage API failed for region %s: %s, falling back to regular conversion", region, e)
                    chunks = []  # Reset chunks to trigger fallback
                    total_processed = 0
            
            # Use fallback if Storage API not available or failed
            if not chunks:
                logger.info("Using fallback DataFrame conversion for region %s...", region)
                if STORAGE_API_AVAILABLE:
                    # Use Storage API with single DataFrame (still fast)
                    bqs = bigquery_storage.BigQueryReadClient()
                    result_df = job.to_dataframe(bqstorage_client=bqs)
                else:
                    # Regular conversion without Storage API
                    result_df = job.to_dataframe()
                    
                if not result_df.empty:
                    result_df = result_df.reindex(columns=JOB_COLS, fill_value=None)
                chunks = [result_df] if not result_df.empty else []
                total_processed = len(result_df) if not result_df.empty else 0
                logger.info("Region %s: Fallback conversion complete - %d records", region, total_processed)
            
            final_time = time.time()
            total_processing_time = final_time - start_time
            total_processing_minutes = total_processing_time / 60.0
            logger.info("Region %s: Download complete - %d records - Total time: %.1fm (%.1fs)", 
                       region, total_processed, total_processing_minutes, total_processing_time)
            
            # Concatenate all chunks into single result
            if chunks:
                result_df = pd.concat(chunks, ignore_index=True) if len(chunks) > 1 else chunks[0]
                logger.info("Region %s: Final DataFrame - %d rows, %d columns", 
                          region, len(result_df), len(result_df.columns))
                return result_df
            else:
                logger.info("Region %s: No data found, returning empty DataFrame", region)
                return pd.DataFrame(columns=JOB_COLS)

        try:
            logger.info("Executing query for region %s...", region)
            # Run the entire sync operation in a background thread
            df = await asyncio.to_thread(fetch_sync)
            logger.info("Successfully fetched %d raw job records from region: %s", len(df), region)
            return df
        except Exception as e:
            logger.warning("Failed to fetch raw jobs from region %s: %s", region, e)
            # Return empty DataFrame with consistent columns
            return pd.DataFrame(columns=JOB_COLS)

    async def get_raw_job_history(self, days_back: int = 180) -> pd.DataFrame:
        """
        Fetches the complete query job history across all project regions concurrently.

        Args:
            days_back: The number of days of history to retrieve.

        Returns:
            A pandas DataFrame containing the aggregated job history from all regions.
        """
        logger.info("Phase 1: Starting raw job history ingestion...")
        # Step 1: Discover all active regions to ensure comprehensive data collection.
        dataset_regions = await self._get_dataset_regions()
        if not dataset_regions:
            logger.error("No dataset regions found. Cannot fetch job history.")
            return pd.DataFrame()

        regions = list(dataset_regions.keys())
        start_date = datetime.now() - timedelta(days=days_back)

        # Step 2: Concurrently fetch job history from all discovered regions.
        # This dramatically speeds up the data collection process.
        logger.info("Fetching jobs from %d regions concurrently...", len(regions))
        tasks = [self._fetch_raw_jobs_for_region(region, start_date) for region in regions]
        regional_results = await asyncio.gather(*tasks)

        # Step 3: Log results and concatenate non-empty DataFrames
        for region_name, df in zip(regions, regional_results):
            logger.info("Region %s: Fetched %d jobs", region_name, len(df))

        non_empty = [df for df in regional_results if not df.empty]
        if not non_empty:
            logger.warning("No jobs found in the specified time window.")
            return pd.DataFrame(columns=JOB_COLS)

        # Single efficient concat operation 
        jobs_df = pd.concat(non_empty, ignore_index=True)
        logger.info("Phase 1 complete: Ingested a total of %d jobs from %d regions.", len(jobs_df), len(regions))
        return jobs_df


def identify_top_candidates(jobs_df: pd.DataFrame, num_candidates: int = 50000) -> Tuple[set, pd.Series]:
    """
    Identifies the most frequently executed raw queries to form the analysis sample.

    Reasoning:
    Before performing expensive parsing on all jobs, we create a high-value sample
    based on raw execution frequency. This is a fast and effective heuristic for
    finding potentially important queries.

    Args:
        jobs_df: DataFrame of all raw jobs.
        num_candidates: The number of top queries to select.

    Returns:
        A tuple containing:
        - set: Raw SQL strings of the top candidates
        - pd.Series: Frequency counts for all queries (query -> count)
    """
    logger.info("Phase 2: Identifying top %d query candidates by frequency...", num_candidates)
    if 'query' not in jobs_df.columns or jobs_df.empty:
        logger.warning("No query data available for candidate identification")
        return set(), pd.Series(dtype=int)
    
    frequency_series = jobs_df['query'].value_counts()
    top_queries = frequency_series.nlargest(num_candidates).index.tolist()
    
    logger.info("Phase 2 complete: Identified %d candidate queries.", len(top_queries))
    logger.info("Top 5 most frequent queries:")
    for i, (query, count) in enumerate(frequency_series.head(5).items()):
        logger.info("  %d. [%d executions] %s", i+1, count, query[:100] + "..." if len(query) > 100 else query)
    
    return set(top_queries), frequency_series


def normalize_sql_to_shape(sql: str) -> Tuple[str, str]:
    """
    Normalizes a raw SQL query into a canonical "shape" and generates a unique ID.

    Reasoning:
    This process ensures that queries that are logically identical but have different
    formatting, comments, or literal values (e.g., different dates) are grouped
    together for accurate analysis of their usage patterns.

    Args:
        sql: The raw SQL string.

    Returns:
        A tuple containing (Query Shape ID, Normalized SQL String).
    """
    try:
        # Use sqlglot to parse and then regenerate the SQL in a standard format.
        # This handles differences in casing, whitespace, and comments.
        # We also anonymize literals to group queries by structure, not by value.
        parsed = sqlglot.parse_one(sql, read='bigquery')
        
        # Replace all literal values with placeholders
        for literal in parsed.find_all(exp.Literal):
            literal.replace(exp.Identifier(this="?"))

        normalized_sql = parsed.sql(dialect="bigquery", pretty=True)
        
        # Create a stable SHA256 hash of the normalized SQL to serve as the unique ID.
        shape_id = hashlib.sha256(normalized_sql.encode('utf-8')).hexdigest()
        return shape_id, normalized_sql
    except Exception as e:
        # If parsing fails, use the raw query and its hash as a fallback.
        logger.warning("Failed to parse SQL for normalization, using raw query: %s", str(e)[:100])
        return hashlib.sha256(sql.encode('utf-8')).hexdigest(), sql


def extract_structural_features(normalized_sql: str) -> Dict[str, Any]:
    """
    Parses the normalized SQL to extract features related to its complexity.

    Reasoning:
    A query's structure is a proxy for the complexity and value of the analytical
    question it answers. Complex queries often represent critical, codified business logic.

    Args:
        normalized_sql: The canonical SQL string for the query shape.

    Returns:
        A dictionary of structural complexity metrics.
    """
    try:
        parsed = sqlglot.parse_one(normalized_sql, read='bigquery')
        return {
            "join_count": len(list(parsed.find_all(exp.Join))),
            "cte_count": len(list(parsed.find_all(exp.CTE))),
            "window_function_count": len(list(parsed.find_all(exp.Window))),
            "aggregation_presence": bool(parsed.find(exp.Group)),
            # Count subqueries by finding all SELECTs and subtracting the main one.
            "subquery_count": max(0, len(list(parsed.find_all(exp.Select))) - 1)
        }
    except Exception as e:
        logger.warning("Could not parse SQL for structural features: %s", str(e)[:100])
        return {
            "join_count": 0, "cte_count": 0, "window_function_count": 0,
            "aggregation_presence": False, "subquery_count": 0
        }


def is_temporary_write(destination_table: Optional[str]) -> bool:
    """
    Determines if a destination table is likely temporary based on naming conventions.

    Args:
        destination_table: The full ID of the destination table.

    Returns:
        True if the table appears to be temporary, False otherwise.
    """
    if not destination_table:
        return False
    
    # Common patterns for temporary/scratch datasets and tables.
    temp_patterns = ['_temp_', '_tmp_', 'scratch', 'temp_']
    table_id = destination_table.lower()
    
    return any(pattern in table_id for pattern in temp_patterns)


def calculate_hours_since_last_run(last_execution_timestamp: str) -> Optional[float]:
    """
    Calculate the number of hours since the last execution.
    
    Args:
        last_execution_timestamp: ISO timestamp string of the last execution
    
    Returns:
        Number of hours since last run, or None if parsing fails
    """
    try:
        last_run = datetime.fromisoformat(last_execution_timestamp.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        return (now - last_run).total_seconds() / 3600  # Convert to hours
    except Exception:
        return None


def calculate_regularity_hours(execution_regularity_stdev) -> str:
    """
    Convert execution regularity from seconds to hours.
    For single executions, returns "SINGLE_EXECUTION".
    
    Args:
        execution_regularity_stdev: Standard deviation of execution intervals in seconds, or "SINGLE_EXECUTION"
    
    Returns:
        Standard deviation in hours as string, or "SINGLE_EXECUTION" if input indicates single execution
    """
    if execution_regularity_stdev == "SINGLE_EXECUTION":
        return "SINGLE_EXECUTION"
    try:
        hours = execution_regularity_stdev / 3600  # Convert seconds to hours
        return f"{hours:.2f}"  # Return as formatted string
    except Exception:
        return "SINGLE_EXECUTION"


def calculate_raw_complexity_score(join_count: int, cte_count: int, window_function_count: int, 
                                 subquery_count: int, aggregation_presence: bool) -> int:
    """
    Calculate the raw complexity score based on SQL structural features.
    
    Args:
        join_count: Number of joins
        cte_count: Number of CTEs
        window_function_count: Number of window functions
        subquery_count: Number of subqueries
        aggregation_presence: Whether aggregation is present
    
    Returns:
        Raw complexity score (integer)
    """
    try:
        score = (join_count + 
                2 * cte_count + 
                3 * window_function_count + 
                subquery_count + 
                (1 if aggregation_presence else 0))
        return score
    except Exception:
        return 0


def normalize_complexity_scores(raw_scores: List[int]) -> List[float]:
    """
    Normalize complexity scores to [0,1] range using the actual maximum from the data.
    
    Args:
        raw_scores: List of raw complexity scores
    
    Returns:
        List of normalized complexity scores between 0.0 and 1.0
    """
    if not raw_scores:
        return []
    
    max_score = max(raw_scores)
    if max_score == 0:
        return [0.0] * len(raw_scores)
    
    return [score / max_score for score in raw_scores]


def calculate_source_table_count(source_tables: List[str]) -> int:
    """
    Count the number of source tables.
    
    Args:
        source_tables: List of source table identifiers
    
    Returns:
        Number of source tables
    """
    try:
        if not source_tables:
            return 0
        return len(source_tables)
    except Exception:
        return 0


def is_service_account(user_email: str) -> bool:
    """
    Determine if a user email is a service account.
    
    Args:
        user_email: Email address of the user
    
    Returns:
        True if the email appears to be a service account, False otherwise
    """
    try:
        import re
        return bool(re.search(r'\.iam\.gserviceaccount\.com$', user_email, re.IGNORECASE))
    except Exception:
        return False


def has_persistent_destination(destination_table: Optional[str], is_temp_write: bool) -> bool:
    """
    Determine if the query has a persistent destination table.
    
    Args:
        destination_table: The destination table identifier
        is_temp_write: Whether the write is temporary
    
    Returns:
        True if has persistent destination, False otherwise
    """
    try:
        return bool(destination_table) and not is_temp_write
    except Exception:
        return False


def is_dml_statement(statement_type: str) -> bool:
    """
    Determine if the statement is a DML (Data Manipulation Language) operation.
    
    Args:
        statement_type: The type of SQL statement
    
    Returns:
        True if the statement is DML, False otherwise
    """
    try:
        import re
        dml_patterns = r'(?i)INSERT|MERGE|UPDATE|DELETE|CREATE_TABLE_AS_SELECT'
        return bool(re.search(dml_patterns, statement_type))
    except Exception:
        return False


async def main():
    """
    Main orchestration function for the Golden Query Feature Extraction PoC.
    """
    # --- Phase 0: Setup and Connection ---
    sa_creds_json = os.getenv('BIGQUERY_SA_CREDS_JSON')
    project_id = os.getenv('BIGQUERY_PROJECT_ID')
    client_email = os.getenv('BIGQUERY_CLIENT_EMAIL')

    if not all([sa_creds_json, project_id]):
        logger.error("Missing required environment variables: BIGQUERY_SA_CREDS_JSON and BIGQUERY_PROJECT_ID")
        return

    try:
        credentials = {
            'sa_creds_json': json.loads(sa_creds_json),
            'project_id': project_id,
            'client_email': client_email or "N/A"
        }
        extractor = GoldenQueryFeatureExtractor(credentials)
        success, msg = await extractor.test_connection()
        if not success:
            logger.error("BigQuery connection failed: %s", msg)
            return
        
        logger.info("✅ Phase 0 complete: Setup and connection established")
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Credential loading failed: %s", e)
        return

    # --- Phase 1: Raw Job History Ingestion ---
    jobs_df = await extractor.get_raw_job_history(days_back=180)
    if jobs_df.empty:
        logger.info("No jobs found. Exiting.")
        return
    
    logger.info("✅ Phase 1 complete: Raw job history ingestion finished")
    logger.info("Total jobs ingested from all regions: %d", len(jobs_df))

    # --- Phase 2: Process All Queries (No Filtering) ---
    # top_50k_queries, _ = identify_top_candidates(jobs_df, num_candidates=50000)
    # candidate_jobs_df = jobs_df[jobs_df['query'].isin(top_50k_queries)].copy()
    # Use all jobs instead of filtering to top candidates
    candidate_jobs_df = jobs_df.copy()
    if candidate_jobs_df.empty:
        logger.info("No jobs found for analysis. Exiting.")
        return
    logger.info("Processing all %d jobs for comprehensive analysis.", len(candidate_jobs_df))
    
    logger.info("✅ Phase 2 complete: Using all queries (no filtering)")
    
    # --- Phase 3: Normalization & Grouping ---
    total_queries = len(candidate_jobs_df)
    logger.info("Phase 3: Normalizing SQL and grouping jobs by query shape...")
    logger.info("Total queries to process: %d", total_queries)
    
    # Process normalization with progress logging
    shapes_list = []
    unique_shapes = set()
    
    for idx, (_, row) in enumerate(candidate_jobs_df.iterrows(), 1):
        shape_id, normalized_sql = normalize_sql_to_shape(row['query'])
        shapes_list.append((shape_id, normalized_sql))
        unique_shapes.add(shape_id)
        
        # Log progress every 50 queries
        if idx % 50 == 0 or idx == total_queries:
            logger.info("Processed %d/%d queries (%.1f%%) - Found %d unique shapes so far", 
                       idx, total_queries, (idx/total_queries)*100, len(unique_shapes))
    
    # Add the normalized data to the dataframe
    candidate_jobs_df[['query_shape_id', 'normalized_sql']] = pd.DataFrame(shapes_list, index=candidate_jobs_df.index)
    
    grouped_by_shape = candidate_jobs_df.groupby('query_shape_id')
    logger.info("Phase 3 complete: Found %d unique query shapes from %d total queries.", len(grouped_by_shape), total_queries)
    
    logger.info("✅ Phase 3 complete: SQL normalization and grouping finished")

    # --- Phase 4: Detailed Feature Extraction ---
    total_shapes = len(grouped_by_shape)
    logger.info("Phase 4: Starting detailed feature extraction for %d unique shapes...", total_shapes)
    
    # First pass: Calculate raw complexity scores for normalization and execution data
    logger.info("Phase 4a: Calculating raw complexity scores for normalization...")
    raw_complexity_scores = []
    shape_structural_features = {}
    shape_execution_data = {}
    
    for shape_idx, (shape_id, group_df) in enumerate(grouped_by_shape, 1):
        rep_row = group_df.iloc[0]
        structural_features = extract_structural_features(rep_row['normalized_sql'])
        shape_structural_features[shape_id] = structural_features
        
        # Calculate raw complexity score
        raw_score = calculate_raw_complexity_score(
            structural_features.get('join_count', 0),
            structural_features.get('cte_count', 0),
            structural_features.get('window_function_count', 0),
            structural_features.get('subquery_count', 0),
            structural_features.get('aggregation_presence', False)
        )
        raw_complexity_scores.append(raw_score)
        
        # Calculate execution statistics for this shape
        timestamps = sorted(group_df['creation_time'].tolist())
        if len(timestamps) > 1:
            deltas = [(timestamps[i] - timestamps[i-1]).total_seconds() for i in range(1, len(timestamps))]
            execution_regularity_stdev = stdev(deltas) if len(deltas) > 1 else 0.0
        else:
            execution_regularity_stdev = "SINGLE_EXECUTION"  # More readable than None
            
        shape_execution_data[shape_id] = execution_regularity_stdev
        
        # Log progress every 50 shapes
        if shape_idx % 50 == 0 or shape_idx == total_shapes:
            logger.info("Phase 4a: Processed %d/%d shapes (%.1f%%) - complexity scores calculated", 
                       shape_idx, total_shapes, (shape_idx/total_shapes)*100)
    
    # Normalize complexity scores using actual maximum
    normalized_scores = normalize_complexity_scores(raw_complexity_scores)
    logger.info("Phase 4a complete: Normalized complexity scores using max value of %d", 
                max(raw_complexity_scores) if raw_complexity_scores else 0)
    
    # Second pass: Build final feature dictionaries
    logger.info("Phase 4b: Building final feature dictionaries for %d shapes...", total_shapes)
    final_output_list = []
    score_index = 0
    
    for shape_idx, (shape_id, group_df) in enumerate(grouped_by_shape, 1):
        # Get a representative row for shape-level data
        rep_row = group_df.iloc[0]
        
        feature_dict = {
            "query_shape_id": shape_id,
            "normalized_sql": rep_row['normalized_sql'],
        }

        # Execution & Usage Features
        timestamps = sorted(group_df['creation_time'].tolist())
        user_emails = group_df['user_email'].tolist()
        
        feature_dict['total_execution_count'] = len(timestamps)
        feature_dict['list_of_distinct_users'] = list(set(user_emails))
        feature_dict['distinct_user_count'] = len(feature_dict['list_of_distinct_users'])
        feature_dict['full_execution_history'] = [ts.isoformat() for ts in timestamps]
        feature_dict['last_execution_timestamp'] = timestamps[-1].isoformat()
        
        # Use pre-calculated execution regularity data
        feature_dict['execution_regularity_stdev'] = shape_execution_data[shape_id]

        # Authorship & Ownership Features
        feature_dict['creator_first_seen_user'] = group_df.loc[group_df['creation_time'].idxmin()]['user_email']
        feature_dict['primary_user_most_frequent_executor'] = Counter(user_emails).most_common(1)[0][0]

        # Lineage & Asset Interaction Features
        feature_dict['source_tables'] = list(set(t for sublist in group_df['referenced_tables'] for t in sublist))
        
        # Check if destination table is consistent
        dest_tables = group_df['destination_table'].dropna().unique()
        dest_table = dest_tables[0] if len(dest_tables) == 1 else None
        
        feature_dict['destination_table'] = dest_table
        feature_dict['is_temporary_write'] = is_temporary_write(dest_table)
        
        # Placeholders for scores that will be calculated in a later, full-scale implementation
        feature_dict['source_asset_golden_scores'] = None
        feature_dict['destination_asset_golden_score'] = None
        
        # Structural Complexity Features
        feature_dict.update(shape_structural_features[shape_id])
        feature_dict['statement_type'] = rep_row['statement_type']
        
        # Additional Calculated Columns (T-Z equivalent)
        # T: HoursSinceLastRun
        feature_dict['hours_since_last_run'] = calculate_hours_since_last_run(feature_dict['last_execution_timestamp'])
        
        # U: RegularityHours (single executions get "SINGLE_EXECUTION" string)
        feature_dict['regularity_hours'] = calculate_regularity_hours(feature_dict['execution_regularity_stdev'])
        
        # V: ComplexityScore (normalized using actual data maximum)
        feature_dict['complexity_score'] = normalized_scores[score_index]
        
        # W: SourceTableCount
        feature_dict['source_table_count'] = calculate_source_table_count(feature_dict['source_tables'])
        
        # X: IsServiceAccount
        feature_dict['is_service_account'] = is_service_account(feature_dict['primary_user_most_frequent_executor'])
        
        # Y: HasPersistentDestination
        feature_dict['has_persistent_destination'] = has_persistent_destination(
            feature_dict['destination_table'], 
            feature_dict['is_temporary_write']
        )
        
        # Z: IsDML
        feature_dict['is_dml'] = is_dml_statement(feature_dict['statement_type'])
        
        final_output_list.append(feature_dict)
        score_index += 1
        
        # Log progress every 50 shapes
        if shape_idx % 50 == 0 or shape_idx == total_shapes:
            logger.info("Phase 4b: Built features for %d/%d shapes (%.1f%%) - %d complete", 
                       shape_idx, total_shapes, (shape_idx/total_shapes)*100, len(final_output_list))

    logger.info("Phase 4 complete: Extracted features for %d shapes.", len(final_output_list))
    
    logger.info("✅ Phase 4 complete: Feature extraction finished")
    
    # --- Phase 5: Final Output Generation ---
    json_output_filename = 'bq_golden_queries_output.json'
    csv_output_filename = 'bq_golden_queries_output.csv'
    logger.info("Phase 5: Writing output to %s and %s...", json_output_filename, csv_output_filename)

    if final_output_list:
        # Output to JSON
        with open(json_output_filename, 'w') as f:
            json.dump(final_output_list, f, indent=2)
        logger.info("JSON output written to %s", json_output_filename)

        # Output to CSV
        # Convert the list of dictionaries to a pandas DataFrame for easy CSV export.
        output_df = pd.DataFrame(final_output_list)
        
        # Define a logical column order to make the CSV easier to analyze (from plan2.txt).
        # Original columns (A-S) plus new calculated columns (T-Z)
        column_order = [
            # Original columns A-S
            'query_shape_id', 'statement_type', 'total_execution_count', 'distinct_user_count', 
            'last_execution_timestamp', 'creator_first_seen_user', 'primary_user_most_frequent_executor',
            'join_count', 'cte_count', 'window_function_count', 'aggregation_presence', 'subquery_count',
            'destination_table', 'is_temporary_write', 'source_tables', 'list_of_distinct_users', 
            'full_execution_history', 'execution_regularity_stdev', 'normalized_sql',
            # New calculated columns T-Z
            'hours_since_last_run',       # T: HoursSinceLastRun
            'regularity_hours',           # U: RegularityHours  
            'complexity_score',           # V: ComplexityScore
            'source_table_count',         # W: SourceTableCount
            'is_service_account',         # X: IsServiceAccount
            'has_persistent_destination', # Y: HasPersistentDestination
            'is_dml'                      # Z: IsDML
        ]
        
        # Filter to only include columns that were actually generated, maintaining order.
        existing_columns = [col for col in column_order if col in output_df.columns]
        output_df = output_df[existing_columns]

        # Save to CSV. quoting=1 ensures that fields containing special characters
        # (like commas or newlines in the SQL) are properly quoted.
        output_df.to_csv(csv_output_filename, index=False, quoting=1) # quoting=1 is csv.QUOTE_ALL
        logger.info("CSV output written to %s", csv_output_filename)
    else:
        # Create empty files if there's no data to prevent errors.
        with open(json_output_filename, 'w') as f:
            json.dump([], f)
        with open(csv_output_filename, 'w') as f:
            f.write('')
        logger.info("No query shapes were processed, empty output files have been created.")

    # Final analysis summary
    if final_output_list:
        logger.info("📊 ANALYSIS SUMMARY:")
        logger.info("  • Total jobs processed: %d", len(jobs_df))
        logger.info("  • Unique query shapes found: %d", len(final_output_list))
        logger.info("  • Output files: %s, %s", json_output_filename, csv_output_filename)
        logger.info("  • Analysis coverage: %.1f%% reduction (from %d jobs to %d shapes)", 
                   (1 - len(final_output_list)/len(jobs_df)) * 100, len(jobs_df), len(final_output_list))

    logger.info("✅ Golden Query analysis finished successfully.")


if __name__ == "__main__":
    # Ensure you have the following in your .env file:
    # BIGQUERY_SA_CREDS_JSON='{"type": "service_account", ...}'
    # BIGQUERY_PROJECT_ID='your-gcp-project-id'
    # BIGQUERY_CLIENT_EMAIL='your-sa-email@your-project.iam.gserviceaccount.com'
    
    # To run, execute from the root directory:
    # python -m bigquery_v2.query_feature_extractor
    asyncio.run(main())