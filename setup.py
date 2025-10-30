#!/usr/bin/env python3
"""
Trilo Discord Bot Setup Script
Automates the installation and setup process for the bot.
"""

import sys
import subprocess
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    directories = [
        "data/databases",
        "data/scripts",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created {directory}")

def check_env_file():
    """Check if secrets.env exists"""
    env_file = Path("secrets.env")
    if not env_file.exists():
        print("⚠️  secrets.env file not found")
        print("Please create a secrets.env file with:")
        print("ENV=dev   # or prod")
        print("DEV_DISCORD_TOKEN=your_dev_discord_token_here")
        print("DISCORD_TOKEN=your_live_discord_token_here")
        print("OPENAI_API_KEY=your_openai_api_key_here")
        return False
    else:
        print("✅ secrets.env file found")
        return True

def run_database_setup():
    """Run database setup scripts"""
    print("🗄️  Setting up databases...")
    scripts_dir = Path("data/scripts")
    
    if not scripts_dir.exists():
        print("⚠️  No database setup scripts found")
        return
    
    setup_scripts = list(scripts_dir.glob("trilo_setup_*.py"))
    if not setup_scripts:
        print("⚠️  No setup scripts found in data/scripts/")
        return
    
    for script in setup_scripts:
        try:
            print(f"Running {script.name}...")
            subprocess.check_call([sys.executable, str(script)])
            print(f"✅ {script.name} completed")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to run {script.name}: {e}")

def main():
    """Main setup function"""
    print("🚀 Trilo Discord Bot Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        print("\n❌ Setup failed: Python version incompatible")
        return
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Setup failed: Dependencies installation failed")
        return
    
    # Create directories
    create_directories()
    
    # Check environment file
    env_ok = check_env_file()
    
    # Run database setup
    run_database_setup()
    
    print("\n" + "=" * 40)
    if env_ok:
        print("✅ Setup completed successfully!")
        print("\nTo run the bot:")
        print("  python main.py      # Main bot file")
    else:
        print("⚠️  Setup completed, but please configure secrets.env")
        print("\nAfter configuring secrets.env, run:")
        print("  python main.py")

if __name__ == "__main__":
    main() 
    