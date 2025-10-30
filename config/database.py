"""
Database configuration and connection settings
"""
import os
from pathlib import Path

class DatabaseConfig:
    """Centralized database configuration"""
    
    # Base directory for the project
    BASE_DIR = Path(__file__).parent.parent
    
    # Database directory
    DATA_DIR = BASE_DIR / "data" / "databases"
    
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Database file paths - Uniform naming convention
    DATABASES = {
        "keys": DATA_DIR / "trilo_keys.db",
        "teams": DATA_DIR / "trilo_teams.db", 
        "matchups": DATA_DIR / "trilo_matchups.db",
        "attributes": DATA_DIR / "trilo_attributes.db",

        "archetypes": DATA_DIR / "trilo_archetypes.db"
    }
    
    @classmethod
    def get_db_path(cls, db_name: str) -> str:
        """Get the absolute path for a database"""
        if db_name not in cls.DATABASES:
            raise ValueError(f"Unknown database: {db_name}")
        return str(cls.DATABASES[db_name])
    
    @classmethod
    def get_all_paths(cls) -> dict:
        """Get all database paths as a dictionary"""
        return {name: str(path) for name, path in cls.DATABASES.items()}
    
    @classmethod
    def ensure_data_dir(cls):
        """Ensure the data directory exists"""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True) 
        