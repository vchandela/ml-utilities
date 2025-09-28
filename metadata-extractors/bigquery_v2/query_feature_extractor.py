#!/usr/bin/env python3
"""
Golden Query Feature Extractor (Proof of Concept)

This script implements a detailed feature extraction process for BigQuery queries
to support the "Golden Queries" ranking initiative.

**Objective of this PoC:**
To extract a rich set of features for a sample of the ~50 most frequently used
query patterns in the last 180 days. The output will be a single JSON file
that can be analyzed to refine the final query scoring logic.

**Workflow:**
1.  **Connect & Configure:** Establishes a connection to BigQuery using
    service account credentials.
2.  **Raw Job Ingestion:** Fetches the full history of query jobs from the
    last 180 days across all active regions in the project.
3.  **Candidate Identification:** Identifies the top 50 most frequent raw SQL
    queries from the job history to act as our PoC sample.
4.  **Normalization & Grouping:** For the jobs in our sample, normalizes the SQL
    text to create a canonical "query shape" and groups all executions
    of the same shape together.
5.  **Feature Extraction:** For each unique query shape, calculates a
    comprehensive set of features across several categories:
    - Execution & Usage
    - Authorship & Ownership
    - Lineage & Asset Interaction
    - Structural Complexity
6.  **Output:** Writes the final list of feature-rich query shape objects
    to a JSON file for analysis.
"""

import os
import sys
import json
import asyncio
import hashlib
import logging
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

# --- Configuration ---
# Load environment variables from .env file
load_dotenv()

# Configure logging to be informative
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GoldenQueryFeatureExtractor(BigQueryMetadataExtractor):
    """
    Extends the BigQueryMetadataExtractor to perform detailed feature extraction
    on query jobs for the Golden Query PoC.
    """

    def __init__(self, credentials: Dict[str, Any]):
        """Initialize the Golden Query Feature Extractor"""
        super().__init__(credentials)
        logger.info("Initialized GoldenQueryFeatureExtractor")

    async def _fetch_raw_jobs_for_region(self, region: str, start_date: datetime) -> List[Dict[str, Any]]:
        """
        Queries a single BigQuery region to fetch detailed job history.

        Args:
            region: The BigQuery region to query (e.g., 'US', 'EU').
            start_date: The earliest creation time for jobs to fetch.

        Returns:
            A list of dictionaries, where each dictionary represents a raw job record.
        """
        # This query is designed to fetch all necessary fields for the subsequent
        # feature extraction process.
        query = f"""
            SELECT
                query,
                user_email,
                creation_time,
                start_time,
                end_time,
                statement_type,
                referenced_tables,
                destination_table,
                job_id
            FROM
                `{self.project_id}.region-{region}.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
            WHERE
                job_type = 'QUERY'
                AND state = 'DONE'
                AND start_time >= '{start_date.isoformat()}'
        """
        try:
            query_job = await asyncio.to_thread(self.client.query, query)
            # The result of referenced_tables is a list of structs. We must unpack it.
            rows = []
            for row in query_job:
                # Handle destination_table safely
                dest_table = None
                if row.destination_table:
                    try:
                        dest_table = f"{row.destination_table['project_id']}.{row.destination_table['dataset_id']}.{row.destination_table['table_id']}"
                    except (KeyError, TypeError) as e:
                        logger.debug("Destination table parsing error: %s", e)
                        dest_table = str(row.destination_table)  # Fallback to string representation
                
                # Handle referenced_tables safely  
                ref_tables = []
                if row.referenced_tables:
                    try:
                        ref_tables = [f"{t['project_id']}.{t['dataset_id']}.{t['table_id']}" for t in row.referenced_tables]
                    except (KeyError, TypeError) as e:
                        logger.debug("Referenced tables parsing error: %s", e)
                        ref_tables = [str(t) for t in row.referenced_tables]  # Fallback
                
                rows.append({
                    "query": row.query,
                    "user_email": row.user_email,
                    "creation_time": row.creation_time,
                    "start_time": row.start_time,
                    "end_time": row.end_time,
                    "statement_type": row.statement_type,
                    "destination_table": dest_table,
                    "referenced_tables": ref_tables,
                    "job_id": row.job_id
                })

                # TODO: Remove this after testing. Stop after fetching 100 jobs
                if len(rows) >= 100:
                    break
            logger.info("Fetched %d raw job records from region: %s", len(rows), region)
            return rows
        except Exception as e:
            logger.warning("Failed to fetch raw jobs from region %s: %s", region, e)
            return []

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
        tasks = [self._fetch_raw_jobs_for_region(region, start_date) for region in regions]
        regional_results = await asyncio.gather(*tasks)

        # Step 3: Aggregate results into a single list and convert to a DataFrame.
        all_jobs = [job for result in regional_results for job in result]
        if not all_jobs:
            logger.warning("No jobs found in the specified time window.")
            return pd.DataFrame()
        
        logger.info("Phase 1 complete: Ingested a total of %d jobs.", len(all_jobs))
        return pd.DataFrame(all_jobs)


def identify_top_candidates(jobs_df: pd.DataFrame, num_candidates: int = 50) -> Tuple[set, pd.Series]:
    """
    Identifies the most frequently executed raw queries to form the PoC sample.

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

    # --- Phase 2: Identifying Top 50 Candidates ---
    top_50_queries, query_frequencies = identify_top_candidates(jobs_df, num_candidates=50)
    candidate_jobs_df = jobs_df[jobs_df['query'].isin(top_50_queries)].copy()
    if candidate_jobs_df.empty:
        logger.info("No jobs match the top candidates. Exiting.")
        return
    logger.info("Filtered down to %d jobs for deep analysis.", len(candidate_jobs_df))
    
    logger.info("✅ Phase 2 complete: Top candidates identified")
    
    # --- Phase 3: Shaping and Grouping Candidate Data ---
    logger.info("Phase 3: Normalizing SQL and grouping jobs by query shape...")
    shapes = candidate_jobs_df['query'].apply(normalize_sql_to_shape)
    candidate_jobs_df[['query_shape_id', 'normalized_sql']] = pd.DataFrame(shapes.tolist(), index=candidate_jobs_df.index)
    
    grouped_by_shape = candidate_jobs_df.groupby('query_shape_id')
    logger.info("Phase 3 complete: Found %d unique query shapes from candidates.", len(grouped_by_shape))
    
    logger.info("✅ Phase 3 complete: SQL normalization and grouping finished")

    # --- Phase 4: Detailed Feature Extraction ---
    logger.info("Phase 4: Starting detailed feature extraction for each shape...")
    final_output_list = []
    for shape_id, group_df in grouped_by_shape:
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

        if len(timestamps) > 1:
            deltas = [(timestamps[i] - timestamps[i-1]).total_seconds() for i in range(1, len(timestamps))]
            feature_dict['execution_regularity_stdev'] = stdev(deltas) if len(deltas) > 1 else 0.0
        else:
            feature_dict['execution_regularity_stdev'] = None

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
        feature_dict.update(extract_structural_features(rep_row['normalized_sql']))
        feature_dict['statement_type'] = rep_row['statement_type']
        
        final_output_list.append(feature_dict)

    logger.info("Phase 4 complete: Extracted features for %d shapes.", len(final_output_list))
    
    logger.info("✅ Phase 4 complete: Feature extraction finished")
    
    # --- Phase 5: Final Output Generation ---
    json_output_filename = 'golden_queries_poc_output.json'
    csv_output_filename = 'golden_queries_poc_output.csv'
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
        column_order = [
            'query_shape_id', 'statement_type', 'total_execution_count', 'distinct_user_count', 
            'last_execution_timestamp', 'creator_first_seen_user', 'primary_user_most_frequent_executor',
            'join_count', 'cte_count', 'window_function_count', 'aggregation_presence', 'subquery_count',
            'destination_table', 'is_temporary_write', 'source_tables', 'list_of_distinct_users', 
            'full_execution_history', 'execution_regularity_stdev', 'normalized_sql'
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

    logger.info("✅ Proof of Concept script finished successfully.")


if __name__ == "__main__":
    # Ensure you have the following in your .env file:
    # BIGQUERY_SA_CREDS_JSON='{"type": "service_account", ...}'
    # BIGQUERY_PROJECT_ID='your-gcp-project-id'
    # BIGQUERY_CLIENT_EMAIL='your-sa-email@your-project.iam.gserviceaccount.com'
    
    # To run, execute from the root directory:
    # python -m bigquery_v2.query_feature_extractor
    asyncio.run(main())
