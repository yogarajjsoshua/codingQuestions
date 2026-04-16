# Testing Guide - Context Management UI

## Quick Start

### 1. Start Backend
```bash
# Terminal 1
python -m uvicorn app.main:app --reload --port 8000

# Wait for:
# ✓ mongodb_connected
# ✓ Application startup complete
```

### 2. Start Frontend
```bash
# Terminal 2
streamlit run ui.py

# Opens browser automatically at http://localhost:8501
```

---

## Test Suite

### Test 1: Basic Context Flow ✅

**Steps:**
1. Open UI (should show ⚪ New Session)
2. Type: "What is the population of Germany?"
3. Send and wait for response
4. **Verify:** Indicator changes to 🟢 Context Active
5. Type: "What about France?"
6. Send and wait
7. **Verify:** Response talks about France's population
8. Type: "What is its capital?"
9. **Verify:** Response says "The capital of France is Paris"

**Expected Result:**
- ✅ Each response understands context
- ✅ Indicator stays green throughout
- ✅ "France" and "its" are resolved correctly

---

### Test 2: Pronoun Resolution ✅

**Steps:**
1. Clear chat (click 🗑️)
2. **Verify:** Indicator changes to ⚪ New Session
3. Ask: "Tell me about Japan"
4. **Verify:** 🟢 Context Active appears
5. Ask: "What is its capital?"
6. **Verify:** Response mentions Tokyo
7. Ask: "What currency does it use?"
8. **Verify:** Response mentions Yen

**Expected Result:**
- ✅ "its" resolves to Japan
- ✅ "it" resolves to Japan
- ✅ Context maintained through pronouns

---

### Test 3: Multi-turn Conversation ✅

**Long conversation to test context persistence:**

```
Q1: "What is Brazil's population?"
   → Expect: Population of Brazil
   → Verify: 🟢 appears

Q2: "What about its capital?"
   → Expect: Brasília
   → Verify: Understands "its" = Brazil

Q3: "What currency does it use?"
   → Expect: Brazilian Real
   → Verify: "it" = Brazil

Q4: "Tell me about Argentina"
   → Expect: Info about Argentina
   → Verify: Context switches to Argentina

Q5: "What is its capital?"
   → Expect: Buenos Aires
   → Verify: "its" = Argentina (new context)

Q6: "Compare it to Brazil"
   → Expect: Comparison
   → Verify: "it" = Argentina, remembers Brazil
```

**Expected Result:**
- ✅ Context maintained through 6 questions
- ✅ Proper country switching
- ✅ Correct pronoun resolution

---

### Test 4: Session Reset ✅

**Steps:**
1. Have a conversation (3-4 questions)
2. Note the countries discussed
3. Click 🗑️ Clear Chat button
4. **Verify:** 
   - Messages disappear
   - Indicator changes to ⚪ New Session
5. Ask about a country mentioned earlier using "it"
   - Example: If you discussed France, ask "What is its capital?"
6. **Expected:** Should NOT remember France, asks for clarification

**Expected Result:**
- ✅ Chat cleared visually
- ✅ Session reset (⚪ indicator)
- ✅ No context from previous conversation
- ✅ New conversation starts fresh

---

### Test 5: Dark Mode Toggle ✅

**Steps:**
1. Click 🌙 button (top right)
2. **Verify:** UI switches to dark theme
3. Click ☀️ button
4. **Verify:** UI switches back to light theme
5. **Check:** Context indicator still visible in both modes

**Expected Result:**
- ✅ Smooth theme transition
- ✅ All text remains readable
- ✅ Context indicator visible in both modes
- ✅ Session persists through theme changes

---

### Test 6: Backend Connection Check ✅

**Steps:**
1. Stop backend server (Ctrl+C in Terminal 1)
2. Try to ask a question in UI
3. **Verify:** Error message appears:
   ```
   ⚠️ Cannot connect to backend API.
   Make sure it's running on http://localhost:8000
   ```
4. Restart backend
5. Ask question again
6. **Verify:** Works normally

**Expected Result:**
- ✅ Clear error message when backend down
- ✅ Automatic recovery when backend restarts
- ✅ No crashes or freezes

---

### Test 7: Out-of-Scope Query ✅

**Steps:**
1. Ask: "How are you doing today?"
2. **Verify:** Response is:
   ```
   I am only allowed to assist you with Country information 
   but I am doing quite well thank you.
   ```
3. Ask: "What is the population of Germany?" (valid question)
4. **Verify:** Normal response returns
5. **Check:** Context still works for follow-ups

**Expected Result:**
- ✅ Out-of-scope handled gracefully
- ✅ Context not broken by invalid questions
- ✅ Can resume normal conversation

---

### Test 8: Rapid Questions ✅

**Steps:**
1. Ask 3 questions quickly (without waiting for responses)
2. **Note:** Only first question sends, others queue
3. Wait for response
4. **Verify:** Can ask second question
5. **Verify:** Context maintained properly

**Expected Result:**
- ✅ No race conditions
- ✅ Questions process in order
- ✅ Context maintained through queue

---

### Test 9: Long Session (Summarization) ✅

**Steps:**
1. Ask 6+ questions about different countries:
   ```
   1. "Population of India?"
   2. "What about China?"
   3. "Capital of Brazil?"
   4. "France's currency?"
   5. "Germany's area?"
   6. "Japan's timezone?"
   ```
2. Check backend logs after 5th message
3. **Look for:** `summarization_triggered`
4. Continue conversation
5. **Verify:** Context still works

**Expected Result:**
- ✅ Summarization happens in background
- ✅ No noticeable delay for user
- ✅ Context still maintained
- ✅ Token optimization working

**Backend Logs to Watch:**
```
INFO: context_retrieved messages_count=5
INFO: conversation_saved
INFO: summarization_triggered total_messages=5
INFO: summarization_complete tokens_saved=300
```

---

### Test 10: Multiple Browser Sessions ✅

**Steps:**
1. Open UI in Chrome
2. Start conversation, note 🟢 indicator
3. Open UI in Firefox (new browser)
4. **Verify:** New session (⚪ indicator)
5. Have different conversation in Firefox
6. Return to Chrome
7. **Verify:** Original context still works

**Expected Result:**
- ✅ Each browser has independent session
- ✅ Sessions don't interfere
- ✅ Context isolated per browser

---

## Monitoring & Debugging

### Frontend (Browser Console)

Press F12 to open Developer Tools, watch Console for:

```javascript
// No errors should appear
// Network tab should show:
POST /api/v1/query
Status: 200 OK
Response: { session_id: "...", answer: "..." }
```

### Backend (Terminal Logs)

Watch for these log messages:

```bash
# Good signs:
✓ mongodb_connected
✓ context_retrieved session_id=abc123
✓ conversation_saved
✓ query_success

# Watch for:
⚠ context_not_found  # Normal for first message
⚠ summarization_triggered  # Every 5 messages
```

### MongoDB (Atlas Dashboard)

1. Log into MongoDB Atlas
2. Browse Collections → `country_agent` → `conversations`
3. Look for documents with your session_id
4. Verify conversations array is growing
5. Check summary field after 5+ messages

---

## Performance Benchmarks

### Expected Timings:

| Operation | Time | Indicator |
|-----------|------|-----------|
| First query (no context) | 800-1000ms | ⏱️ |
| Follow-up (with context) | 750-850ms | ⏱️ |
| Context retrieval | +10-20ms | (in total) |
| Background save | 50-100ms | (async) |
| Summarization | 1-2s | (background) |

### Response Time Components:

```
Total: ~850ms
├─ Context Retrieval: 15ms
├─ Intent Identification: 350ms (Gemini call)
├─ Tool Invocation: 200ms (REST API)
└─ Answer Synthesis: 285ms (Gemini call)
```

---

## Common Issues & Solutions

### Issue 1: Indicator Stays Gray (⚪)

**Symptoms:**
- Indicator never turns green
- Follow-ups don't work

**Check:**
1. Backend logs for `session_id` in response
2. Browser console for errors
3. MongoDB connection status

**Solution:**
```bash
# Restart backend
python -m uvicorn app.main:app --reload --port 8000

# Check .env has MONGODB_CONNECTION_STRING
# Verify MongoDB Atlas is accessible
```

---

### Issue 2: Context Not Working

**Symptoms:**
- Indicator is green (🟢)
- But follow-ups don't understand context

**Check:**
1. Backend logs: `context_retrieved` appears?
2. MongoDB has conversations?
3. Session ID matches?

**Debug:**
```bash
# Check backend logs
tail -f logs.txt | grep context_retrieved

# Expected:
# context_retrieved session_id=abc123 messages_count=2
```

---

### Issue 3: Slow Responses

**Symptoms:**
- ⏱️ shows > 2000ms
- UI feels sluggish

**Check:**
1. MongoDB Atlas region (use closest)
2. Internet connection
3. Gemini API rate limits

**Solution:**
```bash
# Check MongoDB latency
ping your-cluster.mongodb.net

# Reduce context:
# In .env: RECENT_MESSAGES_COUNT=2
```

---

### Issue 4: UI Freezes

**Symptoms:**
- Input not responding
- Can't click buttons

**Solution:**
```bash
# Force refresh: Ctrl+F5 (or Cmd+R on Mac)
# If persists, restart Streamlit:
Ctrl+C
streamlit run ui.py
```

---

## Success Criteria Checklist

Run through these to verify everything works:

- [ ] ⚪ Shows on first load
- [ ] 🟢 Appears after first question
- [ ] Follow-up questions work
- [ ] Pronouns resolve correctly
- [ ] 🗑️ clears chat and resets session
- [ ] Dark mode toggle works
- [ ] Metadata displays (country, fields, time)
- [ ] Error handling works (backend down)
- [ ] Out-of-scope handled gracefully
- [ ] Multiple questions maintain context
- [ ] Session persists across page refresh
- [ ] Context resets on clear
- [ ] Performance is acceptable (< 1s responses)

---

## Final Verification

### Quick Smoke Test (2 minutes):

```bash
# Terminal 1: Start backend
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2: Start frontend  
streamlit run ui.py

# Browser: Run this conversation
1. "What is the population of Germany?"
   ✓ Response received, 🟢 appears

2. "What about France?"
   ✓ Understands to get France's population

3. "What is its capital?"
   ✓ Responds with "Paris"

4. Click 🗑️
   ✓ Chat clears, ⚪ appears

5. "What is the capital of Japan?"
   ✓ New session, no confusion with France
```

**If all 5 steps pass → Everything works! 🎉**

---

## Next Steps

1. ✅ Run smoke test
2. ✅ Try longer conversations (5+ turns)
3. ✅ Test edge cases (errors, out-of-scope)
4. ✅ Monitor MongoDB for data
5. ✅ Check backend logs for summarization
6. 🚀 Deploy to production!

---

**Questions or issues?** Check:
- `FRONTEND_UPDATES.md` - Implementation details
- `UI_VISUAL_GUIDE.md` - Visual examples
- `CONTEXT_MANAGEMENT.md` - Technical architecture
- `CONTEXT_QUICK_START.md` - Setup guide

**Happy testing! 🎉**
