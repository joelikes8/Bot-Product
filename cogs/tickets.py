import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import logging
import json
from datetime import datetime
from utils.database import execute_query, fetch_query
from utils.embed_builder import create_embed

logger = logging.getLogger('discord_bot.tickets')

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view that doesn't timeout
    
    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket", emoji="🎫")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle ticket creation when the button is clicked"""
        guild_id = interaction.guild.id
        user_id = interaction.user.id
        
        # Check if user already has an open ticket
        existing_ticket = await fetch_query(
            "SELECT channel_id FROM tickets WHERE guild_id = $1 AND user_id = $2 AND status = 'open'",
            guild_id, user_id
        )
        
        if existing_ticket:
            # User already has an open ticket
            channel_id = existing_ticket[0]['channel_id']
            channel = interaction.guild.get_channel(channel_id)
            
            if channel:
                await interaction.response.send_message(
                    f"You already have an open ticket: {channel.mention}",
                    ephemeral=True
                )
            else:
                # Channel doesn't exist anymore, update database
                await execute_query(
                    "UPDATE tickets SET status = 'closed' WHERE channel_id = $1",
                    channel_id
                )
                # Proceed with creating a new ticket
                await self.create_ticket(interaction)
        else:
            # Create a new ticket
            await self.create_ticket(interaction)
    
    async def create_ticket(self, interaction: discord.Interaction):
        """Create a new ticket channel"""
        guild = interaction.guild
        user = interaction.user
        
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
            ticket_name = f"ticket-{user.name}-{user.discriminator}"
            ticket_channel = await guild.create_text_channel(
                name=ticket_name,
                overwrites=overwrites,
                category=category,
                reason=f"Ticket created by {user}"
            )
            
            # Add ticket to database
            await execute_query(
                """
                INSERT INTO tickets (guild_id, channel_id, user_id, created_at, status)
                VALUES ($1, $2, $3, $4, $5)
                """,
                guild.id, ticket_channel.id, user.id, datetime.now(), 'open'
            )
            
            # Create welcome embed for the ticket
            welcome_embed = create_embed(
                title="Ticket Created",
                description=(
                    f"Hello {user.mention}, your ticket has been created!\n\n"
                    f"Please describe your issue and a staff member will assist you shortly.\n\n"
                    f"To close this ticket when your issue is resolved, use the button below."
                ),
                color=discord.Color.green()
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
            
            # Notify the user
            await interaction.response.send_message(
                f"Your ticket has been created: {ticket_channel.mention}",
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to create channels. Please contact an administrator.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error creating ticket channel: {e}")
            await interaction.response.send_message(
                "An error occurred while creating your ticket. Please try again later.",
                ephemeral=True
            )

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Register persistent view
        self.bot.add_view(TicketView())
    
    @app_commands.command(name="sendticket", description="Send a ticket creation message to a channel")
    @app_commands.describe(channel="The channel to send the ticket message to")
    @app_commands.default_permissions(administrator=True)
    async def sendticket(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Send a ticket creation message to a channel"""
        await interaction.response.defer(ephemeral=True)
        
        # Check if bot has permissions to send messages in the channel
        permissions = channel.permissions_for(interaction.guild.me)
        if not permissions.send_messages or not permissions.embed_links:
            await interaction.followup.send(
                f"I don't have permission to send messages or embed links in {channel.mention}",
                ephemeral=True
            )
            return
        
        # Create ticket system embed
        ticket_embed = create_embed(
            title="🎫 Support Ticket System",
            description=(
                "Need assistance? Click the button below to create a ticket!\n\n"
                "Our support team will help you as soon as possible.\n\n"
                "**Please Note:**\n"
                "• Only open a ticket if you have a legitimate issue\n"
                "• Be patient and respectful to our staff\n"
                "• Provide as much detail as possible about your issue"
            ),
            color=discord.Color.blue()
        )
        
        # Send the embed with the ticket button
        await channel.send(embed=ticket_embed, view=TicketView())
        
        await interaction.followup.send(
            f"Ticket system message sent to {channel.mention} successfully!",
            ephemeral=True
        )
    
    @app_commands.command(name="setupticket", description="Configure which roles can access tickets")
    @app_commands.describe(
        role="The role to add as a ticket support role",
        category="The category where tickets should be created"
    )
    @app_commands.default_permissions(administrator=True)
    async def setupticket(
        self, 
        interaction: discord.Interaction, 
        role: discord.Role,
        category: discord.CategoryChannel = None
    ):
        """Configure ticket system settings"""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild.id
        
        # Add support role to database
        await execute_query(
            """
            INSERT INTO ticket_support_roles (guild_id, role_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id, role_id) DO NOTHING
            """,
            guild_id, role.id
        )
        
        # If category provided, update guild settings
        if category:
            await execute_query(
                """
                INSERT INTO guild_settings (guild_id, ticket_category_id)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE SET
                ticket_category_id = $2
                """,
                guild_id, category.id
            )
        
        # Get all current support roles
        support_roles = await fetch_query(
            "SELECT role_id FROM ticket_support_roles WHERE guild_id = $1",
            guild_id
        )
        
        role_mentions = []
        for role_data in support_roles:
            role_id = role_data['role_id']
            role_obj = interaction.guild.get_role(role_id)
            if role_obj:
                role_mentions.append(role_obj.mention)
        
        roles_text = ", ".join(role_mentions) if role_mentions else "None"
        
        # Get current category
        category_data = await fetch_query(
            "SELECT ticket_category_id FROM guild_settings WHERE guild_id = $1",
            guild_id
        )
        
        category_text = "None"
        if category_data and category_data[0]['ticket_category_id']:
            category_obj = interaction.guild.get_channel(category_data[0]['ticket_category_id'])
            if category_obj:
                category_text = category_obj.mention
        
        # Create response embed
        setup_embed = create_embed(
            title="Ticket System Configuration",
            description=(
                f"Ticket system has been configured successfully!\n\n"
                f"**Support Roles:** {roles_text}\n"
                f"**Ticket Category:** {category_text}\n\n"
                f"Use `/sendticket` to create a ticket panel in a channel."
            ),
            color=discord.Color.green()
        )
        
        await interaction.followup.send(embed=setup_embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Tickets(bot))
