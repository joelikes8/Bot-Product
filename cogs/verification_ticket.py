import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import logging
from datetime import datetime
from utils.database import execute_query, fetch_query
from utils.embed_builder import create_embed

logger = logging.getLogger('discord_bot.verification_ticket')

class VerificationTicketView(discord.ui.View):
    def __init__(self, roblox_username=None, roblox_id=None, verification_code=None):
        super().__init__(timeout=None)
        self.roblox_username = roblox_username
        self.roblox_id = roblox_id
        self.verification_code = verification_code
    
    @discord.ui.button(label="Get Verification Help", style=discord.ButtonStyle.primary, custom_id="verification_help", emoji="🎫")
    async def create_verification_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Create a support ticket specifically for verification issues"""
        await self.create_verification_support_ticket(interaction)
    
    async def create_verification_support_ticket(self, interaction: discord.Interaction):
        """Create a new ticket channel for verification help"""
        guild = interaction.guild
        user = interaction.user
        
        # Check if user already has an open ticket
        existing_ticket = await fetch_query(
            "SELECT channel_id FROM tickets WHERE guild_id = $1 AND user_id = $2 AND status = 'open'",
            guild.id, user.id
        )
        
        if existing_ticket:
            # User already has an open ticket
            channel_id = existing_ticket[0]['channel_id']
            channel = interaction.guild.get_channel(channel_id)
            
            if channel:
                await interaction.response.send_message(
                    f"You already have an open ticket: {channel.mention}\nPlease use that ticket for your verification issues.",
                    ephemeral=True
                )
                return
            else:
                # Channel doesn't exist anymore, update database
                await execute_query(
                    "UPDATE tickets SET status = 'closed' WHERE channel_id = $1",
                    channel_id
                )
                # Continue with creating a new ticket
        
        # Get support role IDs from database
        support_roles = await fetch_query(
            "SELECT role_id FROM ticket_support_roles WHERE guild_id = $1",
            guild.id
        )
        
        # Get ticket category from database
        category_data = await fetch_query(
            "SELECT ticket_category_id FROM guild_settings WHERE guild_id = $1",
            guild.id
        )
        
        category_id = category_data[0]['ticket_category_id'] if category_data else None
        category = guild.get_channel(category_id) if category_id else None
        
        # Create permissions for the ticket channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Add support roles to overwrites
        for role_data in support_roles:
            role = guild.get_role(role_data['role_id'])
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        # Create the ticket channel
        try:
            ticket_name = f"verify-{user.name}"
            ticket_channel = await guild.create_text_channel(
                name=ticket_name,
                overwrites=overwrites,
                category=category,
                reason=f"Verification help ticket created by {user}"
            )
            
            # Add ticket to database
            await execute_query(
                """
                INSERT INTO tickets (guild_id, channel_id, user_id, created_at, status, ticket_type)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                guild.id, ticket_channel.id, user.id, datetime.now(), 'open', 'verification'
            )
            
            # Create welcome embed for the verification ticket
            verification_details = ""
            if self.roblox_username:
                verification_details += f"**Roblox Username:** {self.roblox_username}\n"
            if self.roblox_id:
                verification_details += f"**Roblox ID:** {self.roblox_id}\n"
            if self.verification_code:
                verification_details += f"**Verification Code:** `{self.verification_code}`\n"
            
            welcome_embed = create_embed(
                title="Verification Help Ticket",
                description=(
                    f"Hello {user.mention}, your verification help ticket has been created!\n\n"
                    f"Please describe the issue you're having with verification and a staff member will assist you shortly.\n\n"
                    f"{verification_details}\n"
                    f"To close this ticket when your issue is resolved, use the button below."
                ),
                color=discord.Color.blue()
            )
            
            # Create close ticket button
            class CloseTicketView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=None)
                
                @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket", emoji="🔒")
                async def close_ticket(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    if button_interaction.user == user or any(role.id in [r['role_id'] for r in support_roles] for role in button_interaction.user.roles):
                        close_embed = create_embed(
                            title="Ticket Closing",
                            description=f"This ticket was closed by {button_interaction.user.mention}.",
                            color=discord.Color.red()
                        )
                        await button_interaction.response.send_message(embed=close_embed)
                        
                        # Update database
                        await execute_query(
                            "UPDATE tickets SET status = 'closed', closed_at = $1 WHERE channel_id = $2",
                            datetime.now(), ticket_channel.id
                        )
                        
                        # Create delete view
                        delete_view = discord.ui.View()
                        delete_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="Delete Channel", emoji="⛔")
                        
                        async def delete_callback(delete_interaction):
                            if any(role.id in [r['role_id'] for r in support_roles] for role in delete_interaction.user.roles):
                                await delete_interaction.response.send_message("Deleting this channel in 5 seconds...")
                                await asyncio.sleep(5)
                                await ticket_channel.delete(reason=f"Ticket closed by {delete_interaction.user}")
                            else:
                                await delete_interaction.response.send_message("You don't have permission to delete this channel.", ephemeral=True)
                        
                        delete_button.callback = delete_callback
                        delete_view.add_item(delete_button)
                        
                        await ticket_channel.send("This ticket is now closed. Staff can delete this channel using the button below:", view=delete_view)
                        
                        # Change channel permissions
                        await ticket_channel.set_permissions(user, send_messages=False)
                    else:
                        await button_interaction.response.send_message("Only the ticket creator or support staff can close this ticket.", ephemeral=True)
            
            # Send the welcome message with the close button
            await ticket_channel.send(user.mention, embed=welcome_embed, view=CloseTicketView())
            
            # Alert staff with a ping if verification support roles exist
            if support_roles:
                role_mentions = [f"<@&{role_data['role_id']}>" for role_data in support_roles]
                await ticket_channel.send(f"Verification support needed: {', '.join(role_mentions)}")
            
            # Notify the user
            await interaction.response.send_message(
                f"Your verification help ticket has been created: {ticket_channel.mention}",
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to create channels. Please contact an administrator.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error creating verification ticket channel: {e}")
            await interaction.response.send_message(
                "An error occurred while creating your verification help ticket. Please try again later.",
                ephemeral=True
            )

class VerificationTicket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    await bot.add_cog(VerificationTicket(bot))