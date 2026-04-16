# UI Visual Guide - Context Management Features

## Before & After Comparison

### BEFORE (No Context)
```
┌─────────────────────────────────────────────────────────────┐
│  🌍 Country Information AI                                  │
└─────────────────────────────────────────────────────────────┘

    What would you like to know?
    Ask me anything about countries around the world

    💭 What is the population of Germany?
    💭 What currency does Japan use?
    💭 Tell me about France's geography
    💭 What languages are spoken in Switzerland?

┌─────────────────────────────────────────────────────────────┐
│  Ask a question about any country...               [Send]   │
└─────────────────────────────────────────────────────────────┘

❌ Each question is isolated
❌ No conversation memory
❌ Can't ask "What about France?"
```

### AFTER (With Context)
```
┌─────────────────────────────────────────────────────────────┐
│  🌍 Country Information AI          🟢 Context Active       │
└─────────────────────────────────────────────────────────────┘

    What would you like to know?
    Ask me anything about countries around the world. 
    I remember our conversation!

    💭 What is the population of Germany?
    💭 What currency does Japan use?
    💭 Tell me about France's geography
    💭 What is its capital?  ← NEW: Shows contextual question

┌─────────────────────────────────────────────────────────────┐
│  Ask a question about any country...               [Send]   │
└─────────────────────────────────────────────────────────────┘

✅ Maintains conversation context
✅ Remembers previous countries
✅ Understands "it", "its", "that"
```

---

## Context Indicator States

### ⚪ New Session (Gray)
```
┌─────────────────────────────────────────────────────────────┐
│  🌍 Country Information AI          ⚪ New Session          │
└─────────────────────────────────────────────────────────────┘

Status: No active session
Behavior: Next question starts new conversation
Context: None available
```

### 🟢 Context Active (Green)
```
┌─────────────────────────────────────────────────────────────┐
│  🌍 Country Information AI          🟢 Context Active       │
└─────────────────────────────────────────────────────────────┘

Status: Session ID stored
Behavior: Questions use conversation history
Context: Previous messages available
```

---

## Example Conversation Flow

### Conversation 1: Basic Follow-ups

```
┌─────────────────────────────────────────────────────────────┐
│  🌍 Country Information AI          ⚪ New Session          │
│                                     🌙  🗑️                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  👤 You                                                      │
│  What is the population of Germany?                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  🤖 AI Assistant                                            │
│  Germany has a population of approximately 83 million       │
│  people.                                                     │
│                                                              │
│  📍 Germany  📊 population  ⏱️ 820ms                        │
└─────────────────────────────────────────────────────────────┘

Status changed to: 🟢 Context Active

┌─────────────────────────────────────────────────────────────┐
│  👤 You                                                      │
│  What about France?                                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  🤖 AI Assistant                                            │
│  France has a population of approximately 67 million        │
│  people.                                                     │
│                                                              │
│  📍 France  📊 population  ⏱️ 780ms                         │
└─────────────────────────────────────────────────────────────┘

Context: ✅ Understood "France" means "population of France"

┌─────────────────────────────────────────────────────────────┐
│  👤 You                                                      │
│  What is its capital?                                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  🤖 AI Assistant                                            │
│  The capital of France is Paris.                            │
│                                                              │
│  📍 France  📊 capital  ⏱️ 750ms                            │
└─────────────────────────────────────────────────────────────┘

Context: ✅ Resolved "its" = France (from previous question)
```

---

### Conversation 2: Multi-Country Context

```
┌─────────────────────────────────────────────────────────────┐
│  🌍 Country Information AI          🟢 Context Active       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  👤 You                                                      │
│  Tell me about Japan's population and capital               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  🤖 AI Assistant                                            │
│  Japan has a population of approximately 125 million and    │
│  its capital is Tokyo.                                       │
│                                                              │
│  📍 Japan  📊 population, capital  ⏱️ 890ms                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  👤 You                                                      │
│  What currency does it use?                                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  🤖 AI Assistant                                            │
│  Japan uses the Japanese Yen (¥).                           │
│                                                              │
│  📍 Japan  📊 currency  ⏱️ 760ms                            │
└─────────────────────────────────────────────────────────────┘

Context: ✅ "it" resolved to Japan

┌─────────────────────────────────────────────────────────────┐
│  👤 You                                                      │
│  How about South Korea?                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  🤖 AI Assistant                                            │
│  South Korea uses the South Korean Won (₩).                 │
│                                                              │
│  📍 South Korea  📊 currency  ⏱️ 780ms                      │
└─────────────────────────────────────────────────────────────┘

Context: ✅ Inferred same question type (currency) from context
```

---

## Button Functions

### 🌙 / ☀️ Toggle Dark Mode
```
Light Mode (☀️)           Dark Mode (🌙)
┌──────────────┐         ┌──────────────┐
│ White BG     │   →     │ Dark BG      │
│ Dark text    │         │ Light text   │
│ Light borders│         │ Dark borders │
└──────────────┘         └──────────────┘
```

### 🗑️ Clear Chat
```
Before Clear              After Clear
┌──────────────┐         ┌──────────────┐
│ 🟢 Active    │   →     │ ⚪ New        │
│              │         │              │
│ [Messages]   │         │ [Empty]      │
│ [Context]    │         │ [No context] │
│              │         │              │
│ Session: abc │         │ Session: None│
└──────────────┘         └──────────────┘

Effect:
- Clears all messages from screen
- Removes session_id from state
- Next question starts NEW session
- Context history reset
```

---

## Metadata Display

### Response Metadata Bar
```
┌─────────────────────────────────────────────────────────────┐
│  📍 Germany                  Country name                    │
│  📊 population, area         Fields retrieved                │
│  ⏱️ 820ms                     Execution time                  │
└─────────────────────────────────────────────────────────────┘
```

**Legend:**
- 📍 Country queried
- 📊 Data fields returned (max 3 shown)
- ⏱️ API response time

---

## Session Lifecycle Visualization

```
User Opens App
    ↓
⚪ New Session
    ↓
User asks question
    ↓
Backend creates session_id: "abc-123"
    ↓
Frontend saves: st.session_state.session_id = "abc-123"
    ↓
🟢 Context Active
    ↓
User asks follow-up
    ↓
Frontend sends session_id: "abc-123"
    ↓
Backend retrieves context from MongoDB
    ↓
🟢 Context Active (continues)
    ↓
User clicks 🗑️
    ↓
Frontend clears: session_id = None
    ↓
⚪ New Session
    ↓
Next question starts fresh
```

---

## Error States

### Backend Disconnected
```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️ Cannot connect to backend API.                          │
│  Make sure it's running on http://localhost:8000           │
└─────────────────────────────────────────────────────────────┘
```

### Rate Limited
```
┌─────────────────────────────────────────────────────────────┐
│  🤖 AI Assistant                                            │
│  ❌ Rate limit exceeded. Please wait a moment and try       │
│  again.                                                      │
└─────────────────────────────────────────────────────────────┘
```

### Out of Scope
```
┌─────────────────────────────────────────────────────────────┐
│  🤖 AI Assistant                                            │
│  I am only allowed to assist you with Country information  │
│  but I am doing quite well thank you.                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Tips for Best Experience

### ✅ DO:
- Ask follow-up questions naturally
- Use pronouns like "it", "its", "that country"
- Ask "What about X?" for similar queries
- Keep conversations focused on countries

### ❌ DON'T:
- Don't expect context after clearing chat (🗑️)
- Don't assume context works without green indicator (🟢)
- Don't ask unrelated questions mid-conversation

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Enter | Send message (from input field) |
| Esc | Clear input field |
| Ctrl+K | Focus input field (browser default) |

---

## Mobile Responsiveness

### Desktop (> 900px)
```
┌────────────────────────────────┐
│  Header                        │
├────────────────────────────────┤
│                                │
│      Chat (max 900px)          │
│                                │
├────────────────────────────────┤
│  Input                         │
└────────────────────────────────┘
```

### Mobile (< 600px)
```
┌──────────────┐
│  Header      │
├──────────────┤
│              │
│  Chat        │
│  (full       │
│   width)     │
│              │
├──────────────┤
│  Input       │
└──────────────┘
```

All context features work identically on mobile!

---

## Summary

**UI Changes:**
- ✅ Visual session indicator (🟢/⚪)
- ✅ Context-aware messaging
- ✅ Session management (clear button)
- ✅ Updated welcome message
- ✅ Contextual example questions

**User Benefits:**
- 🎯 Natural conversations
- 💡 Smart context handling
- 👁️ Visual feedback
- 🚀 Seamless experience

**Technical:**
- Session ID stored in browser memory
- Automatic session creation
- Context maintained across requests
- Clean session reset on clear

---

**Ready to test?** Run: `streamlit run ui.py`
