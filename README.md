# ViGo

<p align="center">
  <img src="vigo.png" width="400" alt="Auto Agent Result">
</p>

**The AI Scripting Language.**
**v3.8 Stable Beta**

ViGo is a lightweight, embeddable scripting language purpose-built for AI workflows.
Concise syntax, native pipe operator, optional chaining, null coalescing, and a
batteries-included standard library spanning **41 modules** — from AI agents and RAG
retrieval to concurrency, sandboxing, and scientific computing.

- **Three execution modes:** Tree-walk interpreter, Bytecode VM, Python transpiler (native speed)
- **Transpiler: 10–30x faster** than interpreter
- **Pure core:** ~950 KB Python source, zero external dependencies beyond stdlib
- **99/99 regression tests passing** · **32/32 Embedded tests** · **14/14 Extended stdlib tests**

---

## Quick Look

```vigo
Fun as greet(name):
    Ret "Hello, {name}!"
Fin
print(greet("World") |> upper())

# Output: HELLO, WORLD!
```

### AI in 3 Lines

```vigo
ai_set_key("sk-...")
answer = "What is the capital of France?" |> ai_ask()
print(answer)
```

### Agent with Tools

```vigo
agent = ai_agent("gpt-4o")
agent |> ai_agent_add_tool("calculator", Fun x: eval(x) Fin, "Evaluate math")
result = agent |> ai_agent_run("Calculate 2^10 and tell me the result")
print(result)
```

### Sandboxed AI Execution

```vigo
result = sandbox_run("ai_ask('What is 2+2?')", {"timeout": 10, "max_memory": 256})
print(result["stdout"])
```

### Parallel Processing

```vigo
pool = TaskPool(8, "thread")
results = pool.map(str, [1, 2, 3, 4, 5])
pool.shutdown()
```

---

## What's New in v3.8

### 🚀 Performance
- **Transpiler mode**: 10–30x faster than interpreter
- Tail-call optimization (TCO) for deep recursion
- Bytecode VM with full class and pipe support
- IR optimization: constant folding, dead code elimination, builtin inlining
- Hook system for community extensions (5 hooks)

### 🧠 AI Expansion (85+ functions)
- **Function Calling** — `ai_ask_with_tools`, `ai_register_function`, `ai_execute_tool_call`
- **Embeddings** — `ai_embed`, `ai_embed_batch`
- **Structured Output** — `ai_ask_json`, `ai_extract`
- **Vision** — `ai_vision`, `ai_ask_multimodal` (text + images + audio + video)
- **Batch & Streaming** — `ai_batch`, `ai_batch_async`, `ai_stream`
- **Evaluation** — `ai_evaluate`, `ai_compare`, `ai_debate`
- **RAG Integration** — `ai_rag_ask`, `ai_rag_chat`, `ai_create_knowledge_base`
- **Web Search** — `ai_web_search`, `ai_web_search_ask`, `ai_news_search`
- **AI Chart Generation** — `ai_generate_chart` (bar/line/pie/scatter/auto)
- **Conversation Management** — branch, rollback, summarize, compress
- **Token Counting** — `ai_count_tokens`, `ai_token_cost`
- **Semantic Cache** — `Cache`, `cache_store`, `cache_recall`
- **Model Management** — `ai_list_models_live`, `ai_model_info`
- **20 AI Providers** — OpenAI, Claude, DeepSeek, Groq, Mistral, Ollama, and 14 more

### 📦 New Standard Library Modules (15 new, 41 total)

| Module | Description | Functions |
|--------|-------------|-----------|
| `scilib` | Scientific computing (stats, vectors, matrices, calculus) | 29 |
| `fmtlib` | Data formats (YAML/TOML/XML/CSV/INI) | 20 |
| `seclib` | Security & cryptography (AES, JWT, bcrypt, HMAC) | 20 |
| `multilib` | Multimedia (images/audio/video) | 14 |
| `cloudlib` | Cloud storage (S3, presigned URLs) | 8 |
| `vislib` | Data visualization (bar/line/pie/scatter/histogram) | 6 |
| `concurrentlib` | Concurrency (Lock, Workload, Asyn, TaskPool, Queue) | 7 |
| `cachelib` | Semantic caching with embedding similarity | 10 |
| `streamlib` | Lazy stream processing (map/filter/chunk/dedupe) | 13 |
| `proflib` | Performance profiling & benchmarking | 3 |
| `pipelinelib` | ETL data pipelines | 7 |
| `packlib` | Binary serialization (MessagePack/CBOR/BSON) | 2 |
| `watchlib` | File system watcher with callbacks | 5 |
| `sandboxlib` | Sandboxed code execution with resource limits | 1 |
| `netlib` (extended) | TCP/UDP/DNS added | 19 total |

### 🏖️ Sandbox
- Process isolation via subprocess
- Resource limits (CPU/memory)
- File system & network restrictions
- Restricted builtins (no `__import__`, `exec`, `eval`)
- Timeout control

### 🔌 ViGo Embedded (C API)
- C API for embedding ViGo in C/C++/Rust/Go/Python applications
- Lifecycle: `vigo_init`, `vigo_destroy`, `vigo_reset`
- Code execution: `vigo_eval`, `vigo_eval_file`, `vigo_eval_bool`, `vigo_eval_string`, `vigo_eval_number`
- Function registration: `vigo_register`, `vigo_call`
- AI integration: `vigo_ai_ask`, `vigo_ai_create_agent`, `vigo_ai_agent_run`
- Value type system: null, bool, number, string, list
- 17 source files, 32/32 tests passing

### 🐛 Bug Fixes (v3.7 → v3.8)
- Pipe operator semantic consistency across interpreter and transpiler
- TCO closure capture (nested functions with tail calls now work correctly)
- Switch parser edge cases with nested blocks
- Provider parameter passed correctly in `make_request`
- Transpiler method name mapping (`push` → `append`, etc.)
- Cross-eval function registration via persistent registry

---

## Changelog

### v3.8 (Stable Beta) — 2026-05-15
- 15 new standard library modules (41 total)
- 85+ AI functions across 14 capability modules
- Sandbox with process isolation and resource limits
- ViGo Embedded C API with 32 passing tests
- Concurrency library with true parallel execution (300x speedup)
- Semantic caching with embedding similarity
- Stream processing, ETL pipelines, file watching, binary serialization
- Performance profiling and benchmarking
- TCO closure fix, switch parser fix, pipe semantic fix

### v3.7 (Beta) — 2026-05-05
- TCO (Tail Call Optimization)
- IR optimization layer with constant folding and dead code elimination
- Hook system for community extensions
- Bytecode VM with class and pipe support
- Switch parser edge case fixes
- Transpiler: 10-30x performance improvement
- Package Manager: `vigo install`, `vigo uninstall`, `vigo list`, `vigo publish`

### v3.6 (Stable Beta) — 2026-05-04
- Full release with IR, hooks, new stdlib modules
- See RM3.md for complete v3.6 release notes

---

## Installation

### Windows Installer (Recommended)
Download `ViGo_Installer.exe` from the [releases page](https://github.com/Beck-HM/ViGo/releases). One click, done.

The installer will:
- Copy all files to `C:\ViGo`
- Add `C:\ViGo` to your system PATH (`vigo` command)
- Create `vigo.bat` launcher
- Associate `.vigo` files (double-click to run)

After installation, open a **new terminal** and type:

```bash
vigo
```

### From Source

```bash
git clone https://github.com/Beck-HM/ViGo.git
cd ViGo
python main.py
```

**Requirements:** Python 3.10+

---

## 30-Second Start

Create `hello.vigo`:

```vigo
print("Hello from ViGo!")
```

Run it:

```bash
vigo hello.vigo
# or
python main.py hello.vigo
```

---

## Language Reference

### Block syntax — `ts` / `Fin`

ViGo uses `ts` to open a block and `Fin` to close it. Each must appear on its own line.

```vigo
if x > 0 ts
    print("positive")
Fin
```

### Variables & Constants

```vigo
name = "ViGo"           # mutable
const PI = 3.14159      # immutable
x += 1                  # compound assignment
a, b, c = [1, 2, 3]     # destructuring
```

### Booleans — `ok` / `no`

```vigo
ready = ok              # true
done = no               # false
```

`true` and `false` also work.

### Functions

```vigo
Fun as add(a, b):
    Ret a + b
Fin

# Lambda — single expression
double = Fun x: x * 2 Fin

# Lambda — multi-line
fn = Fun x, y:
    result = x + y
    Ret result
Fin

# Default parameters
Fun as greet(name = "World"):
    Ret "Hi, {name}!"
Fin

# Rest parameters
Fun as sum_all(...nums):
    Ret nums |> sum()
Fin
```

### Conditionals — `if` / `eif` / `el`

```vigo
if score >= 90 ts
    grade = "A"
eif score >= 80 ts
    grade = "B"
el ts
    grade = "F"
Fin
```

### Loops

```vigo
# while loop
loop count > 0 ts
    print(count)
    count -= 1
Fin

# for-in loop
for item in items ts
    print(item)
Fin

# unless loop (while not)
skip done ts
    process()
Fin

# do-while loop
go ts
    line = input("> ")
Fin loop line != "quit"
```

### Switch with range matching

```vigo
switch score ts
    case 90..100 ts grade = "A" Fin
    case 80..89  ts grade = "B" Fin
    case 70..79  ts grade = "C" Fin
    default      ts grade = "F" Fin
Fin
```

### Pipe operator `|>`

Chains function calls left-to-right, eliminating deep nesting:

```vigo
data |> filter(ok) |> map(Fun x: x * 2 Fin) |> sum()
```

The left side becomes the **first argument** to the function on the right.

### Optional chaining `?.` & Null coalescing `??`

```vigo
city = user?.address?.city       # returns null if any link is missing
name = input("Name: ") ?? "Anonymous"  # fallback for null
```

### String interpolation

```vigo
greeting = "Hello, {name}! Score: {score:.2f}"
```

### Classes & Inheritance

```vigo
class Animal ts
    Fun as init(name): this.name = name Fin
    Fun as speak(): Ret "{this.name} makes a sound" Fin
Fin

class Dog extends Animal ts
    Fun as speak(): Ret "{this.name} barks!" Fin
Fin

d = new Dog("Rex")
print(d.speak())  # Rex barks!
```

### Try / Catch / Throw

```vigo
try ts
    risky_operation()
catch err ts
    print("Caught: {err}")
Fin

throw "Something went wrong"
```

### Many more features...
List comprehension, regex literals, enums, interfaces, static methods, chained comparisons, spread operator, slicing, range expressions, module loading, assertions, and more.

---

## Execution Modes

| Mode | Description | Speed |
|------|-------------|-------|
| Tree-walk interpreter | Full step-through, breakpoints, variable inspection, hooks | Baseline |
| Bytecode VM | Stack-based virtual machine | ~1x |
| **Python transpiler** | ViGo → Python, runs at native speed | **10–30x** |
| IR optimized | Constant folding, dead code elimination, builtin inlining | — |

---

## AI Functions (partial list)

### Core
`ai_ask` · `ai_chat` · `ai_ollama` · `ai_chain` · `ai_compare` · `ai_debate`

### Agent
`ai_agent` · `ai_agent_add_tool` · `ai_agent_run`

### Embedding
`ai_embed` · `ai_embed_batch`

### Function Calling
`ai_ask_with_tools` · `ai_register_function` · `ai_execute_tool_call`

### Vision & Multimodal
`ai_vision` · `ai_ask_multimodal` · `ai_describe_image`

### Structured Output
`ai_ask_json` · `ai_extract`

### Batch & Stream
`ai_batch` · `ai_batch_async` · `ai_stream`

### Search
`ai_web_search` · `ai_web_search_ask` · `ai_news_search`

### RAG
`ai_rag_ask` · `ai_rag_chat` · `ai_create_knowledge_base`

### Evaluation
`ai_evaluate` · `ai_fine_tune` · `ai_fine_tune_status`

### Token & Cost
`ai_count_tokens` · `ai_token_cost`

### Chart
`ai_generate_chart`

### Cache & Safety
`ai_enable_cache` · `ai_enable_semantic_cache` · `ai_enable_guardrails` · `ai_set_blocked_words`

---

## Standard Library Modules (41 total)

| Module | Purpose |
|--------|---------|
| `ai` | AI multi-provider, agents, embeddings, RAG, vision, function calling |
| `math` | Math, trig, random, constants (PI, E, TAU) |
| `io` | File I/O, path operations |
| `crypto` | MD5, SHA-256, SHA-512, Base64 |
| `net` | HTTP, TCP, UDP, DNS, URL parsing |
| `data` | JSON, CSV, map, filter, reduce |
| `sys` | OS info, environment variables, process management |
| `db` | SQLite, MySQL, PostgreSQL, Redis |
| `log` | Structured logging with levels |
| `color` | Terminal ANSI colors |
| `ini` | INI config file parsing |
| `gui` | GUI dialogs (tkinter) |
| `rag` | RAG retrieval (PDF, DOCX, HTML), ChromaDB |
| `image` | Stable Diffusion image generation |
| `prompt` | Prompt templates with auto-optimization |
| `email` | SMTP email sending |
| `workflow` | DAG workflow engine |
| `i18n` | Internationalization |
| `chart` | Chart generation |
| `kg` | Knowledge graph operations |
| `type` | Runtime type checking |
| `module` | Enhanced module loading |
| `cron` | Cron-style scheduling |
| `ws` | WebSocket client/server |
| `train` | Model training utilities |
| `mem` | Long-term memory (ChromaDB + AI facts) |
| `sci` | Scientific computing (29 functions) |
| `fmt` | Data formats (YAML, TOML, XML, CSV, INI) |
| `sec` | Security & cryptography (AES, JWT, bcrypt) |
| `multi` | Multimedia (images, audio, video) |
| `cloud` | Cloud storage (S3) |
| `vis` | Data visualization (matplotlib) |
| `concurrent` | Concurrency (Lock, Semaphore, TaskPool, Queue) |
| `cache` | Semantic caching |
| `stream` | Stream processing |
| `prof` | Performance profiling |
| `pipeline` | ETL data pipelines |
| `pack` | Binary serialization (MessagePack, CBOR, BSON) |
| `watch` | File system watcher |
| `sandbox` | Sandboxed code execution |

---

## Command Line

```bash
vigo run script.vigo      # Interpret and run
vigo build script.vigo    # Transpile to Python
vigo                      # Launch REPL (if available)
```

---

## Project Structure

```
ViGo/
├── main.py                # Entry point
├── setup.py               # Package setup
├── installer.py           # Windows EXE installer
├── vigo/
│   ├── lexer/             # Tokenizer (tokens.py, lexer.py)
│   ├── parser/            # Parser (ast_nodes.py, parser.py)
│   ├── runtime/           # Interpreter (environment, objects, builtins, errors, interpreter, ir)
│   ├── stdlib/            # 41 standard library modules
│   ├── bytecode/          # Bytecode compiler & VM
│   └── transpiler/        # ViGo → Python transpiler
├── embedded/              # C embedding API
│   ├── include/vigo.h     # Public C API header
│   ├── src/               # 7 C source files
│   └── tests/             # 32 C test cases
└── tests/                 # ViGo regression tests (99/99)
```

---

## Why ViGo?

- **Built for AI:** First-class AI primitives — 85+ functions, 20 providers, agents, RAG, embeddings, vision
- **Readable:** `ts`/`Fin` blocks are visually clean; no bracket hunting
- **Pipeline-native:** `|>` makes data transformation chains obvious
- **Safe by default:** `?.` and `??` eliminate null reference crashes
- **Sandbox-ready:** Process isolation, resource limits, restricted builtins
- **Fast when needed:** Transpile to Python for native performance (10–30x)
- **Embeddable:** C API for integrating ViGo AI into any C/C++ application
- **Compact:** 41 stdlib modules, 85+ AI capabilities, all in ~950 KB
- **Zero external dependencies:** Everything runs on Python stdlib; optional deps for advanced features

---

## Status

**Version:** v3.8 Stable Beta  
**Tests:** 99/99 ViGo regression · 32/32 Embedded C · 14/14 Extended Stdlib  
**Platform:** Windows (primary), Linux/macOS (via Python source)

### Known Limitations

- **Bytecode VM**: Classes and pipe operations not fully supported in bytecode mode
- **ViGo function callbacks**: Custom `Fun` functions cannot be called from Python threads (affects `TaskPool.map`, `stream.filter/map`, `Pipeline`, `profile`/`benchmark`)
- **Closure writes in threads**: ViGo closure variables are read-only in Python sub-threads
- **Switch edge cases**: Single-line `switch` with nested blocks may have parser edge cases
- **Nested list literals**: `[[1, 2], [3, 4]]` requires splitting across variables
- **Named parameters**: Not supported; use positional arguments

---

## Contributing

ViGo is under active development. Contributions are welcome:

1. Fork the repository
2. Create a feature branch
3. Add passing tests for any changes
4. Submit a pull request

---