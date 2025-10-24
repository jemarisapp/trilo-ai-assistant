# 🤝 Contributing to Trilo

Thank you for your interest in contributing to Trilo! This document provides guidelines and information for contributors.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Guidelines](#contributing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Feature Requests](#feature-requests)

## 🤝 Code of Conduct

This project follows a code of conduct that we expect all contributors to follow:

- **Be respectful**: Treat everyone with respect and kindness
- **Be constructive**: Provide helpful feedback and suggestions
- **Be patient**: Remember that everyone is learning and growing
- **Be inclusive**: Welcome contributors from all backgrounds

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Discord Bot Token (for testing)
- Basic understanding of Discord bots and Python

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/yourusername/trilo-discord-bot.git
   cd trilo-discord-bot
   ```

3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/originalusername/trilo-discord-bot.git
   ```

## 🛠️ Development Setup

### Environment Setup

1. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp secrets.env.example secrets.env
   # Edit secrets.env with your test tokens
   ```

4. **Initialize databases**:
   ```bash
   python setup.py
   ```

### Testing Setup

1. **Create a test Discord server** for development
2. **Generate a bot token** from Discord Developer Portal
3. **Set up test data** using the setup scripts
4. **Run the bot** in development mode

## 📝 Contributing Guidelines

### What Can You Contribute?

- **Bug Fixes**: Fix issues reported in the issue tracker
- **New Features**: Add new functionality (check with maintainers first)
- **Documentation**: Improve README, code comments, or guides
- **Testing**: Add tests or improve test coverage
- **Performance**: Optimize existing code
- **UI/UX**: Improve user experience and interface

### Code Style

- **Python**: Follow PEP 8 style guidelines
- **Comments**: Add clear, helpful comments for complex logic
- **Docstrings**: Document functions and classes
- **Type Hints**: Use type hints where appropriate
- **Naming**: Use descriptive variable and function names

### Commit Messages

Use clear, descriptive commit messages:

```bash
# Good examples
git commit -m "Fix team assignment validation bug"
git commit -m "Add error handling for database connections"
git commit -m "Update README with new installation steps"

# Avoid
git commit -m "fix stuff"
git commit -m "WIP"
git commit -m "updates"
```

### Branch Naming

Use descriptive branch names:

```bash
# Feature branches
feature/add-user-roles
feature/improve-matchup-ui

# Bug fix branches
fix/team-assignment-bug
fix/database-connection-error

# Documentation branches
docs/update-readme
docs/add-contributing-guide
```

## 🔄 Pull Request Process

### Before Submitting

1. **Test your changes** thoroughly
2. **Update documentation** if needed
3. **Add tests** for new functionality
4. **Check for linting errors**:
   ```bash
   python -m flake8 .
   ```

### Pull Request Template

When creating a PR, include:

- **Description**: What changes were made and why
- **Type**: Bug fix, feature, documentation, etc.
- **Testing**: How the changes were tested
- **Screenshots**: If applicable, include screenshots
- **Breaking Changes**: Any breaking changes and migration steps

### Review Process

1. **Automated Checks**: CI/CD pipeline runs tests and checks
2. **Code Review**: Maintainers review the code
3. **Testing**: Changes are tested in a staging environment
4. **Approval**: Once approved, changes are merged

## 🐛 Issue Reporting

### Before Creating an Issue

1. **Search existing issues** to avoid duplicates
2. **Check if it's already fixed** in the latest version
3. **Gather information** about the problem

### Issue Template

When reporting bugs, include:

- **Description**: Clear description of the problem
- **Steps to Reproduce**: Detailed steps to reproduce the issue
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**: Python version, OS, bot version
- **Logs**: Relevant error messages or logs
- **Screenshots**: If applicable

### Bug Report Example

```markdown
## Bug Description
The `/teams assign-user` command fails when assigning users to teams with special characters.

## Steps to Reproduce
1. Create a team with name "Team A & B"
2. Try to assign a user to this team
3. Command fails with error

## Expected Behavior
User should be successfully assigned to the team.

## Actual Behavior
Command fails with "Invalid team name" error.

## Environment
- Python: 3.9.7
- OS: Windows 10
- Bot Version: 1.2.0
```

## 💡 Feature Requests

### Before Requesting a Feature

1. **Check existing issues** for similar requests
2. **Consider the scope** and complexity
3. **Think about use cases** and benefits
4. **Consider alternatives** or workarounds

### Feature Request Template

```markdown
## Feature Description
Brief description of the requested feature.

## Use Case
Why is this feature needed? What problem does it solve?

## Proposed Solution
How should this feature work? Any specific implementation ideas?

## Alternatives Considered
What other solutions were considered?

## Additional Context
Any other relevant information, screenshots, or examples.
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_teams.py

# Run with coverage
python -m pytest --cov=src tests/
```

### Writing Tests

- **Unit Tests**: Test individual functions and methods
- **Integration Tests**: Test command flows and interactions
- **Mock External Services**: Use mocks for Discord API calls
- **Test Edge Cases**: Include error conditions and edge cases

### Test Example

```python
import pytest
from unittest.mock import Mock, patch
from commands.teams import assign_user_command

@pytest.mark.asyncio
async def test_assign_user_success():
    # Mock interaction and database
    interaction = Mock()
    interaction.guild.id = "123456789"
    interaction.user.id = "987654321"
    
    with patch('utils.utils.get_db_connection') as mock_db:
        # Test the command
        await assign_user_command(interaction, "Team A", "user")
        
        # Assertions
        mock_db.assert_called_once()
        interaction.response.send_message.assert_called_once()
```

## 📚 Documentation

### Code Documentation

- **Docstrings**: Document all functions and classes
- **Comments**: Explain complex logic and algorithms
- **Type Hints**: Use type hints for better code clarity
- **README Updates**: Update README when adding features

### Documentation Standards

```python
def assign_user_to_team(interaction: discord.Interaction, team_name: str, user: discord.Member) -> bool:
    """
    Assign a user to a specific team.
    
    Args:
        interaction: Discord interaction object
        team_name: Name of the team to assign to
        user: Discord member to assign
        
    Returns:
        bool: True if assignment successful, False otherwise
        
    Raises:
        ValueError: If team name is invalid
        PermissionError: If user lacks required permissions
    """
    # Implementation here
    pass
```

## 🎯 Getting Help

### Resources

- **Discord**: Join our support server for real-time help
- **Issues**: Use GitHub issues for bug reports and feature requests
- **Discussions**: Use GitHub discussions for questions and ideas
- **Documentation**: Check the README and ARCHITECTURE.md files

### Community Guidelines

- **Be patient**: Maintainers are volunteers with limited time
- **Be specific**: Provide detailed information when asking for help
- **Be respectful**: Treat everyone with kindness and respect
- **Be helpful**: Help others when you can

## 🏆 Recognition

Contributors will be recognized in:

- **README**: Listed as contributors
- **Release Notes**: Mentioned in release announcements
- **Discord**: Special contributor role in support server
- **GitHub**: Listed in the contributors section

## 📄 License

By contributing to Trilo, you agree that your contributions will be licensed under the same MIT License that covers the project.

---

Thank you for contributing to Trilo! Your contributions help make dynasty fantasy football leagues more engaging and organized. 🏈
