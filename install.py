#!/usr/bin/env python3
"""
Trilo Discord Bot Installation Script
Automates the complete setup process for the bot.
"""

import sys
import subprocess
import os
from pathlib import Path
import shutil

def print_banner():
    """Print installation banner"""
    print("=" * 60)
    print("🏈 Trilo Discord Bot - Installation Script")
    print("=" * 60)
    print()

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def create_virtual_environment():
    """Create a virtual environment"""
    print("\n📦 Creating virtual environment...")
    try:
        subprocess.check_call([sys.executable, "-m", "venv", "venv"])
        print("✅ Virtual environment created successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create virtual environment: {e}")
        return False

def install_dependencies():
    """Install required Python packages"""
    print("\n📦 Installing dependencies...")
    try:
        # Determine pip path based on OS
        if os.name == 'nt':  # Windows
            pip_path = "venv/Scripts/pip"
        else:  # Unix-like
            pip_path = "venv/bin/pip"
        
        subprocess.check_call([pip_path, "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating directories...")
    directories = [
        "data/databases",
        "data/scripts",
        "logs",
        "tests"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created {directory}")

def setup_environment_file():
    """Set up environment file"""
    print("\n🔧 Setting up environment file...")
    env_file = Path("secrets.env")
    example_file = Path("secrets.env.example")
    
    if not env_file.exists():
        if example_file.exists():
            shutil.copy(example_file, env_file)
            print("✅ Created secrets.env from template")
            print("⚠️  Please edit secrets.env with your actual tokens")
        else:
            print("⚠️  secrets.env.example not found, creating basic template")
            with open(env_file, 'w') as f:
                f.write("ENV=dev\n")
                f.write("DISCORD_TOKEN=your_discord_bot_token_here\n")
                f.write("OPENAI_API_KEY=your_openai_api_key_here\n")
    else:
        print("✅ secrets.env already exists")

def run_database_setup():
    """Run database setup scripts"""
    print("\n🗄️  Setting up databases...")
    scripts_dir = Path("data/scripts")
    
    if not scripts_dir.exists():
        print("⚠️  No database setup scripts found")
        return
    
    setup_scripts = list(scripts_dir.glob("trilo_setup_*.py"))
    if not setup_scripts:
        print("⚠️  No setup scripts found in data/scripts/")
        return
    
    # Determine python path based on OS
    if os.name == 'nt':  # Windows
        python_path = "venv/Scripts/python"
    else:  # Unix-like
        python_path = "venv/bin/python"
    
    for script in setup_scripts:
        try:
            print(f"Running {script.name}...")
            subprocess.check_call([python_path, str(script)])
            print(f"✅ {script.name} completed")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to run {script.name}: {e}")

def create_run_script():
    """Create a run script for easy bot startup"""
    print("\n🚀 Creating run script...")
    
    if os.name == 'nt':  # Windows
        run_script = "run_bot.bat"
        content = """@echo off
echo Starting Trilo Discord Bot...
venv\\Scripts\\python main.py
pause
"""
    else:  # Unix-like
        run_script = "run_bot.sh"
        content = """#!/bin/bash
echo "Starting Trilo Discord Bot..."
venv/bin/python main.py
"""
    
    with open(run_script, 'w') as f:
        f.write(content)
    
    if os.name != 'nt':  # Make executable on Unix-like systems
        os.chmod(run_script, 0o755)
    
    print(f"✅ Created {run_script}")

def print_next_steps():
    """Print next steps for the user"""
    print("\n" + "=" * 60)
    print("🎉 Installation Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Edit secrets.env with your Discord bot token and OpenAI API key")
    print("2. Invite your bot to a Discord server")
    print("3. Run the bot using one of these methods:")
    print()
    
    if os.name == 'nt':  # Windows
        print("   • Double-click run_bot.bat")
        print("   • Or run: venv\\Scripts\\python main.py")
    else:  # Unix-like
        print("   • Run: ./run_bot.sh")
        print("   • Or run: venv/bin/python main.py")
    
    print()
    print("For help and support:")
    print("• Use /trilo help in Discord for command help")
    print("• Check the README.md for detailed documentation")
    print("• Report issues on GitHub")
    print()
    print("Happy botting! 🏈")

def main():
    """Main installation function"""
    print_banner()
    
    # Check Python version
    if not check_python_version():
        print("\n❌ Installation failed: Python version incompatible")
        return False
    
    # Create virtual environment
    if not create_virtual_environment():
        print("\n❌ Installation failed: Could not create virtual environment")
        return False
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Installation failed: Could not install dependencies")
        return False
    
    # Create directories
    create_directories()
    
    # Setup environment file
    setup_environment_file()
    
    # Run database setup
    run_database_setup()
    
    # Create run script
    create_run_script()
    
    # Print next steps
    print_next_steps()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
