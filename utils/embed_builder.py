import discord
from typing import Optional, Union
import datetime

def create_embed(
    title: str = None,
    description: str = None,
    color: Union[discord.Color, int] = discord.Color.blurple(),
    timestamp: bool = True,
    url: str = None,
    thumbnail_url: str = None,
    image_url: str = None,
    author_name: str = None,
    author_url: str = None,
    author_icon_url: str = None,
    footer_text: str = None,
    footer_icon_url: str = None,
    fields: list = None
) -> discord.Embed:
    """
    Create a Discord embed with the provided parameters.
    
    Args:
        title: The title of the embed
        description: The description of the embed
        color: The color of the embed
        timestamp: Whether to add the current time as a timestamp
        url: The URL for the title to link to
        thumbnail_url: The URL of the thumbnail image
        image_url: The URL of the main image
        author_name: The name of the author
        author_url: The URL for the author's name to link to
        author_icon_url: The URL of the author's icon
        footer_text: The text in the footer
        footer_icon_url: The URL of the footer icon
        fields: A list of fields to add, each as a dict with 'name', 'value', and optionally 'inline'
    
    Returns:
        A Discord embed object
    """
    # Create the embed
    embed = discord.Embed(color=color)
    
    # Set title if provided
    if title:
        embed.title = title
    
    # Set description if provided
    if description:
        embed.description = description
    
    # Set URL if provided
    if url:
        embed.url = url
    
    # Set timestamp if requested
    if timestamp:
        embed.timestamp = datetime.datetime.now()
    
    # Set thumbnail if provided
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    
    # Set image if provided
    if image_url:
        embed.set_image(url=image_url)
    
    # Set author if name is provided
    if author_name:
        embed.set_author(
            name=author_name,
            url=author_url,
            icon_url=author_icon_url
        )
    
    # Set footer if text is provided
    if footer_text:
        embed.set_footer(
            text=footer_text,
            icon_url=footer_icon_url
        )
    
    # Add fields if provided
    if fields:
        for field in fields:
            embed.add_field(
                name=field['name'],
                value=field['value'],
                inline=field.get('inline', False)
            )
    
    return embed
