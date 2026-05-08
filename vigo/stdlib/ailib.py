"""ViGo AI Standard Library - Multi-Provider Agent Framework with Cache, Guardrails, Multimodal"""
import json, time, hashlib
import urllib.request, urllib.error
import os, sqlite3
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError
from .providers import PROVIDERS
from .providers.request import make_request


class AIClient:
    def __init__(self):
        self.default_model = "gpt-3.5-turbo"
        self.default_temp = 0.7
        self.default_max_tokens = 2000
        self.default_provider = "openai"
        self.api_key = None
        self.base_url = None
        self.total_tokens = 0
        self.call_count = 0
        self.cache = {}
        self.cache_enabled = True
        self.guardrails_enabled = True
        self.blocked_words = []
        self.provider = "openai"
        self.max_retries = 3
        self.retry_delay = 2.0
        self.stream_callback = None
        self.stream_chunks = []

    def set_api_key(self, key): self.api_key = key; return self
    def set_base_url(self, url): self.base_url = url; return self
    def set_provider(self, provider):
        if provider in PROVIDERS:
            self.provider = provider
        return self

    def enable_cache(self, enabled=True): self.cache_enabled = enabled; return self
    def enable_guardrails(self, enabled=True): self.guardrails_enabled = enabled; return self
    def set_blocked_words(self, words): self.blocked_words = words; return self

    def _cache_key(self, prompt, model, provider):
        return hashlib.md5(f"{prompt}|{model}|{provider}".encode()).hexdigest()

    def _apply_guardrails(self, text, direction="output"):
        if not self.guardrails_enabled:
            return text, True
        for word in self.blocked_words:
            if word.lower() in text.lower():
                return f"[BLOCKED: contains '{word}']", False
        return text, True

    def set_stream_callback(self, callback):
        """Register a callback function for streaming chunks."""
        self.stream_callback = callback
        return self

    def get_stream_chunks(self):
        """Return and clear the collected stream chunks."""
        chunks = self.stream_chunks.copy()
        self.stream_chunks = []
        return chunks

    def ask(self, prompt, model=None, temp=None, max_tokens=None, provider=None, stream=False):
        clean_prompt, ok = self._apply_guardrails(prompt, "input")
        if not ok:
            return clean_prompt

        if self.cache_enabled and not stream:
            key = self._cache_key(clean_prompt, model or self.default_model, provider or self.provider)
            if key in self.cache:
                return self.cache[key]

        response = make_request(
            self,
            [{"role": "user", "content": str(clean_prompt)}],
            model, temp, max_tokens, stream, provider
        )

        if stream and not response:
            response = make_request(
                self,
                [{"role": "user", "content": str(clean_prompt)}],
                model, temp, max_tokens, False, provider
            )

        clean_response, ok = self._apply_guardrails(response, "output")

        if self.cache_enabled and not stream:
            key = self._cache_key(clean_prompt, model or self.default_model, provider or self.provider)
            self.cache[key] = clean_response

        return clean_response

    def chat(self, messages, model=None, temp=None, max_tokens=None, provider=None):
        clean_messages = []
        for msg in messages:
            if isinstance(msg, (list, tuple)) and len(msg) >= 2:
                content, _ = self._apply_guardrails(str(msg[1]), "input")
                clean_messages.append({"role": str(msg[0]), "content": content})
            elif isinstance(msg, dict):
                content, _ = self._apply_guardrails(str(msg.get("content", "")), "input")
                clean_messages.append({"role": msg.get("role", "user"), "content": content})

        if self.cache_enabled and clean_messages:
            key = self._cache_key(str(clean_messages[-1].get("content","")), model or self.default_model, provider or self.provider)
            if key in self.cache:
                return self.cache[key]

        response = make_request(
            self,
            clean_messages,
            model, temp, max_tokens, False
        )

        clean_response, ok = self._apply_guardrails(response, "output")
        if self.cache_enabled and clean_messages:
            key = self._cache_key(str(clean_messages[-1].get("content","")), model or self.default_model, provider or self.provider)
            self.cache[key] = clean_response

        return clean_response

    def list_providers(self):
        return list(PROVIDERS.keys())

    def list_models(self, provider=None):
        models_by_provider = {
            "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
            "claude": ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307", "claude-3-opus-20240229"],
            "groq": ["llama-3.3-70b", "mixtral-8x7b", "gemma2-9b-it"],
            "deepseek": ["deepseek-chat", "deepseek-coder"],
            "mistral": ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest"],
            "together": ["meta-llama/Llama-3.3-70B-Instruct-Turbo", "mistralai/Mixtral-8x7B-Instruct-v0.1"],
            "fireworks": ["accounts/fireworks/models/llama-v3p1-70b-instruct", "accounts/fireworks/models/mixtral-8x7b-instruct"],
            "perplexity": ["sonar-pro", "sonar", "llama-3.1-sonar-large-128k-online"],
            "cohere": ["command-r-plus", "command-r", "command"],
            "grok": ["grok-beta", "grok-2"],
            "cerebras": ["llama3.1-70b", "llama3.1-8b"],
            "sambanova": ["Meta-Llama-3.1-70B-Instruct", "Meta-Llama-3.1-8B-Instruct"],
            "gemini": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
            "openrouter": [],
            "ollama": ["(use ollama list)"],
            "lmstudio": ["(use LM Studio UI)"],
            "vllm": ["(check vLLM server)"],
            "localai": ["(check LocalAI server)"],
            "textgen": ["(check text-generation-webui)"],
            "llamacpp": ["(check llama.cpp server)"],
        }
        p = provider or self.provider
        return models_by_provider.get(p, ["(unknown - check provider docs)"])

    def ollama(self, prompt, model="llama3", host="http://localhost:11434"):
        clean_prompt, ok = self._apply_guardrails(prompt, "input")
        if not ok:
            return clean_prompt

        if self.cache_enabled:
            key = self._cache_key(clean_prompt, model, "ollama-local")
            if key in self.cache:
                return self.cache[key]

        url = f"{host}/api/generate"
        data = json.dumps({"model": model, "prompt": str(clean_prompt), "stream": False}).encode('utf-8')
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=300) as resp:
                    result = json.loads(resp.read().decode('utf-8'))
                    response = result.get("response", "")
                    break
            except (urllib.error.URLError, ConnectionResetError, TimeoutError) as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
            except Exception as e:
                raise ViGoError(f"Ollama error: {e}")
        else:
            raise ViGoError(f"Ollama connection failed after {self.max_retries+1} attempts: {last_error}")

        clean_response, ok = self._apply_guardrails(response, "output")
        self.total_tokens += len(prompt) // 4 + len(response) // 4
        self.call_count += 1
        if self.cache_enabled:
            key = self._cache_key(clean_prompt, model, "ollama-local")
            self.cache[key] = clean_response
        return clean_response

    def chain(self, steps, default_model="gemma-4b", provider=None):
        result = ""
        for step in steps:
            prompt_template = step[0]
            model = step[1] if len(step) > 1 else default_model
            p = step[2] if len(step) > 2 else (provider or self.provider)
            result = self.ask(prompt_template.replace("__OUTPUT__", result), model, provider=p)
        return result

    def compare(self, prompt, models, provider=None):
        results = {}
        for model in models:
            results[model] = self.ask(prompt, model, provider=provider)
        return results

    def get_stats(self):
        return {"total_tokens": self.total_tokens, "call_count": self.call_count, "cache_size": len(self.cache)}

    def clear_cache(self):
        self.cache = {}
        return True

    def debate(self, question, models, rounds=2, provider=None):
        responses = {}
        for model in models:
            responses[model] = self.ask(
                f"Answer this question with your best reasoning:\n{question}",
                model, provider=provider
            )

        for r in range(rounds - 1):
            for model in models:
                others = {m: responses[m] for m in models if m != model}
                critique_prompt = f"""Question: {question}

Your previous answer: {responses[model]}

Other answers from different models:
{json.dumps(others, indent=2)}

Critique the weaknesses in the other answers and improve your own answer. Be concise and direct."""
                responses[model] = self.ask(critique_prompt, model, provider=provider)

        return responses

    def describe_image(self, image_path, model="llava", host="http://localhost:11434"):
        import base64
        try:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            return f"Image read error: {e}"

        url = f"{host}/api/generate"
        data = json.dumps({
            "model": model,
            "prompt": "Describe this image in detail.",
            "images": [img_b64],
            "stream": False,
        }).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result.get("response", "No description generated.")
        except Exception as e:
            return f"Multimodal error: {e}. Make sure {model} model is loaded in Ollama."


class AIAgent:
    def __init__(self, model="gemma-4b", max_steps=5, verbose=False, provider="ollama"):
        self.model = model
        self.max_steps = max_steps
        self.verbose = verbose
        self.provider = provider
        self.tools = {}
        self.memory = []
        self.long_term_memory = []
        self.retry_count = 2
        self._register_builtin_tools()
        self.stream_callback = None
        self._stream_callback_raw = None

    def _register_builtin_tools(self):
        self.tools["web_search"] = {"func": self._web_search, "desc": "Search the web"}
        self.tools["run_code"] = {"func": self._run_code, "desc": "Execute Python code"}
        self.tools["read_file"] = {"func": self._read_file, "desc": "Read a file"}
        self.tools["write_file"] = {"func": self._write_file, "desc": "Write to a file"}
        self.tools["list_files"] = {"func": self._list_files, "desc": "List files"}
        self.tools["db_query"] = {"func": self._db_query, "desc": "Query SQLite"}

    def _web_search(self, query):
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers={"User-Agent": "ViGo/3.5"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                import re
                snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
                if snippets:
                    return "\n".join(re.sub(r'<[^>]+>', '', s).strip()[:300] for s in snippets[:5])
                return "No results."
        except Exception as e:
            return f"Search error: {e}"

    def _run_code(self, code):
        import sys, io
        old_stdout = sys.stdout
        captured = io.StringIO()
        sys.stdout = captured
        try:
            exec(code, {"__builtins__": __builtins__}, {})
            return captured.getvalue() or "(no output)"
        except Exception as e:
            return f"Code error: {e}"
        finally:
            sys.stdout = old_stdout

    def _read_file(self, path):
        try:
            with open(path.strip(), "r", encoding="utf-8") as f:
                return f.read()[:2000]
        except Exception as e:
            return f"Read error: {e}"

    def _write_file(self, args):
        parts = args.split("|||", 1)
        if len(parts) != 2:
            return "Format: path ||| content"
        try:
            with open(parts[0].strip(), "w", encoding="utf-8") as f:
                f.write(parts[1].strip())
            return "Written."
        except Exception as e:
            return f"Write error: {e}"

    def _list_files(self, path):
        try:
            return "\n".join(os.listdir(path.strip() or ".")[:50])
        except Exception as e:
            return f"List error: {e}"

    def _db_query(self, args):
        parts = args.split("|||", 1)
        try:
            conn = sqlite3.connect(parts[0].strip())
            cur = conn.execute(parts[1].strip() if len(parts) > 1 else "SELECT name FROM sqlite_master")
            rows = cur.fetchall()
            conn.close()
            return json.dumps([dict(r) for r in rows] if cur.description else [list(r) for r in rows], default=str)[:2000]
        except Exception as e:
            return f"DB error: {e}"

    def add_tool(self, name, func, description):
        self.tools[name] = {"func": func, "desc": description}
        return self

    def _build_system_prompt(self):
        prompt = "You are a helpful AI assistant with tools.\n\nTools:\n"
        for n, i in self.tools.items():
            prompt += f"- {n}: {i['desc']}\n"
        prompt += "\nTOOL: name\nINPUT: value\n\nTOOLS: a,b\nINPUTS: x|||y\n\nFINAL: answer\n"
        return prompt

    def _call_tool(self, name, input_str):
        if name not in self.tools:
            return f"Tool '{name}' not found"
        for _ in range(self.retry_count + 1):
            try:
                return str(self.tools[name]["func"](input_str.strip()))
            except Exception:
                continue
        return "Tool error"

    def _log(self, msg):
        if self.verbose:
            print(f"[Agent] {msg}")

    def run(self, task):
        self._log(f"Task: {task}")
        self.memory = []
        ai = AIClient()
        prompt = f"{self._build_system_prompt()}\n\nTask: {task}"
        for step in range(self.max_steps):
            self._log(f"Step {step+1}/{self.max_steps}")
            if self.provider == "ollama":
                response = ai.ollama(prompt, self.model)
            else:
                response = ai.ask(prompt, self.model, provider=self.provider)
            self.memory.append({"step": step+1, "response": response})
            if "TOOLS:" in response and "INPUTS:" in response:
                ts = response.split("TOOLS:")[1].split("\n")[0].strip()
                ins = response.split("INPUTS:")[1].split("\n")[0].strip()
                names = [t.strip() for t in ts.split(",")]
                inputs = [i.strip() for i in ins.split("|||")]
                results = []
                for i, n in enumerate(names):
                    inp = inputs[i] if i < len(inputs) else ""
                    results.append(f"{n}: {self._call_tool(n, inp)}")
                prompt = f"{prompt}\n\nResults:\n" + "\n".join(results) + "\n\nContinue."
                continue
            if "TOOL:" in response:
                tn = response.split("TOOL:")[1].split("\n")[0].strip()
                ti = response.split("INPUT:")[1].split("\n")[0].strip() if "INPUT:" in response else ""
                result = self._call_tool(tn, ti)
                prompt = f"{prompt}\n\nTool result: {result}\n\nContinue."
                continue
            if "FINAL:" in response:
                return response.split("FINAL:")[1].strip()
        return "Max steps reached."


_ai = AIClient()


def register(env):
    env.define('ai_ask', BuiltinFunction(
        lambda p, m=None, t=None, mt=None, prv=None, stream=False: _ai.ask(p, m, t, mt, prv, stream), 'ai_ask'))
    env.define('ai_chat', BuiltinFunction(
        lambda msgs, m=None, t=None, mt=None, prv=None: _ai.chat(msgs, m, t, mt, prv), 'ai_chat'))
    env.define('ai_on_chunk', BuiltinFunction(
        lambda callback: _ai.set_stream_callback(callback) and True, 'ai_on_chunk'))
    env.define('ai_stream_chunks', BuiltinFunction(
        lambda: _ai.get_stream_chunks(), 'ai_stream_chunks'))

    env.define('ai_ollama', BuiltinFunction(
        lambda p, m="llama3", h="http://localhost:11434": _ai.ollama(p, m, h), 'ai_ollama'))

    env.define('ai_set_provider', BuiltinFunction(
        lambda p: _ai.set_provider(p) and True, 'ai_set_provider'))
    env.define('ai_list_providers', BuiltinFunction(
        lambda: _ai.list_providers(), 'ai_list_providers'))
    env.define('ai_list_models', BuiltinFunction(
        lambda p=None: _ai.list_models(p), 'ai_list_models'))

    env.define('ai_chain', BuiltinFunction(
        lambda steps, dm="gemma-4b", p=None: _ai.chain(steps, dm, p), 'ai_chain'))
    env.define('ai_compare', BuiltinFunction(
        lambda prompt, models, p=None: _ai.compare(prompt, models, p), 'ai_compare'))
    env.define('ai_debate', BuiltinFunction(
        lambda q, models, r=2, p=None: _ai.debate(q, models, r, p), 'ai_debate'))

    env.define('ai_stats', BuiltinFunction(lambda: _ai.get_stats(), 'ai_stats'))
    env.define('ai_set_key', BuiltinFunction(lambda k: _ai.set_api_key(k) and True, 'ai_set_key'))
    env.define('ai_set_base_url', BuiltinFunction(lambda u: _ai.set_base_url(u) and True, 'ai_set_base_url'))
    env.define('ai_enable_cache', BuiltinFunction(lambda e=True: _ai.enable_cache(e) and True, 'ai_enable_cache'))
    env.define('ai_clear_cache', BuiltinFunction(lambda: _ai.clear_cache(), 'ai_clear_cache'))
    env.define('ai_enable_guardrails', BuiltinFunction(lambda e=True: _ai.enable_guardrails(e) and True, 'ai_enable_guardrails'))
    env.define('ai_set_blocked_words', BuiltinFunction(lambda words: _ai.set_blocked_words(words) and True, 'ai_set_blocked_words'))

    env.define('ai_set_retries', BuiltinFunction(lambda n: setattr(_ai, 'max_retries', int(n)) or True, 'ai_set_retries'))
    env.define('ai_set_retry_delay', BuiltinFunction(lambda d: setattr(_ai, 'retry_delay', float(d)) or True, 'ai_set_retry_delay'))
    env.define('ai_get_retry_config', BuiltinFunction(lambda: {"max_retries": _ai.max_retries, "retry_delay": _ai.retry_delay}, 'ai_get_retry_config'))

    env.define('ai_describe_image', BuiltinFunction(
        lambda path, model="llava", host="http://localhost:11434": _ai.describe_image(path, model, host), 'ai_describe_image'))

    def _create_agent(model="gemma-4b", max_steps=5, verbose=False, provider="ollama"):
        return AIAgent(model, max_steps, verbose, provider)

    def _agent_add_tool(agent, name, func, desc):
        if isinstance(agent, AIAgent):
            agent.add_tool(name, func, desc)
            return agent

    def _agent_run(agent, task):
        if isinstance(agent, AIAgent):
            return agent.run(task)
        return "Invalid agent"

    env.define('ai_agent', BuiltinFunction(_create_agent, 'ai_agent'))
    env.define('ai_agent_add_tool', BuiltinFunction(_agent_add_tool, 'ai_agent_add_tool'))
    env.define('ai_agent_run', BuiltinFunction(_agent_run, 'ai_agent_run'))