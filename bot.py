import os
import discord
import logging
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import asyncio
import config

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('discord_bot')

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class RobloxBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or('!'),
            intents=intents,
            application_id=os.getenv('APPLICATION_ID')
        )
        self.synced = False
        
    async def setup_hook(self):
        # Load all cogs
        for cog_file in ["verification", "announcements", "tickets", "moderation", "verification_ticket"]:
            try:
                await self.load_extension(f"cogs.{cog_file}")
                logger.info(f"Loaded cog: {cog_file}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog_file}: {e}")
        
        # Database initialization
        try:
            from utils.database import create_tables
            await create_tables()
            logger.info("Database tables initialized")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    async def on_ready(self):
        await self.wait_until_ready()
        if not self.synced:
            # Sync slash commands
            await self.tree.sync()
            self.synced = True
            
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guilds')
        logger.info(f'Bot is ready!')
        
        # Set custom status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Roblox Community"
            )
        )

bot = RobloxBot()

# Error handling for slash commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.",
            ephemeral=True
        )
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "You don't have the required permissions to use this command.",
            ephemeral=True
        )
    else:
        logger.error(f"Command error: {error}")
        await interaction.response.send_message(
            "An error occurred while executing this command. Please try again later.",
            ephemeral=True
        )

if __name__ == "__main__":
    # Run the bot with the token from environment variables
    bot.run(os.getenv('DISCORD_TOKEN'))
