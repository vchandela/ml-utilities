"""
BigQuery Specialized Counter

This module provides functionality to count resources in Google BigQuery including:
- Total number of datasets
- Total number of logical tables (date-sharded tables counted as one)
- Total number of unique queries in a specified time period

Authentication is handled via Google Cloud service account credentials.
"""

import asyncio
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json

try:
    from google.cloud import bigquery
    from google.oauth2 import service_account
    from google.api_core import exceptions as gcp_exceptions
except ImportError:
    bigquery = None
    service_account = None
    gcp_exceptions = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress urllib3 connection pool warnings (they're noise from our concurrent API calls)
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)


def _get_base_table_name(table_name: str) -> str:
    """
    Strips common date shard suffixes from a table name to find its base name.
    Example: 'my_table_20230101' -> 'my_table'
    """
    # This regex matches _YYYYMMDD, _YYYY_MM_DD, and _YYYYMM suffixes
    pattern = r"_\d{4}(?:_?\d{2}){1,2}$"
    base_name = re.sub(pattern, "", table_name)
    return base_name


class BigQueryMetadataExtractor:
    """Main class for counting resources in BigQuery"""
    
    def __init__(self, credentials: Dict[str, Any]):
        """
        Initialize BigQuery metadata counter
        
        Args:
            credentials: Dictionary containing:
                - sa_creds_json: Service account credentials as dict
                - project_id: GCP project ID
                - client_email: Service account email
        """
        self.credentials = credentials
        self.client = None
        self.project_id = credentials.get('project_id')
        
        if not bigquery:
            raise ImportError("google-cloud-bigquery is required but not installed")
            
        self._validate_credentials()
        self._initialize_client()

    def _validate_credentials(self):
        """Validate required credentials"""
        required_fields = ['sa_creds_json', 'project_id', 'client_email']
        missing_fields = [field for field in required_fields if not self.credentials.get(field)]
        
        if missing_fields:
            raise ValueError(f"Missing required credentials: {', '.join(missing_fields)}")
            
        sa_creds = self.credentials.get('sa_creds_json')
        if not isinstance(sa_creds, dict):
            raise ValueError("sa_creds_json must be a dictionary")

    def _initialize_client(self):
        """Initialize BigQuery client with service account credentials"""
        try:
            sa_creds = self.credentials['sa_creds_json']
            credentials = service_account.Credentials.from_service_account_info(sa_creds)
            self.client = bigquery.Client(credentials=credentials, project=self.project_id)
            logger.info(f"Initialized BigQuery client for project: {self.project_id}")
        except Exception as e:
            logger.error(f"Failed to initialize BigQuery client: {e}")
            raise

    async def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to BigQuery with a lightweight query
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Simple, lightweight connection test
            query = f"SELECT 1 as test_connection"
            await asyncio.to_thread(self.client.query, query)
            message = f"Connection successful to project: {self.project_id}"
            logger.info(message)
            return True, message
        except Exception as e:
            message = f"Connection failed: {str(e)}"
            logger.error(message)
            return False, message

    async def _get_dataset_info(self, dataset_ref) -> Tuple[str, str]:
        """Get dataset ID and region for a dataset reference"""
        dataset = await asyncio.to_thread(self.client.get_dataset, dataset_ref.dataset_id)
        region = dataset.location or 'US'
        return dataset_ref.dataset_id, region

    async def _query_region_tables(self, region: str, dataset_ids: List[str]) -> List[str]:
        """Query a specific region for table names"""
        try:
            query = f"""
                SELECT table_name
                FROM `{self.project_id}.region-{region}.INFORMATION_SCHEMA.TABLES`
                WHERE table_schema IN ({','.join([f'"{ds}"' for ds in dataset_ids])})
            """
            query_job = await asyncio.to_thread(self.client.query, query)
            return [row.table_name for row in query_job]
        except Exception as region_error:
            logger.warning(f"Failed to query region {region}: {region_error}")
            return []

    async def _query_region_queries(self, region: str, start_date: datetime) -> int:
        """Query a specific region for unique query count"""
        try:
            query = f"""
            SELECT
                COUNT(DISTINCT query) as unique_query_count
            FROM `{self.project_id}.region-{region}.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
            WHERE job_type = 'QUERY'
                AND state = 'DONE'
                AND start_time >= '{start_date.isoformat()}'
            """
            query_job = await asyncio.to_thread(self.client.query, query)
            result = list(query_job)
            return result[0].unique_query_count if result else 0
        except Exception as region_error:
            logger.warning(f"Failed to query queries in region {region}: {region_error}")
            return 0

    async def _get_dataset_regions(self) -> Dict[str, List[str]]:
        """
        Discover dataset regions in parallel for optimal performance.
        
        Returns:
            Dict mapping region -> list of dataset_ids in that region
        """
        try:
            # Get all dataset references
            dataset_list = await asyncio.to_thread(list, self.client.list_datasets())
            
            # Run all dataset queries concurrently
            dataset_tasks = [self._get_dataset_info(dataset_ref) for dataset_ref in dataset_list]
            dataset_results = await asyncio.gather(*dataset_tasks)
            
            # Group datasets by region
            dataset_regions = {}
            for dataset_id, region in dataset_results:
                if region not in dataset_regions:
                    dataset_regions[region] = []
                dataset_regions[region].append(dataset_id)
            
            logger.info(f"Found datasets in regions: {dict((k, len(v)) for k, v in dataset_regions.items())}")
            return dataset_regions
            
        except Exception as e:
            logger.error(f"Error discovering dataset regions: {e}")
            return {}

    async def count_datasets(self) -> int:
        """Counts the total number of datasets in the project."""
        try:
            dataset_list = await asyncio.to_thread(list, self.client.list_datasets())
            logger.info(f"Found {len(dataset_list)} datasets.")
            return len(dataset_list)
        except Exception as e:
            logger.error(f"Error counting datasets: {e}")
            return 0

    async def count_logical_tables(self) -> int:
        """
        Counts logical tables, collapsing date-sharded tables into a single entity.
        Queries all regions concurrently for maximum performance.
        """
        dataset_regions = await self._get_dataset_regions()
        return await self._count_logical_tables_with_regions(dataset_regions)

    async def _count_logical_tables_with_regions(self, dataset_regions: Dict[str, List[str]]) -> int:
        """
        Counts logical tables using pre-discovered dataset regions.
        """
        try:
            if not dataset_regions:
                return 0
            
            # Run all region queries concurrently
            region_tasks = [self._query_region_tables(region, dataset_ids) 
                          for region, dataset_ids in dataset_regions.items()]
            region_results = await asyncio.gather(*region_tasks)
            
            # Flatten all table names from all regions
            all_table_names = []
            for region_table_names in region_results:
                all_table_names.extend(region_table_names)
            
            # Use a set to store unique base names
            logical_table_names = set()
            for name in all_table_names:
                logical_table_names.add(_get_base_table_name(name))
            
            count = len(logical_table_names)
            logger.info(f"Found {len(all_table_names)} physical tables, collapsed into {count} logical tables.")
            return count

        except Exception as e:
            logger.error(f"Error counting logical tables: {e}")
            return 0

    async def count_unique_queries(self, days_back: int) -> int:
        """
        Counts unique queries executed over a specified period.
        Automatically detects regions and queries all concurrently.
        """
        dataset_regions = await self._get_dataset_regions()
        return await self._count_unique_queries_with_regions(dataset_regions, days_back)

    async def _count_unique_queries_with_regions(self, dataset_regions: Dict[str, List[str]], days_back: int) -> int:
        """
        Counts unique queries using pre-discovered dataset regions.
        """
        try:
            regions = set(dataset_regions.keys())
            
            if not regions:
                return 0
            
            start_date = datetime.now() - timedelta(days=days_back)
            
            # Run all region queries concurrently
            query_tasks = [self._query_region_queries(region, start_date) for region in regions]
            region_counts = await asyncio.gather(*query_tasks)
            
            # Sum up counts from all regions
            total_count = sum(region_counts)
            logger.info(f"Found {total_count} unique queries in the last {days_back} days across {len(regions)} regions.")
            return total_count

        except Exception as e:
            logger.error(f"Error counting unique queries: {e}")
            return 0


async def extract_metadata(credentials: Dict[str, Any],
                         query_days_back: int) -> Dict[str, Any]:
    """
    Main function to extract BigQuery metadata counts.
    
    Args:
        credentials: BigQuery credentials dictionary.
        query_days_back: Days back to fetch query history.
        
    Returns:
        Dict[str, Any]: A dictionary with the counts of datasets, tables, and queries.
    """
    extractor = BigQueryMetadataExtractor(credentials)
    
    # Test connection first
    success, message = await extractor.test_connection()
    if not success:
        return {"error": message}
    
    # Discover dataset regions once (shared by both table and query counting)
    dataset_regions = await extractor._get_dataset_regions()
    
    # Run all counting operations concurrently, reusing region discovery
    dataset_count_task = extractor.count_datasets()
    table_count_task = extractor._count_logical_tables_with_regions(dataset_regions)
    query_count_task = extractor._count_unique_queries_with_regions(dataset_regions, query_days_back)
    
    datasets, tables, queries = await asyncio.gather(
        dataset_count_task,
        table_count_task,
        query_count_task
    )
    
    results = {
        "connection_test": {"success": True, "message": message},
        "counts": {
            "datasets": datasets,
            "logical_tables": tables,
            "unique_queries": queries
        }
    }
    
    return results


if __name__ == "__main__":
    import os
    
    # Example usage with environment variables
    credentials = {
        "sa_creds_json": json.loads(os.getenv("BIGQUERY_SA_CREDS_JSON", "{}")),
        "project_id": os.getenv("BIGQUERY_PROJECT_ID"),
        "client_email": os.getenv("BIGQUERY_CLIENT_EMAIL")
    }
    
    async def main():
        try:
            query_days_back = int(os.getenv("QUERY_DAYS_BACK", 800))
            metadata = await extract_metadata(credentials, query_days_back=query_days_back)
            print(json.dumps(metadata, indent=2, default=str))
        except Exception as e:
            print(f"Error: {e}")
    
    asyncio.run(main()) 