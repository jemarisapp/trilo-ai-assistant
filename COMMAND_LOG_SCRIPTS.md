# 🛠️ Trilo Script Management

Quick reference for managing your Discord bot's scripts, organized by category.

## 📊 **Analytics & Logging** (`data/scripts/logging/`)

### Quick Stats Overview
```bash
python3 data/scripts/logging/trilo_analyze_logs.py --stats-only
```

### Detailed Analysis (Last 7 Days)
```bash
python3 data/scripts/logging/trilo_analyze_logs.py --days 7
```

### Analysis for Specific Time Period
```bash
# Last 3 days
python3 data/scripts/logging/trilo_analyze_logs.py --days 3

# Last 30 days  
python3 data/scripts/logging/trilo_analyze_logs.py --days 30
```

## 🧹 **Database Cleanup** (`data/scripts/logging/`)

### Remove Duplicates
```bash
# Analyze duplicate entries first
python3 data/scripts/logging/trilo_deduplicate_logs.py --analyze

# Remove duplicate entries (keeps best result per timestamp + user + command, 3-second tolerance)
python3 data/scripts/logging/trilo_deduplicate_logs.py --clean
```

### Clean Up Orphaned Errors
```bash
# Remove duplicate error logs
python3 data/scripts/logging/trilo_cleanup_orphaned_errors.py
```

### Complete Cleanup
```bash
# Run all cleanup operations
python3 data/scripts/logging/trilo_auto_cleanup.py
```

## 🔧 **Database Setup** (`data/scripts/setup/`)

### Initialize Command Logging
```bash
# Set up the command logging database
python3 data/scripts/setup/trilo_setup_command_logging.py
```

### Setup Core Databases
```bash
# Teams database
python3 data/scripts/setup/trilo_setup_teams.py

# Attributes database  
python3 data/scripts/setup/trilo_setup_attributes.py

# Archetypes database
python3 data/scripts/setup/trilo_setup_archetypes.py

# Keys database
python3 data/scripts/setup/trilo_setup_keys.py
```

### Setup Sports Data
```bash
# NFL teams
python3 data/scripts/setup/trilo_setup_nfl_teams.py

# NFL matchups
python3 data/scripts/setup/trilo_setup_nfl_matchups.py

# CFB teams
python3 data/scripts/setup/trilo_setup_cfb_teams.py

# CFB matchups
python3 data/scripts/setup/trilo_setup_cfb_matchups.py

# General matchups
python3 data/scripts/setup/trilo_setup_matchups.py

# Rankings
python3 data/scripts/setup/trilo_setup_rankings.py
```

## 🔄 **Data Migration** (`data/scripts/migration/`)

### Migrate Teams
```bash
# Migrate teams to CFB format
python3 data/scripts/migration/trilo_migrate_teams_to_cfb.py
```

### Migrate Matchups
```bash
# Migrate matchups to CFB format
python3 data/scripts/migration/trilo_migrate_matchups_to_cfb.py
```

## 🛠️ **Maintenance** (`data/scripts/maintenance/`)

### Add Timestamps
```bash
# Add timestamp columns to existing tables
python3 data/scripts/maintenance/trilo_add_timestamps.py
```

### Generate Keys
```bash
# Generate encryption keys
python3 data/scripts/maintenance/trilo_generate_keys.py
```

### Remove Performance Metrics
```bash
# Remove performance_metrics table (one-time cleanup)
python3 data/scripts/maintenance/trilo_remove_performance_metrics.py
```

## 🗑️ **Database Management**

### Clear All Logs (Fresh Start)
```bash
# Delete the database
rm data/databases/trilo_command_logs.db

# Recreate it
python3 data/scripts/setup/trilo_setup_command_logging.py
```

### Reset Specific Database
```bash
# Remove specific database file
rm data/databases/trilo_teams.db

# Recreate it
python3 data/scripts/setup/trilo_setup_teams.py
```

## 📈 **Usage Examples**

### Daily Workflow
```bash
# Check today's stats
python3 data/scripts/logging/trilo_analyze_logs.py --stats-only

# Clean up any duplicates
python3 data/scripts/logging/trilo_deduplicate_logs.py --clean
```

### Weekly Maintenance
```bash
# Full analysis
python3 data/scripts/logging/trilo_analyze_logs.py --days 7

# Complete cleanup
python3 data/scripts/logging/trilo_auto_cleanup.py
```

### Fresh Installation
```bash
# Setup all databases
python3 data/scripts/setup/trilo_setup_command_logging.py
python3 data/scripts/setup/trilo_setup_teams.py
python3 data/scripts/setup/trilo_setup_attributes.py
python3 data/scripts/setup/trilo_setup_archetypes.py
python3 data/scripts/setup/trilo_setup_keys.py

# Add timestamps to existing data
python3 data/scripts/maintenance/trilo_add_timestamps.py
```

## 🎯 **Quick Reference**

| Category | Purpose | Location |
|----------|---------|----------|
| **Analytics** | View stats and reports | `data/scripts/logging/` |
| **Cleanup** | Remove duplicates and errors | `data/scripts/logging/` |
| **Setup** | Initialize databases | `data/scripts/setup/` |
| **Migration** | Move data between formats | `data/scripts/migration/` |
| **Maintenance** | Add features and utilities | `data/scripts/maintenance/` |

---

💡 **Tip**: All scripts are now organized by function. Use the folder structure to quickly find what you need!