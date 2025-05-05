import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import logging
import re
import os
import random
import string
from utils.database import execute_query, fetch_query
from utils.embed_builder import create_embed
from utils.roblox_api import get_roblox_user, verify_roblox_user

logger = logging.getLogger('discord_bot.verification')

class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="verify", description="Verify your Roblox account with Discord")
    @app_commands.describe(roblox_username="Your Roblox username")
    async def verify(self, interaction: discord.Interaction, roblox_username: str):
        """Verify a user's Roblox account and link it to their Discord account"""
        await interaction.response.defer(ephemeral=True)
        
        discord_id = interaction.user.id
        discord_username = str(interaction.user)
        
        # Check if user is already verified
        existing_user = await fetch_query(
            "SELECT roblox_id FROM verified_users WHERE discord_id = $1",
            discord_id
        )
        
        if existing_user:
            await interaction.followup.send(
                "You are already verified! If you want to change your account, use `/update` command.",
                ephemeral=True
            )
            return
        
        # Get Roblox user info
        roblox_user = await get_roblox_user(roblox_username)
        if not roblox_user:
            await interaction.followup.send(
                f"Could not find a Roblox user with username: `{roblox_username}`",
                ephemeral=True
            )
            return
        
        roblox_id = roblox_user["id"]
        roblox_display_name = roblox_user["displayName"]
        
        # Generate random verification code like "Verify-L6AQ"
        random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        verification_code = f"Verify-{random_code}"
        
        verify_embed = create_embed(
            title="Verification Process",
            description=(
                f"To verify that you own the Roblox account **{roblox_display_name}** (@{roblox_username}), "
                f"please put the following code in your Roblox profile description:\n\n"
                f"```{verification_code}```\n\n"
                f"Once you've added this code, click the 'Verify' button below. "
                f"You can remove the code after verification is complete."
            ),
            color=discord.Color.blue()
        )
        
        verify_embed.set_thumbnail(url=f"https://www.roblox.com/bust-thumbnail/image?userId={roblox_id}&width=150&height=150")
        
        # Create verification button
        verify_button = discord.ui.Button(style=discord.ButtonStyle.green, label="Verify")
        cancel_button = discord.ui.Button(style=discord.ButtonStyle.red, label="Cancel")
        
        async def verify_callback(button_interaction):
            # Check if the verification code is in the profile
            is_verified = await verify_roblox_user(roblox_id, verification_code)
            
            if is_verified:
                # Store verification in database
                await execute_query(
                    """
                    INSERT INTO verified_users (discord_id, discord_username, roblox_id, roblox_username)
                    VALUES ($1, $2, $3, $4)
                    """,
                    discord_id, discord_username, roblox_id, roblox_username
                )
                
                # Try to give verified role if it exists
                try:
                    guild = button_interaction.guild
                    if guild:
                        verified_role_id = await fetch_query(
                            "SELECT verified_role_id FROM guild_settings WHERE guild_id = $1",
                            guild.id
                        )
                        
                        if verified_role_id:
                            verified_role = guild.get_role(verified_role_id[0]['verified_role_id'])
                            if verified_role:
                                await interaction.user.add_roles(verified_role)
                                
                        # Try to update nickname if we have permission
                        try:
                            await interaction.user.edit(nick=f"{roblox_display_name}")
                        except discord.Forbidden:
                            logger.warning(f"Could not update nickname for {interaction.user.id}")
                except Exception as e:
                    logger.error(f"Error giving verified role: {e}")
                
                success_embed = create_embed(
                    title="Verification Successful",
                    description=f"You have been verified as **{roblox_display_name}** (@{roblox_username})!",
                    color=discord.Color.green()
                )
                
                success_embed.set_thumbnail(url=f"https://www.roblox.com/bust-thumbnail/image?userId={roblox_id}&width=150&height=150")
                
                await button_interaction.response.edit_message(embed=success_embed, view=None)
            else:
                failure_embed = create_embed(
                    title="Verification Failed",
                    description=(
                        f"Could not find the verification code in your Roblox profile. "
                        f"Please make sure you added:\n\n"
                        f"```{verification_code}```\n\n"
                        f"to your profile description and try again, or click the button below to get help."
                    ),
                    color=discord.Color.red()
                )
                
                # Create help button view
                help_view = discord.ui.View()
                get_help_button = discord.ui.Button(
                    style=discord.ButtonStyle.primary, 
                    label="Get Help With Verification", 
                    emoji="🎫"
                )
                
                # Create the callback for the help button
                async def help_callback(help_interaction):
                    from cogs.verification_ticket import VerificationTicketView
                    ticket_view = VerificationTicketView(
                        roblox_username=roblox_username,
                        roblox_id=roblox_id,
                        verification_code=verification_code
                    )
                    await ticket_view.create_verification_support_ticket(help_interaction)
                
                get_help_button.callback = help_callback
                help_view.add_item(get_help_button)
                
                await button_interaction.response.edit_message(embed=failure_embed, view=help_view)
        
        async def cancel_callback(button_interaction):
            await button_interaction.response.edit_message(
                embed=create_embed(
                    title="Verification Cancelled",
                    description="You've cancelled the verification process.",
                    color=discord.Color.light_gray()
                ),
                view=None
            )
        
        verify_button.callback = verify_callback
        cancel_button.callback = cancel_callback
        
        view = discord.ui.View()
        view.add_item(verify_button)
        view.add_item(cancel_button)
        
        await interaction.followup.send(embed=verify_embed, view=view, ephemeral=True)

    @app_commands.command(name="update", description="Update your linked Roblox account")
    @app_commands.describe(roblox_username="Your new Roblox username")
    async def update(self, interaction: discord.Interaction, roblox_username: str):
        """Update a user's linked Roblox account"""
        await interaction.response.defer(ephemeral=True)
        
        discord_id = interaction.user.id
        discord_username = str(interaction.user)
        
        # Check if user is already verified
        existing_user = await fetch_query(
            "SELECT roblox_id, roblox_username FROM verified_users WHERE discord_id = $1",
            discord_id
        )
        
        if not existing_user:
            await interaction.followup.send(
                "You are not verified! Please use `/verify` command first.",
                ephemeral=True
            )
            return
        
        current_roblox_username = existing_user[0]['roblox_username']
        
        # Get Roblox user info for the new username
        roblox_user = await get_roblox_user(roblox_username)
        if not roblox_user:
            await interaction.followup.send(
                f"Could not find a Roblox user with username: `{roblox_username}`",
                ephemeral=True
            )
            return
        
        roblox_id = roblox_user["id"]
        roblox_display_name = roblox_user["displayName"]
        
        # Generate random verification code like "Verify-L6AQ"
        random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        verification_code = f"Verify-{random_code}"
        
        update_embed = create_embed(
            title="Update Roblox Account",
            description=(
                f"You are changing your verified account from **@{current_roblox_username}** to "
                f"**{roblox_display_name}** (@{roblox_username}).\n\n"
                f"To verify you own this new account, please put the following code in your Roblox profile description:\n\n"
                f"```{verification_code}```\n\n"
                f"Once you've added this code, click the 'Update' button below. "
                f"You can remove the code after verification is complete."
            ),
            color=discord.Color.blue()
        )
        
        update_embed.set_thumbnail(url=f"https://www.roblox.com/bust-thumbnail/image?userId={roblox_id}&width=150&height=150")
        
        # Create update button
        update_button = discord.ui.Button(style=discord.ButtonStyle.green, label="Update")
        cancel_button = discord.ui.Button(style=discord.ButtonStyle.red, label="Cancel")
        
        async def update_callback(button_interaction):
            # Check if the verification code is in the profile
            is_verified = await verify_roblox_user(roblox_id, verification_code)
            
            if is_verified:
                # Update verification in database
                await execute_query(
                    """
                    UPDATE verified_users
                    SET roblox_id = $1, roblox_username = $2, discord_username = $3
                    WHERE discord_id = $4
                    """,
                    roblox_id, roblox_username, discord_username, discord_id
                )
                
                # Try to update nickname if we have permission
                try:
                    await interaction.user.edit(nick=f"{roblox_display_name}")
                except discord.Forbidden:
                    logger.warning(f"Could not update nickname for {interaction.user.id}")
                
                success_embed = create_embed(
                    title="Update Successful",
                    description=f"Your account has been updated to **{roblox_display_name}** (@{roblox_username})!",
                    color=discord.Color.green()
                )
                
                success_embed.set_thumbnail(url=f"https://www.roblox.com/bust-thumbnail/image?userId={roblox_id}&width=150&height=150")
                
                await button_interaction.response.edit_message(embed=success_embed, view=None)
            else:
                failure_embed = create_embed(
                    title="Update Failed",
                    description=(
                        f"Could not find the verification code in your Roblox profile. "
                        f"Please make sure you added:\n\n"
                        f"```{verification_code}```\n\n"
                        f"to your profile description and try again, or click the button below to get help."
                    ),
                    color=discord.Color.red()
                )
                
                # Create help button view
                help_view = discord.ui.View()
                get_help_button = discord.ui.Button(
                    style=discord.ButtonStyle.primary, 
                    label="Get Help With Verification", 
                    emoji="🎫"
                )
                
                # Create the callback for the help button
                async def help_callback(help_interaction):
                    from cogs.verification_ticket import VerificationTicketView
                    ticket_view = VerificationTicketView(
                        roblox_username=roblox_username,
                        roblox_id=roblox_id,
                        verification_code=verification_code
                    )
                    await ticket_view.create_verification_support_ticket(help_interaction)
                
                get_help_button.callback = help_callback
                help_view.add_item(get_help_button)
                
                await button_interaction.response.edit_message(embed=failure_embed, view=help_view)
        
        async def cancel_callback(button_interaction):
            await button_interaction.response.edit_message(
                embed=create_embed(
                    title="Update Cancelled",
                    description="You've cancelled the account update process.",
                    color=discord.Color.light_gray()
                ),
                view=None
            )
        
        update_button.callback = update_callback
        cancel_button.callback = cancel_callback
        
        view = discord.ui.View()
        view.add_item(update_button)
        view.add_item(cancel_button)
        
        await interaction.followup.send(embed=update_embed, view=view, ephemeral=True)
    
    @app_commands.command(name="info-roblox", description="Get information about a Roblox user")
    @app_commands.describe(roblox_username="Roblox username to look up")
    async def info_roblox(self, interaction: discord.Interaction, roblox_username: str):
        """Get information about a Roblox user"""
        await interaction.response.defer()
        
        # Get Roblox user info
        roblox_user = await get_roblox_user(roblox_username)
        if not roblox_user:
            await interaction.followup.send(
                f"Could not find a Roblox user with username: `{roblox_username}`",
                ephemeral=True
            )
            return
        
        roblox_id = roblox_user["id"]
        roblox_display_name = roblox_user["displayName"]
        created_date = roblox_user.get("created", "Unknown")
        description = roblox_user.get("description", "No description")
        
        # Check if this Roblox user is verified with any Discord user
        verified_user = await fetch_query(
            "SELECT discord_id FROM verified_users WHERE roblox_id = $1",
            roblox_id
        )
        
        # Create embed with user info
        info_embed = create_embed(
            title=f"Roblox User: {roblox_display_name}",
            description=f"**Username:** @{roblox_username}\n**User ID:** {roblox_id}",
            color=discord.Color.blue()
        )
        
        info_embed.set_thumbnail(url=f"https://www.roblox.com/bust-thumbnail/image?userId={roblox_id}&width=150&height=150")
        
        # Add account creation date if available
        if created_date != "Unknown":
            if isinstance(created_date, str):
                info_embed.add_field(name="Account Created", value=created_date, inline=True)
            else:
                info_embed.add_field(name="Account Created", value=created_date.strftime("%Y-%m-%d"), inline=True)
        
        # Add profile URL
        info_embed.add_field(name="Profile URL", value=f"https://www.roblox.com/users/{roblox_id}/profile", inline=True)
        
        # Add verification status
        if verified_user:
            discord_id = verified_user[0]['discord_id']
            discord_member = interaction.guild.get_member(discord_id)
            discord_mention = f"<@{discord_id}>" if discord_member else f"User ID: {discord_id}"
            info_embed.add_field(name="Verified With", value=discord_mention, inline=False)
        else:
            info_embed.add_field(name="Verification Status", value="Not verified with any Discord user", inline=False)
        
        # Add description field if it's not empty
        if description and description != "No description":
            # Truncate if too long
            if len(description) > 1024:
                description = description[:1021] + "..."
            info_embed.add_field(name="Description", value=description, inline=False)
        
        await interaction.followup.send(embed=info_embed)

async def setup(bot):
    await bot.add_cog(Verification(bot))