import os
from typing import Dict, Any, List

# Bot configuration
BOT_CONFIG: Dict[str, Any] = {
    # Customize the bot's status message
    "status": "Roblox Community",
    
    # Default cooldowns for commands (in seconds)
    "cooldowns": {
        "verify": 30,
        "update": 60,
        "info-roblox": 5,
        "host": 30,
        "announce": 30,
        "sendticket": 120,
        "setupticket": 30
    },
    
    # Embed colors
    "colors": {
        "primary": 0x5865F2,  # Discord Blurple
        "success": 0x57F287,  # Green
        "error": 0xED4245,    # Red
        "warning": 0xFEE75C,  # Yellow
        "info": 0x5865F2      # Blue
    },
    
    # Custom emojis (if used)
    "emojis": {
        "verify": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
        "ticket": "🎫"
    }
}

# Verification system configuration
VERIFICATION_CONFIG: Dict[str, Any] = {
    # Whether to update nickname on verification
    "update_nickname": True,
    
    # Whether to assign a role on verification
    "assign_role": True,
    
    # Default format for nicknames (supports placeholders: {roblox_name}, {discord_name})
    "nickname_format": "{roblox_name}"
}

# Ticket system configuration
TICKET_CONFIG: Dict[str, Any] = {
    # Default ticket message title
    "ticket_title": "🎫 Support Ticket System",
    
    # Default ticket message content
    "ticket_description": (
        "Need assistance? Click the button below to create a ticket!\n\n"
        "Our support team will help you as soon as possible.\n\n"
        "**Please Note:**\n"
        "• Only open a ticket if you have a legitimate issue\n"
        "• Be patient and respectful to our staff\n"
        "• Provide as much detail as possible about your issue"
    ),
    
    # Default name format for ticket channels
    "ticket_channel_format": "ticket-{username}"
}
