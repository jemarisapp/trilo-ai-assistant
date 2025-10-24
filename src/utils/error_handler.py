"""
Error handling utilities for Trilo Discord Bot
"""
import logging
import traceback
import discord
from typing import Optional, Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)

class TriloError(Exception):
    """Base exception for Trilo bot errors"""
    pass

class DatabaseError(TriloError):
    """Database-related errors"""
    pass

class PermissionError(TriloError):
    """Permission-related errors"""
    pass

class ValidationError(TriloError):
    """Validation errors"""
    pass

def handle_errors(func: Callable) -> Callable:
    """Decorator to handle errors in async functions"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except discord.Forbidden as e:
            logger.error(f"Permission error in {func.__name__}: {e}")
            # Try to send error message to user if possible
            await _send_permission_error(args[0] if args else None, e)
        except discord.NotFound as e:
            logger.error(f"Resource not found in {func.__name__}: {e}")
        except discord.HTTPException as e:
            logger.error(f"HTTP error in {func.__name__}: {e}")
        except DatabaseError as e:
            logger.error(f"Database error in {func.__name__}: {e}")
            await _send_database_error(args[0] if args else None, e)
        except ValidationError as e:
            logger.error(f"Validation error in {func.__name__}: {e}")
            await _send_validation_error(args[0] if args else None, e)
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            await _send_generic_error(args[0] if args else None, e)
    return wrapper

async def _send_permission_error(interaction: Optional[discord.Interaction], error: Exception):
    """Send permission error message"""
    if interaction and hasattr(interaction, 'response'):
        try:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have the required permissions to perform this action.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="Required Permissions",
                value="• Manage Channels\n• Send Messages\n• Manage Messages\n• Add Reactions",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            pass

async def _send_database_error(interaction: Optional[discord.Interaction], error: Exception):
    """Send database error message"""
    if interaction and hasattr(interaction, 'response'):
        try:
            embed = discord.Embed(
                title="❌ Database Error",
                description="There was an error accessing the database. Please try again later.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            pass

async def _send_validation_error(interaction: Optional[discord.Interaction], error: Exception):
    """Send validation error message"""
    if interaction and hasattr(interaction, 'response'):
        try:
            embed = discord.Embed(
                title="❌ Validation Error",
                description=str(error),
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            pass

async def _send_generic_error(interaction: Optional[discord.Interaction], error: Exception):
    """Send generic error message"""
    if interaction and hasattr(interaction, 'response'):
        try:
            embed = discord.Embed(
                title="❌ Error",
                description="An unexpected error occurred. Please try again later.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            pass

def log_error(error: Exception, context: str = "", extra_info: dict = None):
    """Log an error with context and extra information"""
    error_msg = f"[{context}] {type(error).__name__}: {str(error)}"
    if extra_info:
        error_msg += f" | Extra: {extra_info}"
    
    logger.error(error_msg)
    logger.error(f"Traceback: {traceback.format_exc()}")

def safe_execute(func: Callable, *args, **kwargs) -> tuple[Any, Optional[Exception]]:
    """Safely execute a function and return result and error"""
    try:
        result = func(*args, **kwargs)
        return result, None
    except Exception as e:
        log_error(e, f"safe_execute({func.__name__})")
        return None, e

async def safe_execute_async(func: Callable, *args, **kwargs) -> tuple[Any, Optional[Exception]]:
    """Safely execute an async function and return result and error"""
    try:
        result = await func(*args, **kwargs)
        return result, None
    except Exception as e:
        log_error(e, f"safe_execute_async({func.__name__})")
        return None, e 