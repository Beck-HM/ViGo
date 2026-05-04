"""ViGo v3.5 Regression Test Suite - Tests for ailib, interpreter, parser, and REPL"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vigo.lexer.lexer import Lexer
from vigo.parser.parser import Parser
from vigo.runtime.interpreter import Interpreter
from vigo.runtime.errors import ViGoError

# ── Test framework ──
PASSED = 0
FAILED = 0
ERRORS = []

def test(name, source, expected, interpreter=None):
    """Run a ViGo source snippet and assert the last statement's result equals expected."""
    global PASSED, FAILED, ERRORS
    try:
        interp = interpreter or Interpreter(source_file="<test>")
        ast = Parser(Lexer(source)).parse_program()
        result = None
        for stmt in ast.statements:
            result = interp.eval(stmt, interp.global_env)
        if result == expected:
            PASSED += 1
            print(f"  PASS: {name}")
        else:
            FAILED += 1
            msg = f"FAIL: {name} - expected {repr(expected)}, got {repr(result)}"
            ERRORS.append(msg)
            print(f"  {msg}")
    except ViGoError as e:
        if expected == ViGoError or expected == "ViGoError":
            PASSED += 1
            print(f"  PASS: {name} (caught ViGoError)")
        else:
            FAILED += 1
            msg = f"FAIL: {name} - unexpected ViGoError: {e}"
            ERRORS.append(msg)
            print(f"  {msg}")
    except Exception as e:
        FAILED += 1
        msg = f"FAIL: {name} - exception: {type(e).__name__}: {e}"
        ERRORS.append(msg)
        print(f"  {msg}")


def test_error(name, source):
    """Assert that source raises a ViGoError."""
    global PASSED, FAILED, ERRORS
    try:
        interp = Interpreter(source_file="<test>")
        ast = Parser(Lexer(source)).parse_program()
        for stmt in ast.statements:
            interp.eval(stmt, interp.global_env)
        FAILED += 1
        msg = f"FAIL: {name} - expected ViGoError, but no error raised"
        ERRORS.append(msg)
        print(f"  {msg}")
    except ViGoError:
        PASSED += 1
        print(f"  PASS: {name} (expected error)")
    except Exception as e:
        FAILED += 1
        msg = f"FAIL: {name} - expected ViGoError, got {type(e).__name__}: {e}"
        ERRORS.append(msg)
        print(f"  {msg}")
test("list.pop empty", "x = []\nx.pop()", None)
test("list.reverse", "x = [3,1,2]\nx.reverse()\nx", [2, 1, 3])
test("list.extend", "x = [1]\nx.extend([2,3])\nx", [1, 2, 3])
test("list.insert", "x = [1,3]\nx.insert(1, 2)\nx", [1, 2, 3])
test("list.insert at 0", "x = [2,3]\nx.insert(0, 1)\nx", [1, 2, 3])
test("list.remove", "x = [1,2,3]\nx.remove(2)\nx", [1, 3])
test("list.find found", "x = [10,20,30]\nx.find(20)", 1)
test("list.find not found", "x = [10,20,30]\nx.find(99)", -1)
test("list.sort default", "x = [3,1,2]\nx.sort()\nx", [1, 2, 3])

# string methods (ViGo uses double quotes only)
test("str.upper", 'x = "hello"\nx.upper()', "HELLO")
test("str.lower", 'x = "HELLO"\nx.lower()', "hello")
test("str.trim", 'x = "  hi  "\nx.trim()', "hi")
test("str.split", 'x = "a,b,c"\nx.split(",")', ["a", "b", "c"])
test("str.join", 'x = ","\nx.join(["a","b"])', "a,b")
test("str.replace", 'x = "hello"\nx.replace("l", "L")', "heLLo")
test("str.startswith true", 'x = "hello"\nx.startswith("he")', True)
test("str.startswith false", 'x = "hello"\nx.startswith("xx")', False)
test("str.endswith true", 'x = "hello"\nx.endswith("lo")', True)
test("str.endswith false", 'x = "hello"\nx.endswith("xx")', False)
test("str.contains true", 'x = "hello"\nx.contains("ell")', True)
test("str.contains false", 'x = "hello"\nx.contains("xx")', False)
test("str.find found", 'x = "hello"\nx.find("ll")', 2)
test("str.find not found", 'x = "hello"\nx.find("xx")', -1)
test("str.count", 'x = "banana"\nx.count("a")', 3)

# dict methods
test("dict.keys", 'd = {"a":1,"b":2}\nd.keys()', ["a", "b"])
test("dict.values", 'd = {"a":1,"b":2}\nd.values()', [1, 2])
test("dict.get present", 'd = {"a":1}\nd.get("a")', 1)
test("dict.get missing", 'd = {"a":1}\nd.get("b", 99)', 99)
test("dict.get missing no default", 'd = {"a":1}\nd.get("b")', None)
test("dict.items", 'd = {"a":1,"b":2}\nd.items()', [("a", 1), ("b", 2)])


# ═══════════════════════════════════════════════════════════════════════
# Test 2: Switch multi-line case body (Task 4)
# ═══════════════════════════════════════════════════════════════════════
print("\n--- Switch Multi-line Case Body ---")

test("switch single case",
"""x = 1
switch x ts
    case 1 ts
        result = "one"
    Fin
Fin
result
""", "one")

test("switch multi-line case body",
"""x = 2
result = ""
switch x ts
    case 1 ts
        result = "one"
        result = result + "!"
    Fin
    case 2 ts
        a = "two"
        result = a + "!"
    Fin
Fin
result
""", "two!")

test("switch with nested if in case",
"""x = 10
result = ""
switch x ts
    case 10 ts
        if ok ts
            result = "ten"
        Fin
    Fin
Fin
result
""", "ten")

test("switch with range and multi-line",
"""x = 85
grade = ""
switch x ts
    case 90..100 ts
        grade = "A"
    Fin
    case 80..89 ts
        grade = "B"
        grade = grade + "+"
    Fin
    default ts
        grade = "F"
    Fin
Fin
grade
""", "B+")

test("switch default multi-line",
"""x = 50
msg = ""
switch x ts
    case 100 ts
        msg = "full"
    Fin
    default ts
        msg = "not full"
        msg = msg + " marks"
    Fin
Fin
msg
""", "not full marks")

test("switch fall-through to default",
"""x = 42
r = ""
switch x ts
    case 1 ts r = "one" Fin
    case 2 ts r = "two" Fin
    default ts
        r = "other"
    Fin
Fin
r
""", "other")


# ═══════════════════════════════════════════════════════════════════════
# Test 3: ailib.py - Agent registration & basic AI functions (Task 1)
# ═══════════════════════════════════════════════════════════════════════
print("\n--- AI Library ---")

test("ai_list_providers", "ai_list_providers()",
    ["openai", "deepseek", "groq", "claude", "mistral", "together",
     "fireworks", "perplexity", "cohere", "grok", "cerebras", "sambanova",
     "gemini", "openrouter", "ollama", "lmstudio", "vllm", "localai",
     "textgen", "llamacpp"])

test("ai_set_provider", 'ai_set_provider("openai")\nok', True)

test("ai_stats returns dict",
    "ai_stats()",
    {"total_tokens": 0, "call_count": 0, "cache_size": 0})

test("ai_set_retries", "ai_set_retries(5)\nok", True)

test("ai_get_retry_config", "ai_get_retry_config()",
    {"max_retries": 5, "retry_delay": 2.0})

test("ai_agent creates agent",
    'agent = ai_agent("gemma-4b", 3, False, "ollama")\nagent != null', True)

test("ai_set_key default", 'ai_set_key("test-key")\nok', True)

test("ai_enable_cache toggle", "ai_enable_cache(ok)\nok", True)

test("ai_clear_cache", "ai_clear_cache()\nok", True)


# ═══════════════════════════════════════════════════════════════════════
# Test 4: Core language features (sanity check)
# ═══════════════════════════════════════════════════════════════════════
print("\n--- Core Language ---")

test("arithmetic", "2 + 3 * 4", 14)
test("string concat", '"hello" + " world"', "hello world")
test("bool ok", "ok", True)
test("bool no", "no", False)
test("bool true alias", "true", True)
test("bool false alias", "false", False)
test("if with ts", "x = 5\nif x > 0 ts\n  r = 1\nFin", 1)
test("function definition", "Fun as double(x): ts Ret x * 2 Fin Fin\ndouble(5)", 10)
test("pipe operator", "[1,2,3] |> sum()", 6)
test("optional chaining on null", "u = null\nu?.name", None)
test("null coalescing", 'u = null\nu ?? "default"', "default")
test("list comprehension", "[x*x for x in 1..3]", [1, 4, 9])
test("const protection", "const PI = 3.14\nPI", 3.14)
test_error("const mutation", "const X = 1\nX = 2")
test("enum auto", "enum Color ts Red,Green,Blue Fin\nColor.Green", 1)
test("class inheritance",
"""class Animal ts
    Fun as init(name): ts this.name = name Fin
    Fun as speak(): ts Ret "sound" Fin
Fin
class Dog extends Animal ts
    Fun as speak(): ts Ret "bark" Fin
Fin
d = new Dog("Rex")
d.speak()
""", "bark")
test("switch range matching",
"""x = 75
r = ""
switch x ts
    case 90..100 ts r = "A" Fin
    case 80..89 ts r = "B" Fin
    case 70..79 ts r = "C" Fin
    default ts r = "F" Fin
Fin
r
""", "C")
test("string interpolation", 'name = "World"\n"Hello, {name}!"', "Hello, World!")
test("chained comparison", "x = 50\nif 0 < x and x < 100 ts r = ok Fin el ts r = no Fin\nr", True)
test("skip loop semantics", "x = 3\nskip x <= 0 ts\n  x = x - 1\nFin\nx", 0)
test("go loop", "x = 0\ngo ts\n  x = x + 1\nFin loop x < 3\nx", 3)
test("try catch",
"""r = ""
try ts
    throw "oops"
catch e ts
    r = e
Fin
r != null
""", True)


# ═══════════════════════════════════════════════════════════════════════
# Results
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print(f"RESULTS: {PASSED} passed, {FAILED} failed, {PASSED + FAILED} total")
if ERRORS:
    print("\nFAILURES:")
    for e in ERRORS:
        print(f"  {e}")
print("=" * 60)

sys.exit(0 if FAILED == 0 else 1)