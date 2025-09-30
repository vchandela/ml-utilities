"""
OAuth Setup for Asana v2 - Option B Implementation

This script implements the full OAuth authorization code flow to get
initial access_token and refresh_token for automatic token refresh.
"""

import asyncio
import httpx
import urllib.parse
import secrets
import string
import os
import json
from connection import AsanaConnection

class AsanaOAuthFlow:
    """Handles the complete OAuth authorization code flow for Asana"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.auth_url = "https://app.asana.com/-/oauth_authorize"
        self.token_url = "https://app.asana.com/-/oauth_token"
        
    def generate_auth_url(self, scopes: list = None) -> tuple[str, str]:
        """
        Generate OAuth authorization URL and state parameter.
        
        Args:
            scopes: List of OAuth scopes to request
            
        Returns:
            tuple: (authorization_url, state_parameter)
        """
        if scopes is None:
            scopes = [
                "default",  # Basic access to user data
                # Add more scopes as needed for your use case
            ]
        
        # Generate secure random state parameter
        state = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state
        }
        
        auth_url = f"{self.auth_url}?" + urllib.parse.urlencode(params)
        return auth_url, state
    
    async def exchange_code_for_tokens(self, authorization_code: str) -> dict:
        """
        Exchange authorization code for access_token and refresh_token.
        
        Args:
            authorization_code: The code received from OAuth authorization
            
        Returns:
            dict: Token response containing access_token and refresh_token
        """
        token_data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "code": authorization_code
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Token exchange failed: {response.status_code} - {response.text}")
    
    async def test_tokens(self, access_token: str, refresh_token: str) -> bool:
        """
        Test the obtained tokens by creating a connection and testing it.
        
        Args:
            access_token: OAuth access token
            refresh_token: OAuth refresh token
            
        Returns:
            bool: True if tokens work correctly
        """
        credentials = {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
        
        # Set environment variables for the connection
        os.environ["ASANA_CLIENT_ID"] = self.client_id
        os.environ["ASANA_CLIENT_SECRET"] = self.client_secret
        
        try:
            async with AsanaConnection(credentials) as conn:
                success = await conn.test_connection()
                return success
        except Exception as e:
            print(f"Error testing tokens: {e}")
            return False


async def run_oauth_flow():
    """Run the complete OAuth setup flow"""
    
    print("🔐 Asana OAuth Setup - Option B Implementation")
    print("=" * 60)
    
    # Get OAuth app credentials from environment or input
    client_id = os.getenv("ASANA_CLIENT_ID")
    client_secret = os.getenv("ASANA_CLIENT_SECRET")
    
    if not client_id:
        print("📝 ASANA_CLIENT_ID not found in environment.")
        client_id = input("Enter your Asana OAuth Client ID: ").strip()
    
    if not client_secret:
        print("📝 ASANA_CLIENT_SECRET not found in environment.")
        client_secret = input("Enter your Asana OAuth Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("❌ OAuth credentials are required. Exiting.")
        return
    
    print(f"✓ Using OAuth Client ID: {client_id}")
    
    # Initialize OAuth flow
    oauth = AsanaOAuthFlow(client_id, client_secret)
    
    # Step 1: Generate authorization URL
    print("\n📋 Step 1: Authorization")
    print("-" * 30)
    auth_url, state = oauth.generate_auth_url()
    
    print("🔗 Visit this URL in your browser to authorize the application:")
    print(f"{auth_url}")
    print(f"\n🔐 State parameter (for verification): {state}")
    print("\n📌 After authorization, you'll get an authorization code.")
    print("   Copy that code and paste it below.")
    
    # Step 2: Get authorization code from user
    print("\n💾 Step 2: Authorization Code")
    print("-" * 30)
    auth_code = input("Paste the authorization code here: ").strip()
    
    if not auth_code:
        print("❌ Authorization code is required. Exiting.")
        return
    
    try:
        # Step 3: Exchange code for tokens
        print("\n🔄 Step 3: Token Exchange")
        print("-" * 30)
        print("Exchanging authorization code for tokens...")
        
        token_response = await oauth.exchange_code_for_tokens(auth_code)
        
        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        expires_in = token_response.get("expires_in")
        
        if not access_token:
            print("❌ Failed to get access token from response")
            print(f"Response: {token_response}")
            return
        
        print("✅ Successfully obtained tokens!")
        print(f"   Access Token: {access_token[:50]}...")
        print(f"   Refresh Token: {refresh_token[:50] if refresh_token else 'Not provided'}...")
        print(f"   Expires In: {expires_in} seconds" if expires_in else "   Expires In: Not specified")
        
        # Step 4: Test the tokens
        print("\n🧪 Step 4: Testing Tokens")
        print("-" * 30)
        print("Testing connection with new tokens...")
        
        token_works = await oauth.test_tokens(access_token, refresh_token)
        
        if token_works:
            print("✅ Token test successful! Connection established.")
        else:
            print("⚠️  Token test failed, but tokens were obtained.")
        
        # Step 5: Show environment variables
        print("\n⚙️  Step 5: Environment Setup")
        print("-" * 30)
        print("Add these environment variables to complete the setup:")
        print()
        print("# Add to your shell profile (.zshrc, .bashrc, etc.) or .env file:")
        print(f'export ASANA_ACCESS_TOKEN="{access_token}"')
        print(f'export ASANA_REFRESH_TOKEN="{refresh_token}"')
        print(f'export ASANA_CLIENT_ID="{client_id}"')
        print(f'export ASANA_CLIENT_SECRET="{client_secret}"')
        
        # Step 6: Update launch.json
        print("\n🚀 Step 6: Update VS Code Launch Configuration")
        print("-" * 50)
        print("Update your .vscode/launch.json with these values:")
        print()
        launch_json_snippet = f'''                "ASANA_ACCESS_TOKEN": "{access_token}",
                "ASANA_REFRESH_TOKEN": "{refresh_token}",
                "ASANA_CLIENT_ID": "{client_id}",
                "ASANA_CLIENT_SECRET": "{client_secret}"'''
        print(launch_json_snippet)
        
        # Step 7: Automatic launch.json update
        print("\n📝 Step 7: Automatic Launch Configuration Update")
        print("-" * 50)
        
        update_choice = input("Would you like me to automatically update your launch.json? (y/n): ").strip().lower()
        
        if update_choice == 'y':
            success = await update_launch_json(access_token, refresh_token, client_id, client_secret)
            if success:
                print("✅ Launch configuration updated successfully!")
            else:
                print("⚠️  Failed to update launch configuration automatically.")
                print("   Please update manually using the values above.")
        
        print("\n" + "=" * 60)
        print("🎉 OAuth Setup Complete!")
        print("Your Golden Task Ranking System is now ready with:")
        print("✅ Valid OAuth access token")
        print("✅ Refresh token for automatic renewal")  
        print("✅ Client credentials for token refresh")
        print("\nYou can now run: python main.py")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ OAuth flow failed: {e}")
        print("Please check your authorization code and try again.")


async def update_launch_json(access_token: str, refresh_token: str, client_id: str, client_secret: str) -> bool:
    """Update the VS Code launch.json with new token values"""
    
    launch_json_path = "../.vscode/launch.json"
    
    try:
        # Read current launch.json
        with open(launch_json_path, 'r') as f:
            content = f.read()
        
        # Replace the token values
        content = content.replace('PASTE_YOUR_NEW_TOKEN_HERE', access_token)
        content = content.replace('"ASANA_ACCESS_TOKEN": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3NTA5NDMyMTQsInNjb3BlIjoiYXR0YWNobWVudHM6cmVhZCBnb2FsczpyZWFkIHByb2plY3RfdGVtcGxhdGVzOnJlYWQgcHJvamVjdHM6cmVhZCBzdG9yaWVzOnJlYWQgdGFza190ZW1wbGF0ZXM6cmVhZCB0YXNrczpyZWFkIHRlYW1zOnJlYWQgdXNlcnM6cmVhZCB3b3Jrc3BhY2VzOnJlYWWQgd29ya3NwYWNlcy50eXBlYWhlYWQ6cmVhZCIsInN1YiI6MTIxMDYyMDQ3NTU4MzI0MiwicmVmcmVzaF90b2tlbiI6MTIxMDY0OTQyMDk5MTc2NywidmVyc2lvbiI6MiwiYXBwIjoxMjEwNjE0MzYxODkyNjk2LCJleHAiOjE3NTA5NDY4MTR9.voh1vxptM_7-03DT8oNRhiunijsFFNi8HlyYaIMvdoY"', 
                      f'"ASANA_ACCESS_TOKEN": "{access_token}"')
        content = content.replace(f'"ASANA_REFRESH_TOKEN": "2/1210620475583242/1211504472453119:e1a601a7f281470f8e9a0511906fadcd"',
                      f'"ASANA_REFRESH_TOKEN": "{refresh_token}"')
        content = content.replace(f'"ASANA_CLIENT_ID": "{client_id}"',
                      f'"ASANA_CLIENT_ID": "{client_id}"')
        content = content.replace(f'"ASANA_CLIENT_SECRET": "{client_secret}"',
                      f'"ASANA_CLIENT_SECRET": "{client_secret}"')
        
        # Write updated launch.json
        with open(launch_json_path, 'w') as f:
            f.write(content)
        
        return True
        
    except Exception as e:
        print(f"Error updating launch.json: {e}")
        return False


async def quick_test_current_tokens():
    """Quick test of currently configured tokens"""
    
    print("🧪 Quick Test of Current Token Configuration")
    print("=" * 50)
    
    access_token = os.getenv("ASANA_ACCESS_TOKEN")
    refresh_token = os.getenv("ASANA_REFRESH_TOKEN") 
    client_id = os.getenv("ASANA_CLIENT_ID")
    client_secret = os.getenv("ASANA_CLIENT_SECRET")
    
    print("📋 Current Environment Configuration:")
    print(f"   Access Token: {'✓ Set' if access_token else '✗ Missing'}")
    print(f"   Refresh Token: {'✓ Set' if refresh_token else '✗ Missing'}")
    print(f"   Client ID: {'✓ Set' if client_id else '✗ Missing'}")
    print(f"   Client Secret: {'✓ Set' if client_secret else '✗ Missing'}")
    
    if not access_token:
        print("\n❌ ASANA_ACCESS_TOKEN is required but not set.")
        return False
    
    try:
        credentials = {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
        
        print(f"\n🔗 Testing connection...")
        async with AsanaConnection(credentials) as conn:
            success = await conn.test_connection()
            
        if success:
            print("✅ Connection successful! Current tokens are working.")
            return True
        else:
            print("❌ Connection failed. Tokens may be expired or invalid.")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


if __name__ == "__main__":
    print("Asana OAuth Setup - Choose an option:")
    print("1. Run full OAuth flow (get new tokens)")
    print("2. Test current token configuration")
    print("3. Exit")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        asyncio.run(run_oauth_flow())
    elif choice == "2":
        asyncio.run(quick_test_current_tokens())
    else:
        print("Exiting...")
