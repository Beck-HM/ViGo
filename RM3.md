```markdown
# ViGo v3.7 Release Notes

## New Features

### 1. Memlib — Long-term Memory with AI Fact Extraction
- **File:** `vigo/stdlib/memlib.py` (NEW)
- **Description:** RAG-based memory system with ChromaDB vector search and AI-powered fact extraction.
- **Architecture:**
  - Storage: ChromaDB for semantic vector search
  - AI: Auto-extracts key facts from saved content via Ollama
  - Fallback: In-memory dictionary when ChromaDB is unavailable
- **ViGo Functions (9):**
  - `mem_save(key, content, threshold?)` — Save with AI fact extraction and duplicate detection
  - `mem_recall(query, limit?, hours?)` — Semantic search with optional time filtering
  - `mem_enhanced_ask(prompt, model?, memory_limit?, hours?)` — AI call with automatic memory injection
  - `mem_snapshot()` — Summary of stored memories (count, time range, ChromaDB status)
  - `mem_get(key)` — Retrieve a single memory by key
  - `mem_forget(key)` — Delete a specific memory
  - `mem_clear()` — Remove all memories
  - `mem_size()` — Count stored memories
  - `mem_list()` — List all memory keys
- **Usage:**
```vigo
mem_save("parser_fix", "Fixed switch multi-line case body in parser.py")
memories = mem_recall("parser bug", 5)
answer = mem_enhanced_ask("What was recently fixed?")
```

### 2. Stream Output for AI Calls
- **File:** `vigo/stdlib/ailib.py`
- **Description:** AI responses now stream token-by-token in the IDE chat panel.
- **Implementation:**
  - Ollama API streaming via `subprocess` with stdin/stdout pipe
  - Simulated streaming with chunked display (15ms per chunk)
  - Automatic non-stream fallback on connection failure
  - Timing display: `⏱️ 3.2s` on each AI response
- **ViGo Functions:**
  - `ai_on_chunk(callback)` — Register a chunk callback function
  - `ai_stream_chunks()` — Retrieve collected chunks after streaming call

### 3. ViGo Dev IDE
- **Directory:** `vigo-dev/` (NEW)
- **Description:** A native desktop IDE for ViGo development, built with PyWebView and Monaco Editor.
- **Architecture:**
  - `main.py` — PyWebView window entry point + JSBridge for Python-JS communication
  - `api.py` — Backend API: file operations, AI calls, memory, project management
  - `ui/index.html` — Full frontend with embedded CSS and JavaScript
- **Features:**
  - **Project Management:** Create, open, import projects via native folder picker
  - **File Tree:** Lazy-loaded directory browser with right-click context menu (New File/Folder, Rename, Delete)
  - **Code Editor:** Monaco Editor with ViGo syntax highlighting and autocomplete (30+ keywords)
  - **AI Chat Panel:** Stream output, code block rendering, copy button, memory integration
  - **Terminal Panel:** Run `.vigo` files with F5, display output/errors
  - **Model Switcher:** Auto-discovers local Ollama models, supports cloud model configs
  - **Memory Panel:** View memory snapshots from the IDE
  - **Auto-save:** Remembers last opened file per project
- **ViGo Language Support in Monaco:**
  - 30+ keywords highlighted (Fun, as, Ret, ts, Fin, loop, for, switch, etc.)
  - 27 autocomplete snippets (Fun as, if, loop, for, switch, class, try, etc.)
  - ViGo operators (|>, ?., ??, .., ...)

### 4. Interpreter — Built-in Methods Expansion
- **File:** `vigo/runtime/interpreter.py`
- **New List Methods:** `.extend()`, `.insert()`, `.remove()`, `.find()`, `.sort()`
- **New String Methods:** `.startswith()`, `.endswith()`, `.contains()`, `.find()`, `.count()`
- **New Dict Methods:** `.get(key, default?)`, `.items()`

### 5. New Standard Library Modules
- **`regexlib.py`** — 9 regex functions (test, match, search, find_all, replace, split, escape, groups, count)
- **`markdownlib.py`** — 8 markdown functions (to_html, extract_links, extract_headers, extract_code, to_plain, count_words, table_to_list, escape_html)
- **`htmllib.py`** — 10 HTML functions (strip, text, links, images, table, count_tag, meta, title, to_text, attrs)
- **`csslib.py`** — 10 CSS functions (rules, get, colors, classes, ids, fonts, minify, pretty, parse_inline, to_inline)

### 6. REPL Module
- **File:** `vigo/repl.py` (NEW)
- **Features:** Multi-line input with ts/Fin depth tracking, command history, `_` variable, .exit/.quit/.help/.clear commands

---

## Bug Fixes

### 1. AILib — Duplicate Code Removed
- **File:** `vigo/stdlib/ailib.py`
- Removed duplicated `_create_agent`, `_agent_add_tool`, `_agent_run` function definitions in `register()`

### 2. Parser — Switch Multi-line Case Body
- **File:** `vigo/parser/parser.py`
- Replaced manual depth counting with unified `_parse_block()` for case body parsing
- Added inline comments documenting depth tracking and terminators logic

### 3. Interpreter — Null Comparison Safety
- **File:** `vigo/runtime/interpreter.py`
- Added `_null_safe_compare()` static method shared by `_binary_op` and `_chained_compare`
- Fixed `TypeError: '<' not supported between instances of 'NoneType'` edge cases

### 4. Provider Layer — `provider` Parameter Fix
- **File:** `vigo/stdlib/providers/request.py`
- `make_request()` now accepts and passes through `provider` parameter
- **File:** `vigo/stdlib/ailib.py`
- `ask()` method now correctly passes `provider` to `make_request()`

---

## Refactoring

### 1. Interpreter `eval()` Method
- Split 200-line `eval()` into dispatch table + 47 dedicated `_eval_*()` handler methods
- Each AST node type has a single-responsibility handler

### 2. Provider Layer Extraction
- **Directory:** `vigo/stdlib/providers/` (5 new files)
- `__init__.py` — Provider registry + `get_provider_config()`
- `request.py` — Request building, sending, streaming
- `openai_format.py` — OpenAI-compatible parsing + body building
- `claude_format.py` — Claude format handling
- `cohere_format.py` — Cohere format handling

### 3. Control Flow Blocks Extraction
- **File:** `vigo/runtime/blocks.py` (NEW)
- Extracted: `eval_block`, `is_truthy`, `eval_if`, `eval_for_in`, `eval_loop`, `eval_do_while`, `eval_switch`, `eval_try`, `eval_listcomp`

### 4. Standard Library Auto-Discovery
- **File:** `vigo/stdlib/__init__.py`
- Replaced 25 manual imports with `os.listdir('stdlib')` auto-discovery
- Adding a new stdlib module now requires zero config

---

## Architecture Upgrades

### 1. Friendly Error System
- Upgraded `error()` method with `^` column pointer and optional help text
- Added named parameter detection in `parse_args()`: suggests positional arguments
- Example:
```
Syntax error [Line5, Column15]: Expected RPAREN, but got ASSIGN('=')
    result = ai_ask("Hello", model="gpt-4o")
                  ^
Help: ViGo does not support named parameters. Use positional arguments instead.
```

### 2. Plugin System — Community Extension Hooks
- 5 hook points: `before_eval`, `after_eval`, `before_func_call`, `after_func_call`, `on_error`
- `register_hook()` and `unregister_hook()` methods on Interpreter

### 3. Intermediate Representation (IR) Layer
- **File:** `vigo/ir.py` (NEW, ~150 lines)
- `IRBuilder` — AST → IR translation with constant folding
- `IROptimizer` — Dead code elimination
- Three execution paths: `interpret()` (debug), `interpret_ir()` (optimized), `transpile_ir()` (native speed)
- Example: `x = 2 + 3 * 4` → IR constant folding produces `x = 14` directly

---

## Test Coverage

| Test Suite | Result |
|-----------|--------|
| `test_all_v36.vigo` (55 tests) | 55/55 PASS |
| `test_new_stdlib.vigo` (43 tests) | 43/43 PASS |
| `test_regression_v36.vigo` (65 tests) | 65/65 PASS |
| `test_memlib.vigo` (14 tests) | 14/14 PASS |
| `test_memlib_full.vigo` (18 tests) | 18/18 PASS |
| `test_memlib_ranking.vigo` (TF-IDF ranking) | Verified |
| Python Unit Tests (67 tests) | 62/67 PASS |
| IR constant folding test | Verified |
| IR dead code elimination test | Verified |

---

## File Changes Summary

| File | Status | Change |
|------|--------|--------|
| `vigo/stdlib/memlib.py` | **NEW** | RAG memory system with ChromaDB |
| `vigo/stdlib/regexlib.py` | **NEW** | Regex standard library |
| `vigo/stdlib/markdownlib.py` | **NEW** | Markdown standard library |
| `vigo/stdlib/htmllib.py` | **NEW** | HTML standard library |
| `vigo/stdlib/csslib.py` | **NEW** | CSS standard library |
| `vigo/repl.py` | **NEW** | Interactive REPL module |
| `vigo/ir.py` | **NEW** | IR layer (IRBuilder + IROptimizer) |
| `vigo/runtime/blocks.py` | **NEW** | Control flow block execution |
| `vigo/stdlib/providers/` | **NEW** | Provider layer (5 files) |
| `vigo-dev/` | **NEW** | ViGo Dev IDE (main.py, api.py, ui/) |
| `tests/test_memlib*.vigo` | **NEW** | Memory library tests (3 files) |
| `vigo/parser/parser.py` | Modified | Friendly error system, switch case fix, comments |
| `vigo/runtime/interpreter.py` | Modified | Plugin hooks, IR interpreter, eval refactor, built-in methods, null-safe compare |
| `vigo/transpiler/transpiler.py` | Modified | IR transpile entry point |
| `vigo/bytecode/instructions.py` | Modified | +10 IR instructions |
| `vigo/stdlib/ailib.py` | Modified | Duplicate code removed, stream support, provider fix |
| `vigo/stdlib/__init__.py` | Modified | Auto-discovery loader |
| `vigo/stdlib/providers/request.py` | Modified | `provider` parameter pass-through |
```

---