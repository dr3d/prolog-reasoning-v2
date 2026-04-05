---
layout: post
title: "Local LLM Integration with MCP"
description: "Setting up structured reasoning with LM Studio"
level: "Beginner"
domain: "LLM Tools & Integration"
duration: "15 minutes"
---
# Local LLM Integration with MCP

**Setting up structured reasoning with LM Studio**

---

## 🎓 Learning Objectives

By the end of this module, you'll understand:
- What MCP is and why it matters
- How to set up Prolog Reasoning as a tool in LM Studio
- How to use it to give your AI perfect memory
- Real examples of queries your AI can now answer reliably
- How to build your own knowledge base

---

## 🧠 The Setup: Your AI's New Superpower

Remember how we learned about:
1. **Course 1**: AI has bad memory 🧠❌
2. **Course 2**: We fix that with knowledge bases 📚✅
3. **Course 3**: Errors teach us things 🎓
4. **Now**: We give YOUR local AI all of this! 🚀

Here's what we're building today:

```
Your Local LLM (in LM Studio)
        ↓ (via MCP tool)
Prolog Reasoning (with perfect memory + logic)
        ↓
Deterministic Answers (100% accurate)
```

**What this means in practice:**
- You: "Does my knowledge base say John is allergic to peanuts?"
- LLM uses the Prolog tool → Queries the knowledge base
- Prolog: "Yes, 100% certain" or "No, not in the system"
- LLM: "According to your knowledge base..." (no guessing!)

---

## 💡 What is MCP? (The Simple Version)

**MCP = Model Context Protocol**

Think of it like giving your AI a new skill:

### Without MCP
```
You: "Is John allergic to anything?"
AI: *thinks hard* "Hmm, maybe? I think I saw something 
about John and allergies in my training data... 
possibly peanuts? Or was that Alice? I'm not sure..."
Result: ❌ Uncertain guessing
```

### With MCP (Our Tool)
```
You: "Is John allergic to anything?"
AI: *uses Prolog tool* 
    "Checking knowledge base..."
    → System: "John is allergic to peanuts (severe)"
AI: "Yes! According to the knowledge base, John is 
allergic to peanuts with 100% certainty."
Result: ✅ Certain answer
```

---

## 🛠️ Setup: 5 Simple Steps

### Step 1: Have LM Studio Running

1. Download and install [LM Studio](https://lmstudio.ai/) if you don't have it
2. Open it up
3. Load your favorite local model (Mistral, Llama, etc.)

### Step 2: Get Prolog Reasoning

```bash
# Clone the repo (one time)
git clone https://github.com/dr3d/prolog-reasoning-v2.git
cd prolog-reasoning-v2

# Install dependencies (one time)
pip install -r requirements.txt
```

Done! 🎉

### Step 3: Test the Tool (Optional but Recommended)

```bash
# This verifies everything works before LM Studio
python src/mcp_server.py --test

# You should see:
# ✅ MCP Server initialized successfully
# Available Tools:
#   • query_prolog: Query the knowledge base
#   • list_known_facts: Show what's known
#   • explain_error: Help with errors
#   • show_system_info: System info
```

If you see that, skip to Step 5! ✅

### Step 4: Configure LM Studio (If Step 3 Worked)

1. Open **LM Studio**
2. Click ⚙️ **Settings** (bottom right)
3. Click **Developer**
4. Click **Model Context Protocol (MCP)**
5. You'll see a configuration area

**Add this to the "servers" section:**

```json
{
  "prolog": {
    "command": "python",
    "args": ["D:\\path\\to\\prolog-reasoning-v2\\src\\mcp_server.py", "--stdio"]
  }
}
```

**Important**: Replace `D:\\path\\to\\prolog-reasoning-v2` with your actual path!

**On Windows:**
- Path should look like: `C:\\Users\\YourName\\Downloads\\prolog-reasoning-v2`
- Use backslashes `\\` or forward slashes `/` (both work)

**On Mac/Linux:**
- Path should look like: `/Users/yourname/projects/prolog-reasoning-v2`

### Step 5: Restart and Test! 🎉

1. Close and reopen LM Studio
2. Start a chat with your AI
3. Look for the "Prolog" tool in the available tools list
4. Try a message like:

```
I uploaded my family data. Can you check if John's parent 
is Alice using the Prolog tool? (Use the query_prolog tool)
```

Your AI should now use the tool! 🚀

---

## 🎮 Using It: Real Examples

### Example 1: Your AI Checks Facts

**You**: Using the knowledge base, tell me about John's family.

**What happens:**
1. LLM thinks "I need to use the Prolog tool"
2. LLM calls: `query_prolog({"query": "Who is John's parent?"})`
3. Prolog responds: `{"status": "success", "answer": "Alice"}`
4. LLM says: "According to the knowledge base, John's parent is Alice."

**The magic:** No guessing! Prolog is certain!

### Example 2: Your AI Discovers Errors 

**You**: Is Charlie in the system? Check with the tool.

**What happens:**
1. LLM calls: `query_prolog({"query": "Tell me about Charlie"})`
2. Prolog responds: `{"status": "validation_error", "explanation": "I don't know who 'charlie' is. System only knows: john, alice, bob"}`
3. LLM says: "The system doesn't have information about Charlie. Known people: John, Alice, Bob. Would you like to ask about one of them?"

**The magic:** Error messages help the AI understand what to do next!

### Example 3: Your AI Explores What's Known

**You**: What facts are in the knowledge base?

**What happens:**
1. LLM calls: `list_known_facts({})`
2. Prolog responds with all known entities and relationships
3. LLM can now make smart decisions based on what's available

---

## 📚 Building Your Own Knowledge Base

Once you understand the basics, you can add your own facts!

### Example: Medical Allergy Tracker

Edit `prolog/core.pl` and add:

```prolog
% Your patients
patient(alice).
patient(bob).

% Their allergies
allergic_to(alice, peanuts, severe).
allergic_to(bob, shellfish, moderate).

% A rule: If someone has a severe allergy, flag it
at_risk(Patient, Allergen) :- allergic_to(Patient, Allergen, severe).
```

Now your AI can query this!

**You**: "Is Alice at risk for any allergies?"

**LLM** (using Prolog tool):
- Calls: `query_prolog({"query": "What is Alice allergic to?"})`
- Gets: `peanuts (severe)`
- Says: "Yes, Alice has a **severe** peanut allergy. This is high-risk."

### Example: Access Control

```prolog
% Users and roles
user(alice).
role(alice, admin).

% Permissions
can_access(User, Resource) :- role(User, admin).
can_access(User, Resource) :- granted_permission(User, Resource).

% Specific permissions
granted_permission(bob, shared_files).
```

Your AI can now answer:
- "Can Alice access the admin panel?"
- "What can Bob access?"
- "Who has admin privileges?"

---

## 🎯 Why This Matters for Beginners

### Before (Without Tools)
```
Human: "Did I tell you I'm allergic to peanuts?"
AI: *checks training data* "Hmm, you MIGHT have 
mentioned allergies once... possibly? Maybe peanuts? 
I'm 40% sure?"
Result: Confusion 😕
```

### After (With This Tool)
```
Human: "Did I tell you I'm allergic to peanuts?"
AI: *checks knowledge base* "Yes! Your allergy 
profile says you have a SEVERE peanut allergy. 
100% confidence."
Result: Safety ✅ and Relief 😊
```

**For healthcare, finance, safety-critical apps:** This difference is everything!

---

## ⚠️ Common Mistakes (And How to Avoid Them)

### Mistake 1: Asking About Things Not in the KB

```
Wrong: "Tell me about Charlie's favorite food"
AI checks: "I don't know Charlie"
You think: "This tool is broken!"

Right: "First, who is in the system?" (LLM uses list_known_facts)
AI: "John, Alice, Bob"
You: "Great, tell me about John's family"
```

**Lesson:** Always check what's known first!

### Mistake 2: Adding Facts Wrong

```
Wrong: "John is Alice's parent" (random order)
Right: parent(alice, john). (correct order in Prolog)
```

**Lesson:** Order matters in relationships!

### Mistake 3: Forgetting to Restart

```
Wrong: Modify prolog/core.pl, but don't restart server
Wrong: LLM still sees old facts

Right: Modify prolog/core.pl
Right: Restart the MCP server
Right: Chat with the fresh knowledge
```

**Lesson:** Changes need to be reloaded!

---

## 🚀 What You Can Build

### Home Automation
```prolog
device(smart_light).
device(thermostat).
location(kitchen).
installed_at(smart_light, kitchen).

% Query: "What devices do we have in the kitchen?"
```

### Gift Manager
```prolog
person(alice).
person(bob).
likes(alice, books).
likes(alice, coffee).
allergic_to(bob, peanuts).

% Query: "What can I NOT gift to Bob?"
% Query: "What does Alice like?"
```

### Pet Care
```prolog
pet(fluffy, cat).
pet(rex, dog).
feeds_per_day(fluffy, 2).
feeds_per_day(rex, 1).

% Query: "How often should I feed fluffy?"
```

---

## 📝 Quick Reference: Tool Commands

Your AI can use these tools:

### 1. Query the Knowledge Base
```
Tool: query_prolog
Input: {"query": "Who is John's parent?"}
Use when: You want to ask a logical question
```

### 2. See What's Known
```
Tool: list_known_facts
Input: {}
Use when: You want to explore the knowledge base
```

### 3. Understand Errors
```
Tool: explain_error
Input: {"error_message": "undefined_entity"}
Use when: Something went wrong and you need help
```

### 4. Get System Info
```
Tool: show_system_info
Input: {}
Use when: You want to understand capabilities
```

---

## 🎓 Next Level: Debugging

### If the tool isn't showing up in LM Studio:

**In Windows Powershell**, test manually:

```powershell
python src/mcp_server.py --test
# Should show all 4 tools

python src/mcp_server.py
# Should show interactive prompt (type "help")
```

### If queries return errors:

1. Check spelling (typos matter!)
2. Use `list_known_facts` to verify entities exist
3. Try simpler queries first
4. Read the error message—it's helpful!

---

## 💡 Key Takeaways

✅ **MCP is just a tool you give your AI**
- Like giving someone a calculator
- Or a dictionary
- Or a notebook

✅ **This tool gives perfect memory**
- No hallucinations
- No forgetting
- No approximations

✅ **You control the knowledge**
- You decide what's in the knowledge base
- Modify `prolog/core.pl` to change facts
- Your AI can now query YOUR data

✅ **It's local (no internet!)**
- Runs on your machine
- Your data stays private
- No API calls needed

---

## 🎉 You're Ready!

You now have:
- ✅ A local LLM (from LM Studio)
- ✅ Perfect memory (knowledge base)
- ✅ Logical reasoning (Prolog engine)
- ✅ Tool integration (MCP)

**This is professional-grade AI setup!** 🚀

---

## 📚 Continue Your Learning

1. **[01 - LLM Memory Magic](01-llm-memory-magic.md)** - Why memory matters
2. **[02 - Knowledge Bases 101](02-knowledge-bases-101.md)** - How to structure facts
3. **[03 - Learning from Failures](03-learning-from-failures.md)** - Error handling
4. **[04 - This Course!](04-lm-studio-mcp.md)** - Putting it all together
5. **[LM Studio MCP Guide](../docs/lm-studio-mcp-guide.md)** - Technical details

---

## 🤔 Remember...

The best AI isn't the one that guesses best. It's the one that **knows for sure** when it knows, and **says "I don't know"** when it doesn't.

Congratulations! You've built exactly that. 🎓✨

---

**Ready to teach your local LLM to remember like an human expert? Set up is literally 5 steps. Let's go!** 🚀
