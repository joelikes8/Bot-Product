import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import logging
import datetime
from typing import Optional, Literal
from utils.embed_builder import create_embed
from utils.database import execute_query, fetch_query

logger = logging.getLogger('discord_bot.moderation')

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(
        member="The member to kick",
        reason="The reason for kicking the member"
    )
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "No reason provided"):
        """Kick a member from the server"""
        # Check if bot can kick the target member
        if not interaction.guild.me.guild_permissions.kick_members:
            await interaction.response.send_message(
                "I don't have permission to kick members.",
                ephemeral=True
            )
            return
        
        # Check if the target member is higher in hierarchy than the bot
        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "I can't kick this member because their highest role is above or equal to mine.",
                ephemeral=True
            )
            return
        
        # Check if the command user is trying to kick themselves
        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "You can't kick yourself.",
                ephemeral=True
            )
            return
        
        # Check if the target member is higher in hierarchy than the command user
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                "You can't kick this member because their highest role is above or equal to yours.",
                ephemeral=True
            )
            return
        
        try:
            # Create a kick confirmation button
            class KickConfirmation(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=60)  # 60 seconds timeout
                    self.value = None
                
                @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
                async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    if button_interaction.user.id != interaction.user.id:
                        await button_interaction.response.send_message("You cannot use this button.", ephemeral=True)
                        return
                    
                    self.value = True
                    self.stop()
                    
                    # Perform the kick
                    try:
                        # Log the kick in the database
                        await execute_query(
                            """
                            INSERT INTO mod_actions (guild_id, user_id, target_id, action_type, reason, timestamp)
                            VALUES ($1, $2, $3, $4, $5, $6)
                            """,
                            interaction.guild.id, interaction.user.id, member.id, 'kick', reason, datetime.datetime.now()
                        )
                        
                        # Send DM to the user if possible
                        try:
                            kick_dm = create_embed(
                                title=f"You have been kicked from {interaction.guild.name}",
                                description=f"**Reason:** {reason}",
                                color=discord.Color.red()
                            )
                            await member.send(embed=kick_dm)
                        except:
                            pass  # Can't DM the user
                        
                        # Kick the member
                        await member.kick(reason=f"Kicked by {interaction.user}: {reason}")
                        
                        # Send confirmation
                        kick_confirm = create_embed(
                            title="Member Kicked",
                            description=f"{member.mention} has been kicked.\n**Reason:** {reason}",
                            color=discord.Color.green()
                        )
                        await button_interaction.response.edit_message(embed=kick_confirm, view=None)
                        
                    except discord.Forbidden:
                        await button_interaction.response.edit_message(
                            embed=create_embed(
                                title="Kick Failed",
                                description="I don't have permission to kick this member.",
                                color=discord.Color.red()
                            ),
                            view=None
                        )
                    except Exception as e:
                        logger.error(f"Error kicking member: {e}")
                        await button_interaction.response.edit_message(
                            embed=create_embed(
                                title="Kick Failed",
                                description=f"An error occurred: {str(e)}",
                                color=discord.Color.red()
                            ),
                            view=None
                        )
                
                @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
                async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    if button_interaction.user.id != interaction.user.id:
                        await button_interaction.response.send_message("You cannot use this button.", ephemeral=True)
                        return
                    
                    self.value = False
                    self.stop()
                    
                    await button_interaction.response.edit_message(
                        embed=create_embed(
                            title="Kick Cancelled",
                            description=f"The kick action for {member.mention} has been cancelled.",
                            color=discord.Color.grey()
                        ),
                        view=None
                    )
                
                async def on_timeout(self):
                    # When the view times out, edit the message to indicate it
                    try:
                        await interaction.edit_original_response(
                            embed=create_embed(
                                title="Kick Cancelled",
                                description="Confirmation timed out.",
                                color=discord.Color.grey()
                            ),
                            view=None
                        )
                    except:
                        pass
            
            # Create confirmation embed
            confirm_embed = create_embed(
                title="Kick Confirmation",
                description=f"Are you sure you want to kick {member.mention}?\n**Reason:** {reason}",
                color=discord.Color.yellow()
            )
            
            view = KickConfirmation()
            await interaction.response.send_message(embed=confirm_embed, view=view)
            
        except Exception as e:
            logger.error(f"Error in kick command: {e}")
            await interaction.response.send_message(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.describe(
        member="The member to ban",
        reason="The reason for banning the member",
        delete_days="Number of days worth of messages to delete"
    )
    @app_commands.default_permissions(ban_members=True)
    async def ban(
        self, 
        interaction: discord.Interaction, 
        member: discord.Member, 
        reason: Optional[str] = "No reason provided",
        delete_days: Optional[Literal[0, 1, 7]] = 1
    ):
        """Ban a member from the server"""
        # Check if bot can ban the target member
        if not interaction.guild.me.guild_permissions.ban_members:
            await interaction.response.send_message(
                "I don't have permission to ban members.",
                ephemeral=True
            )
            return
        
        # Check if the target member is higher in hierarchy than the bot
        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "I can't ban this member because their highest role is above or equal to mine.",
                ephemeral=True
            )
            return
        
        # Check if the command user is trying to ban themselves
        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "You can't ban yourself.",
                ephemeral=True
            )
            return
        
        # Check if the target member is higher in hierarchy than the command user
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                "You can't ban this member because their highest role is above or equal to yours.",
                ephemeral=True
            )
            return
        
        try:
            # Create a ban confirmation button
            class BanConfirmation(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=60)  # 60 seconds timeout
                    self.value = None
                
                @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
                async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    if button_interaction.user.id != interaction.user.id:
                        await button_interaction.response.send_message("You cannot use this button.", ephemeral=True)
                        return
                    
                    self.value = True
                    self.stop()
                    
                    # Perform the ban
                    try:
                        # Log the ban in the database
                        await execute_query(
                            """
                            INSERT INTO mod_actions (guild_id, user_id, target_id, action_type, reason, timestamp)
                            VALUES ($1, $2, $3, $4, $5, $6)
                            """,
                            interaction.guild.id, interaction.user.id, member.id, 'ban', reason, datetime.datetime.now()
                        )
                        
                        # Send DM to the user if possible
                        try:
                            ban_dm = create_embed(
                                title=f"You have been banned from {interaction.guild.name}",
                                description=f"**Reason:** {reason}",
                                color=discord.Color.red()
                            )
                            await member.send(embed=ban_dm)
                        except:
                            pass  # Can't DM the user
                        
                        # Ban the member
                        await member.ban(reason=f"Banned by {interaction.user}: {reason}", delete_message_days=delete_days)
                        
                        # Send confirmation
                        ban_confirm = create_embed(
                            title="Member Banned",
                            description=f"{member.mention} has been banned.\n**Reason:** {reason}",
                            color=discord.Color.green()
                        )
                        await button_interaction.response.edit_message(embed=ban_confirm, view=None)
                        
                    except discord.Forbidden:
                        await button_interaction.response.edit_message(
                            embed=create_embed(
                                title="Ban Failed",
                                description="I don't have permission to ban this member.",
                                color=discord.Color.red()
                            ),
                            view=None
                        )
                    except Exception as e:
                        logger.error(f"Error banning member: {e}")
                        await button_interaction.response.edit_message(
                            embed=create_embed(
                                title="Ban Failed",
                                description=f"An error occurred: {str(e)}",
                                color=discord.Color.red()
                            ),
                            view=None
                        )
                
                @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
                async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    if button_interaction.user.id != interaction.user.id:
                        await button_interaction.response.send_message("You cannot use this button.", ephemeral=True)
                        return
                    
                    self.value = False
                    self.stop()
                    
                    await button_interaction.response.edit_message(
                        embed=create_embed(
                            title="Ban Cancelled",
                            description=f"The ban action for {member.mention} has been cancelled.",
                            color=discord.Color.grey()
                        ),
                        view=None
                    )
                
                async def on_timeout(self):
                    # When the view times out, edit the message to indicate it
                    try:
                        await interaction.edit_original_response(
                            embed=create_embed(
                                title="Ban Cancelled",
                                description="Confirmation timed out.",
                                color=discord.Color.grey()
                            ),
                            view=None
                        )
                    except:
                        pass
            
            # Create confirmation embed
            confirm_embed = create_embed(
                title="Ban Confirmation",
                description=(
                    f"Are you sure you want to ban {member.mention}?\n"
                    f"**Reason:** {reason}\n"
                    f"**Delete Message History:** {delete_days} days"
                ),
                color=discord.Color.yellow()
            )
            
            view = BanConfirmation()
            await interaction.response.send_message(embed=confirm_embed, view=view)
            
        except Exception as e:
            logger.error(f"Error in ban command: {e}")
            await interaction.response.send_message(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.describe(
        member="The member to warn",
        reason="The reason for the warning"
    )
    @app_commands.default_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        """Warn a member and keep a record of it"""
        # Check if the command user is trying to warn themselves
        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "You can't warn yourself.",
                ephemeral=True
            )
            return
        
        # Check if the target member is higher in hierarchy than the command user
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                "You can't warn this member because their highest role is above or equal to yours.",
                ephemeral=True
            )
            return
        
        try:
            # Log the warning in the database
            await execute_query(
                """
                INSERT INTO mod_actions (guild_id, user_id, target_id, action_type, reason, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                interaction.guild.id, interaction.user.id, member.id, 'warn', reason, datetime.datetime.now()
            )
            
            # Create warning embed for the channel
            warn_embed = create_embed(
                title="Member Warned",
                description=f"{member.mention} has been warned.\n**Reason:** {reason}",
                color=discord.Color.yellow()
            )
            
            # Create warning DM for the member
            warn_dm = create_embed(
                title=f"You have been warned in {interaction.guild.name}",
                description=f"**Reason:** {reason}\n\nPlease make sure to follow the server rules to avoid further actions.",
                color=discord.Color.yellow()
            )
            
            # Try to DM the user
            try:
                await member.send(embed=warn_dm)
                dm_sent = True
            except:
                dm_sent = False
            
            # Add field indicating if DM was sent
            warn_embed.add_field(name="DM Notification", value="Sent ✅" if dm_sent else "Failed to send ❌", inline=False)
            
            # Get warning count for this user
            warnings = await fetch_query(
                """
                SELECT COUNT(*) as count FROM mod_actions 
                WHERE guild_id = $1 AND target_id = $2 AND action_type = 'warn'
                """,
                interaction.guild.id, member.id
            )
            
            warning_count = warnings[0]['count'] if warnings else 0
            
            # Add warning count field
            warn_embed.add_field(name="Warning Count", value=f"{warning_count} warning(s)", inline=False)
            
            await interaction.response.send_message(embed=warn_embed)
            
        except Exception as e:
            logger.error(f"Error in warn command: {e}")
            await interaction.response.send_message(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="mute", description="Mute a member for a specified duration")
    @app_commands.describe(
        member="The member to mute",
        duration="Duration (e.g., 1h, 30m, 12h)",
        reason="The reason for muting the member"
    )
    @app_commands.default_permissions(moderate_members=True)
    async def mute(
        self, 
        interaction: discord.Interaction, 
        member: discord.Member, 
        duration: str,
        reason: Optional[str] = "No reason provided"
    ):
        """Timeout (mute) a member for a specified duration"""
        # Check if bot can moderate the target member
        if not interaction.guild.me.guild_permissions.moderate_members:
            await interaction.response.send_message(
                "I don't have permission to timeout members.",
                ephemeral=True
            )
            return
        
        # Check if the target member is higher in hierarchy than the bot
        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "I can't timeout this member because their highest role is above or equal to mine.",
                ephemeral=True
            )
            return
        
        # Check if the command user is trying to mute themselves
        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "You can't timeout yourself.",
                ephemeral=True
            )
            return
        
        # Check if the target member is higher in hierarchy than the command user
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                "You can't timeout this member because their highest role is above or equal to yours.",
                ephemeral=True
            )
            return
        
        # Parse duration string (e.g., "1h", "30m", "12h30m")
        try:
            total_seconds = 0
            
            # Extract hours
            hours_match = re.search(r'(\d+)h', duration)
            if hours_match:
                total_seconds += int(hours_match.group(1)) * 3600
            
            # Extract minutes
            minutes_match = re.search(r'(\d+)m', duration)
            if minutes_match:
                total_seconds += int(minutes_match.group(1)) * 60
            
            # Extract days
            days_match = re.search(r'(\d+)d', duration)
            if days_match:
                total_seconds += int(days_match.group(1)) * 86400
            
            # If no valid duration specified
            if total_seconds == 0:
                await interaction.response.send_message(
                    "Invalid duration format. Examples: 1h, 30m, 1d, 1h30m",
                    ephemeral=True
                )
                return
            
            # Check for maximum timeout duration (28 days)
            if total_seconds > 2419200:  # 28 days in seconds
                await interaction.response.send_message(
                    "Timeout duration cannot exceed 28 days.",
                    ephemeral=True
                )
                return
            
            # Calculate end time
            until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=total_seconds)
            
            # Format duration for display
            duration_text = []
            days = total_seconds // 86400
            if days > 0:
                duration_text.append(f"{days} day(s)")
            
            hours = (total_seconds % 86400) // 3600
            if hours > 0:
                duration_text.append(f"{hours} hour(s)")
            
            minutes = (total_seconds % 3600) // 60
            if minutes > 0:
                duration_text.append(f"{minutes} minute(s)")
            
            seconds = total_seconds % 60
            if seconds > 0:
                duration_text.append(f"{seconds} second(s)")
            
            duration_display = ", ".join(duration_text)
            
            # Log the timeout in the database
            await execute_query(
                """
                INSERT INTO mod_actions (guild_id, user_id, target_id, action_type, reason, timestamp, duration)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                interaction.guild.id, interaction.user.id, member.id, 'timeout', reason, datetime.datetime.now(), total_seconds
            )
            
            # Apply timeout
            await member.timeout(until=until, reason=f"Timed out by {interaction.user}: {reason}")
            
            # Try to send DM to the user
            try:
                timeout_dm = create_embed(
                    title=f"You have been timed out in {interaction.guild.name}",
                    description=(
                        f"**Duration:** {duration_display}\n"
                        f"**Reason:** {reason}\n\n"
                        f"You will be able to send messages again <t:{int(until.timestamp())}:R>."
                    ),
                    color=discord.Color.red()
                )
                await member.send(embed=timeout_dm)
                dm_sent = True
            except:
                dm_sent = False
            
            # Send confirmation
            timeout_embed = create_embed(
                title="Member Timed Out",
                description=(
                    f"{member.mention} has been timed out.\n"
                    f"**Duration:** {duration_display}\n"
                    f"**Expires:** <t:{int(until.timestamp())}:R>\n"
                    f"**Reason:** {reason}"
                ),
                color=discord.Color.orange()
            )
            
            timeout_embed.add_field(name="DM Notification", value="Sent ✅" if dm_sent else "Failed to send ❌", inline=False)
            
            await interaction.response.send_message(embed=timeout_embed)
            
        except Exception as e:
            logger.error(f"Error in mute command: {e}")
            await interaction.response.send_message(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(name="unmute", description="Remove timeout from a member")
    @app_commands.describe(
        member="The member to unmute",
        reason="The reason for removing the timeout"
    )
    @app_commands.default_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "No reason provided"):
        """Remove timeout from a member"""
        # Check if bot can moderate the target member
        if not interaction.guild.me.guild_permissions.moderate_members:
            await interaction.response.send_message(
                "I don't have permission to remove timeouts.",
                ephemeral=True
            )
            return
        
        # Check if the member is actually timed out
        if not member.is_timed_out():
            await interaction.response.send_message(
                f"{member.mention} is not currently timed out.",
                ephemeral=True
            )
            return
        
        try:
            # Remove the timeout
            await member.timeout(until=None, reason=f"Timeout removed by {interaction.user}: {reason}")
            
            # Log the action
            await execute_query(
                """
                INSERT INTO mod_actions (guild_id, user_id, target_id, action_type, reason, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                interaction.guild.id, interaction.user.id, member.id, 'unmute', reason, datetime.datetime.now()
            )
            
            # Try to send DM to the user
            try:
                unmute_dm = create_embed(
                    title=f"Your timeout has been removed in {interaction.guild.name}",
                    description=f"**Reason:** {reason}\n\nYou can now send messages again.",
                    color=discord.Color.green()
                )
                await member.send(embed=unmute_dm)
                dm_sent = True
            except:
                dm_sent = False
            
            # Send confirmation
            unmute_embed = create_embed(
                title="Timeout Removed",
                description=f"{member.mention}'s timeout has been removed.\n**Reason:** {reason}",
                color=discord.Color.green()
            )
            
            unmute_embed.add_field(name="DM Notification", value="Sent ✅" if dm_sent else "Failed to send ❌", inline=False)
            
            await interaction.response.send_message(embed=unmute_embed)
            
        except Exception as e:
            logger.error(f"Error in unmute command: {e}")
            await interaction.response.send_message(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )
            
    @app_commands.command(name="clear", description="Delete a specified number of messages")
    @app_commands.describe(
        amount="Number of messages to delete (1-100)",
        user="Only delete messages from this user (optional)"
    )
    @app_commands.default_permissions(manage_messages=True)
    async def clear(
        self, 
        interaction: discord.Interaction, 
        amount: app_commands.Range[int, 1, 100],
        user: Optional[discord.Member] = None
    ):
        """Delete a specified number of messages from a channel"""
        # Check if bot has permission to manage messages
        if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
            await interaction.response.send_message(
                "I don't have permission to delete messages in this channel.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # If a user is specified, delete only their messages
            if user:
                def check(message):
                    return message.author.id == user.id
                
                # We need to fetch more messages than requested because we're filtering
                fetched = await interaction.channel.history(limit=amount * 5).flatten()
                to_delete = []
                
                for message in fetched:
                    if check(message):
                        to_delete.append(message)
                        if len(to_delete) >= amount:
                            break
                
                # If no messages found
                if not to_delete:
                    await interaction.followup.send(
                        f"No recent messages from {user.mention} were found to delete.",
                        ephemeral=True
                    )
                    return
                
                # Delete messages
                await interaction.channel.delete_messages(to_delete)
                
                await interaction.followup.send(
                    f"Successfully deleted {len(to_delete)} message(s) from {user.mention}.",
                    ephemeral=True
                )
            else:
                # Delete messages without filtering
                deleted = await interaction.channel.purge(limit=amount)
                
                await interaction.followup.send(
                    f"Successfully deleted {len(deleted)} message(s).",
                    ephemeral=True
                )
                
        except discord.errors.HTTPException as e:
            if e.code == 50034:
                await interaction.followup.send(
                    "Cannot delete messages that are older than 14 days.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"An error occurred: {str(e)}",
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error in clear command: {e}")
            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="modlogs", description="View moderation logs for a user")
    @app_commands.describe(
        user="The user to check moderation logs for"
    )
    @app_commands.default_permissions(moderate_members=True)
    async def modlogs(self, interaction: discord.Interaction, user: discord.Member):
        """View moderation logs for a specified user"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get moderation logs for the user
            logs = await fetch_query(
                """
                SELECT action_type, reason, timestamp, user_id, duration
                FROM mod_actions
                WHERE guild_id = $1 AND target_id = $2
                ORDER BY timestamp DESC
                LIMIT 10
                """,
                interaction.guild.id, user.id
            )
            
            if not logs:
                await interaction.followup.send(
                    f"No moderation logs found for {user.mention}.",
                    ephemeral=True
                )
                return
            
            # Create embed for moderation logs
            logs_embed = create_embed(
                title=f"Moderation Logs for {user.display_name}",
                description=f"Showing the last {len(logs)} moderation actions for {user.mention}",
                color=discord.Color.blue()
            )
            
            # Add thumbnail
            logs_embed.set_thumbnail(url=user.display_avatar.url)
            
            # Add each log entry as a field
            for i, log in enumerate(logs, 1):
                action_type = log['action_type'].capitalize()
                reason = log['reason']
                timestamp = log['timestamp']
                moderator_id = log['user_id']
                
                # Get moderator mention
                moderator = interaction.guild.get_member(moderator_id)
                moderator_mention = moderator.mention if moderator else f"<@{moderator_id}>"
                
                # Format the field value
                field_value = f"**Moderator:** {moderator_mention}\n**Reason:** {reason}\n**When:** <t:{int(timestamp.timestamp())}:R>"
                
                # Add duration if applicable (for timeouts)
                if log['duration'] and action_type.lower() == "timeout":
                    duration_seconds = log['duration']
                    if duration_seconds < 60:
                        duration_text = f"{duration_seconds} seconds"
                    elif duration_seconds < 3600:
                        duration_text = f"{duration_seconds // 60} minutes"
                    elif duration_seconds < 86400:
                        duration_text = f"{duration_seconds // 3600} hours"
                    else:
                        duration_text = f"{duration_seconds // 86400} days"
                    
                    field_value += f"\n**Duration:** {duration_text}"
                
                logs_embed.add_field(
                    name=f"{i}. {action_type} - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                    value=field_value,
                    inline=False
                )
            
            await interaction.followup.send(embed=logs_embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in modlogs command: {e}")
            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Moderation(bot))
