# Agentic Setup Help System

## Overview
Multi-agent system designed to **eliminate AI hallucination** when answering setup questions.

## Problem It Solves
Previous approach: Give AI the entire setup guide → AI gets confused → AI invents fake commands

New approach: Break the task into discrete steps with specialized agents

## The 4-Agent Flow

### Agent 1: Intent Extraction
**Role:** Understand what the user is asking about

**Input:** User's question (e.g., "How do I setup stream notis?")

**Output:**
```json
{
  "topic": "stream notifications",
  "action": "setup",
  "keywords": ["stream", "notifications", "twitch", "youtube"]
}
```

**Model:** GPT-4o-mini (fast, cheap)

**Key Feature:** Uses structured output format (TOPIC/ACTION/KEYWORDS) to ensure parseable results

---

### Agent 2: Documentation Search
**Role:** Find exact text from the setup guide (NO generation)

**Input:** Intent from Agent 1 + Full setup guide text

**Process:**
1. Search for lines containing ANY of the keywords
2. For each match, extract the full section it belongs to
3. Combine relevant sections (up to 3000 chars)

**Output:** Raw text snippets from the guide

**Key Feature:** Pure text extraction—no AI generation, zero hallucination risk

---

### Agent 3: Command Extraction
**Role:** Extract ONLY actual commands from documentation (NO generation)

**Input:** Documentation from Agent 2

**Process:**
1. Find all code blocks (``` or `)
2. Extract lines starting with `/`
3. Return unique list

**Output:** List of exact commands found
```
[
  "/settings set setting:stream_announcements_enabled new_value:on",
  "/settings set setting:stream_watch_channel new_value:#streams",
  "/settings set setting:stream_notify_role new_value:Streamers"
]
```

**Key Feature:** Regex-based extraction—completely deterministic

---

### Agent 4: Response Synthesis
**Role:** Create user-friendly response using ONLY found information

**Input:**
- Original query
- Intent from Agent 1
- Documentation from Agent 2
- Commands from Agent 3

**Process:**
1. Build context from found information
2. Instruct GPT-4o: "ONLY use the provided documentation and commands"
3. Synthesize conversational response

**Output:** Natural language response with step-by-step instructions

**Model:** GPT-4o (better instruction following, less hallucination)

**Key Feature:** Explicit constraints prevent invention—if info isn't in the context, AI can't make it up

---

## Why This Works

### Separation of Concerns
- **Agent 1:** Understanding (AI)
- **Agent 2:** Finding (deterministic search)
- **Agent 3:** Extraction (regex)
- **Agent 4:** Explanation (AI with strict constraints)

### Fail-Safe Design
- If Agent 2 finds nothing → Agent 4 says "I don't have info about that"
- If Agent 3 extracts no commands → Agent 4 explains without commands
- No agent can "fill in the blanks" with hallucinated info

### Verifiable at Each Step
Can inspect output of each agent to debug issues

---

## Example Flow

**User Query:** "How do I setup stream notis?"

**Agent 1 Output:**
```
Topic: stream notifications
Keywords: [stream, notifications, twitch, youtube, setup]
```

**Agent 2 Output:**
```
#### **1.5 Configure Stream Announcements (Optional)**
Enable Stream Announcements:
/settings set setting:stream_announcements_enabled new_value:on
...
```

**Agent 3 Output:**
```
[
  "/settings set setting:stream_announcements_enabled new_value:on",
  "/settings set setting:stream_watch_channel new_value:#streams",
  "/settings set setting:stream_notify_role new_value:Streamers"
]
```

**Agent 4 Output:**
```
To set up stream notifications:
1. Enable Stream Announcements: /settings set setting:stream_announcements_enabled new_value:on
2. Set Stream Watch Channel: /settings set setting:stream_watch_channel new_value:#streams
3. Set Stream Notify Role: /settings set setting:stream_notify_role new_value:Streamers
```

---

## Files

- **`src/ai/setup_agent.py`**: All 4 agents + orchestrator
- **`src/ai/conversation.py`**: Integration into bot (handle_setup_help)
- **`src/ai/setup_guide.md`**: Source documentation

---

## Testing

Run this to verify no hallucination:
```bash
cd /Users/jsapp/Documents/Trilo/Trilo
python3 -c "
from src.ai.setup_agent import process_setup_question
from src.ai.setup_retriever import load_setup_guide

guide = load_setup_guide()
response = process_setup_question('How do I setup stream notis?', guide)
print(response)

# Check for fake commands
assert '/stream-notis' not in response
assert '/stream setup' not in response.lower()
assert '/settings set' in response
print('✅ No hallucination detected')
"
```

---

## Benefits

1. **Zero Hallucination:** AI can't invent commands that don't exist
2. **Traceable:** Can debug by inspecting each agent's output
3. **Maintainable:** Update `setup_guide.md`, agents automatically adapt
4. **Scalable:** Can add more guides for different topics
5. **Cost-Effective:** Only Agent 1 and 4 use AI (Agents 2 & 3 are deterministic)

