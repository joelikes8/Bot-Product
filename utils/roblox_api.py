import os
import aiohttp
import logging
import re
import json
from typing import Dict, Any, Optional, List, Union

# Setup logging
logger = logging.getLogger('discord_bot.roblox_api')

# Constants
ROBLOX_API_BASE = "https://api.roblox.com"
ROBLOX_USERS_API_BASE = "https://users.roblox.com"
ROBLOX_THUMBNAILS_API = "https://thumbnails.roblox.com"

async def get_roblox_user(username: str) -> Optional[Dict[str, Any]]:
    """
    Get Roblox user information by username
    
    Args:
        username: The Roblox username to look up
    
    Returns:
        Dict containing user information or None if not found
    """
    try:
        async with aiohttp.ClientSession() as session:
            # First get the user ID from the username
            async with session.post(
                f"{ROBLOX_USERS_API_BASE}/v1/usernames/users",
                json={"usernames": [username], "excludeBannedUsers": False}
            ) as response:
                if response.status != 200:
                    logger.error(f"Failed to get Roblox user ID: {response.status}")
                    return None
                
                data = await response.json()
                if not data.get("data") or len(data["data"]) == 0:
                    logger.info(f"No Roblox user found with username: {username}")
                    return None
                
                user_data = data["data"][0]
                user_id = user_data["id"]
                
                # Now get more detailed user information
                async with session.get(f"{ROBLOX_USERS_API_BASE}/v1/users/{user_id}") as detail_response:
                    if detail_response.status != 200:
                        logger.error(f"Failed to get Roblox user details: {detail_response.status}")
                        return user_data
                    
                    user_details = await detail_response.json()
                    
                    # Merge the user data
                    user_data.update(user_details)
                    
                    return user_data
    
    except Exception as e:
        logger.error(f"Error getting Roblox user: {e}")
        return None

async def verify_roblox_user(roblox_id: int, verification_code: str) -> bool:
    """
    Verify if a Roblox user has the verification code in their profile
    
    Args:
        roblox_id: The Roblox user ID
        verification_code: The verification code to check for
        
    Returns:
        True if verified, False otherwise
    """
    try:
        async with aiohttp.ClientSession() as session:
            # Get user's profile description
            async with session.get(f"{ROBLOX_USERS_API_BASE}/v1/users/{roblox_id}") as response:
                if response.status != 200:
                    logger.error(f"Failed to get Roblox user profile: {response.status}")
                    return False
                
                data = await response.json()
                description = data.get("description", "")
                
                # Check if verification code is in the description
                return verification_code in description
    
    except Exception as e:
        logger.error(f"Error verifying Roblox user: {e}")
        return False

async def get_roblox_avatar(roblox_id: int) -> Optional[str]:
    """
    Get the Roblox user's avatar URL
    
    Args:
        roblox_id: The Roblox user ID
        
    Returns:
        Avatar URL or None if failed
    """
    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "userIds": roblox_id,
                "size": "420x420",
                "format": "Png",
                "isCircular": "false"
            }
            
            async with session.get(
                f"{ROBLOX_THUMBNAILS_API}/v1/users/avatar-headshot",
                params=params
            ) as response:
                if response.status != 200:
                    logger.error(f"Failed to get Roblox avatar: {response.status}")
                    return None
                
                data = await response.json()
                if not data.get("data") or len(data["data"]) == 0:
                    return None
                
                return data["data"][0]["imageUrl"]
    
    except Exception as e:
        logger.error(f"Error getting Roblox avatar: {e}")
        return None

async def get_roblox_username_from_id(roblox_id: int) -> Optional[str]:
    """
    Get Roblox username from user ID
    
    Args:
        roblox_id: The Roblox user ID
        
    Returns:
        Username or None if failed
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ROBLOX_API_BASE}/users/{roblox_id}") as response:
                if response.status != 200:
                    logger.error(f"Failed to get Roblox username: {response.status}")
                    return None
                
                data = await response.json()
                return data.get("Username")
    
    except Exception as e:
        logger.error(f"Error getting Roblox username: {e}")
        return None
