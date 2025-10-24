# 🏈 Trilo - Sports League Discord Bot

A comprehensive Discord bot designed specifically for dynasty fantasy football leagues, featuring team management, matchup automation, attribute points, and advanced analytics. Built using AI-assisted development to rapidly prototype and deliver a production-ready product.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Discord.py](https://img.shields.io/badge/discord.py-2.4.0-blue.svg)
![License](https://img.shields.io/badge/license-All%20Rights%20Reserved-red.svg)
![AI-Powered](https://img.shields.io/badge/AI-Powered%20Development-purple.svg)

![AI-Assited-Development](https://img.shields.io/badge/AI-Assited-Development-purple.svg)

![Trilo Bot Header](images/header.jpg)

## 📖 Project Overview

**For a detailed product-focused overview of Trilo, including the problem, strategy, and AI-assisted development process, please see my [Product Overview Document](OVERVIEW.md).**

This comprehensive overview showcases the intersection of product management, AI leverage, and technical execution—demonstrating how strategic use of AI can accelerate product development while maintaining focus on user needs and business value.

## ✨ Features

### 🎮 Core Features
- **Team Management**: Assign users to teams, track ownership, manage league structure
- **Matchup Automation**: Auto-generate weekly matchups, create Discord channels, sync records
- **Attribute Point System**: Award points, manage upgrade requests, track player development
- **Win/Loss Records**: Automatic record tracking, manual adjustments, league standings
- **Messaging Tools**: Custom announcements, advance notifications, automated communications

### 🧪 Advanced Features
- **Ability Lab Dashboard**: Interactive web interface for player ability analysis
- **AI Upgrade Assistant**: Personalized upgrade recommendations
- **Subscription Management**: Free, Core, and Pro tiers with feature gating
- **Analytics & Logging**: Comprehensive usage tracking and performance monitoring
- **Privacy Compliant**: GDPR-compliant data handling with minimal data collection

### 🔧 Technical Features
- **Multi-Database Architecture**: Separate databases for different data types
- **Command Logging**: Track usage patterns and performance metrics
- **Automated Cleanup**: Self-maintaining database with duplicate removal
- **Error Handling**: Comprehensive error tracking and recovery
- **Scalable Design**: Built to handle multiple servers and large leagues

## 🤖 AI-Powered Development

This project showcases the power of AI-assisted product development:

- **Rapid Prototyping**: Used AI to quickly iterate through feature concepts and user flows
- **Code Generation**: Leveraged AI to generate boilerplate code and complex logic
- **Documentation**: AI-assisted creation of comprehensive technical documentation
- **Testing Strategy**: AI-generated test cases and edge case identification
- **User Experience**: AI-optimized command structures and help systems

**Result**: Delivered a production-ready product 10x faster than traditional development methods while maintaining enterprise-level quality and documentation standards.

## 📁 Project Structure

```
trilo-discord-bot/
├── commands/                 # Discord slash commands
│   ├── admin.py             # Server management commands
│   ├── teams.py             # Team assignment commands
│   ├── matchups.py          # Matchup automation
│   ├── points.py            # Attribute point system
│   ├── records.py           # Win/loss tracking
│   ├── message.py           # Messaging tools
│   ├── settings.py          # Server configuration
│   └── ability_lab.py       # Ability lab integration
├── config/                  # Configuration files
│   ├── database.py          # Database configuration
│   └── settings.py          # Bot settings
├── data/                    # Data storage
│   ├── databases/           # SQLite database files
│   └── scripts/             # Database management scripts
├── src/                     # Core bot functionality
│   ├── bot.py               # Main bot class
│   └── events/              # Event handlers
├── utils/                   # Utility functions
│   ├── command_logger.py    # Command logging system
│   ├── entitlements.py      # Subscription management
│   └── utils.py             # Helper functions
└── main.py                  # Application entry point
```

## 🎯 Command Overview

### Admin Commands
- `/admin trial` - Start 10-day free trial
- `/admin purchase` - View premium plans
- `/admin setup-league` - Create league structure
- `/admin guide` - Setup walkthrough

### Team Management
- `/teams assign-user` - Assign user to team
- `/teams list-all` - View all assignments
- `/teams who-has` - Check team ownership

### Matchup Automation
- `/matchups create` - Generate weekly matchups
- `/matchups tag-users` - Auto-tag participants
- `/matchups sync-records` - Update with current records

### Attribute Points (Pro Feature)
- `/attributes give` - Award points to users
- `/attributes request` - Request player upgrade
- `/attributes approve-request` - Approve upgrade

### Records & Analytics
- `/records check-record` - View team record
- `/records view-all-records` - League standings
- `/ability-lab` - Access interactive dashboard

## 🔧 Configuration

### Environment Variables
Create a `secrets.env` file with:
```env
ENV=dev
DISCORD_TOKEN=your_discord_bot_token
OPENAI_API_KEY=your_openai_api_key
```

### Server Settings
Configure your server with:
- Commissioner roles
- Record tracking preferences
- Channel assignments
- Notification settings

## 📊 Database Schema

The bot uses multiple SQLite databases:
- **teams.db**: Team assignments and ownership
- **matchups.db**: Matchup data and scheduling
- **attributes.db**: Point system and requests
- **archetypes.db**: Player archetype data
- **keys.db**: Subscription and access management

## 🛠️ Development

### Running Tests
```bash
# Analyze command logs
python data/scripts/logging/trilo_analyze_logs.py --stats-only

# Clean up duplicates
python data/scripts/logging/trilo_deduplicate_logs.py --clean
```

### Database Management
```bash
# Setup all databases
python data/scripts/setup/trilo_setup_command_logging.py
python data/scripts/setup/trilo_setup_teams.py
# ... (see COMMAND_LOG_SCRIPTS.md for full list)

# Run maintenance
python data/scripts/logging/trilo_auto_cleanup.py
```

## 🔒 Privacy & Security

- **Minimal Data Collection**: Only command usage, timestamps, and success/failure status
- **No Personal Data**: No message content, usernames, or personal information stored
- **Local Storage**: All data stored in encrypted SQLite databases
- **GDPR Compliant**: Follows EU privacy regulations
- **Automatic Cleanup**: Logs automatically deleted after 30 days

See [PRIVACY_POLICY.md](PRIVACY_POLICY.md) for complete details.

## 📈 Analytics

The bot includes comprehensive analytics:
- Command usage statistics
- Performance monitoring
- Error tracking and reporting
- User engagement metrics
- Feature adoption rates

## 📄 License

This project is licensed under All Rights Reserved - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Use `/trilo help` in Discord for command help
- **Issues**: Report bugs or request features via GitHub Issues
- **Discord**: Join our support server for real-time help

## 🎉 Acknowledgments

- Built with [discord.py](https://github.com/Rapptz/discord.py)
- AI features powered by [OpenAI](https://openai.com/)
- Dashboard built with [Streamlit](https://streamlit.io/)

---

**Trilo** - The Dynasty League Assistant 🏈

*Demonstrating how AI can accelerate product development while maintaining focus on user needs and business value. This project showcases the intersection of product management, AI leverage, and technical execution.*
