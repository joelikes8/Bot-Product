import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import logging
import datetime
from typing import Optional
from utils.embed_builder import create_embed

logger = logging.getLogger('discord_bot.announcements')

class Announcements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="announce", description="Create and send an announcement to a channel")
    @app_commands.describe(
        channel="The channel to send the announcement to",
        title="Title of the announcement",
        message="Content of the announcement"
    )
    @app_commands.default_permissions(manage_messages=True)
    async def announce(self, interaction: discord.Interaction, channel: discord.TextChannel, title: str, message: str):
        """Create and send an announcement to a channel"""
        # First check if the user has permission to send messages in the target channel
        permissions = channel.permissions_for(interaction.user)
        if not permissions.send_messages:
            await interaction.response.send_message(
                f"You don't have permission to send messages in {channel.mention}",
                ephemeral=True
            )
            return
        
        # Create a modal for additional customization
        class AnnouncementModal(discord.ui.Modal, title="Customize Announcement"):
            color = discord.ui.TextInput(
                label="Embed Color (hex code without #)",
                placeholder="e.g. FF5733 for red, 33FF57 for green",
                required=False,
                default="5865F2"  # Discord blue
            )
            
            image_url = discord.ui.TextInput(
                label="Image URL (optional)",
                placeholder="https://example.com/image.png",
                required=False
            )
            
            footer = discord.ui.TextInput(
                label="Footer Text (optional)",
                placeholder="Additional information",
                required=False
            )

            async def on_submit(self, modal_interaction: discord.Interaction):
                # Try to parse the color
                try:
                    color_value = int(self.color.value.strip(), 16)
                    embed_color = discord.Color(color_value)
                except ValueError:
                    embed_color = discord.Color.blue()
                
                # Create the announcement embed
                announcement_embed = create_embed(
                    title=title,
                    description=message,
                    color=embed_color
                )
                
                # Add image if provided
                image_url_value = self.image_url.value.strip()
                if image_url_value:
                    announcement_embed.set_image(url=image_url_value)
                
                # Add footer if provided
                footer_text = self.footer.value.strip()
                if footer_text:
                    announcement_embed.set_footer(text=footer_text)
                
                # Add author info
                announcement_embed.set_author(
                    name=interaction.user.display_name,
                    icon_url=interaction.user.display_avatar.url
                )
                
                # Add timestamp
                announcement_embed.timestamp = datetime.datetime.now()
                
                # Send the announcement
                try:
                    await channel.send(embed=announcement_embed)
                    await modal_interaction.response.send_message(
                        f"Announcement sent to {channel.mention} successfully!",
                        ephemeral=True
                    )
                except discord.Forbidden:
                    await modal_interaction.response.send_message(
                        f"I don't have permission to send messages in {channel.mention}",
                        ephemeral=True
                    )
                except Exception as e:
                    logger.error(f"Error sending announcement: {e}")
                    await modal_interaction.response.send_message(
                        f"An error occurred while sending the announcement: {str(e)}",
                        ephemeral=True
                    )

        # Show the modal
        await interaction.response.send_modal(AnnouncementModal())
    
    @app_commands.command(name="host", description="Create an event hosting announcement")
    @app_commands.describe(
        host_channel="The channel to send the host announcement to",
        event_type="The type of event (e.g., tryout, training)",
        starts="When the event starts (e.g., 3:30PM EST)",
        ends="When the event ends (e.g., 5:00PM EST)",
        description="Additional details about the event"
    )
    @app_commands.default_permissions(manage_messages=True)
    async def host(
        self, 
        interaction: discord.Interaction, 
        host_channel: discord.TextChannel, 
        event_type: str, 
        starts: str, 
        ends: str,
        description: Optional[str] = None
    ):
        """Create and send an event hosting announcement"""
        # Check if the user has permission to send messages in the target channel
        permissions = host_channel.permissions_for(interaction.user)
        if not permissions.send_messages:
            await interaction.response.send_message(
                f"You don't have permission to send messages in {host_channel.mention}",
                ephemeral=True
            )
            return
        
        # Create a modal for additional customization
        class HostingModal(discord.ui.Modal, title="Event Hosting Details"):
            additional_info = discord.ui.TextInput(
                label="Additional Information (optional)",
                style=discord.TextStyle.paragraph,
                placeholder="Any additional information about the event",
                required=False
            )
            
            location = discord.ui.TextInput(
                label="Location (optional)",
                placeholder="e.g., Game link, private server code, etc.",
                required=False
            )
            
            requirements = discord.ui.TextInput(
                label="Requirements (optional)",
                style=discord.TextStyle.paragraph,
                placeholder="Any requirements for participants",
                required=False
            )

            async def on_submit(self, modal_interaction: discord.Interaction):
                # Prepare the description
                full_description = f"**Event Type:** {event_type}\n**Starts:** {starts}\n**Ends:** {ends}\n"
                
                if description:
                    full_description += f"\n**Description:**\n{description}\n"
                
                if self.location.value.strip():
                    full_description += f"\n**Location:**\n{self.location.value.strip()}\n"
                
                if self.requirements.value.strip():
                    full_description += f"\n**Requirements:**\n{self.requirements.value.strip()}\n"
                
                if self.additional_info.value.strip():
                    full_description += f"\n**Additional Information:**\n{self.additional_info.value.strip()}\n"
                
                # Add a contact field
                full_description += f"\n**Host:** {interaction.user.mention}"
                
                # Create the hosting embed
                hosting_embed = create_embed(
                    title=f"🎮 {event_type.upper()} EVENT 🎮",
                    description=full_description,
                    color=discord.Color.green()
                )
                
                # Add author info
                hosting_embed.set_author(
                    name=f"Hosted by {interaction.user.display_name}",
                    icon_url=interaction.user.display_avatar.url
                )
                
                # Add timestamp
                hosting_embed.timestamp = datetime.datetime.now()
                
                # Add footer
                hosting_embed.set_footer(text=f"Event by {interaction.guild.name}")
                
                # Create the buttons
                class EventButtons(discord.ui.View):
                    def __init__(self):
                        super().__init__(timeout=None)  # Make the buttons persist
                    
                    @discord.ui.button(label="I'll Join!", style=discord.ButtonStyle.green, emoji="✅")
                    async def join_callback(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                        await button_interaction.response.send_message(
                            f"You've signed up for the {event_type} event! The host will provide more details.",
                            ephemeral=True
                        )
                    
                    @discord.ui.button(label="More Information", style=discord.ButtonStyle.blurple, emoji="ℹ️")
                    async def info_callback(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                        await button_interaction.response.send_message(
                            f"For more information about this event, please contact {interaction.user.mention}.",
                            ephemeral=True
                        )
                
                # Send the hosting announcement
                try:
                    await host_channel.send(embed=hosting_embed, view=EventButtons())
                    await modal_interaction.response.send_message(
                        f"Event hosting announcement sent to {host_channel.mention} successfully!",
                        ephemeral=True
                    )
                except discord.Forbidden:
                    await modal_interaction.response.send_message(
                        f"I don't have permission to send messages in {host_channel.mention}",
                        ephemeral=True
                    )
                except Exception as e:
                    logger.error(f"Error sending hosting announcement: {e}")
                    await modal_interaction.response.send_message(
                        f"An error occurred while sending the hosting announcement: {str(e)}",
                        ephemeral=True
                    )

        # Show the modal
        await interaction.response.send_modal(HostingModal())

async def setup(bot):
    await bot.add_cog(Announcements(bot))
