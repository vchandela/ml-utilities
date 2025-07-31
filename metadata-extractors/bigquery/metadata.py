"""
BigQuery Metadata Extractor

This module provides functionality to extract metadata from Google BigQuery including:
- Dataset/Project information 
- Table metadata (schema, size, partitioning, etc.)
- Query history and statistics

Authentication is handled via Google Cloud service account credentials.
"""

import asyncio
import logging
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


class BigQueryDatasetMetadata:
    """Represents BigQuery dataset metadata"""
    
    def __init__(self, dataset_id: str, description: str = None, owner: str = None, 
                 created_at: datetime = None, default_table_expiration: int = None,
                 labels: Dict[str, str] = None, table_count: int = 0):
        self.dataset_id = dataset_id
        self.description = description
        self.owner = owner
        self.created_at = created_at
        self.default_table_expiration = default_table_expiration
        self.labels = labels or {}
        self.table_count = table_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "description": self.description,
            "owner": self.owner,
            "created_at": self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') and self.created_at else str(self.created_at) if self.created_at else None,
            "default_table_expiration": self.default_table_expiration,
            "labels": self.labels,
            "table_count": self.table_count
        }


class TableMetadata:
    """Represents BigQuery table metadata"""
    
    def __init__(self, table_name: str, dataset_name: str, project_id: str,
                 description: str = None, owner: str = None, created_at: datetime = None,
                 modified_at: datetime = None, row_count: int = None, size_bytes: int = None,
                 partition_info: Dict = None, clustering_keys: List[str] = None,
                 columns: List[Dict] = None):
        self.table_name = table_name
        self.dataset_name = dataset_name
        self.project_id = project_id
        self.description = description
        self.owner = owner
        self.created_at = created_at
        self.modified_at = modified_at
        self.row_count = row_count
        self.size_bytes = size_bytes
        self.partition_info = partition_info or {}
        self.clustering_keys = clustering_keys or []
        self.columns = columns or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "dataset_name": self.dataset_name,
            "project_id": self.project_id,
            "description": self.description,
            "owner": self.owner,
            "created_at": self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') and self.created_at else str(self.created_at) if self.created_at else None,
            "modified_at": self.modified_at.isoformat() if hasattr(self.modified_at, 'isoformat') and self.modified_at else str(self.modified_at) if self.modified_at else None,
            "row_count": self.row_count,
            "size_bytes": self.size_bytes,
            "partition_info": self.partition_info,
            "clustering_keys": self.clustering_keys,
            "columns": self.columns
        }


class QueryMetadata:
    """Represents BigQuery query metadata"""
    
    def __init__(self, query_id: str, query_text: str, user_email: str,
                 start_time: datetime, end_time: datetime = None, duration_ms: int = None,
                 bytes_scanned: int = None, cached: bool = False, status: str = None,
                 referenced_tables: List[str] = None, importance_score: float = 0.0):
        self.query_id = query_id
        self.query_text = query_text
        self.user_email = user_email
        self.start_time = start_time
        self.end_time = end_time
        self.duration_ms = duration_ms
        self.bytes_scanned = bytes_scanned
        self.cached = cached
        self.status = status
        self.referenced_tables = referenced_tables or []
        self.importance_score = importance_score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "query_text": self.query_text,
            "user_email": self.user_email,
            "start_time": self.start_time.isoformat() if hasattr(self.start_time, 'isoformat') and self.start_time else str(self.start_time) if self.start_time else None,
            "end_time": self.end_time.isoformat() if hasattr(self.end_time, 'isoformat') and self.end_time else str(self.end_time) if self.end_time else None,
            "duration_ms": self.duration_ms,
            "bytes_scanned": self.bytes_scanned,
            "cached": self.cached,
            "status": self.status,
            "referenced_tables": self.referenced_tables,
            "importance_score": self.importance_score
        }


class BigQueryMetadataExtractor:
    """Main class for extracting metadata from BigQuery"""
    
    def __init__(self, credentials: Dict[str, Any]):
        """
        Initialize BigQuery metadata extractor
        
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
        Test connection to BigQuery
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Test by listing datasets
            datasets = await asyncio.to_thread(list, self.client.list_datasets())
            dataset_count = len(datasets)
            message = f"Connection successful. Found {dataset_count} datasets."
            logger.info(message)
            return True, message
        except Exception as e:
            message = f"Connection failed: {str(e)}"
            logger.error(message)
            return False, message

    async def get_dataset_metadata(self) -> List[BigQueryDatasetMetadata]:
        """
        Fetch metadata for all datasets in the project
        
        Returns:
            List[BigQueryDatasetMetadata]: List of dataset metadata objects
        """
        try:
            datasets = []
            dataset_list = await asyncio.to_thread(list, self.client.list_datasets())
            
            for dataset_ref in dataset_list:
                dataset = await asyncio.to_thread(self.client.get_dataset, dataset_ref.dataset_id)
                
                # Count tables in dataset
                table_count = await self._count_tables_in_dataset(dataset.dataset_id)
                
                dataset_metadata = BigQueryDatasetMetadata(
                    dataset_id=dataset.dataset_id,
                    description=dataset.description,
                    owner=None,  # BigQuery doesn't provide owner info directly
                    created_at=dataset.created,
                    default_table_expiration=dataset.default_table_expiration_ms,
                    labels=dict(dataset.labels) if dataset.labels else {},
                    table_count=table_count
                )
                datasets.append(dataset_metadata)
                
            logger.info(f"Retrieved metadata for {len(datasets)} datasets")
            return datasets
            
        except Exception as e:
            logger.error(f"Error fetching dataset metadata: {e}")
            return []

    async def _count_tables_in_dataset(self, dataset_id: str) -> int:
        """Count tables in a specific dataset"""
        try:
            query = f"""
            SELECT COUNT(*) as table_count
            FROM `{self.project_id}.{dataset_id}.INFORMATION_SCHEMA.TABLES`
            """
            result = await asyncio.to_thread(self.client.query, query)
            for row in result:
                return row.table_count
            return 0
        except Exception as e:
            logger.warning(f"Could not count tables in dataset {dataset_id}: {e}")
            return 0

    async def get_table_metadata(self, dataset_id: str = None) -> List[TableMetadata]:
        """
        Fetch metadata for tables in specified dataset or all datasets
        
        Args:
            dataset_id: Optional specific dataset ID to process
            
        Returns:
            List[TableMetadata]: List of table metadata objects
        """
        try:
            tables = []
            
            if dataset_id:
                dataset_ids = [dataset_id]
            else:
                dataset_list = await asyncio.to_thread(list, self.client.list_datasets())
                dataset_ids = [d.dataset_id for d in dataset_list]
            
            for ds_id in dataset_ids:
                dataset_tables = await self._get_tables_in_dataset(ds_id)
                tables.extend(dataset_tables)
                
            logger.info(f"Retrieved metadata for {len(tables)} tables")
            return tables
            
        except Exception as e:
            logger.error(f"Error fetching table metadata: {e}")
            return []

    async def _get_tables_in_dataset(self, dataset_id: str) -> List[TableMetadata]:
        """Get all tables in a specific dataset"""
        try:
            tables = []
            table_list = await asyncio.to_thread(list, self.client.list_tables(dataset_id))
            
            for table_ref in table_list:
                table = await asyncio.to_thread(self.client.get_table, table_ref)
                
                # Get column information
                columns = []
                for field in table.schema:
                    columns.append({
                        "name": field.name,
                        "type": field.field_type,
                        "mode": field.mode,
                        "description": field.description
                    })
                
                # Get partition and clustering info
                partition_info = {}
                if table.time_partitioning:
                    partition_info = {
                        "type": table.time_partitioning.type_,
                        "field": table.time_partitioning.field,
                        "expiration_ms": table.time_partitioning.expiration_ms
                    }
                
                clustering_keys = []
                if table.clustering_fields:
                    clustering_keys = list(table.clustering_fields)
                
                table_metadata = TableMetadata(
                    table_name=table.table_id,
                    dataset_name=table.dataset_id,
                    project_id=table.project,
                    description=table.description,
                    owner=None,  # Not directly available
                    created_at=table.created,
                    modified_at=table.modified,
                    row_count=table.num_rows,
                    size_bytes=table.num_bytes,
                    partition_info=partition_info,
                    clustering_keys=clustering_keys,
                    columns=columns
                )
                tables.append(table_metadata)
                
            return tables
            
        except Exception as e:
            logger.error(f"Error fetching tables in dataset {dataset_id}: {e}")
            return []

    async def get_query_history(self, days_back: int = 7) -> List[QueryMetadata]:
        """
        Fetch query history from BigQuery
        
        Args:
            days_back: Number of days to look back for query history
            
        Returns:
            List[QueryMetadata]: List of query metadata objects
        """
        try:
            start_date = datetime.now() - timedelta(days=days_back)
            
            query = f"""
            SELECT 
                job_id,
                query,
                user_email,
                start_time,
                end_time,
                total_slot_ms,
                total_bytes_processed,
                cache_hit,
                state,
                referenced_tables
            FROM `{self.project_id}.region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
            WHERE job_type = 'QUERY'
                AND state = 'DONE'
                AND start_time >= '{start_date.isoformat()}'
            ORDER BY start_time DESC
            LIMIT 1000
            """
            
            result = await asyncio.to_thread(self.client.query, query)
            queries = []
            
            for row in result:
                # Calculate importance score based on query complexity
                importance_score = self._calculate_importance_score(row.query, row.referenced_tables)
                
                query_metadata = QueryMetadata(
                    query_id=row.job_id,
                    query_text=row.query,
                    user_email=row.user_email,
                    start_time=row.start_time,
                    end_time=row.end_time,
                    duration_ms=row.total_slot_ms,
                    bytes_scanned=row.total_bytes_processed,
                    cached=row.cache_hit,
                    status=row.state,
                    referenced_tables=row.referenced_tables or [],
                    importance_score=importance_score
                )
                queries.append(query_metadata)
                
            logger.info(f"Retrieved {len(queries)} queries from the last {days_back} days")
            return queries
            
        except Exception as e:
            logger.error(f"Error fetching query history: {e}")
            return []

    def _calculate_importance_score(self, query_text: str, referenced_tables: List[str]) -> float:
        """Calculate importance score based on query complexity"""
        if not query_text:
            return 0.0
            
        score = 0.0
        query_lower = query_text.lower()
        
        # Score based on query complexity indicators
        if 'join' in query_lower:
            score += 2.0
        if 'with' in query_lower:  # CTEs
            score += 1.5
        if any(agg in query_lower for agg in ['sum', 'count', 'avg', 'max', 'min']):
            score += 1.0
        if 'group by' in query_lower:
            score += 1.0
        if 'window' in query_lower or 'over' in query_lower:
            score += 1.5
        
        # Score based on number of referenced tables
        if referenced_tables:
            score += len(referenced_tables) * 0.5
            
        return min(score, 10.0)  # Cap at 10.0

    async def get_document_counts_by_subtype(self) -> Dict[str, int]:
        """
        Get document counts by subtype (datasets, tables, views, etc.)
        
        Returns:
            Dict[str, int]: Counts by document subtype
        """
        try:
            counts = {
                "datasets": 0,
                "tables": 0,
                "views": 0,
                "external_tables": 0,
                "materialized_views": 0
            }
            
            dataset_list = await asyncio.to_thread(list, self.client.list_datasets())
            counts["datasets"] = len(dataset_list)
            
            for dataset_ref in dataset_list:
                tables = await asyncio.to_thread(list, self.client.list_tables(dataset_ref.dataset_id))
                
                for table_ref in tables:
                    table = await asyncio.to_thread(self.client.get_table, table_ref)
                    
                    if table.table_type == "TABLE":
                        counts["tables"] += 1
                    elif table.table_type == "VIEW":
                        counts["views"] += 1
                    elif table.table_type == "EXTERNAL":
                        counts["external_tables"] += 1
                    elif table.table_type == "MATERIALIZED_VIEW":
                        counts["materialized_views"] += 1
            
            logger.info(f"Document counts: {counts}")
            return counts
            
        except Exception as e:
            logger.error(f"Error getting document counts: {e}")
            return {}


async def extract_metadata(credentials: Dict[str, Any], 
                         include_datasets: bool = True,
                         include_tables: bool = True, 
                         include_queries: bool = True,
                         query_days_back: int = 7) -> Dict[str, Any]:
    """
    Main function to extract BigQuery metadata
    
    Args:
        credentials: BigQuery credentials dictionary
        include_datasets: Whether to include dataset metadata
        include_tables: Whether to include table metadata  
        include_queries: Whether to include query history
        query_days_back: Days back to fetch query history
        
    Returns:
        Dict[str, Any]: Complete metadata extraction results
    """
    extractor = BigQueryMetadataExtractor(credentials)
    
    # Test connection first
    success, message = await extractor.test_connection()
    if not success:
        return {"error": message}
    
    results = {
        "connection_test": {"success": True, "message": message},
        "document_counts": await extractor.get_document_counts_by_subtype()
    }
    
    if include_datasets:
        datasets = await extractor.get_dataset_metadata()
        results["datasets"] = [d.to_dict() for d in datasets]
    
    if include_tables:
        tables = await extractor.get_table_metadata()
        results["tables"] = [t.to_dict() for t in tables]
    
    if include_queries:
        queries = await extractor.get_query_history(query_days_back)
        results["queries"] = [q.to_dict() for q in queries]
    
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
            metadata = await extract_metadata(credentials)
            print(json.dumps(metadata, indent=2, default=str))
        except Exception as e:
            print(f"Error: {e}")
    
    asyncio.run(main()) 