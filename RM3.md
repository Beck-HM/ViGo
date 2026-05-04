```markdown
# ViGo v3.6 Release Notes

## Bug Fixes

### 1. AILib - Duplicate Code Removed
- **File:** `vigo/stdlib/ailib.py`
- **Issue:** `register()` function had duplicated `_create_agent`, `_agent_add_tool`, and `_agent_run` function definitions, causing unnecessary code bloat.
- **Fix:** Removed the duplicate block, keeping only one definition of each helper function at the end of `register()`.

### 2. Parser - Switch Multi-line Case Body
- **File:** `vigo/parser/parser.py`
- **Issue:** `parse_switch_stmt()` used manual depth counting for case body parsing, which could miscount nested `ts`/`Fin` blocks inside case bodies, leading to "stray Fin" or "switch missing Fin" syntax errors on complex switch statements.
- **Fix:** Replaced manual `while True` loops with the unified `_parse_block()` helper, using `{CASE, DEFAULT}` as terminators for case bodies and empty terminators set for default bodies. This ensures consistent `Fin` consumption across all nested block structures.

### 3. Interpreter - Null Comparison Safety
- **File:** `vigo/runtime/interpreter.py`
- **Issue:** `_binary_op()` and `_chained_compare()` methods could crash with Python `TypeError: '<' not supported between instances of 'NoneType'` when comparing null-adjacent values in chained comparisons or ternary expressions.
- **Fix:** Added `try/except TypeError` guards in both methods. `_chained_compare` now catches `TypeError` during comparison and returns `False` gracefully.

---

## New Features

### 1. Stream Output for AI Calls
- **File:** `vigo/stdlib/ailib.py`
- **Added Methods:**
  - `_stream_request()` - Handles SSE (Server-Sent Events) streaming responses from OpenAI-compatible APIs
  - `_extract_stream_delta()` - Parses delta text chunks from streaming response objects
  - `get_stream_chunks()` - Returns collected stream chunks for retrieval after streaming completes
  - `set_stream_callback()` - Registers a callback function for real-time chunk processing
- **Modified:** `ask()` now accepts `stream=False` parameter; when `True`, uses `_stream_request()` with automatic non-stream fallback on empty response
- **ViGo Functions:**
  - `ai_on_chunk(callback)` - Register a chunk callback function
  - `ai_stream_chunks()` - Retrieve collected chunks after streaming call
- **Usage:**
```vigo
ai_on_chunk(my_handler)
result = ai_ask("prompt", "gemma-4b", 0.7, 200, "ollama", ok)
chunks = ai_stream_chunks()
```

### 2. Interpreter - Built-in Methods Expansion
- **File:** `vigo/runtime/interpreter.py`
- **New List Methods (via `.method()` syntax):**
  - `.extend(other)` - Extend list with another iterable
  - `.insert(idx, item)` - Insert item at position
  - `.remove(item)` - Remove first occurrence of item
  - `.find(item)` - Return index of item or -1
  - `.sort(key?, reverse?)` - Sort list in place
- **New String Methods (via `.method()` syntax):**
  - `.startswith(prefix)` - Check if string starts with prefix
  - `.endswith(suffix)` - Check if string ends with suffix
  - `.contains(sub)` - Check if substring is present
  - `.find(sub)` - Return index of substring or -1
  - `.count(sub)` - Count occurrences of substring
- **New Dict Methods (via `.method()` syntax):**
  - `.get(key, default?)` - Get value with optional default
  - `.items()` - Return list of [key, value] pairs

### 3. REPL Module
- **File:** `vigo/repl.py` (NEW)
- **Features:**
  - Multi-line input with automatic `ts`/`Fin` depth tracking
  - Command history via `readline` (Unix) or `pyreadline3` (Windows)
  - `_` variable references last expression result
  - `.exit`, `.quit`, `.help`, `.clear` meta-commands
  - Keyboard interrupt and EOF handling
  - History persistence to `~/.vigo_history`

### 4. New Standard Library Modules

#### Regex Library
- **File:** `vigo/stdlib/regexlib.py` (NEW)
- **ViGo Functions (9):**
  - `regex_test(pattern)` - Validate regex pattern (returns ok/no)
  - `regex_match(pattern, text)` - Check if pattern matches (returns ok/no)
  - `regex_search(pattern, text)` - Return first match or null
  - `regex_find_all(pattern, text)` - Return all non-overlapping matches
  - `regex_replace(pattern, replacement, text, count?)` - Replace matches
  - `regex_split(pattern, text, maxsplit?)` - Split by pattern
  - `regex_escape(text)` - Escape special regex characters
  - `regex_groups(pattern, text)` - Return captured groups
  - `regex_count(pattern, text)` - Count matches

#### Markdown Library
- **File:** `vigo/stdlib/markdownlib.py` (NEW)
- **ViGo Functions (8):**
  - `md_to_html(text)` - Convert Markdown to HTML
  - `md_extract_links(text)` - Extract all [text](url) links
  - `md_extract_headers(text)` - Extract all headers with levels
  - `md_extract_code(text)` - Extract fenced code blocks
  - `md_to_plain(text)` - Strip all Markdown formatting
  - `md_count_words(text)` - Count words after stripping formatting
  - `md_table_to_list(text)` - Extract tables as nested lists
  - `md_escape_html(text)` - HTML-escape text

#### HTML Library
- **File:** `vigo/stdlib/htmllib.py` (NEW)
- **ViGo Functions (10):**
  - `html_strip(html)` - Remove all HTML tags
  - `html_text(html)` - Extract visible text preserving paragraphs
  - `html_links(html)` - Extract all [text, href] from `<a>` tags
  - `html_images(html)` - Extract all [alt, src] from `<img>` tags
  - `html_table(html, index?)` - Extract table as nested lists
  - `html_count_tag(html, tag)` - Count occurrences of a tag
  - `html_meta(html, name)` - Get `<meta name="...">` content
  - `html_title(html)` - Extract `<title>` text
  - `html_to_text(html)` - Full HTML to readable text
  - `html_attrs(html, tag, attr)` - Extract attribute values from tags

#### CSS Library
- **File:** `vigo/stdlib/csslib.py` (NEW)
- **ViGo Functions (10):**
  - `css_rules(css)` - Extract all selector/properties pairs
  - `css_get(css, selector, property)` - Get specific property value
  - `css_colors(css)` - Extract all color values
  - `css_classes(css)` - Extract all class selectors
  - `css_ids(css)` - Extract all ID selectors
  - `css_fonts(css)` - Extract all font-family values
  - `css_minify(css)` - Minify/compress CSS
  - `css_pretty(css)` - Format CSS with indentation
  - `css_parse_inline(style)` - Parse inline style to dict
  - `css_to_inline(dict)` - Convert dict to inline style string

---

## Architecture Upgrades

### 1. Friendly Error System
- **File:** `vigo/parser/parser.py`
- **Changes:**
  - Upgraded `error()` method to display source line with `^` column pointer
  - Added optional `help_text` parameter for actionable fix suggestions
  - Upgraded `eat()` to provide contextual help on delimiter mismatches
  - Upgraded `parse_args()` to detect named parameter syntax (`name=value`) and suggest positional arguments
- **Example output:**
```
Syntax error [Line5, Column15]: Expected RPAREN, but got ASSIGN('=')
    result = ai_ask("Hello", model="gpt-4o")
                  ^
Help: ViGo does not support named parameters. Use positional arguments instead.
```

### 2. Plugin System — Community Extension Hooks
- **File:** `vigo/runtime/interpreter.py`
- **Changes:**
  - Added `hooks` dictionary with 5 hook points: `before_eval`, `after_eval`, `before_func_call`, `after_func_call`, `on_error`
  - Added `register_hook(hook_name, callback)` method
  - Added `unregister_hook(hook_name, callback)` method
  - Embedded hook triggers in `eval()` and `_func_call()` methods
- **Usage:**
```python
interp = Interpreter()
interp.register_hook("before_func_call", lambda node, args, env: print(f"Calling: {node.name}"))
interp.register_hook("after_func_call", lambda node, result, env: print(f"Returned: {result}"))
```
- **Available hooks:**

| Hook | Signature | Use Case |
|------|-----------|----------|
| `before_eval` | `(node, env)` | Profiling, code coverage |
| `after_eval` | `(node, result, env)` | Result tracking, debugging |
| `before_func_call` | `(call_node, args, env)` | Call logging, parameter validation |
| `after_func_call` | `(call_node, result, env)` | Return value monitoring |
| `on_error` | `(exception, node, env)` | Error reporting, recovery |

### 3. Intermediate Representation (IR) Layer
- **New File:** `vigo/ir.py` (~150 lines)
- **Modified:** `vigo/bytecode/instructions.py` (+10 IR instructions)
- **Modified:** `vigo/runtime/interpreter.py` (+`interpret_ir()`, `_exec_ir()`, `_ir_value()`)
- **Modified:** `vigo/transpiler/transpiler.py` (+`transpile_ir()`, `_ir_to_python()`)

#### IR Instruction Set
| Instruction | Description |
|-------------|-------------|
| `IR_LOAD_CONST` | Load a constant value into a temp |
| `IR_ADD` / `IR_SUB` / `IR_MUL` / `IR_DIV` | Arithmetic operations on temps |
| `IR_STORE` | Store a temp value into a variable |
| `IR_LOAD` | Load a variable into a temp |
| `IR_JUMP_IF_FALSE` | Conditional jump to label |
| `IR_CALL` | Function call with temp args |
| `IR_RETURN` | Return from function |

#### Classes
- **`IRInstruction`** — Single IR instruction: `(opcode, operands, result_temp)`
- **`IRBuilder`** — AST → IR translator with constant folding
- **`IROptimizer`** — Dead code elimination (removes unused temps)

#### Execution Paths
| Path | Entry Point | Use Case |
|------|-------------|----------|
| Tree-walk Interpreter | `interpret()` | Development, debugging |
| IR Interpreter | `interpret_ir()` | Optimized execution |
| IR Transpiler | `transpile_ir()` | Maximum speed (native Python) |

#### Example: `x = 2 + 3 * 4`
```
AST → Generated IR:
  t1 = IR_LOAD_CONST 2
  t2 = IR_LOAD_CONST 3
  t3 = IR_LOAD_CONST 4
  t4 = IR_LOAD_CONST 12     # constant folded: 3 * 4
  t5 = IR_LOAD_CONST 14     # constant folded: 2 + 12
  IR_STORE x, t5

After Optimization:
  t5 = IR_LOAD_CONST 14
  IR_STORE x, t5
```

---

## Refactoring

### 1. Interpreter `eval()` Method Refactored
- **File:** `vigo/runtime/interpreter.py`
- Split the 200-line `eval()` method into a dispatch table + 47 dedicated `_eval_*()` handler methods
- New AST nodes only require adding one entry to the dispatch table and one handler method

### 2. Provider Layer Extracted
- **Directory:** `vigo/stdlib/providers/` (5 new files)
  - `__init__.py` — Provider registry + `get_provider_config()`
  - `request.py` — Request building, sending, streaming
  - `openai_format.py` — OpenAI-compatible response parsing + body building
  - `claude_format.py` — Claude format handling
  - `cohere_format.py` — Cohere format handling
- **File:** `vigo/stdlib/ailib.py` — Slimmed from ~950 lines to ~750 lines

### 3. Control Flow Blocks Extracted
- **New File:** `vigo/runtime/blocks.py`
- Extracted from interpreter: `eval_block`, `is_truthy`, `eval_if`, `eval_for_in`, `eval_loop`, `eval_do_while`, `eval_switch`, `eval_try`, `eval_listcomp`
- Adding a new loop type now only requires modifying one file

### 4. Standard Library Auto-Discovery
- **File:** `vigo/stdlib/__init__.py`
- Replaced 25 manual imports + 25 manual `register_*()` calls with `os.listdir('stdlib')` auto-discovery
- Adding a new stdlib module now requires zero config — just drop the file in `stdlib/`

### 5. Null-Safe Comparison Utility
- **File:** `vigo/runtime/interpreter.py`
- Extracted `_null_safe_compare(left, right, op)` static method
- Shared by both `_binary_op()` and `_chained_compare()`

### 6. Switch Parser Documentation
- **File:** `vigo/parser/parser.py`
- Added inline comments to `parse_switch_stmt()` explaining depth tracking, block delegation, and terminators

---

## Test Coverage

| Test Suite | Result |
|-----------|--------|
| v3.6 Original Regression | 55/55 PASS |
| New 4 Modules Test | 43/43 PASS |
| Full Regression | 65/65 PASS |
| Python Unit Tests | 62/67 PASS |
| IR constant folding test | Verified |
| IR dead code elimination test | Verified |

---

## Known Limitations (Non-blocking)

1. **Ollama streaming instability:** Ollama's OpenAI-compatible endpoint occasionally returns empty streaming responses. ViGo handles this with automatic non-stream fallback in `ai_ask()`.
2. **Single-line block edge cases:** Single-line `if`/`for`/`switch`/`try-catch` blocks have parser edge cases with `Fin` consumption. Multi-line forms are fully stable.
3. **Bytecode VM:** Supports basic operations, variables, conditionals, loops, and functions, but does not support classes or pipes in bytecode mode. Use interpreter or transpiler for these features.
4. **String interpolation with `{}`:** CSS/JSON strings containing curly braces must use `{{` and `}}` to escape them in ViGo string literals. Alternatively, read these from files.

---

## File Changes Summary

| File | Status | Change |
|------|--------|--------|
| `vigo/ir.py` | **NEW** | IR layer (IRBuilder + IROptimizer + IRInstruction) |
| `vigo/parser/parser.py` | Modified | Rust-style error system, switch case body unified, switch comments |
| `vigo/runtime/interpreter.py` | Modified | Plugin hooks, IR interpreter, eval refactor, built-in methods, null-safe compare |
| `vigo/runtime/blocks.py` | **NEW** | Control flow block execution |
| `vigo/transpiler/transpiler.py` | Modified | IR transpile entry point |
| `vigo/bytecode/instructions.py` | Modified | +10 IR instructions |
| `vigo/stdlib/ailib.py` | Modified | Duplicate code removed, stream support, provider layer extracted |
| `vigo/stdlib/__init__.py` | Modified | Auto-discovery loader, new modules registered |
| `vigo/stdlib/providers/__init__.py` | **NEW** | Provider registry |
| `vigo/stdlib/providers/request.py` | **NEW** | Request execution |
| `vigo/stdlib/providers/openai_format.py` | **NEW** | OpenAI format |
| `vigo/stdlib/providers/claude_format.py` | **NEW** | Claude format |
| `vigo/stdlib/providers/cohere_format.py` | **NEW** | Cohere format |
| `vigo/stdlib/regexlib.py` | **NEW** | Regex standard library |
| `vigo/stdlib/markdownlib.py` | **NEW** | Markdown standard library |
| `vigo/stdlib/htmllib.py` | **NEW** | HTML standard library |
| `vigo/stdlib/csslib.py` | **NEW** | CSS standard library |
| `vigo/repl.py` | **NEW** | Interactive REPL module |
| `tests/test_all.py` | **NEW** | Python unit tests (67 tests) |
| `tests/test_all.vigo` | **NEW** | ViGo core tests (16 tests) |
| `tests/test_all_v36.vigo` | **NEW** | Original regression suite (55 tests) |
| `tests/test_new_stdlib.vigo` | **NEW** | New stdlib modules test (43 tests) |
| `tests/test_null.vigo` | **NEW** | Minimal null expression test |
| `tests/test_regression_v36.vigo` | **NEW** | Full regression test (65 tests) |
| `tests/test_stream.vigo` | **NEW** | Stream output test |
| `tests/test_stream_py.py` | **NEW** | Python stream validation script |
| `tests/test_ir.py` | **NEW** | IR Layer test |
```

---