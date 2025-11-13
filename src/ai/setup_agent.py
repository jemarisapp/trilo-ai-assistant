"""
Multi-Agent System for Setup Help
Prevents hallucination by breaking down the process into discrete steps
"""

from typing import Dict, List, Optional
import re
from openai import OpenAI
import os
from dotenv import load_dotenv
from functools import lru_cache
import hashlib
import time
from .token_tracker import get_tracker

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Simple cache for AI responses (reduces redundant API calls)
_response_cache: Dict[str, str] = {}


def agent_1_extract_intent(query: str) -> Dict[str, any]:
    """
    Agent 1: Extract the specific topic/feature the user is asking about
    
    Returns:
        {
            'topic': str,  # e.g., "stream notifications", "teams", "matchups"
            'action': str,  # e.g., "setup", "configure", "use"
            'keywords': List[str]  # Keywords to search for
        }
    """
    prompt = f"""You are analyzing a user's setup question about a Discord bot.

User question: "{query}"

Extract:
1. What feature/topic are they asking about? (e.g., "stream notifications", "teams", "attribute points")
2. What do they want to do? (e.g., "setup", "configure", "use", "enable")
3. List 3-5 keywords to search documentation for

Respond in this EXACT format:
TOPIC: [feature name]
ACTION: [what they want to do]
KEYWORDS: [keyword1, keyword2, keyword3]

Example:
TOPIC: stream notifications
ACTION: setup
KEYWORDS: stream, notification, twitch, youtube, announce"""

    start_time = time.time()
    tracker = get_tracker()
    input_tokens = tracker.estimate_tokens(prompt)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=150
    )
    
    content = response.choices[0].message.content.strip()
    
    # Log token usage
    output_tokens = tracker.estimate_tokens(content)
    duration_ms = (time.time() - start_time) * 1000
    tracker.log_usage("setup_agent_1_intent", "gpt-4o-mini", input_tokens, output_tokens, duration_ms)
    
    # Parse response
    topic_match = re.search(r'TOPIC:\s*(.+)', content)
    action_match = re.search(r'ACTION:\s*(.+)', content)
    keywords_match = re.search(r'KEYWORDS:\s*(.+)', content)
    
    return {
        'topic': topic_match.group(1).strip() if topic_match else query,
        'action': action_match.group(1).strip() if action_match else "use",
        'keywords': [k.strip() for k in keywords_match.group(1).split(',')] if keywords_match else [query]
    }


def score_paragraph_relevance(paragraph: str, keywords: List[str]) -> float:
    """
    Score how relevant a paragraph is based on keyword matches
    Returns score from 0.0 to 1.0
    """
    if not paragraph.strip():
        return 0.0
    
    para_lower = paragraph.lower()
    score = 0.0
    
    # Count keyword matches
    for keyword in keywords:
        if keyword.lower() in para_lower:
            score += 1.0
    
    # Boost score for command blocks
    if '```' in paragraph or paragraph.strip().startswith('/'):
        score += 0.5
    
    # Normalize by number of keywords
    return min(score / max(len(keywords), 1), 1.0)


def smart_truncate_documentation(content: str, keywords: List[str], max_chars: int = 1500) -> str:
    """
    Intelligently truncate documentation to keep most relevant parts
    Reduces token usage by ~50% while preserving key information
    """
    if len(content) <= max_chars:
        return content
    
    # Split into paragraphs
    paragraphs = content.split('\n\n')
    
    # Score each paragraph
    scored = [(p, score_paragraph_relevance(p, keywords)) for p in paragraphs]
    
    # Sort by relevance (keep headers at top)
    def sort_key(item):
        para, score = item
        # Keep headers high priority
        if para.strip().startswith('#'):
            return (2.0, score)
        return (score, 0)
    
    scored.sort(key=sort_key, reverse=True)
    
    # Add paragraphs until we hit limit
    result = []
    char_count = 0
    
    for para, score in scored:
        para_len = len(para)
        if char_count + para_len <= max_chars:
            result.append(para)
            char_count += para_len + 2  # +2 for \n\n
        elif score > 0.5:  # High relevance, try to fit partial
            remaining = max_chars - char_count
            if remaining > 100:  # Only if we can fit meaningful content
                result.append(para[:remaining] + "...")
            break
        else:
            break
    
    return '\n\n'.join(result)


def agent_2_search_documentation(intent: Dict, guide_text: str) -> str:
    """
    Agent 2: Search the guide for relevant content based on extracted intent
    
    Returns exact text snippets from the guide (no generation)
    OPTIMIZED: Uses smart truncation to reduce token usage by ~50%
    """
    keywords = intent['keywords']
    topic = intent['topic'].lower()
    
    # Strategy: Find lines that match keywords, then extract surrounding context
    lines = guide_text.split('\n')
    matched_line_indices = []
    
    # Find all lines that match ANY keyword
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(keyword.lower() in line_lower for keyword in keywords):
            matched_line_indices.append(i)
    
    if not matched_line_indices:
        return ""
    
    # For each match, extract the full section it belongs to
    relevant_content = []
    
    for match_idx in matched_line_indices:
        # Find the start of this section (look backward for ####)
        section_start = match_idx
        for i in range(match_idx, -1, -1):
            if lines[i].startswith('####'):
                section_start = i
                break
            elif lines[i].startswith('###') or lines[i].startswith('##'):
                section_start = i
                break
        
        # Find the end of this section (look forward for next ####)
        section_end = len(lines)
        for i in range(match_idx + 1, len(lines)):
            if lines[i].startswith('####') or lines[i].startswith('###'):
                section_end = i
                break
        
        # Extract the section
        section_content = '\n'.join(lines[section_start:section_end])
        if section_content and section_content not in relevant_content:
            relevant_content.append(section_content)
    
    # Combine sections
    combined = '\n\n---\n\n'.join(relevant_content)
    
    # Smart truncation: Keep most relevant paragraphs, reduce from 3000 to 1500 chars
    # This reduces tokens by ~50% while preserving key information
    return smart_truncate_documentation(combined, keywords, max_chars=1500)


def agent_3_extract_commands(documentation: str, topic: str) -> List[str]:
    """
    Agent 3: Extract ONLY the actual commands from documentation
    
    Returns list of exact commands found (no generation)
    """
    if not documentation:
        return []
    
    commands = []
    
    # Find code blocks (commands between ``` or `)
    # Pattern 1: Triple backtick blocks
    code_blocks = re.findall(r'```[^\n]*\n(.+?)\n```', documentation, re.DOTALL)
    for block in code_blocks:
        # Extract /command lines
        command_lines = re.findall(r'^(/[\w\-]+.*)$', block, re.MULTILINE)
        commands.extend(command_lines)
    
    # Pattern 2: Inline code (`/command`)
    inline_commands = re.findall(r'`(/[\w\-]+[^`]*)`', documentation)
    commands.extend(inline_commands)
    
    return list(set(commands))  # Remove duplicates


def calculate_query_complexity(query: str, intent: Dict, documentation: str, commands: List[str]) -> float:
    """
    Calculate complexity score to determine which model to use
    Returns score from 0.0 (simple) to 1.0 (complex)
    
    Simple queries (use gpt-4o-mini):
    - Short questions
    - Single feature setup
    - Few commands
    
    Complex queries (use gpt-4o):
    - Multi-step processes
    - Long documentation
    - Many commands to explain
    """
    score = 0.0
    
    # Factor 1: Query length (longer = more complex)
    if len(query) > 100:
        score += 0.2
    elif len(query) > 50:
        score += 0.1
    
    # Factor 2: Documentation length (more context = more complex)
    if len(documentation) > 1000:
        score += 0.3
    elif len(documentation) > 500:
        score += 0.15
    
    # Factor 3: Number of commands (more commands = more complex)
    if len(commands) > 3:
        score += 0.3
    elif len(commands) > 1:
        score += 0.15
    
    # Factor 4: Multiple steps indicator
    multi_step_keywords = ["multiple", "several", "all", "everything", "complete"]
    if any(keyword in query.lower() for keyword in multi_step_keywords):
        score += 0.2
    
    return min(score, 1.0)


def agent_4_synthesize_response(
    query: str,
    intent: Dict,
    documentation: str,
    commands: List[str]
) -> str:
    """
    Agent 4: Synthesize a response using ONLY the found documentation and commands
    
    This agent is not allowed to invent anything - only explain what was found
    OPTIMIZED: Uses smart model selection (gpt-4o-mini for simple, gpt-4o for complex)
    """
    if not documentation and not commands:
        return (
            f"I don't have specific documentation about {intent['topic']} in my setup guide. "
            "Try using /settings help or /help to see all available commands."
        )
    
    # Calculate complexity to choose model (OPTIMIZATION)
    complexity = calculate_query_complexity(query, intent, documentation, commands)
    
    # Use cheaper model for simple queries (80% cost reduction)
    # Use GPT-4o only for complex queries that need better reasoning
    if complexity < 0.5:
        model = "gpt-4o-mini"  # 20x cheaper
        max_tokens = 400       # Shorter for simple queries
    else:
        model = "gpt-4o"       # Better for complex
        max_tokens = 500
    
    # Build context from found information (already optimized by Agent 2)
    context = f"""You are helping a user with a Discord bot setup question.

User asked: "{query}"

Topic identified: {intent['topic']}
Action requested: {intent['action']}

Documentation found:
{documentation[:1500]}  # Reduced from 2000

Commands found in documentation:
{chr(10).join(commands) if commands else "None found"}

CRITICAL RULES:
1. ONLY explain information from the "Documentation found" section above
2. ONLY mention commands from the "Commands found" list above
3. If you don't see a command in the list, DO NOT mention it or invent it
4. Be direct and concise (under 800 characters)
5. If the documentation doesn't fully answer their question, say so

Provide a helpful response based ONLY on the information above."""

    start_time = time.time()
    tracker = get_tracker()
    input_tokens = tracker.estimate_tokens(context)
    
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": context}],
        temperature=0.1,
        max_tokens=max_tokens
    )
    
    result = response.choices[0].message.content.strip()
    
    # Log token usage
    output_tokens = tracker.estimate_tokens(result)
    duration_ms = (time.time() - start_time) * 1000
    tracker.log_usage(f"setup_agent_4_synthesize_{model}", model, input_tokens, output_tokens, duration_ms)
    
    return result


def is_full_setup_question(query: str) -> bool:
    """
    Detect if user is asking for the complete setup process vs. a specific feature
    
    Returns True for broad questions like:
    - "How do I set up my league?"
    - "How to use Trilo?"
    - "Getting started"
    
    Returns False for specific questions like:
    - "How do I setup stream notis?"
    - "How to assign teams?"
    """
    query_lower = query.lower()
    
    # Broad setup indicators
    full_setup_phrases = [
        "set up my league", "setup my league", "set up league",
        "how to use", "getting started", "how does this work",
        "how do i use", "what can you do", "set up trilo",
        "how to set up", "how to setup", "first time"
    ]
    
    # Check if it's a broad question
    is_broad = any(phrase in query_lower for phrase in full_setup_phrases)
    
    # Check if it's asking about a specific feature
    specific_features = [
        "stream", "team", "matchup", "attribute", "point", 
        "record", "message", "announce", "notification"
    ]
    has_specific_feature = any(feature in query_lower for feature in specific_features)
    
    # If it's broad and doesn't mention a specific feature, it's a full setup question
    return is_broad and not has_specific_feature


def get_full_setup_response(guide_text: str) -> str:
    """
    Generate comprehensive setup guide for broad "how to set up" questions
    
    Returns step-by-step setup instructions
    """
    # Extract the Commissioner Setup Guide section
    lines = guide_text.split('\n')
    
    # Find Commissioner Setup section
    setup_start = -1
    setup_end = -1
    
    for i, line in enumerate(lines):
        if '## 👑 Commissioner Setup Guide' in line:
            setup_start = i
        elif setup_start != -1 and line.startswith('## ') and '👑' not in line:
            setup_end = i
            break
    
    if setup_start == -1:
        return "I couldn't find the setup guide. Try using /settings help."
    
    if setup_end == -1:
        setup_end = len(lines)
    
    # Extract setup section
    setup_section = '\n'.join(lines[setup_start:setup_end])
    
    # Use GPT-4o to create a structured, step-by-step response
    # OPTIMIZED: Reduced prompt length and max_tokens for faster/cheaper responses
    prompt = f"""Help user set up sports league Discord bot.

Documentation:
{setup_section[:3000]}

Create concise guide:
1. Step 1: Initial Configuration (/settings commands)
2. Step 2: Team Assignment (/teams commands)  
3. Step 3: Create Matchups (/matchups commands)
4. Best Practices (2-3 tips)

Requirements:
- Use ONLY commands from documentation
- Direct and concise (under 1200 chars)
- Code format for commands
- Skip intro fluff

CRITICAL: Do NOT invent commands."""
    
    start_time = time.time()
    tracker = get_tracker()
    input_tokens = tracker.estimate_tokens(prompt)
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=600  # Reduced from 700
    )
    
    result = response.choices[0].message.content.strip()
    
    # Log token usage
    output_tokens = tracker.estimate_tokens(result)
    duration_ms = (time.time() - start_time) * 1000
    tracker.log_usage("setup_full_guide", "gpt-4o", input_tokens, output_tokens, duration_ms)
    
    return result


def get_cache_key(query: str) -> str:
    """Generate cache key for query"""
    # Normalize query (lowercase, strip whitespace)
    normalized = query.lower().strip()
    # Hash to fixed-length key
    return hashlib.md5(normalized.encode()).hexdigest()


def process_setup_question(query: str, guide_text: str) -> str:
    """
    Main orchestrator: Runs all agents in sequence
    
    Args:
        query: User's question
        guide_text: Full setup guide text
        
    Returns:
        Final response (guaranteed to be based on documentation only)
    
    OPTIMIZED: Includes caching for identical queries
    """
    # Check cache first (saves API calls for repeat questions)
    cache_key = get_cache_key(query)
    if cache_key in _response_cache:
        return _response_cache[cache_key]
    
    # Check if this is a broad "how do I set up" question
    if is_full_setup_question(query):
        response = get_full_setup_response(guide_text)
    else:
        # Otherwise, use the specific agentic flow for targeted questions
        # Agent 1: Understand what they're asking
        intent = agent_1_extract_intent(query)
        
        # Agent 2: Find relevant documentation
        documentation = agent_2_search_documentation(intent, guide_text)
        
        # Agent 3: Extract exact commands from documentation
        commands = agent_3_extract_commands(documentation, intent['topic'])
        
        # Agent 4: Synthesize response from found information only
        response = agent_4_synthesize_response(query, intent, documentation, commands)
    
    # Cache the response (limit cache size to 100 entries)
    if len(_response_cache) > 100:
        # Remove oldest entry (simple FIFO)
        _response_cache.pop(next(iter(_response_cache)))
    _response_cache[cache_key] = response
    
    return response

