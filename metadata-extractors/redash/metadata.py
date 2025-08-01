"""
Redash Metadata Extractor

This module provides functionality to extract metadata from Redash including:
- Dashboard metadata (name, description, widgets, authors)
- Widget metadata (queries, visualizations, data points)
- Saved query metadata (SQL, execution stats, scheduling)

Authentication is handled via Redash API keys.
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress urllib3 connection pool warnings
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)


class RedashMetadataExtractor:
    """Main class for extracting metadata from Redash"""
    
    def __init__(self, credentials: Dict[str, Any]):
        """
        Initialize Redash metadata extractor
        
        Args:
            credentials: Dictionary containing:
                - api_url: Redash instance URL
                - api_key: Redash API key
        """
        self.credentials = credentials
        self.api_url = credentials.get('api_url', '').rstrip('/')
        self.api_key = credentials.get('api_key')
        self.session: Optional[requests.Session] = None
        self.redash_version: Optional[str] = None
        
        self._validate_credentials()
        self._initialize_session()

    def _validate_credentials(self):
        """Validate required credentials"""
        required_fields = ['api_url', 'api_key']
        missing_fields = [field for field in required_fields if not self.credentials.get(field)]
        
        if missing_fields:
            raise ValueError(f"Missing required credentials: {', '.join(missing_fields)}")

    def _initialize_session(self):
        """Initialize requests session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Key {self.api_key}',
            'Content-Type': 'application/json'
        })

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make HTTP request to Redash API with retries
        
        Args:
            endpoint: API endpoint (without base URL)
            params: Optional query parameters
            
        Returns:
            JSON response as dictionary
        """
        url = f"{self.api_url}/api/{endpoint}"
        
        if not self.session:
            raise RuntimeError("Session not initialized")
            
        response = None
        try:
            response = self.session.get(url, params=params)
            
            # Log less verbose details (only for non-routine requests)
            if logger.level <= logging.DEBUG:
                logger.debug(f"API Request: {url}")
                logger.debug(f"Response Status: {response.status_code}")
            
            # Check if response is successful
            response.raise_for_status()
            
            # Try to parse JSON
            if not response.text.strip():
                raise ValueError("Empty response from server")
                
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if response and response.status_code == 404:
                # 404s are common for deleted/inaccessible dashboards - log as warning
                logger.warning(f"Resource not found: {endpoint} (404 - likely deleted/archived)")
            else:
                logger.error(f"HTTP Error for {endpoint}: {e}")
                logger.error(f"Response content: {response.text[:500] if response else 'No response'}")
            raise
        except ValueError as e:
            logger.error(f"JSON decode error for {endpoint}: {e}")
            logger.error(f"Raw response: {response.text[:500] if response else 'No response'}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {endpoint}: {e}")
            raise

    async def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to Redash API
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Test with session endpoint which is more reliable
            session_data = await asyncio.to_thread(self._make_request, "session")
            user_name = session_data.get('user', {}).get('name', 'Unknown')
            message = f"Connection successful to Redash: {self.api_url} (User: {user_name})"
            logger.info(message)
            return True, message
        except Exception as e:
            message = f"Connection failed: {str(e)}"
            logger.error(message)
            return False, message

    async def _detect_version(self) -> Optional[str]:
        """Detect Redash version from session endpoint"""
        try:
            # Try to get version from session data or client config
            session_data = await asyncio.to_thread(self._make_request, "session")
            
            # Try different places where version might be stored
            version = None
            client_config = session_data.get('client_config', {})
            version = client_config.get('version') or client_config.get('redash_version')
            
            if not version:
                # Fallback: assume a reasonable default based on API structure
                version = "8.0.0"  # Conservative assumption for version detection
                logger.info(f"Version not found in session, assuming: {version}")
            
            self.redash_version = version
            logger.info(f"Detected Redash version: {version}")
            return version
        except Exception as e:
            logger.warning(f"Could not detect Redash version: {e}")
            # Default to using slug-based IDs for safety
            self.redash_version = "8.0.0"
            return "8.0.0"

    def _should_use_slug(self) -> bool:
        """Determine if we should use slug (< v10) or numeric ID (>= v10) for dashboards"""
        if not self.redash_version or self.redash_version == 'unknown':
            return True  # Default to slug for safety
        
        version_str = self.redash_version.lower()
        
        # If this is an explicit pre-release of 10.0.0-beta, treat as legacy
        if "beta" in version_str and version_str.startswith("10.0.0"):
            return True
        
        try:
            # Extract leading numeric portion (e.g., "8" from "8.0.0+b32245")
            numeric_prefix = version_str.split(".")[0]
            major = int("".join(ch for ch in numeric_prefix if ch.isdigit()))
            return major < 10
        except (ValueError, IndexError):
            logger.warning(f"Unable to parse Redash version '{self.redash_version}' - defaulting to slug")
            return True  # Default to slug if version parsing fails

    async def get_dashboards(self) -> List[Dict[str, Any]]:
        """Get all dashboards from Redash"""
        try:
            # Get paginated dashboard list
            page = 1
            all_dashboards = []
            
            while True:
                params = {'page': page, 'page_size': 100}
                response = await asyncio.to_thread(self._make_request, "dashboards", params)
                
                dashboards = response.get('results', [])
                if not dashboards:
                    break
                    
                all_dashboards.extend(dashboards)
                
                # Check if there are more pages
                if len(dashboards) < 100:
                    break
                    
                page += 1
            
            logger.info(f"Found {len(all_dashboards)} dashboards")
            return all_dashboards
            
        except Exception as e:
            logger.error(f"Error fetching dashboards: {e}")
            return []

    async def get_dashboard_details(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed dashboard information including widgets"""
        try:
            dashboard = await asyncio.to_thread(self._make_request, f"dashboards/{dashboard_id}")
            return dashboard
        except Exception as e:
            # Don't log 404s as errors - they're expected for deleted/archived dashboards
            if "404" in str(e):
                logger.debug(f"Dashboard {dashboard_id} not accessible (404 - likely deleted/archived)")
            else:
                logger.warning(f"Error fetching dashboard {dashboard_id}: {e}")
            return None
    
    async def get_query(self, query_id: str) -> Dict[str, Any]:
        """
        Fetches query information by ID.

        Args:
            query_id (str): Query ID

        Returns:
            Dict[str, Any]: Query details
        """
        return await asyncio.to_thread(self._make_request, f"queries/{query_id}")
    
    async def get_query_result(self, result_id: str) -> Dict[str, Any]:
        """
        Fetches query result data by result ID.

        Args:
            result_id (str): Query result ID

        Returns:
            Dict[str, Any]: Query result data
        """
        return await asyncio.to_thread(self._make_request, f"query_results/{result_id}")

    async def _get_dashboard_with_id(self, dashboard: Dict[str, Any], use_slug: bool) -> Optional[Dict[str, Any]]:
        """Get dashboard details with proper ID selection based on version"""
        if use_slug:
            dashboard_id = dashboard.get('slug')
        else:
            dashboard_id = dashboard.get('id')
            if dashboard_id is not None:
                dashboard_id = str(dashboard_id)
        
        if not dashboard_id:
            return None
            
        try:
            details = await self.get_dashboard_details(dashboard_id)
            return details
        except Exception as e:
            logger.debug(f"Failed to fetch dashboard {dashboard_id}: {e}")
            return None

    async def _safe_get_query(self, query_id: str) -> Optional[Dict[str, Any]]:
        """Safely fetch query, return None on failure"""
        try:
            return await self.get_query(str(query_id))
        except Exception as e:
            logger.debug(f"Failed to fetch query {query_id}: {e}")
            return None

    async def get_saved_queries(self) -> List[Dict[str, Any]]:
        """Get all saved queries from Redash"""
        try:
            page = 1
            all_queries = []
            
            while True:
                params = {'page': page, 'page_size': 100, 'order': '-created_at'}
                response = await asyncio.to_thread(self._make_request, "queries", params)
                
                queries = response.get('results', [])
                if not queries:
                    break
                    
                all_queries.extend(queries)
                
                # Check if there are more pages
                if len(queries) < 100:
                    break
                    
                page += 1
            
            logger.info(f"Found {len(all_queries)} saved queries")
            return all_queries
            
        except Exception as e:
            logger.error(f"Error fetching saved queries: {e}")
            return []

    async def count_widgets_from_dashboards(self, dashboards: List[Dict[str, Any]]) -> int:
        """Count total widgets across all dashboards using optimized three-level parallelization"""
        
        # Determine the correct ID type to use based on version
        use_slug = self._should_use_slug()
        logger.info(f"Using {'slug' if use_slug else 'numeric ID'} identifiers for dashboards (version: {self.redash_version})")
        
        # LEVEL 1: Fetch ALL dashboard details in parallel
        logger.info(f"Level 1: Fetching details for {len(dashboards)} dashboards in parallel...")
        
        # Fetch all dashboard details in parallel
        dashboard_details = await asyncio.gather(
            *[self._get_dashboard_with_id(dashboard, use_slug) for dashboard in dashboards],
            return_exceptions=True
        )
        
        # Filter out failed dashboards and extract all query IDs
        valid_dashboards = [d for d in dashboard_details if d and not isinstance(d, Exception)]
        logger.info(f"Level 1 complete: {len(valid_dashboards)}/{len(dashboards)} dashboards accessible")
        
        # LEVEL 2: Flatten and extract ALL query IDs across all dashboards
        all_query_ids = []
        widget_to_query_map = {}  # Map widget back to its query_id for counting
        
        for dashboard in valid_dashboards:
            if not dashboard or not isinstance(dashboard, dict) or 'widgets' not in dashboard:
                continue
                
            for widget in dashboard['widgets']:
                widget_id = widget.get('id')
                visualization = widget.get("visualization", {})
                query_id = visualization.get("query", {}).get("id") if visualization else None
                
                if query_id and widget_id:
                    all_query_ids.append(query_id)
                    widget_to_query_map[widget_id] = query_id
        
        if not all_query_ids:
            logger.info("No widgets with queries found")
            return 0
            
        logger.info(f"Level 2: Found {len(all_query_ids)} widgets with queries, fetching query details in parallel...")
        
        # Fetch ALL query data in parallel (removing duplicates for efficiency)
        unique_query_ids = list(set(all_query_ids))
        logger.info(f"Level 2: Fetching {len(unique_query_ids)} unique queries in parallel...")
        
        all_query_data = await asyncio.gather(
            *[self._safe_get_query(qid) for qid in unique_query_ids],
            return_exceptions=True
        )
        
        # Create query_id -> query_data mapping
        query_data_map = {}
        valid_query_count = 0
        for i, query_data in enumerate(all_query_data):
            if query_data and not isinstance(query_data, Exception):
                query_data_map[unique_query_ids[i]] = query_data
                valid_query_count += 1
        
        logger.info(f"Level 2 complete: {valid_query_count}/{len(unique_query_ids)} queries fetched successfully")
        
        # Count widgets that have valid queries
        widgets_with_valid_queries = 0
        for widget_id, query_id in widget_to_query_map.items():
            if query_id in query_data_map:
                widgets_with_valid_queries += 1
        
        logger.info(f"Widget counting complete: {widgets_with_valid_queries} widgets have accessible queries")
        return widgets_with_valid_queries


async def extract_metadata(credentials: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to extract Redash metadata counts efficiently.
    
    Args:
        credentials: Redash credentials dictionary.
        
    Returns:
        Dict[str, Any]: A dictionary with the counts of dashboards, widgets, and queries.
    """
    extractor = RedashMetadataExtractor(credentials)
    
    # Test connection first
    success, message = await extractor.test_connection()
    if not success:
        return {"error": message}
    
    # Detect Redash version
    await extractor._detect_version()
    
    # Fetch dashboards and queries in parallel (independent operations)
    logger.info("Fetching dashboards and queries in parallel...")
    dashboards_task = extractor.get_dashboards()
    queries_task = extractor.get_saved_queries()
    
    dashboards, queries = await asyncio.gather(
        dashboards_task,
        queries_task
    )
    
    # Now count widgets using the dashboard data we already have
    logger.info("Counting widgets using fetched dashboard data...")
    widgets = await extractor.count_widgets_from_dashboards(dashboards)
    
    results = {
        "connection_test": {"success": True, "message": message},
        "version": extractor.redash_version,
        "counts": {
            "dashboards": len(dashboards),
            "widgets": widgets,
            "saved_queries": len(queries)
        }
    }
    
    return results


if __name__ == "__main__":
    import os
    
    # Example usage with environment variables
    credentials = {
        "api_url": os.getenv("REDASH_API_URL"),
        "api_key": os.getenv("REDASH_API_KEY")
    }
    
    async def main():
        try:
            metadata = await extract_metadata(credentials)
            print(json.dumps(metadata, indent=2, default=str))
        except Exception as e:
            print(f"Error: {e}")
    
    asyncio.run(main()) 