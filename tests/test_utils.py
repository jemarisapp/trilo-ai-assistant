"""
Test utilities and helper functions
"""
import pytest
from unittest.mock import Mock, patch
import tempfile
import os
from pathlib import Path

# Mock Discord objects for testing
class MockInteraction:
    def __init__(self, guild_id="123456789", user_id="987654321"):
        self.guild = Mock()
        self.guild.id = guild_id
        self.user = Mock()
        self.user.id = user_id
        self.response = Mock()
        self.followup = Mock()

class MockGuild:
    def __init__(self, guild_id="123456789"):
        self.id = guild_id
        self.name = "Test Server"

class MockUser:
    def __init__(self, user_id="987654321"):
        self.id = user_id
        self.name = "Test User"

@pytest.fixture
def temp_db_dir():
    """Create a temporary directory for test databases"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

@pytest.fixture
def mock_interaction():
    """Create a mock Discord interaction for testing"""
    return MockInteraction()

@pytest.fixture
def mock_guild():
    """Create a mock Discord guild for testing"""
    return MockGuild()

@pytest.fixture
def mock_user():
    """Create a mock Discord user for testing"""
    return MockUser()

def assert_embed_fields(embed, expected_fields):
    """Helper function to assert embed field values"""
    for field_name, expected_value in expected_fields.items():
        field = next((f for f in embed.fields if f.name == field_name), None)
        assert field is not None, f"Field '{field_name}' not found in embed"
        assert field.value == expected_value, f"Field '{field_name}' value mismatch"

def assert_embed_title(embed, expected_title):
    """Helper function to assert embed title"""
    assert embed.title == expected_title, f"Expected title '{expected_title}', got '{embed.title}'"

def assert_embed_description(embed, expected_description):
    """Helper function to assert embed description"""
    assert embed.description == expected_description, f"Expected description '{expected_description}', got '{embed.description}'"
