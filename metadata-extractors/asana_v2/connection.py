import httpx
import asyncio
import logging
import os
from typing import Dict

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Reduce noise from httpx - only log errors
logging.getLogger("httpx").setLevel(logging.WARNING)

class AsanaConnection:
    """Handles connection and API requests to Asana with automatic token refresh"""
    
    def __init__(self, credentials: Dict[str, str]):
        """
        Initialize Asana connection with credentials.
        
        Args:
            credentials: Dictionary containing 'access_token' and optionally 'refresh_token'
        """
        self.access_token = credentials.get("access_token")
        self.refresh_token = credentials.get("refresh_token")
        
        if not self.access_token:
            raise ValueError("access_token is required in credentials")
            
        self.base_url = "https://app.asana.com/api/1.0"
        
        # Create async HTTP client
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            },
            timeout=httpx.Timeout(30.0)
        )
        
        # Async lock for token refresh
        self._refresh_lock = asyncio.Lock()
        self._refresh_in_progress = False
        self._refresh_complete_event = asyncio.Event()
        
        # Asana OAuth endpoint for token refresh
        self.token_url = "https://app.asana.com/-/oauth_token"
        
        # OAuth client credentials from environment variables
        self.client_id = os.getenv("ASANA_CLIENT_ID")
        self.client_secret = os.getenv("ASANA_CLIENT_SECRET")
        
        if self.client_id and self.client_secret:
            logger.info("✓ OAuth client credentials loaded - refresh token functionality available")
        else:
            logger.warning("⚠️  OAuth client credentials not found - refresh token functionality disabled")
            logger.info("   Set ASANA_CLIENT_ID and ASANA_CLIENT_SECRET environment variables to enable token refresh")
    
    def _update_auth_header(self):
        """Update the authorization header with current access token"""
        self.client.headers.update({
            "Authorization": f"Bearer {self.access_token}"
        })
    
    async def _refresh_access_token(self) -> bool:
        """
        Refresh the access token using the refresh token.
        
        Returns:
            bool: True if refresh was successful, False otherwise
        """
        if not self.refresh_token:
            logger.error("No refresh token available for token refresh")
            return False
            
        if not self.client_id or not self.client_secret:
            logger.error("Asana client credentials not configured - cannot refresh token")
            return False
        
        # Check if refresh is already in progress
        if self._refresh_in_progress:
            logger.info("Token refresh already in progress, waiting...")
            await self._refresh_complete_event.wait()
            return True
        
        try:
            self._refresh_in_progress = True
            self._refresh_complete_event.clear()
            logger.info("Attempting to refresh Asana access token...")
            
            refresh_data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            async with httpx.AsyncClient() as temp_client:
                response = await temp_client.post(
                    self.token_url,
                    data=refresh_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0
                )
            
            if response.status_code == 200:
                token_data = response.json()
                new_access_token = token_data.get("access_token")
                new_refresh_token = token_data.get("refresh_token")
                
                if not new_access_token:
                    logger.error("No access_token in refresh response")
                    return False
                
                # Update tokens
                self.access_token = new_access_token
                if new_refresh_token:
                    self.refresh_token = new_refresh_token
                
                # Update the client's authorization header
                self._update_auth_header()
                logger.info("Successfully refreshed Asana access token")
                return True
            else:
                logger.error("Token refresh failed: %s - %s", response.status_code, response.text)
                return False
                
        except Exception as e:
            logger.error("Exception during token refresh: %s", e)
            return False
        finally:
            self._refresh_in_progress = False
            self._refresh_complete_event.set()
    
    async def make_authenticated_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        Make an authenticated request with automatic token refresh on 401.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional arguments to pass to httpx
            
        Returns:
            httpx.Response: The response object
        """
        max_retries = 3
        attempt = 0
        
        while attempt < max_retries:
            try:
                # Make the request
                response = await self.client.request(method, url, **kwargs)
                
                if response.status_code == 404:
                    logger.error("Received 404 Not Found for %s", url)
                    return response
                
                # If we get a 401, try to refresh the token and retry
                if response.status_code == 401:
                    attempt += 1
                    logger.info("Received 401 Unauthorized, attempting token refresh (attempt %s/%s)", attempt, max_retries)
                    
                    async with self._refresh_lock:
                        if self._refresh_in_progress:
                            logger.info("Token refresh already in progress by another coroutine, waiting...")
                            while self._refresh_in_progress:
                                await asyncio.sleep(0.1)
                            logger.info("Other coroutine completed token refresh, retrying request...")
                        else:
                            if await self._refresh_access_token():
                                logger.info("Token refreshed successfully, retrying request...")
                            else:
                                logger.error("Token refresh failed, request will fail")
                                return response
                    
                    if attempt >= max_retries:
                        logger.error("Request failed after maximum retry attempts - credentials may be invalid")
                        return response
                    
                    continue
                
                # Request was successful or had a non-401 error
                return response
                
            except Exception as e:
                attempt += 1
                logger.error("Error making authenticated request to %s (attempt %s/%s): %s", url, attempt, max_retries, e)
                
                if attempt >= max_retries:
                    logger.error("Failed to make request after %s attempts", max_retries)
                    raise
                else:
                    await asyncio.sleep(1.0)
                    continue
        
        raise RuntimeError("Failed to make request after %s attempts" % max_retries)
    
    async def test_connection(self) -> bool:
        """Test if the connection is working by fetching current user info"""
        try:
            response = await self.make_authenticated_request("GET", self.base_url + "/users/me")
            if response.status_code == 200:
                user_data = response.json()
                logger.info("Asana connection test successful. Connected as: %s", user_data.get('data', {}).get('name', 'Unknown'))
                return True
            else:
                logger.error("Asana connection test failed: %s - %s", response.status_code, response.text)
                return False
        except Exception as e:
            logger.error("Asana connection test failed with exception: %s", e)
            return False
    
    async def close(self) -> None:
        """Close the connection and clean up resources"""
        if hasattr(self, 'client') and self.client:
            await self.client.aclose()
            self.client = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
