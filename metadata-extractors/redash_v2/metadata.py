"""
Redash Golden Asset Ranking System - Metadata Extractor

This module provides the foundational layer for extracting and organizing
metadata from Redash instances to enable golden asset scoring.

Key Features (Phase 1):
- Secure configuration and connection handling
- Robust Redash version detection
- Concurrent metadata ingestion with dependency mapping
- High-performance data extraction optimized for scoring
"""

import asyncio
import csv
import logging
import math
import os
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timezone
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

try:
    import pandas as pd
except ImportError:
    pd = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress urllib3 connection pool warnings
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)


class RedashMetadataExtractor:
    """
    Enhanced Redash metadata extractor for the Golden Asset Ranking System.
    
    This class implements Phase 1 of the plan: Foundational Layer - High-Performance Data Extraction
    """
    
    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize Redash metadata extractor with secure configuration.
        
        Args:
            api_url: Redash instance URL (if not provided, loads from environment)
            api_key: Redash API key (if not provided, loads from environment)
        """
        # Load environment variables if not explicitly provided
        load_dotenv()
        
        self.api_url = api_url or os.getenv('REDASH_API_URL')
        self.api_key = api_key or os.getenv('REDASH_API_KEY')
        
        # Validate credentials
        self._validate_credentials()
        
        # Clean up API URL
        if self.api_url:
            self.api_url = self.api_url.rstrip('/')
        
        # Session and version info
        self.session: Optional[requests.Session] = None
        self.redash_version: Optional[str] = None
        self.use_slug_for_dashboards: bool = True  # Default to True for safety
        
        # Dependency maps (Phase 1 requirement)
        self.query_to_dashboards_map: Dict[int, Set[int]] = {}
        self.query_to_charts_map: Dict[int, Set[int]] = {}
        self.dashboard_to_queries_map: Dict[int, Set[int]] = {}
        
        # Data storage
        self.all_dashboards: List[Dict[str, Any]] = []
        self.all_queries: List[Dict[str, Any]] = []
        self.detailed_dashboards: List[Dict[str, Any]] = []
        self.detailed_queries: List[Dict[str, Any]] = []
        
        # Connection management
        self.max_concurrent_requests = 10  # Limit concurrent requests to avoid overwhelming server
        self._semaphore = None  # Will be initialized when needed
        
        # Initialize session
        self._initialize_session()

    def _validate_credentials(self):
        """Validate required credentials (Phase 1 requirement)"""
        if not self.api_url:
            raise ValueError("Missing required credential: REDASH_API_URL must be set in environment or passed directly")
        
        if not self.api_key:
            raise ValueError("Missing required credential: REDASH_API_KEY must be set in environment or passed directly")

    def _initialize_session(self):
        """Initialize requests session with authentication (Phase 1 requirement)"""
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
                logger.debug("API Request: %s", url)
                logger.debug("Response Status: %s", response.status_code)
            
            # Check if response is successful
            response.raise_for_status()
            
            # Try to parse JSON
            if not response.text.strip():
                raise ValueError("Empty response from server")
                
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if response and response.status_code == 404:
                logger.warning("Resource not found: %s (404 - likely deleted/archived)", endpoint)
            else:
                logger.error("HTTP Error for %s: %s", endpoint, e)
                logger.error("Response content: %s", response.text[:500] if response else 'No response')
            raise
        except ValueError as e:
            logger.error("JSON decode error for %s: %s", endpoint, e)
            logger.error("Raw response: %s", response.text[:500] if response else 'No response')
            raise
        except requests.exceptions.RequestException as e:
            logger.error("Request failed for %s: %s", endpoint, e)
            raise

    async def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to Redash API using /api/session endpoint (Phase 1 requirement)
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            session_data = await asyncio.to_thread(self._make_request, "session")
            user_name = session_data.get('user', {}).get('name', 'Unknown')
            message = "Connection successful to Redash: {} (User: {})".format(self.api_url, user_name)
            logger.info(message)
            return True, message
        except Exception as e:
            message = "Connection failed: {}".format(str(e))
            logger.error(message)
            return False, message

    async def _detect_version(self) -> Optional[str]:
        """
        Detect Redash version from session endpoint (Phase 1 requirement)
        """
        try:
            session_data = await asyncio.to_thread(self._make_request, "session")
            
            # Try different places where version might be stored
            version = None
            client_config = session_data.get('client_config', {})
            version = client_config.get('version') or client_config.get('redash_version')
            
            if not version:
                # Fallback: assume a reasonable default
                version = "8.0.0"
                logger.info("Version not found in session, assuming: %s", version)
            
            self.redash_version = version
            
            # Set use_slug_for_dashboards flag based on version (Phase 1 requirement)
            try:
                major_version = int(version.split('.')[0])
                self.use_slug_for_dashboards = major_version < 10
            except (ValueError, IndexError):
                logger.warning("Unable to parse version '%s' - defaulting to slug", version)
                self.use_slug_for_dashboards = True
                
            logger.info("Detected Redash version: %s (use_slug: %s)", version, self.use_slug_for_dashboards)
            return version
        except Exception as e:
            logger.warning("Could not detect Redash version: %s", e)
            self.redash_version = "8.0.0"
            self.use_slug_for_dashboards = True
            return "8.0.0"

    async def get_all_dashboards(self) -> List[Dict[str, Any]]:
        """Get all dashboards using pagination (Phase 1 requirement)"""
        try:
            page = 1
            all_dashboards = []
            
            while True:
                params = {'page': page, 'page_size': 100}
                response = await asyncio.to_thread(self._make_request, "dashboards", params)
                
                dashboards = response.get('results', [])
                if not dashboards:
                    break
                    
                all_dashboards.extend(dashboards)
                
                if len(dashboards) < 100:
                    break
                    
                page += 1
            
            logger.info("Found %d dashboards", len(all_dashboards))
            self.all_dashboards = all_dashboards
            return all_dashboards
            
        except Exception as e:
            logger.error("Error fetching dashboards: %s", e)
            return []

    async def get_all_queries(self) -> List[Dict[str, Any]]:
        """Get all saved queries using pagination (Phase 1 requirement)"""
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
                
                if len(queries) < 100:
                    break
                    
                page += 1
            
            logger.info("Found %d saved queries", len(all_queries))
            self.all_queries = all_queries
            return all_queries
            
        except Exception as e:
            logger.error("Error fetching saved queries: %s", e)
            return []

    def _get_semaphore(self):
        """Get or create semaphore for concurrency limiting"""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        return self._semaphore

    async def _rate_limited_request(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Make a request with concurrency limiting using semaphore"""
        semaphore = self._get_semaphore()
        async with semaphore:
            try:
                result = await asyncio.to_thread(self._make_request, endpoint)
                return result
            except Exception as e:
                logger.debug("Rate-limited request failed for %s: %s", endpoint, e)
                return None

    async def _get_detailed_dashboard(self, dashboard: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get detailed dashboard information with concurrency limiting"""
        try:
            if self.use_slug_for_dashboards:
                dashboard_id = dashboard.get('slug')
            else:
                dashboard_id = str(dashboard.get('id'))
            
            if not dashboard_id:
                return None
                
            endpoint = f"dashboards/{dashboard_id}"
            detailed = await self._rate_limited_request(endpoint)
            return detailed
        except Exception as e:
            logger.debug("Failed to fetch detailed dashboard %s: %s", dashboard.get('id', 'unknown'), e)
            return None

    async def _get_detailed_query(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get detailed query information with concurrency limiting"""
        try:
            query_id = query.get('id')
            if not query_id:
                return None
                
            endpoint = f"queries/{query_id}"
            detailed = await self._rate_limited_request(endpoint)
            return detailed
        except Exception as e:
            logger.debug("Failed to fetch detailed query %s: %s", query.get('id', 'unknown'), e)
            return None

    def _build_dependency_maps(self, detailed_dashboards: List[Dict[str, Any]]):
        """
        Build dependency maps from detailed dashboard data (Phase 1 requirement)
        
        Creates:
        - query_to_dashboards_map: {query_id: {dashboard_id_1, dashboard_id_2}}
        - query_to_charts_map: {query_id: {widget_id_1, widget_id_2}}
        - dashboard_to_queries_map: {dashboard_id: {query_id_1, query_id_2}}
        """
        logger.info("Building dependency maps...")
        
        # Reset maps
        self.query_to_dashboards_map = {}
        self.query_to_charts_map = {}
        self.dashboard_to_queries_map = {}
        
        # Debugging statistics
        widget_stats = {
            'total_widgets': 0,
            'widget_types': {},
            'widgets_without_queries': 0,
            'widgets_without_queries_by_type': {}
        }
        
        for dashboard in detailed_dashboards:
            if not dashboard or not isinstance(dashboard, dict):
                continue
                
            dashboard_id = dashboard.get('id')
            if not dashboard_id:
                continue
                
            widgets = dashboard.get('widgets', [])
            dashboard_query_ids = set()
            
            for widget in widgets:
                widget_stats['total_widgets'] += 1
                
                widget_id = widget.get('id')
                visualization = widget.get('visualization', {})
                
                # Determine widget type
                if not visualization:
                    widget_type = 'no_visualization'
                else:
                    widget_type = visualization.get('type', 'unknown_type')
                
                # Count widget types
                widget_stats['widget_types'][widget_type] = widget_stats['widget_types'].get(widget_type, 0) + 1
                
                # Skip text widgets
                if not visualization or visualization.get('type') == 'text':
                    continue
                
                query_info = visualization.get('query', {})
                query_id = query_info.get('id')
                
                # Track widgets without queries
                if not query_id:
                    widget_stats['widgets_without_queries'] += 1
                    widget_stats['widgets_without_queries_by_type'][widget_type] = widget_stats['widgets_without_queries_by_type'].get(widget_type, 0) + 1
                
                if query_id and widget_id:
                    # Add to query -> dashboards mapping
                    if query_id not in self.query_to_dashboards_map:
                        self.query_to_dashboards_map[query_id] = set()
                    self.query_to_dashboards_map[query_id].add(dashboard_id)
                    
                    # Add to query -> charts mapping
                    if query_id not in self.query_to_charts_map:
                        self.query_to_charts_map[query_id] = set()
                    self.query_to_charts_map[query_id].add(widget_id)
                    
                    # Track for dashboard -> queries mapping
                    dashboard_query_ids.add(query_id)
            
            # Add to dashboard -> queries mapping
            if dashboard_query_ids:
                self.dashboard_to_queries_map[dashboard_id] = dashboard_query_ids
        
        # Print debugging statistics
        logger.info("=== WIDGET DEBUGGING STATISTICS ===")
        logger.info("📊 Total widgets across all dashboards: %d", widget_stats['total_widgets'])
        logger.info("📈 Widget types breakdown:")
        for widget_type, count in sorted(widget_stats['widget_types'].items()):
            logger.info("   - %s: %d", widget_type, count)
        
        logger.info("❌ Widgets without queries: %d", widget_stats['widgets_without_queries'])
        if widget_stats['widgets_without_queries_by_type']:
            logger.info("❌ Widgets without queries by type:")
            for widget_type, count in sorted(widget_stats['widgets_without_queries_by_type'].items()):
                logger.info("   - %s: %d", widget_type, count)
        logger.info("=== END WIDGET STATISTICS ===")
        
        logger.info("Built dependency maps:")
        logger.info("  - Unique Queries with dashboard dependencies: %d", len(self.query_to_dashboards_map))
        logger.info("  - Unique Queries with chart widgets: %d", len(self.query_to_charts_map))
        logger.info("  - Dashboards with queries: %d", len(self.dashboard_to_queries_map))

    # ==================================================================================
    # PHASE 2: GOLDEN SAVED QUERY SCORING LOGIC
    # ==================================================================================
    
    def _assemble_query_features(self, detailed_queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Phase 2.1: Raw Feature Assembly
        
        Create feature-rich dictionaries for each query containing all raw data points for scoring.
        
        Args:
            detailed_queries: List of detailed query objects from API
            
        Returns:
            List of feature dictionaries with downstream counts
        """
        logger.info("Phase 2.1: Assembling raw query features...")
        
        query_features = []
        
        for query in detailed_queries:
            if not query or not isinstance(query, dict):
                continue
                
            query_id = query.get('id')
            if not query_id:
                continue
            
            # Get downstream counts from dependency maps
            downstream_dashboard_count = len(self.query_to_dashboards_map.get(query_id, set()))
            downstream_chart_count = len(self.query_to_charts_map.get(query_id, set()))
            
            # Extract user information
            user_info = query.get('user', {}) or query.get('created_by', {})
            user_name = user_info.get('name', 'Unknown') if isinstance(user_info, dict) else 'Unknown'
            
            # Create feature dictionary (Phase 2.1 requirement)
            features = {
                'id': query_id,
                'name': query.get('name', ''),
                'description': query.get('description', ''),
                'query': query.get('query', ''),  # SQL content
                'created_at': query.get('created_at'),
                'user_name': user_name,
                'schedule': query.get('schedule'),  # For curation score
                'updated_at': query.get('updated_at'),
                'downstream_dashboard_count': downstream_dashboard_count,
                'downstream_chart_count': downstream_chart_count
            }
            
            query_features.append(features)
        
        logger.info("Assembled features for %d queries", len(query_features))
        return query_features
    
    def _calculate_query_impact_score(self, query_features: List[Dict[str, Any]]) -> None:
        """
        Phase 2.2.1: Calculate Impact Score (Max: 6 points)
        
        Uses downstream dependencies as proxy for importance with log-transform 
        and 80/20 weighting (dashboards vs charts).
        
        Args:
            query_features: List of query feature dictionaries (modified in place)
        """
        logger.info("Phase 2.2.1: Calculating impact scores...")
        
        if not query_features:
            return
            
        # Calculate log counts for normalization
        max_log_dashboard_count = 0
        max_log_chart_count = 0
        
        for features in query_features:
            dashboard_count = features['downstream_dashboard_count']
            chart_count = features['downstream_chart_count']
            
            # Log transform to dampen outliers (Phase 2 requirement)
            log_dashboard_count = math.log(1 + dashboard_count)
            log_chart_count = math.log(1 + chart_count)
            
            # Track maximums for normalization
            max_log_dashboard_count = max(max_log_dashboard_count, log_dashboard_count)
            max_log_chart_count = max(max_log_chart_count, log_chart_count)
            
            # Store intermediate values
            features['_log_dashboard_count'] = log_dashboard_count
            features['_log_chart_count'] = log_chart_count
        
        # Calculate normalized impact scores
        for features in query_features:
            # Normalize to 0-1 scale
            if max_log_dashboard_count > 0:
                norm_dash_count = features['_log_dashboard_count'] / max_log_dashboard_count
            else:
                norm_dash_count = 0
                
            if max_log_chart_count > 0:
                norm_chart_count = features['_log_chart_count'] / max_log_chart_count  
            else:
                norm_chart_count = 0
            
            # Calculate impact score with 80/20 weighting (Phase 2 requirement)
            impact_score = 6 * ((0.8 * norm_dash_count) + (0.2 * norm_chart_count))
            features['impact_score'] = impact_score
            
            # Clean up intermediate values
            del features['_log_dashboard_count']
            del features['_log_chart_count']
    
    def _calculate_query_recency_score(self, query_features: List[Dict[str, Any]]) -> None:
        """
        Phase 2.2.2: Calculate Recency Score (Max: 3 points)
        
        Rewards queries with fresh data using smooth exponential decay curve.
        
        Args:
            query_features: List of query feature dictionaries (modified in place)
        """
        logger.info("Phase 2.2.2: Calculating recency scores...")
        
        current_time = datetime.now(timezone.utc)
        
        for features in query_features:
            last_updated_str = features.get('updated_at')
            
            if not last_updated_str:
                # No execution data - assign minimum score
                features['recency_score'] = 0.0
                continue
                
            try:
                # Parse the timestamp
                if isinstance(last_updated_str, str):
                    # Handle different timestamp formats
                    if last_updated_str.endswith('Z'):
                        last_updated = datetime.fromisoformat(last_updated_str[:-1]).replace(tzinfo=timezone.utc)
                    elif '+' in last_updated_str or last_updated_str.endswith('+00:00'):
                        last_updated = datetime.fromisoformat(last_updated_str)
                    else:
                        last_updated = datetime.fromisoformat(last_updated_str).replace(tzinfo=timezone.utc)
                else:
                    # Assume it's already a datetime object
                    last_updated = last_updated_str
                    if last_updated.tzinfo is None:
                        last_updated = last_updated.replace(tzinfo=timezone.utc)
                
                # Calculate days since last update
                time_diff = current_time - last_updated
                days_since_last_update = time_diff.total_seconds() / 86400  # Convert to days
                
                # Apply exponential decay (Phase 2 requirement: 3 * exp(-0.02 * days))
                recency_score = 3 * math.exp(-0.02 * days_since_last_update)
                features['recency_score'] = recency_score
                
            except (ValueError, TypeError) as e:
                logger.debug("Failed to parse updated_at for query %s: %s", features['id'], e)
                features['recency_score'] = 0.0
    
    def _calculate_query_curation_score(self, query_features: List[Dict[str, Any]]) -> None:
        """
        Phase 2.2.3: Calculate Curation & Trust Score (Max: 1 point)
        
        Rewards good data stewardship (documentation) and operational reliability (scheduling).
        
        Args:
            query_features: List of query feature dictionaries (modified in place)
        """
        logger.info("Phase 2.2.3: Calculating curation scores...")
        
        for features in query_features:
            curation_score = 0.0
            
            # 0.5 points for having a description (Phase 2 requirement)
            description = features.get('description') or ''  # Handle None values safely
            if description:
                curation_score += 0.5
                
            # 0.5 points for having a schedule (Phase 2 requirement)  
            schedule = features.get('schedule')
            if schedule:
                curation_score += 0.5
                
            features['curation_score'] = curation_score
    
    def _calculate_final_query_scores(self, query_features: List[Dict[str, Any]]) -> None:
        """
        Phase 2.3: Final Score Calculation and Storage
        
        Combine component scores into final golden_query_score and ensure all scores 
        are stored in the feature dictionary.
        
        Args:
            query_features: List of query feature dictionaries (modified in place)
        """
        logger.info("Phase 2.3: Calculating final query scores...")
        
        for features in query_features:
            # Get component scores (should already be calculated)
            impact_score = features.get('impact_score', 0)
            recency_score = features.get('recency_score', 0) 
            curation_score = features.get('curation_score', 0)
            
            # Calculate final golden score (Phase 2 requirement)
            golden_query_score = impact_score + recency_score + curation_score
            features['golden_query_score'] = golden_query_score
    
    def score_all_queries(self) -> List[Dict[str, Any]]:
        """
        Main method for Phase 2: Golden Saved Query Scoring Logic
        
        Executes all steps of query scoring:
        1. Raw feature assembly
        2. Component score calculations (Impact, Recency, Curation)
        3. Final score calculation and storage
        
        Returns:
            List of fully scored query feature dictionaries
        """
        logger.info("Starting Phase 2: Golden Saved Query Scoring Logic")
        
        if not self.detailed_queries:
            logger.warning("No detailed queries available for scoring. Run extract_all_metadata() first.")
            return []
        
        # Phase 2.1: Raw Feature Assembly
        query_features = self._assemble_query_features(self.detailed_queries)
        
        if not query_features:
            logger.warning("No query features assembled")
            return []
        
        # Phase 2.2: Component Score Calculations
        self._calculate_query_impact_score(query_features)
        self._calculate_query_recency_score(query_features)
        self._calculate_query_curation_score(query_features)
        
        # Phase 2.3: Final Score Calculation
        self._calculate_final_query_scores(query_features)
        
        # Sort by golden score for easier analysis
        query_features.sort(key=lambda x: x.get('golden_query_score', 0), reverse=True)
        
        logger.info("Phase 2 completed: Scored %d queries", len(query_features))
        logger.info("Top query score: %.2f", query_features[0].get('golden_query_score', 0) if query_features else 0)
        
        return query_features

    # ==================================================================================
    # PHASE 3: GOLDEN DASHBOARD SCORING LOGIC
    # ==================================================================================
    
    def _assemble_dashboard_features(self, detailed_dashboards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Phase 3.1: Raw Feature Assembly for Dashboards
        
        Create feature-rich dictionaries for each dashboard containing all raw data points for scoring.
        
        Args:
            detailed_dashboards: List of detailed dashboard objects from API
            
        Returns:
            List of dashboard feature dictionaries
        """
        logger.info("Phase 3.1: Assembling raw dashboard features...")
        
        dashboard_features = []
        
        for dashboard in detailed_dashboards:
            if not dashboard or not isinstance(dashboard, dict):
                continue
                
            dashboard_id = dashboard.get('id')
            if not dashboard_id:
                continue
            
            # Extract user information
            user_info = dashboard.get('user', {}) or dashboard.get('created_by', {})
            user_name = user_info.get('name', 'Unknown') if isinstance(user_info, dict) else 'Unknown'
            
            # Create feature dictionary
            features = {
                'id': dashboard_id,
                'name': dashboard.get('name', ''),
                'slug': dashboard.get('slug', ''),
                'created_at': dashboard.get('created_at'),
                'updated_at': dashboard.get('updated_at'),
                'user_name': user_name,
                'widgets': dashboard.get('widgets', []),
                'is_draft': dashboard.get('is_draft', False),
                'tags': dashboard.get('tags', [])
            }
            
            dashboard_features.append(features)
        
        logger.info("Assembled features for %d dashboards", len(dashboard_features))
        return dashboard_features
    
    def _calculate_dashboard_content_quality_score(self, dashboard_features: List[Dict[str, Any]], 
                                                   scored_queries: List[Dict[str, Any]]) -> None:
        """
        Phase 3.2.1: Calculate Content Quality Score (Max: 7 points)
        
        A dashboard's value is the sum of its parts. Uses the sum of golden_query_scores
        to reward dashboards that synthesize information from multiple high-quality sources.
        
        Args:
            dashboard_features: List of dashboard feature dictionaries (modified in place)
            scored_queries: List of scored query dictionaries from Phase 2
        """
        logger.info("Phase 3.2.1: Calculating dashboard content quality scores...")
        
        if not scored_queries:
            logger.warning("No scored queries available for dashboard content scoring")
            for features in dashboard_features:
                features['content_quality_score'] = 0.0
            return
        
        # Create query_id -> golden_query_score mapping
        query_score_map = {q['id']: q.get('golden_query_score', 0) for q in scored_queries}
        
        # Calculate raw content scores for all dashboards
        raw_content_scores = []
        for features in dashboard_features:
            dashboard_id = features['id']
            
            # Get unique queries for this dashboard from dependency map
            query_ids = self.dashboard_to_queries_map.get(dashboard_id, set())
            
            # Sum the golden_query_scores for these queries (Phase 3 requirement)
            raw_content_score = sum(query_score_map.get(qid, 0) for qid in query_ids)
            features['_raw_content_score'] = raw_content_score
            raw_content_scores.append(raw_content_score)
        
        # Normalize to 7-point scale (Phase 3 requirement)
        max_raw_content_score = max(raw_content_scores) if raw_content_scores else 1
        if max_raw_content_score == 0:
            max_raw_content_score = 1  # Avoid division by zero
        
        for features in dashboard_features:
            raw_score = features['_raw_content_score']
            content_quality_score = 7 * (raw_score / max_raw_content_score)
            features['content_quality_score'] = content_quality_score
            
            # Clean up intermediate value
            del features['_raw_content_score']
    
    def _calculate_dashboard_recency_score(self, dashboard_features: List[Dict[str, Any]]) -> None:
        """
        Phase 3.2.2: Calculate Dashboard Recency Score (Max: 2 points)
        
        Rewards actively maintained dashboards with a gentle exponential decay.
        
        Args:
            dashboard_features: List of dashboard feature dictionaries (modified in place)
        """
        logger.info("Phase 3.2.2: Calculating dashboard recency scores...")
        
        current_time = datetime.now(timezone.utc)
        
        for features in dashboard_features:
            updated_at_str = features.get('updated_at')
            
            if not updated_at_str:
                # No update data - assign minimum score
                features['recency_score'] = 0.0
                continue
                
            try:
                # Parse the timestamp
                if isinstance(updated_at_str, str):
                    # Handle different timestamp formats
                    if updated_at_str.endswith('Z'):
                        last_updated = datetime.fromisoformat(updated_at_str[:-1]).replace(tzinfo=timezone.utc)
                    elif '+' in updated_at_str or updated_at_str.endswith('+00:00'):
                        last_updated = datetime.fromisoformat(updated_at_str)
                    else:
                        last_updated = datetime.fromisoformat(updated_at_str).replace(tzinfo=timezone.utc)
                else:
                    # Assume it's already a datetime object
                    last_updated = updated_at_str
                    if last_updated.tzinfo is None:
                        last_updated = last_updated.replace(tzinfo=timezone.utc)
                
                # Calculate days since last update
                time_diff = current_time - last_updated
                days_since_last_updated = time_diff.total_seconds() / 86400  # Convert to days
                
                # Apply exponential decay (Phase 3 requirement: 2 * exp(-0.01 * days))
                recency_score = 2 * math.exp(-0.01 * days_since_last_updated)
                features['recency_score'] = recency_score
                
            except (ValueError, TypeError) as e:
                logger.debug("Failed to parse updated_at for dashboard %s: %s", features['id'], e)
                features['recency_score'] = 0.0
    
    def _calculate_dashboard_curation_score(self, dashboard_features: List[Dict[str, Any]]) -> None:
        """
        Phase 3.2.3: Calculate Dashboard Curation Score (Max: 1 point)
        
        Rewards dashboards with a description, using the "top-left text box" heuristic.
        Finds the top-leftmost widget and checks if it's a text box.
        
        Args:
            dashboard_features: List of dashboard feature dictionaries (modified in place)
        """
        logger.info("Phase 3.2.3: Calculating dashboard curation scores...")
        
        for features in dashboard_features:
            widgets = features.get('widgets', [])
            
            if not widgets:
                features['curation_score'] = 0.0
                continue
            
            # Find the top-leftmost widget (Phase 3 requirement)
            # Widgets have position data: {'col': x, 'row': y, 'sizeX': width, 'sizeY': height}
            text_widgets = []
            
            for widget in widgets:
                # Check if it's a text widget
                visualization = widget.get('visualization')
                if not visualization:
                    # No visualization typically means text widget
                    options = widget.get('options', {})
                    position = options.get('position', {})
                    text_widgets.append({
                        'widget': widget,
                        'row': position.get('row', 0),
                        'col': position.get('col', 0)
                    })
                elif visualization.get('type') == 'text':
                    options = widget.get('options', {})
                    position = options.get('position', {})
                    text_widgets.append({
                        'widget': widget,
                        'row': position.get('row', 0),
                        'col': position.get('col', 0)
                    })
            
            if text_widgets:
                # Find the top-leftmost text widget
                # Sort by row first (top), then by col (left)
                text_widgets.sort(key=lambda w: (w['row'], w['col']))
                top_left_text_widget = text_widgets[0]
                
                # Check if this widget has content (indicating it's being used as description)
                widget_data = top_left_text_widget['widget']
                widget_text = widget_data.get('text', '').strip()
                
                if widget_text:
                    features['curation_score'] = 1.0  # Full point for description
                else:
                    features['curation_score'] = 0.5  # Half point for having text widget but no content
            else:
                features['curation_score'] = 0.0  # No text widgets found
    
    def _calculate_final_dashboard_scores(self, dashboard_features: List[Dict[str, Any]]) -> None:
        """
        Phase 3.3: Final Dashboard Score Calculation and Storage
        
        Combine component scores into final golden_dashboard_score and ensure all scores 
        are stored in the feature dictionary.
        
        Args:
            dashboard_features: List of dashboard feature dictionaries (modified in place)
        """
        logger.info("Phase 3.3: Calculating final dashboard scores...")
        
        for features in dashboard_features:
            # Get component scores (should already be calculated)
            content_quality_score = features.get('content_quality_score', 0)
            recency_score = features.get('recency_score', 0)
            curation_score = features.get('curation_score', 0)
            
            # Calculate final golden dashboard score (Phase 3 requirement)
            golden_dashboard_score = content_quality_score + recency_score + curation_score
            features['golden_dashboard_score'] = golden_dashboard_score
    
    def score_all_dashboards(self, scored_queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Main method for Phase 3: Golden Dashboard Scoring Logic
        
        Executes all steps of dashboard scoring:
        1. Raw feature assembly
        2. Component score calculations (Content Quality, Recency, Curation)
        3. Final score calculation and storage
        
        Args:
            scored_queries: List of scored query dictionaries from Phase 2 (needed for content quality scoring)
        
        Returns:
            List of fully scored dashboard feature dictionaries
        """
        logger.info("Starting Phase 3: Golden Dashboard Scoring Logic")
        
        if not self.detailed_dashboards:
            logger.warning("No detailed dashboards available for scoring. Run extract_all_metadata() first.")
            return []
        
        # Phase 3.1: Raw Feature Assembly
        dashboard_features = self._assemble_dashboard_features(self.detailed_dashboards)
        
        if not dashboard_features:
            logger.warning("No dashboard features assembled")
            return []
        
        # Phase 3.2: Component Score Calculations
        self._calculate_dashboard_content_quality_score(dashboard_features, scored_queries)
        self._calculate_dashboard_recency_score(dashboard_features)
        self._calculate_dashboard_curation_score(dashboard_features)
        
        # Phase 3.3: Final Score Calculation
        self._calculate_final_dashboard_scores(dashboard_features)
        
        # Sort by golden score for easier analysis
        dashboard_features.sort(key=lambda x: x.get('golden_dashboard_score', 0), reverse=True)
        
        logger.info("Phase 3 completed: Scored %d dashboards", len(dashboard_features))
        logger.info("Top dashboard score: %.2f", dashboard_features[0].get('golden_dashboard_score', 0) if dashboard_features else 0)
        
        return dashboard_features

    # ==================================================================================
    # PHASE 4: FINAL OUTPUT GENERATION
    # ==================================================================================
    
    def generate_outputs(self, scored_queries: List[Dict[str, Any]], 
                        scored_dashboards: List[Dict[str, Any]], 
                        output_dir: str = ".") -> Dict[str, str]:
        """
        Phase 4: Final Output Generation
        
        Saves the ranked lists of golden queries and dashboards into both CSV and JSON files,
        ensuring all component scores are included for full transparency.
        
        Args:
            scored_queries: List of scored query feature dictionaries from Phase 2
            scored_dashboards: List of scored dashboard feature dictionaries from Phase 3  
            output_dir: Directory to save output files (defaults to current directory)
            
        Returns:
            Dictionary containing paths to generated files
        """
        logger.info("Starting Phase 4: Final Output Generation")
        
        if pd is None:
            logger.error("pandas is required for output generation. Install with: pip install pandas")
            raise ImportError("pandas is required for Phase 4. Please install pandas.")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        generated_files = {}
        
        # Generate query outputs
        if scored_queries:
            query_files = self._generate_query_outputs(scored_queries, output_dir)
            generated_files.update(query_files)
        else:
            logger.warning("No scored queries provided for output generation")
        
        # Generate dashboard outputs  
        if scored_dashboards:
            dashboard_files = self._generate_dashboard_outputs(scored_dashboards, output_dir)
            generated_files.update(dashboard_files)
        else:
            logger.warning("No scored dashboards provided for output generation")
        
        # Log completion summary
        logger.info("Phase 4 completed successfully!")
        logger.info("Generated files:")
        for file_type, file_path in generated_files.items():
            logger.info("  - %s: %s", file_type, file_path)
        
        return generated_files
    
    def _generate_query_outputs(self, scored_queries: List[Dict[str, Any]], 
                               output_dir: str) -> Dict[str, str]:
        """
        Generate CSV and JSON outputs for scored queries (Phase 4 requirement)
        
        Args:
            scored_queries: List of scored query dictionaries
            output_dir: Directory to save output files
            
        Returns:
            Dictionary mapping output types to file paths
        """
        logger.info("Generating query outputs...")
        
        # Step 1: Create DataFrame (Phase 4 requirement)
        queries_df = pd.DataFrame(scored_queries)
        
        # Step 2: Sort by golden score in descending order (Phase 4 requirement)
        queries_df = queries_df.sort_values(by='golden_query_score', ascending=False)
        
        # Step 3: Define CSV column order (Phase 4 requirement - exact specification from plan)
        query_column_order = [
            'id', 'name', 'golden_query_score', 'impact_score', 'recency_score', 
            'curation_score', 'downstream_dashboard_count', 'downstream_chart_count',
            'user_name', 'last_executed_at', 'created_at', 'query'
        ]
        
        # Filter columns to only include those that exist in the DataFrame
        available_columns = [col for col in query_column_order if col in queries_df.columns]
        
        # Step 4: Write CSV file (Phase 4 requirement)
        csv_path = os.path.join(output_dir, 'golden_queries_output.csv')
        queries_df[available_columns].to_csv(csv_path, index=False, quoting=csv.QUOTE_ALL)
        logger.info("Generated queries CSV: %s (%d queries)", csv_path, len(queries_df))
        
        # Step 5: Write JSON file (Phase 4 requirement)
        json_path = os.path.join(output_dir, 'golden_queries_output.json')
        queries_df.to_json(json_path, orient='records', indent=2, date_format='iso')
        logger.info("Generated queries JSON: %s (%d queries)", json_path, len(queries_df))
        
        return {
            'queries_csv': csv_path,
            'queries_json': json_path
        }
    
    def _generate_dashboard_outputs(self, scored_dashboards: List[Dict[str, Any]], 
                                   output_dir: str) -> Dict[str, str]:
        """
        Generate CSV and JSON outputs for scored dashboards (Phase 4 requirement)
        
        Args:
            scored_dashboards: List of scored dashboard dictionaries
            output_dir: Directory to save output files
            
        Returns:
            Dictionary mapping output types to file paths
        """
        logger.info("Generating dashboard outputs...")
        
        # Step 1: Create DataFrame (Phase 4 requirement)
        dashboards_df = pd.DataFrame(scored_dashboards)
        
        # Step 2: Sort by golden score in descending order (Phase 4 requirement)
        dashboards_df = dashboards_df.sort_values(by='golden_dashboard_score', ascending=False)
        
        # Step 3: Define CSV column order (Phase 4 requirement - exact specification from plan)
        dashboard_column_order = [
            'id', 'name', 'golden_dashboard_score', 'content_quality_score', 
            'recency_score', 'curation_score', 'user_name', 'updated_at', 'created_at'
        ]
        
        # Filter columns to only include those that exist in the DataFrame
        available_columns = [col for col in dashboard_column_order if col in dashboards_df.columns]
        
        # Step 4: Write CSV file (Phase 4 requirement)
        csv_path = os.path.join(output_dir, 'golden_dashboards_output.csv')
        dashboards_df[available_columns].to_csv(csv_path, index=False, quoting=csv.QUOTE_ALL)
        logger.info("Generated dashboards CSV: %s (%d dashboards)", csv_path, len(dashboards_df))
        
        # Step 5: Write JSON file (Phase 4 requirement)
        json_path = os.path.join(output_dir, 'golden_dashboards_output.json')
        dashboards_df.to_json(json_path, orient='records', indent=2, date_format='iso')
        logger.info("Generated dashboards JSON: %s (%d dashboards)", json_path, len(dashboards_df))
        
        return {
            'dashboards_csv': csv_path,
            'dashboards_json': json_path
        }
    
    async def run_complete_analysis(self, output_dir: str = ".") -> Dict[str, Any]:
        """
        Complete end-to-end Golden Asset Ranking System analysis
        
        Runs all phases:
        1. Phase 1: Extract metadata and build dependency maps
        2. Phase 2: Score all queries 
        3. Phase 3: Score all dashboards
        4. Phase 4: Generate CSV and JSON outputs
        
        Args:
            output_dir: Directory to save output files
            
        Returns:
            Complete results dictionary with all phase data and file paths
        """
        logger.info("Starting complete Golden Asset Ranking System analysis")
        
        # Phase 1: Extract metadata
        phase1_results = await self.extract_all_metadata()
        if "error" in phase1_results:
            return phase1_results
        
        # Phase 2: Score queries
        scored_queries = self.score_all_queries()
        
        # Phase 3: Score dashboards
        scored_dashboards = self.score_all_dashboards(scored_queries)
        
        # Phase 4: Generate outputs
        generated_files = self.generate_outputs(scored_queries, scored_dashboards, output_dir)
        
        # Compile complete results
        complete_results = {
            "phase1": phase1_results,
            "phase2": {
                "scored_queries_count": len(scored_queries),
                "top_query_score": scored_queries[0].get('golden_query_score', 0) if scored_queries else 0
            },
            "phase3": {
                "scored_dashboards_count": len(scored_dashboards),
                "top_dashboard_score": scored_dashboards[0].get('golden_dashboard_score', 0) if scored_dashboards else 0
            },
            "phase4": {
                "generated_files": generated_files,
                "output_directory": output_dir
            }
        }
        
        logger.info("Complete Golden Asset Ranking System analysis finished successfully!")
        return complete_results

    async def extract_all_metadata(self) -> Dict[str, Any]:
        """
        Phase 1: Concurrent metadata ingestion and dependency mapping
        
        This is the main method that implements the Phase 1 requirements:
        1. Secure configuration and connection (done in __init__)
        2. Robust version detection
        3. Concurrent metadata ingestion with dependency mapping
        """
        logger.info("Starting Phase 1: Foundational Layer - High-Performance Data Extraction")
        
        # Test connection first
        success, message = await self.test_connection()
        if not success:
            return {"error": message}
        
        # Detect version
        await self._detect_version()
        
        # Step 1: Fetch master lists concurrently (Phase 1 requirement)
        logger.info("Step 1: Fetching master lists concurrently...")
        dashboards_task = self.get_all_dashboards()
        queries_task = self.get_all_queries()
        
        dashboards, queries = await asyncio.gather(dashboards_task, queries_task)
        
        # Step 2: Fetch detailed objects with limited concurrency (Phase 1 requirement)
        logger.info("Step 2: Fetching detailed objects with limited concurrency...")
        logger.info("Using max %d concurrent requests to avoid overwhelming server", self.max_concurrent_requests)
        
        # Fetch detailed dashboards with concurrency limit
        logger.info("Fetching detailed data for %d dashboards...", len(dashboards))
        detailed_dashboards_tasks = [self._get_detailed_dashboard(d) for d in dashboards]
        detailed_dashboards_results = await asyncio.gather(*detailed_dashboards_tasks, return_exceptions=True)
        
        # Filter successful results and count failures
        detailed_dashboards = [d for d in detailed_dashboards_results if d and not isinstance(d, Exception)]
        failed_dashboards = sum(1 for d in detailed_dashboards_results if isinstance(d, Exception))
        self.detailed_dashboards = detailed_dashboards
        
        if failed_dashboards > 0:
            logger.warning("Failed to fetch %d dashboard(s) due to network/server issues", failed_dashboards)
        
        # Fetch detailed queries with concurrency limit  
        logger.info("Fetching detailed data for %d queries...", len(queries))
        detailed_queries_tasks = [self._get_detailed_query(q) for q in queries]
        detailed_queries_results = await asyncio.gather(*detailed_queries_tasks, return_exceptions=True)
        
        # Filter successful results and count failures
        detailed_queries = [q for q in detailed_queries_results if q and not isinstance(q, Exception)]
        failed_queries = sum(1 for q in detailed_queries_results if isinstance(q, Exception))
        self.detailed_queries = detailed_queries
        
        if failed_queries > 0:
            logger.warning("Failed to fetch %d query(s) due to network/server issues", failed_queries)
        
        logger.info("Successfully fetched %d/%d detailed dashboards", len(detailed_dashboards), len(dashboards))
        logger.info("Successfully fetched %d/%d detailed queries", len(detailed_queries), len(queries))
        
        # Step 3: Build dependency maps (Phase 1 requirement)
        self._build_dependency_maps(detailed_dashboards)
        
        # Return summary
        results = {
            "phase": 1,
            "phase_name": "Foundational Layer - High-Performance Data Extraction",
            "connection_test": {"success": True, "message": message},
            "version": self.redash_version,
            "use_slug_for_dashboards": self.use_slug_for_dashboards,
            "counts": {
                "dashboards": len(dashboards),
                "detailed_dashboards": len(detailed_dashboards),
                "queries": len(queries),
                "detailed_queries": len(detailed_queries)
            },
            "dependency_maps": {
                "queries_with_dashboard_deps": len(self.query_to_dashboards_map),
                "queries_with_chart_widgets": len(self.query_to_charts_map),
                "dashboards_with_queries": len(self.dashboard_to_queries_map)
            }
        }
        
        logger.info("Phase 1 completed successfully!")
        return results
