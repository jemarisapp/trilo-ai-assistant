"""
Setup Guide Retrieval System
Retrieves relevant sections from the comprehensive setup guide based on user queries
"""

import os
from pathlib import Path
from typing import List, Dict


def load_setup_guide() -> str:
    """Load the setup guide from markdown file"""
    guide_path = Path(__file__).parent / "setup_guide.md"
    
    if not guide_path.exists():
        return ""
    
    with open(guide_path, 'r', encoding='utf-8') as f:
        return f.read()


def extract_sections(guide_text: str) -> Dict[str, str]:
    """
    Extract sections from the setup guide
    
    Returns:
        Dictionary mapping section titles to content
    """
    sections = {}
    current_section = None
    current_content = []
    
    for line in guide_text.split('\n'):
        # Main section headers (## )
        if line.startswith('## '):
            # Save previous section
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()
            
            # Start new section
            current_section = line.replace('##', '').strip()
            current_content = [line]
        
        # Subsection headers (### )
        elif line.startswith('### '):
            if current_section:
                current_content.append(line)
        
        # Regular content
        else:
            if current_section:
                current_content.append(line)
    
    # Save last section
    if current_section:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections


def search_setup_guide(query: str) -> List[str]:
    """
    Search the setup guide for relevant sections
    
    Args:
        query: User's query text
        
    Returns:
        List of relevant section content
    """
    guide_text = load_setup_guide()
    if not guide_text:
        return []
    
    sections = extract_sections(guide_text)
    query_lower = query.lower()
    
    # Special handling for stream queries - extract just the stream subsection
    if any(keyword in query_lower for keyword in ["stream", "twitch", "youtube"]) and "notif" in query_lower:
        # Find the stream setup content specifically
        stream_content = []
        in_stream_section = False
        
        for line in guide_text.split('\n'):
            # Start capturing at 1.5
            if '#### **1.5 Configure Stream' in line:
                in_stream_section = True
                stream_content.append(line)
            # Stop at 1.6
            elif '#### **1.6' in line and in_stream_section:
                break
            elif in_stream_section:
                stream_content.append(line)
        
        if stream_content:
            return ['\n'.join(stream_content)]
    
    # Keywords to section mapping
    keywords = {
        # Getting started / general help
        "getting started": ["🎯 For First-Time Users", "👑 Commissioner Setup Guide"],
        "how to use": ["🎯 For First-Time Users", "🎮 Player Usage Guide"],
        "setup": ["👑 Commissioner Setup Guide", "🎉 Quick Start Checklist"],
        "configure": ["👑 Commissioner Setup Guide", "Step 1: Initial Configuration"],
        
        # Settings
        "settings": ["Step 1: Initial Configuration (`/settings`)"],
        "league type": ["Step 1: Initial Configuration (`/settings`)"],
        "commissioner role": ["Step 1: Initial Configuration (`/settings`)"],
        "record tracking": ["Step 1: Initial Configuration (`/settings`)"],
        
        # Teams
        "team": ["Step 2: Team Assignment (`/teams`)"],
        "assign": ["Step 2: Team Assignment (`/teams`)"],
        
        # Matchups
        "matchup": ["Step 3: Create Matchups (`/matchups`)"],
        "create matchup": ["Step 3: Create Matchups (`/matchups`)"],
        "ai matchup": ["Step 3: Create Matchups (`/matchups`)"],
        "image": ["Step 3: Create Matchups (`/matchups`)"],
        "game status": ["Step 3: Create Matchups (`/matchups`)"],
        "tag user": ["Step 3: Create Matchups (`/matchups`)"],
        
        # Attribute points
        "attribute": ["Step 4: Attribute Points System"],
        "point": ["Step 4: Attribute Points System"],
        "upgrade": ["Step 4: Attribute Points System"],
        "request": ["Step 4: Attribute Points System"],
        "approve": ["Step 4: Attribute Points System"],
        "deny": ["Step 4: Attribute Points System"],
        
        # Records
        "record": ["Step 5: Records Management"],
        "win": ["Step 5: Records Management"],
        "loss": ["Step 5: Records Management"],
        "standings": ["Step 5: Records Management"],
        
        # Messaging
        "announce": ["Step 6: Messaging & Announcements"],
        "advance": ["Step 6: Messaging & Announcements"],
        "message": ["Step 6: Messaging & Announcements"],
        
        # Player guide
        "player": ["🎮 Player Usage Guide"],
        "member": ["🎮 Player Usage Guide"],
        
        # AI features
        "ai": ["🤖 AI Conversation Features"],
        "natural language": ["🤖 AI Conversation Features"],
        "ask": ["🤖 AI Conversation Features"],
        "conversation": ["🤖 AI Conversation Features"],
        
        # Stream setup
        "stream": ["Step 1: Initial Configuration (`/settings`)"],
        "stream notification": ["Step 1: Initial Configuration (`/settings`)"],
        "stream notif": ["Step 1: Initial Configuration (`/settings`)"],
        "stream setup": ["Step 1: Initial Configuration (`/settings`)"],
        "notify stream": ["Step 1: Initial Configuration (`/settings`)"],
        "twitch": ["Step 1: Initial Configuration (`/settings`)"],
        "youtube": ["Step 1: Initial Configuration (`/settings`)"],
        
        # Advanced
        "advanced": ["🛠️ Advanced Features"],
        "delete": ["🛠️ Advanced Features"],
        "public": ["🛠️ Advanced Features"],
        "private": ["🛠️ Advanced Features"],
        
        # Best practices
        "best practice": ["📋 Best Practices"],
        "tip": ["📋 Best Practices"],
        "recommendation": ["📋 Best Practices"],
        
        # Common questions
        "question": ["❓ Common Questions"],
        "faq": ["❓ Common Questions"],
        
        # Quick start
        "checklist": ["🎉 Quick Start Checklist"],
        "quick start": ["🎉 Quick Start Checklist"],
    }
    
    # Find matching sections
    matching_sections = set()
    
    # Check for keyword matches
    for keyword, section_names in keywords.items():
        if keyword in query_lower:
            for section_name in section_names:
                matching_sections.add(section_name)
    
    # If no keyword matches, do a general search in section content
    if not matching_sections:
        for section_name, content in sections.items():
            # Check if query words appear in section content
            query_words = query_lower.split()
            content_lower = content.lower()
            
            # Count how many query words appear
            matches = sum(1 for word in query_words if len(word) > 3 and word in content_lower)
            
            # If 50%+ of query words match, include this section
            if matches >= len(query_words) * 0.5:
                matching_sections.add(section_name)
    
    # Return matching sections in order of appearance
    result = []
    for section_name in sections.keys():
        if section_name in matching_sections:
            result.append(sections[section_name])
    
    # Limit to top 3 most relevant sections to avoid overwhelming the AI
    return result[:3]


def format_setup_help(sections: List[str]) -> str:
    """
    Format retrieved setup guide sections for AI consumption
    
    Args:
        sections: List of section content
        
    Returns:
        Formatted help text
    """
    if not sections:
        return "No specific setup guide sections found. Refer to general bot knowledge."
    
    formatted = "**Relevant Setup Guide Sections:**\n\n"
    
    for i, section in enumerate(sections, 1):
        # Trim very long sections
        if len(section) > 1500:
            section = section[:1500] + "\n\n...(section truncated)"
        
        formatted += f"{section}\n\n"
        
        # Add separator between sections
        if i < len(sections):
            formatted += "---\n\n"
    
    return formatted


def get_quick_start_guide() -> str:
    """Get the quick start checklist specifically"""
    guide_text = load_setup_guide()
    sections = extract_sections(guide_text)
    
    # Return the quick start checklist and first-time users section
    result = []
    for section_name in ["🎯 For First-Time Users", "🎉 Quick Start Checklist"]:
        if section_name in sections:
            result.append(sections[section_name])
    
    return "\n\n---\n\n".join(result) if result else ""


def get_full_commissioner_guide() -> str:
    """Get the full commissioner setup process"""
    guide_text = load_setup_guide()
    sections = extract_sections(guide_text)
    
    # Return all commissioner-related sections
    commissioner_sections = [
        "👑 Commissioner Setup Guide",
        "Step 1: Initial Configuration (`/settings`)",
        "Step 2: Team Assignment (`/teams`)",
        "Step 3: Create Matchups (`/matchups`)",
        "📋 Best Practices",
        "🎉 Quick Start Checklist"
    ]
    
    result = []
    for section_name in commissioner_sections:
        if section_name in sections:
            result.append(sections[section_name])
    
    return "\n\n---\n\n".join(result) if result else ""


def get_player_guide() -> str:
    """Get the player/member usage guide"""
    guide_text = load_setup_guide()
    sections = extract_sections(guide_text)
    
    # Return player-focused sections
    player_sections = [
        "🎮 Player Usage Guide",
        "🤖 AI Conversation Features"
    ]
    
    result = []
    for section_name in player_sections:
        if section_name in sections:
            result.append(sections[section_name])
    
    return "\n\n---\n\n".join(result) if result else ""

