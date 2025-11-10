"""
Command Knowledge Retriever
RAG-style retrieval system for command documentation
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
import re


# Load knowledge base
KNOWLEDGE_BASE_PATH = Path(__file__).parent / "command_knowledge_base.md"


def load_knowledge_base() -> str:
    """
    Load the command knowledge base from markdown file
    
    Returns:
        Knowledge base content as string
    """
    try:
        with open(KNOWLEDGE_BASE_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"[Command Retriever] Error loading knowledge base: {e}")
        return ""


def extract_command_sections(knowledge_base: str) -> Dict[str, str]:
    """
    Extract command sections from knowledge base
    
    Args:
        knowledge_base: Full knowledge base content
        
    Returns:
        Dictionary mapping section names to content
    """
    sections = {}
    current_section = None
    current_content = []
    
    lines = knowledge_base.split('\n')
    
    for line in lines:
        # Check for section headers (## or ###)
        if line.startswith('##'):
            # Save previous section
            if current_section:
                sections[current_section] = '\n'.join(current_content)
            
            # Start new section
            current_section = line.strip('#').strip()
            current_content = []
        else:
            if current_section:
                current_content.append(line)
    
    # Save last section
    if current_section:
        sections[current_section] = '\n'.join(current_content)
    
    return sections


def search_knowledge_base(query: str, topic: Optional[str] = None) -> str:
    """
    Search the knowledge base for relevant command information
    
    Args:
        query: User's query
        topic: Optional command topic to narrow search
        
    Returns:
        Relevant command documentation
    """
    knowledge_base = load_knowledge_base()
    if not knowledge_base:
        return "I'm sorry, I couldn't load the command documentation. Please use `/trilo help` for assistance."
    
    sections = extract_command_sections(knowledge_base)
    
    query_lower = query.lower()
    
    # If topic is provided, prioritize that section
    if topic:
        category = topic.split()[0] if topic else None
        if category:
            # Look for sections matching the category
            for section_name, content in sections.items():
                if category.lower() in section_name.lower():
                    # Check if this section has relevant info
                    if any(keyword in query_lower for keyword in ["request", "spend", "use", "upgrade"]):
                        if "request" in content.lower() or "spend" in content.lower():
                            return content
                    elif any(keyword in query_lower for keyword in ["points", "balance", "check"]):
                        if "my-points" in content.lower() or "points" in content.lower():
                            return content
    
    # Search for relevant sections based on keywords
    relevant_sections = []
    
    # Keywords to section mapping
    keyword_mapping = {
        "points": ["Attribute Point System", "attributes"],
        "spend": ["Attribute Point System", "attributes request"],
        "request": ["Attribute Point System", "attributes request"],
        "upgrade": ["Attribute Point System", "attributes request"],
        "give": ["Attribute Point System", "attributes give"],
        "approve": ["Attribute Point System", "attributes approve"],
        "deny": ["Attribute Point System", "attributes deny"],
        "team": ["Team Management"],
        "assign": ["Team Management", "teams assign"],
        "matchup": ["Matchup Commands"],
        "delete": ["Matchup Commands"],  # For matchup deletion queries
        "category": ["Matchup Commands"],  # Categories are part of matchups
        "record": ["Record Commands"],
        "message": ["Messaging Commands"],
        "settings": ["Settings Commands"],
        "admin": ["Admin Commands"],
        "help": ["Help Command", "General Usage Tips"]
    }
    
    # Find matching sections
    seen_sections = set()
    for keyword, section_names in keyword_mapping.items():
        if keyword in query_lower:
            for section_name in section_names:
                for full_section_name, content in sections.items():
                    if section_name.lower() in full_section_name.lower():
                        if full_section_name not in seen_sections:
                            relevant_sections.append((full_section_name, content))
                            seen_sections.add(full_section_name)
    
    # Return the most relevant section(s)
    if relevant_sections:
        # Combine relevant sections
        combined = "\n\n".join([f"## {name}\n{content}" for name, content in relevant_sections[:2]])
        return combined
    
    # If no specific match, return general help section
    # Try to find "General Usage Tips" or "Attribute Point System"
    for section_name, content in sections.items():
        if "General Usage Tips" in section_name or "Attribute Point System" in section_name:
            return content
    
    # Fallback: return attribute points section (most common)
    for section_name, content in sections.items():
        if "Attribute Point System" in section_name:
            return content
    
    return "Please use `/trilo help` for detailed command information."


def format_command_help(command_info: str, query: str) -> str:
    """
    Format command help information for AI response
    
    Args:
        command_info: Command documentation from knowledge base
        query: Original user query
        
    Returns:
        Formatted help text
    """
    # Extract the most relevant command from the documentation
    query_lower = query.lower()
    
    # Look for specific command examples
    if "spend" in query_lower or "use points" in query_lower or "request" in query_lower:
        # Extract /attributes request section
        match = re.search(r'#### `/attributes request`(.*?)(?=####|##|$)', command_info, re.DOTALL)
        if match:
            return f"To spend your attribute points, use the `/attributes request` command:\n\n{match.group(1).strip()}"
    
    if "check points" in query_lower or "my points" in query_lower or "how many points" in query_lower:
        # Extract /attributes my-points section
        match = re.search(r'#### `/attributes my-points`(.*?)(?=####|##|$)', command_info, re.DOTALL)
        if match:
            return f"To check your points, use:\n\n{match.group(1).strip()}"
    
    # Check for delete/matchup deletion queries
    if "delete" in query_lower and ("matchup" in query_lower or "category" in query_lower):
        # Extract /matchups delete section
        match = re.search(r'#### `/matchups delete`(.*?)(?=####|##|$)', command_info, re.DOTALL)
        if match:
            return f"To delete matchup categories, use the `/matchups delete` command:\n\n{match.group(1).strip()}"
    
    # Return relevant section
    return command_info[:2000]  # Limit length

