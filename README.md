```markdown
# ViGo

**The AI Scripting Language.**
**The first test version, the latest release**

ViGo is a lightweight, embeddable scripting language purpose-built for AI workflows.
Concise syntax, native pipe operator, optional chaining, null coalescing, and a
batteries-included standard library spanning AI agents, RAG retrieval, image generation,
cron scheduling, and more.

- **Three execution modes:** Tree-walk interpreter, Cython-compiled, Python transpiler (native speed)
- **Pure core:** ~950 KB Python source, zero external dependencies beyond stdlib
- **55/55 regression tests passing**

---

## Quick Look

```vigo
Fun as greet(name):
    Ret "Hello, {name}!"
Fin

print(greet("World"))  |>  upper()
```

```
HELLO, WORLD!
```

### AI in 3 lines

```vigo
ai_set_key("sk-...")
answer = "What is the capital of France?" |> ai_ask()
print(answer)
```

### Agent with tools

```vigo
agent = ai_agent("gpt-4o")
agent |> ai_agent_add_tool("calculator", Fun x: eval(x) Fin, "Evaluate math")
result = agent |> ai_agent_run("Calculate 2^10 and tell me the result")
print(result)
```

## Changelog

### v3.7 (Beta)
See [RM3.md](RM3.md) for the full v3.7 release notes.

### v3.6 (Stable Beta)

See [RM3.md](RM3.md) for the full v3.6 release notes.

### v3.5 (Stable Beta) — 2026-05-03

**Bug Fixes:**
- Fixed `switch` single-line case + multi-line default parsing
- Fixed string interpolation formatting (`{var:.2f}` now works correctly)
- Fixed `null` comparison in chained expressions (`null == null`, `null < 5`, etc.)
- Fixed closure variable assignment (functions can now modify outer variables correctly)
- Registered `sorted()` as a built-in function

**New Features:**
- Package Manager: `vigo install`, `vigo uninstall`, `vigo list`, `vigo publish`, `vigo build`
- Package Registry: `Beck-HM/ViGo-Registry`
- CLI unified under `vigo/cli.py` with subcommand routing

**Language Enhancements:**
- Built-in method support: `list.push()`, `str.upper()`, `dict.keys()`, `str.split()`, etc.
- Smart quote detection with friendly error messages (shows Unicode codepoint)
- Unified block parser (`_parse_block`) for all control flow structures
- `const` variables now properly protected from reassignment

---

## Installation

### Windows Installer (Recommended)

Download `ViGo_Installer.exe` from the [releases page](#). One click, done.

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
cd vigo
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
```

Or via Python:

```bash
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

### Comments

```vigo
# single-line comment

#*
    multi-line comment
*#
```

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

### Ternary expression

```vigo
status = score >= 60 ? "pass" : "fail"
```

### The `skip` loop (unless)

Executes the body while the condition is **false** — equivalent to `while not`:

```vigo
skip done ts
    process()
Fin
```

### The `go` loop (do-while)

Body runs at least once; condition checked afterward:

```vigo
go ts
    line = input("> ")
Fin loop line != "quit"
```

### The `loop` loop (while)

Standard while loop — runs while condition is true:

```vigo
loop count > 0 ts
    print(count)
    count -= 1
Fin
```

### The `for` loop (for-in)

```vigo
for item in items ts
    print(item)
Fin

# With break / continue
for x in data ts
    if x == null ts
        continue
    Fin
    if x > 100 ts
        break
    Fin
    process(x)
Fin
```

### Switch with range matching

```vigo
switch score ts
    case 90..100 ts
        grade = "A"
    case 80..89 ts
        grade = "B"
    case 70..79 ts
        grade = "C"
    default ts
        grade = "F"
Fin
```

Single values also work:

```vigo
switch day ts
    case "Mon" ts print("Monday") Fin
    case "Fri" ts print("TGIF!") Fin
    default ts print("Regular day") Fin
Fin
```

### Pipe operator `|>`

Chains function calls left-to-right, eliminating deep nesting:

```vigo
data |> filter(ok) |> map(Fun x: x * 2 Fin) |> sum()
```

The left side becomes the **first argument** to the function on the right.

### Optional chaining `?.`

Safely access nested properties — returns `null` if any link is missing:

```vigo
city = user?.address?.city
```

### Null coalescing `??`

Provide fallback values for `null`:

```vigo
name = input("Name: ") ?? "Anonymous"
```

### String interpolation

```vigo
greeting = "Hello, {name}! Score: {score:.2f}"
```

Escape braces with double braces: `"{{raw}}"` → `"{raw}"`

### Multiline strings

```vigo
text = """
    This is a
    multiline string.
"""
```

### List comprehension

```vigo
squares = [x * x for x in 1..10 if x % 2 == 0]
```

### Range expression `..`

Creates an inclusive range:

```vigo
1..5   # [1, 2, 3, 4, 5]
```

### Spread / expand `...`

```vigo
combined = [1, 2, ...more_items, 9, 10]
```

### Classes & Inheritance

```vigo
class Animal ts
    Fun as init(name):
        this.name = name
    Fin

    Fun as speak():
        Ret "{this.name} makes a sound"
    Fin
Fin

class Dog extends Animal ts
    Fun as speak():
        Ret "{this.name} barks!"
    Fin
Fin

d = new Dog("Rex")
print(d.speak())       # Rex barks!
```

### Static methods

```vigo
class MathUtils ts
    static Fun as square(x):
        Ret x * x
    Fin
Fin

print(MathUtils.square(5))   # 25
```

### Interfaces

```vigo
interface Drawable ts
    abstract Fun as draw()
    abstract Fun as resize(w, h)
Fin
```

### Enums

```vigo
enum Color ts
    Red         # 0
    Green       # 1
    Blue = 5    # 5
    Yellow      # 6 (auto-increment from previous)
Fin

print(Color.Red)    # 0
print(Color.Blue)   # 5
```

### Try / Catch / Throw

```vigo
try ts
    risky_operation()
catch err ts
    print("Caught: {err}")
Fin
```

Throwing errors:

```vigo
throw "Something went wrong"
```

### Assertions — `sure`

```vigo
sure age >= 0, "Age cannot be negative"
```

### Module loading

```vigo
load "utils.vigo"
load "helpers.vigo" as h

print(h.some_function())
```

### Await (async)

```vigo
await 2.5          # Pauses execution for 2.5 seconds
```

### Chained comparisons

```vigo
if 0 < x < 100 ts
    print("x is in range")
Fin
```

### `in` operator

```vigo
if "apple" in fruits ts
    print("Found it")
Fin

if "admin" not in users ts
    print("Access denied")
Fin
```

### Lists, Dicts, Sets

```vigo
nums = [1, 2, 3, 4, 5]
user = {"name": "Alice", "age": 30}
tags = {"vigo", "ai", "scripting"}

nums[0]         # 1
user["name"]    # Alice
```

### Slicing

```vigo
data = [10, 20, 30, 40, 50]
middle = data[1..3]       # [20, 30, 40] (inclusive range)
first_half = data[0:3]    # [10, 20, 30]
from_third = data[2:]     # [30, 40, 50]
```

---

## Operators (full list)

| Category | Operators |
|----------|-----------|
| Arithmetic | `+` `-` `*` `/` `//` `%` `**` |
| Comparison | `==` `!=` `<` `>` `<=` `>=` |
| Logical | `and` `or` `not` `!` |
| Bitwise | `&` `|` `^` `~` `<<` `>>` |
| Assignment | `=` `+=` `-=` `*=` `/=` `%=` |
| Special | `|>` `?.` `??` `..` `...` `? :` |
| Membership | `in` `not in` |

### Operator precedence (high to low)

1. `?.` `..` `...`
2. `**`
3. `!` `-` (unary) `~` `not` `await`
4. `*` `/` `//` `%`
5. `+` `-`
6. `<<` `>>`
7. `&`
8. `^`
9. `|`
10. `<` `>` `<=` `>=` `==` `!=` (chainable)
11. `and`
12. `or`
13. `??`
14. `? :`
15. `|>`

---

## Keywords (full list)

```
if        el        eif       ts        Fin
Fun       as        Ret       loop      for
in        break     continue  load      and
or        not       null      true      false
ok        no        class     new       extends
this      try       catch     throw     await
switch    case      default   enum      const
static    abstract  interface go        skip
sure
```

---

## Built-in Functions

### Core

| Function | Signature | Description |
|----------|-----------|-------------|
| `print` | `print(*args)` | Print to stdout |
| `input` | `input(prompt?)` | Read line from stdin |
| `len` | `len(x)` | Length of string / list / dict |
| `str` | `str(x)` | Convert to string |
| `int` | `int(x)` | Convert to integer |
| `float` | `float(x)` | Convert to float |
| `bool` | `bool(x)` | Convert to boolean |
| `type` | `type(x)` | Return type name |

### Math

| Function | Signature | Description |
|----------|-----------|-------------|
| `abs` | `abs(x)` | Absolute value |
| `min` | `min(*args)` | Minimum value |
| `max` | `max(*args)` | Maximum value |
| `floor` | `floor(x)` | Floor |
| `ceil` | `ceil(x)` | Ceiling |
| `round` | `round(x, digits?)` | Round |
| `pow` | `pow(x, y)` | Power (also `x ** y`) |
| `sqrt` | `sqrt(x)` | Square root |
| `sin` | `sin(x)` | Sine (radians) |
| `cos` | `cos(x)` | Cosine (radians) |
| `tan` | `tan(x)` | Tangent (radians) |
| `log` | `log(x, base?)` | Logarithm (default: natural) |
| `log10` | `log10(x)` | Base-10 logarithm |
| `degrees` | `degrees(rad)` | Radians to degrees |
| `radians` | `radians(deg)` | Degrees to radians |
| `clamp` | `clamp(x, lo, hi)` | Clamp value to range |
| `lerp` | `lerp(a, b, t)` | Linear interpolation |
| `random` | `random()` | Random float 0–1 |
| `random` | `random(max)` | Random int 0–max |
| `random` | `random(min, max)` | Random int min–max |
| `random_float` | `random_float(a, b)` | Random float a–b |
| `random_choice` | `random_choice(arr)` | Random element |
| `random_shuffle` | `random_shuffle(arr)` | Shuffle in-place |

### Constants

| Constant | Value |
|----------|-------|
| `PI` | 3.141592653589793 |
| `E` | 2.718281828459045 |
| `TAU` | 6.283185307179586 |

### String Operations

| Function | Signature | Description |
|----------|-----------|-------------|
| `upper` | `str.upper()` | Uppercase |
| `lower` | `str.lower()` | Lowercase |
| `trim` | `str.trim()` | Strip whitespace |
| `split` | `str.split(delimiter)` | Split into list |
| `join` | `str.join(list)` | Join list with separator |
| `replace` | `str.replace(old, new)` | Replace substrings |

### Collection Operations

| Function | Signature | Description |
|----------|-----------|-------------|
| `push` | `list.push(item)` | Append to list |
| `pop` | `list.pop()` | Remove and return last |
| `reverse` | `list.reverse()` | Reverse in-place |
| `sort` | `sorted(list)` | Return sorted copy |
| `keys` | `dict.keys()` | Dictionary keys |
| `values` | `dict.values()` | Dictionary values |
| `sum` | `sum(list)` | Sum of elements |

### File I/O

| Function | Signature | Description |
|----------|-----------|-------------|
| `read_file` | `read_file(path)` | Read entire file |
| `write_file` | `write_file(path, content)` | Write file |
| `append_file` | `append_file(path, content)` | Append to file |
| `read_lines` | `read_lines(path)` | Read as list of lines |
| `file_exists` | `file_exists(path)` | Check file existence |

### Path Operations

| Function | Signature | Description |
|----------|-----------|-------------|
| `path_join` | `path_join(*parts)` | Join path components |
| `path_dir` | `path_dir(path)` | Directory name |
| `path_base` | `path_base(path)` | Base file name |
| `path_ext` | `path_ext(path)` | File extension |
| `path_stem` | `path_stem(path)` | File name without extension |
| `path_abs` | `path_abs(path)` | Absolute path |
| `path_exists` | `path_exists(path)` | Path existence |
| `path_isdir` | `path_isdir(path)` | Is directory |
| `path_isfile` | `path_isfile(path)` | Is file |

### Crypto

| Function | Signature | Description |
|----------|-----------|-------------|
| `md5` | `md5(s)` | MD5 hex digest |
| `sha256` | `sha256(s)` | SHA-256 hex digest |
| `sha512` | `sha512(s)` | SHA-512 hex digest |
| `base64_encode` | `base64_encode(data)` | Base64 encode |
| `base64_decode` | `base64_decode(data)` | Base64 decode |

### JSON

| Function | Signature | Description |
|----------|-----------|-------------|
| `to_json` | `to_json(obj)` | Serialize to JSON |
| `parse_json` | `parse_json(s)` | Parse JSON string |

---

## AI Functions

### API Configuration

| Function | Signature | Description |
|----------|-----------|-------------|
| `ai_set_key` | `ai_set_key(key)` | Set API key |
| `ai_set_base_url` | `ai_set_base_url(url)` | Set base URL |

### Core AI Calls

| Function | Signature | Description |
|----------|-----------|-------------|
| `ai_ask` | `ai_ask(prompt, model?, temp?, max_tokens?)` | Single AI request |
| `ai_chat` | `ai_chat(messages, model?, temp?, max_tokens?)` | Multi-turn chat |
| `ai_ollama` | `ai_ollama(prompt, model?, host?)` | Local Ollama call |
| `ai_chain` | `ai_chain(steps, default_model?)` | Chained prompt pipeline |
| `ai_compare` | `ai_compare(prompt, models)` | Compare models on same prompt |
| `ai_debate` | `ai_debate(question, models, rounds?)` | Multi-agent debate |

### Agent Framework

| Function | Signature | Description |
|----------|-----------|-------------|
| `ai_agent` | `ai_agent(model?, max_steps?, verbose?)` | Create an agent |
| `ai_agent_add_tool` | `ai_agent_add_tool(agent, name, func, desc)` | Register a tool |
| `ai_agent_run` | `ai_agent_run(agent, task)` | Run agent with task |

Built-in agent tools: `web_search`, `run_code`, `read_file`, `write_file`, `list_files`, `db_query`.

### Safety & Cache

| Function | Signature | Description |
|----------|-----------|-------------|
| `ai_enable_cache` | `ai_enable_cache(enabled?)` | Toggle response caching |
| `ai_clear_cache` | `ai_clear_cache()` | Clear all cached responses |
| `ai_enable_guardrails` | `ai_enable_guardrails(enabled?)` | Toggle safety filtering |
| `ai_set_blocked_words` | `ai_set_blocked_words(words)` | Set blocked word list |
| `ai_stats` | `ai_stats()` | Get token/call statistics |

### Multimodal

| Function | Signature | Description |
|----------|-----------|-------------|
| `ai_describe_image` | `ai_describe_image(path, model?, host?)` | Describe image via llava |

---

## Transpiler (ViGo → Python)

Any ViGo source can be transpiled to native Python:

```bash
vigo build script.vigo     # produces script.py
```

Or programmatically:

```python
from vigo.transpiler.transpiler import transpile

python_code = transpile(vigo_source)
```

The transpiled output includes all necessary imports and helper functions, and runs at
native Python speed with zero ViGo overhead.

---

## Execution Modes

| Mode | Description |
|------|-------------|
| Tree-walk interpreter | Full step-through, breakpoints, variable inspection |
| Cython-compiled | Pre-compiled modules for speed |
| Python transpiler | ViGo → Python, runs at native speed |

---

## Standard Library Modules (25)

| Module | Purpose |
|--------|---------|
| `math` | Math, trig, random, constants (PI, E, TAU) |
| `io` | File I/O, path operations, print, input |
| `crypto` | MD5, SHA-256, SHA-512, Base64 |
| `net` | HTTP requests, downloads |
| `data` | JSON, CSV, Base64 encode/decode |
| `sys` | OS info, environment variables, sleep, shell exec |
| `db` | SQLite database operations |
| `log` | Structured logging with levels |
| `color` | Terminal ANSI colors |
| `ini` | INI config file parsing |
| `gui` | Simple GUI dialogs (tkinter) |
| `ai` | Single calls, chat, chain, agents, RAG, image gen, debates |
| `rag` | RAG retrieval (PDF, DOCX, HTML), ChromaDB vector DB |
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
└── vigo/
    ├── lexer/             # Tokenizer (tokens.py, lexer.py)
    ├── parser/            # Parser (ast_nodes.py, parser.py)
    ├── runtime/           # Interpreter (environment, objects, builtins, errors, interpreter)
    ├── stdlib/            # 25 standard library modules
    ├── bytecode/          # Bytecode compiler & VM
    └── transpiler/        # ViGo → Python transpiler
```

---

## Why ViGo?

- **Built for AI:** First-class AI primitives — agents, RAG, debates, guardrails
- **Readable:** `ts`/`Fin` blocks are visually clean; no bracket hunting
- **Pipeline-native:** `|>` makes data transformation chains obvious
- **Safe by default:** `?.` and `??` eliminate null reference crashes
- **Fast when needed:** Transpile to Python for native performance
- **Compact:** 25 stdlib modules, 35 AI capabilities, all in ~950 KB

---

## Status

**Version:** v3.6
**Tests:** 55/55 regression tests passing
**Platform:** Windows (primary), Linux/macOS (via Python source)

### Known limitations

- Single-line `if` / `for` / `switch` / `try-catch` blocks have parser edge cases with
  `Fin` consumption. Multi-line forms are fully stable (all 55 tests pass).
- Bytecode VM supports basic operations, variables, conditionals, loops, and functions,
  but does not support classes or pipes in bytecode mode.
- Cython `.pyd` files use pure `.py` fallback to avoid stale bytecode issues.

---

## Contributing

ViGo is under active development. Contributions are welcome:

1. Fork the repository
2. Create a feature branch
3. Add passing tests for any changes
4. Submit a pull request
```

---
