```markdown
# ViGo Dev

**Native Desktop IDE for ViGo Development**

ViGo Dev is a standalone desktop application that combines a code editor, AI coding assistant, and project manager into one native window — built with PyWebView, Monaco Editor, and the ViGo engine.

---

## Features

### Project Management
- Create, open, and import ViGo projects via native folder picker
- Projects are stored in `vigo-dev/Projects/` with symlink support for external directories
- Remembers last opened project and file across sessions

### File Browser
- Lazy-loaded directory tree with expand/collapse
- Right-click context menu: New File, New Folder, Rename, Delete
- Supported file types: `.vigo`, `.py`, `.js`, `.html`, `.css`, `.json`, `.md`, `.txt`

### Code Editor (Monaco Editor)
- ViGo syntax highlighting (30+ keywords)
- ViGo autocomplete with snippets (Fun as, if, loop, for, switch, class, try, const, enum, etc.)
- Python, JavaScript, HTML, CSS, JSON, Markdown syntax support
- Ctrl+S to save, F5 to run

### AI Chat Panel
- Real-time stream output with token-by-token display
- Code block rendering with syntax highlighting
- Copy button on each AI message
- Automatic memory injection via `mem_recall()`
- Model switcher: auto-discovers local Ollama models, supports cloud configs
- Tool call: AI can request to read project files (`read_file`)

### Terminal Panel
- Run `.vigo` files with ▶️ Run button or F5
- Output display with pass/fail status
- Collapsible panel

### Memory System
- `mem_save` — AI auto-extracts key facts and stores to ChromaDB
- `mem_recall` — Semantic search with time filtering
- `mem_enhanced_ask` — AI response with automatic memory context
- Memory snapshot via 🧠 button in toolbar

---

## Quick Start

### Requirements
- Python 3.10+
- Ollama (for local AI models)
- ChromaDB (optional, for memory system)

### Install Dependencies
```bash
pip install pywebview chromadb
```

### Launch
```bash
cd F:\ViGo\vigo-dev
python main.py
```

A 1400×900 dark-themed window will open. Create a new project or open an existing one to start.

### Using AI Features
1. Ensure Ollama is running with at least one model loaded:
   ```bash
   ollama pull gemma-4b
   ```
2. In ViGo Dev, select your model from the 🤖 Model menu
3. Type in the AI chat panel and press Enter
4. The AI can read your project files — just ask it to "look at parser.py"

---

## Project Structure
```
vigo-dev/
├── main.py              # PyWebView window entry point + JSBridge
├── api.py               # Backend API (file ops, AI calls, memory, projects)
├── ui/
│   └── index.html       # Frontend (HTML + CSS + JS, all embedded)
├── models/              # Cloud model configs (JSON files)
├── Projects/            # Default project storage directory
└── .vigo_config.json    # User preferences (last project, model)
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save current file |
| `F5` | Run current `.vigo` file |
| `Enter` | Send AI message |
| `Shift+Enter` | New line in AI input |

---

## Architecture

```
┌─────────────────────────────────────────┐
│  UI Layer (HTML/CSS/JS)                 │
│  Monaco Editor + File Tree + Chat       │
└──────────────┬──────────────────────────┘
               │ PyWebView JS Bridge
┌──────────────▼──────────────────────────┐
│  Python Shell (main.py + api.py)        │
│  Window management, file I/O            │
└──────────────┬──────────────────────────┘
               │ Calls ViGo Interpreter
┌──────────────▼──────────────────────────┐
│  ViGo Engine                            │
│  ailib.py (AI) + memlib.py (Memory)     │
└─────────────────────────────────────────┘
```

---

## Version

ViGo Dev is part of ViGo v3.7.

We are still in the early stages of testing. If you encounter any bugs, you can provide feedback. These are just some demonstrations
```