"""ViGo AI Standard Library - Multi-Provider Agent Framework with Cache, Guardrails, Multimodal, Function Calling, Embeddings"""
import json, time, hashlib
import urllib.request, urllib.error
import os, sqlite3
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError
from .providers import PROVIDERS, get_provider_config
from .providers.request import make_request


def _env(key, default):
    """Read an environment variable, return default if not set."""
    return os.environ.get(key, default)


class AIClient:
    def __init__(self):
        self.default_model = _env("VIGO_AI_MODEL", "")
        self.default_temp = float(_env("VIGO_AI_TEMP", "0.7"))
        self.default_max_tokens = int(_env("VIGO_AI_MAX_TOKENS", "2000"))
        self.default_provider = _env("VIGO_AI_PROVIDER", "ollama")
        self.api_key = _env("VIGO_AI_API_KEY", None)
        self.base_url = _env("VIGO_AI_BASE_URL", None)
        self.total_tokens = 0
        self.call_count = 0
        self.cache = {}
        self.cache_enabled = True
        self.guardrails_enabled = True
        self.blocked_words = []
        self.provider = self.default_provider
        self.max_retries = int(_env("VIGO_AI_RETRIES", "3"))
        self.retry_delay = float(_env("VIGO_AI_RETRY_DELAY", "2.0"))
        self.stream_callback = None
        self.stream_chunks = []
        self._pending_tool_calls = {}
        self.semantic_cache_enabled = False
        self.semantic_similarity_threshold = 0.95
        self.semantic_cache = {}

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
    
    def enable_semantic_cache(self, enabled=True, similarity_threshold=0.95):
        """Enable semantic caching that groups similar prompts together.
        
        When enabled, prompts that are semantically similar (above the threshold)
        will share cached responses, avoiding redundant API calls.
        
        Requires embedding support to compute similarities.
        """
        self.semantic_cache_enabled = enabled
        self.semantic_similarity_threshold = similarity_threshold
        if not hasattr(self, 'semantic_cache'):
            self.semantic_cache = {}  # {embedding_vector: response}
        return True
    
    def _cosine_similarity(self, vec1, vec2):
        """Compute cosine similarity between two vectors."""
        if not vec1 or not vec2:
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)
    
    def _find_semantic_match(self, text, embedding_model=None):
        """Find a semantically similar cached response.
        
        Returns the cached response if similarity > threshold, else None.
        """
        if not getattr(self, 'semantic_cache_enabled', False):
            return None
        if not hasattr(self, 'semantic_cache') or not self.semantic_cache:
            return None
        
        try:
            # Generate embedding for the input text
            vec = self.embed(text, model=embedding_model)
            if not vec:
                return None
            
            # Find most similar cached embedding
            best_similarity = 0
            best_response = None
            
            for cached_vec, cached_response in self.semantic_cache.items():
                sim = self._cosine_similarity(vec, cached_vec)
                if sim > best_similarity:
                    best_similarity = sim
                    best_response = cached_response
            
            threshold = getattr(self, 'semantic_similarity_threshold', 0.95)
            if best_similarity >= threshold:
                return best_response
        except Exception:
            pass
        
        return None
    
    def _add_to_semantic_cache(self, text, response, embedding_model=None):
        """Add a response to the semantic cache."""
        if not getattr(self, 'semantic_cache_enabled', False):
            return
        
        try:
            vec = self.embed(text, model=embedding_model)
            if vec:
                self.semantic_cache[tuple(vec)] = response
        except Exception:
            pass
    
    def clear_semantic_cache(self):
        """Clear the semantic cache."""
        self.semantic_cache = {}
        return True
    
    def get_semantic_cache_stats(self):
        """Get statistics about the semantic cache."""
        if not hasattr(self, 'semantic_cache'):
            return {"enabled": False, "size": 0, "threshold": 0}
        return {
            "enabled": getattr(self, 'semantic_cache_enabled', False),
            "size": len(self.semantic_cache),
            "threshold": getattr(self, 'semantic_similarity_threshold', 0.95),
        }
    
    def deduplicate_prompts(self, prompts, embedding_model=None, similarity_threshold=0.95):
        """Remove semantically duplicate prompts from a list.
        
        Returns a list of unique prompts and a mapping of duplicates.
        """
        if not prompts:
            return [], {}
        
        # Generate embeddings for all prompts
        try:
            embeddings = []
            for prompt in prompts:
                vec = self.embed(str(prompt), model=embedding_model)
                embeddings.append(vec)
        except Exception:
            # If embedding fails, return all prompts as unique
            return prompts, {}
        
        unique_indices = []
        duplicate_map = {}  # {original_index: [duplicate_indices]}
        
        for i, (prompt, vec) in enumerate(zip(prompts, embeddings)):
            if not vec:
                unique_indices.append(i)
                continue
            
            is_duplicate = False
            for j in unique_indices:
                sim = self._cosine_similarity(vec, embeddings[j])
                if sim >= similarity_threshold:
                    if j not in duplicate_map:
                        duplicate_map[j] = []
                    duplicate_map[j].append(i)
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_indices.append(i)
        
        unique_prompts = [prompts[i] for i in unique_indices]
        return unique_prompts, duplicate_map

    def _apply_guardrails(self, text, direction="output"):
        if not self.guardrails_enabled:
            return text, True
        for word in self.blocked_words:
            if word.lower() in text.lower():
                return f"[BLOCKED: contains '{word}']", False
        return text, True

    def _model(self, model): return model or self.default_model or "llama3"
    def _provider(self, provider): return provider or self.provider or "ollama"

    def set_stream_callback(self, callback): self.stream_callback = callback; return self
    def get_stream_chunks(self):
        chunks = self.stream_chunks.copy()
        self.stream_chunks = []
        return chunks

    def ask(self, prompt, model=None, temp=None, max_tokens=None, provider=None, stream=False):
        clean_prompt, ok = self._apply_guardrails(prompt, "input")
        if not ok:
            return clean_prompt
        m = self._model(model)
        p = self._provider(provider)
        if self.cache_enabled and not stream:
            key = self._cache_key(clean_prompt, m, p)
            if key in self.cache:
                return self.cache[key]
        response = make_request(self, [{"role": "user", "content": str(clean_prompt)}],
            m, temp if temp is not None else self.default_temp,
            max_tokens or self.default_max_tokens, stream, p)
        if stream and not response:
            response = make_request(self, [{"role": "user", "content": str(clean_prompt)}],
                m, temp if temp is not None else self.default_temp,
                max_tokens or self.default_max_tokens, False, p)
        clean_response, ok = self._apply_guardrails(response, "output")
        if self.cache_enabled and not stream:
            key = self._cache_key(clean_prompt, m, p)
            self.cache[key] = clean_response
        return clean_response

    def chat(self, messages, model=None, temp=None, max_tokens=None, provider=None):
        m = self._model(model)
        p = self._provider(provider)
        clean_messages = []
        for msg in messages:
            if isinstance(msg, (list, tuple)) and len(msg) >= 2:
                content, _ = self._apply_guardrails(str(msg[1]), "input")
                clean_messages.append({"role": str(msg[0]), "content": content})
            elif isinstance(msg, dict):
                content, _ = self._apply_guardrails(str(msg.get("content", "")), "input")
                clean_messages.append({"role": msg.get("role", "user"), "content": content})
        if self.cache_enabled and clean_messages:
            key = self._cache_key(str(clean_messages[-1].get("content","")), m, p)
            if key in self.cache:
                return self.cache[key]
        response = make_request(self, clean_messages,
            m, temp if temp is not None else self.default_temp,
            max_tokens or self.default_max_tokens, False, p)
        clean_response, ok = self._apply_guardrails(response, "output")
        if self.cache_enabled and clean_messages:
            key = self._cache_key(str(clean_messages[-1].get("content","")), m, p)
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
        return models_by_provider.get(provider or self.provider, ["(unknown - check provider docs)"])
    
    def list_models_live(self, provider=None):
        """Fetch the real-time model list from a provider's API.
        
        Supports:
        - Ollama: GET /api/tags
        - OpenAI-compatible: GET /v1/models
        - DeepSeek: GET /v1/models
        - Others: returns static list as fallback
        
        Returns a list of model name strings.
        """
        p = self._provider(provider)
        
        # Ollama: GET /api/tags
        if p == "ollama":
            try:
                host = _env("OLLAMA_HOST", "http://localhost:11434")
                url = f"{host}/api/tags"
                req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    models = [m.get("name", "") for m in data.get("models", [])]
                    if models:
                        return models
            except Exception:
                pass
            return self.list_models("ollama")
        
        # OpenAI-compatible: GET /v1/models
        config, _ = get_provider_config(p, self.base_url)
        base = config.get("url", "").replace("/chat/completions", "").replace("/v1/chat/completions", "")
        if not base:
            base = config.get("url", "").rsplit("/", 2)[0] if "/" in config.get("url", "") else ""
        
        if base:
            try:
                url = f"{base}/v1/models" if not base.endswith("/v1") else f"{base}/models"
                headers = {"Content-Type": "application/json"}
                if config.get("auth_header") and self.api_key:
                    headers[config["auth_header"]] = config.get("auth_prefix", "Bearer ") + self.api_key
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    models = [m.get("id", m.get("name", "")) for m in data.get("data", [])]
                    if models:
                        return sorted(models)
            except Exception:
                pass
        
        # Fallback to static list
        return self.list_models(p)
    
    def model_info(self, model_name, provider=None):
        """Get detailed information about a specific model.
        
        For Ollama: GET /api/show with model name
        For others: returns basic info from static data
        
        Returns a dict with model details.
        """
        p = self._provider(provider)
        
        # Ollama: GET /api/show
        if p == "ollama":
            try:
                host = _env("OLLAMA_HOST", "http://localhost:11434")
                url = f"{host}/api/show"
                data = json.dumps({"name": model_name}).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    result = json.loads(resp.read().decode('utf-8'))
                    return {
                        "name": model_name,
                        "provider": p,
                        "details": result.get("details", {}),
                        "parameters": result.get("parameters", ""),
                        "template": result.get("template", ""),
                    }
            except Exception as e:
                return {"name": model_name, "provider": p, "error": str(e)}
        
        # Cloud providers: return basic info
        return {
            "name": model_name,
            "provider": p,
            "available": True,
            "note": "Use ai_list_models_live() for real-time model list",
        }

    def ollama(self, prompt, model=None, host=None):
        m = model or self.default_model or "llama3"
        h = host or _env("OLLAMA_HOST", "http://localhost:11434")
        clean_prompt, ok = self._apply_guardrails(prompt, "input")
        if not ok:
            return clean_prompt
        if self.cache_enabled:
            key = self._cache_key(clean_prompt, m, "ollama-local")
            if key in self.cache:
                return self.cache[key]
        url = f"{h}/api/generate"
        data = json.dumps({"model": m, "prompt": str(clean_prompt), "stream": False}).encode('utf-8')
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
            key = self._cache_key(clean_prompt, m, "ollama-local")
            self.cache[key] = clean_response
        return clean_response

    def chain(self, steps, default_model=None, provider=None):
        dm = default_model or self.default_model or "llama3"
        result = ""
        for step in steps:
            prompt_template = step[0]
            model = step[1] if len(step) > 1 else dm
            p = step[2] if len(step) > 2 else self._provider(provider)
            result = self.ask(prompt_template.replace("__OUTPUT__", result), model, provider=p)
        return result

    def compare(self, prompt, models, provider=None):
        results = {}
        for model in models:
            results[model] = self.ask(prompt, model, provider=provider)
        return results
    
    def batch(self, prompts, model=None, temp=None, max_tokens=None, provider=None):
        """Process multiple prompts in parallel and return results.
        
        For cloud providers, sends concurrent requests using threads.
        For Ollama, processes sequentially to avoid overloading the local server.
        
        Returns a list of responses in the same order as the input prompts.
        """
        import concurrent.futures
        
        m = self._model(model)
        p = self._provider(provider)
        t = temp if temp is not None else self.default_temp
        mt = max_tokens or self.default_max_tokens
        
        results = [None] * len(prompts)
        
        # For Ollama, process sequentially to avoid overloading
        if p == "ollama":
            for i, prompt in enumerate(prompts):
                results[i] = self.ask(prompt, m, t, mt, p)
            return results
        
        # For cloud providers, use thread pool for parallel processing
        def _process_one(idx, prompt):
            return idx, self.ask(prompt, m, t, mt, p)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(prompts), 10)) as executor:
            futures = {executor.submit(_process_one, i, prompt): i for i, prompt in enumerate(prompts)}
            for future in concurrent.futures.as_completed(futures):
                try:
                    idx, result = future.result()
                    results[idx] = result
                except Exception as e:
                    idx = futures[future]
                    results[idx] = f"Error: {e}"
        
        return results
    
    def batch_with_tools(self, prompts, tools, model=None, temp=None, max_tokens=None, provider=None):
        """Process multiple prompts with tools in parallel.
        
        Each prompt is processed with the given tools.
        Returns a list of results (text or tool_call dicts) in the same order.
        """
        import concurrent.futures
        
        m = self._model(model)
        p = self._provider(provider)
        t = temp if temp is not None else self.default_temp
        mt = max_tokens or self.default_max_tokens
        
        results = [None] * len(prompts)
        
        if p == "ollama":
            for i, prompt in enumerate(prompts):
                results[i] = self.ask_with_tools(prompt, tools, m, t, mt, p)
            return results
        
        def _process_one(idx, prompt):
            return idx, self.ask_with_tools(prompt, tools, m, t, mt, p)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(prompts), 10)) as executor:
            futures = {executor.submit(_process_one, i, prompt): i for i, prompt in enumerate(prompts)}
            for future in concurrent.futures.as_completed(futures):
                try:
                    idx, result = future.result()
                    results[idx] = result
                except Exception as e:
                    idx = futures[future]
                    results[idx] = f"Error: {e}"
        
        return results
    
    def web_search(self, query, num_results=5, provider=None):
        """Search the web and return results.
        
        Uses DuckDuckGo Instant Answer API (free, no key required).
        Falls back to HTML scraping if the API is unavailable.
        
        Returns a list of dicts with title, url, and snippet.
        """
        import re
        
        results = []
        
        # Try DuckDuckGo Instant Answer API first
        try:
            url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(str(query))}&format=json&no_html=1"
            req = urllib.request.Request(url, headers={"User-Agent": "ViGo/3.7"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                
                # Extract from RelatedTopics
                for topic in data.get("RelatedTopics", [])[:num_results]:
                    if isinstance(topic, dict):
                        results.append({
                            "title": topic.get("Text", "").split(" - ")[0][:100] if " - " in topic.get("Text", "") else topic.get("Text", "")[:100],
                            "url": topic.get("FirstURL", ""),
                            "snippet": topic.get("Text", "")[:300],
                        })
                
                # Also check Abstract
                if data.get("AbstractText"):
                    results.insert(0, {
                        "title": data.get("Heading", query),
                        "url": data.get("AbstractURL", ""),
                        "snippet": data.get("AbstractText", "")[:300],
                    })
                
                if results:
                    return results[:num_results]
        except Exception:
            pass
        
        # Fallback: DuckDuckGo HTML search
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(str(query))}"
            req = urllib.request.Request(url, headers={"User-Agent": "ViGo/3.7"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                
                # Extract results
                result_blocks = re.findall(r'class="result__body"[^>]*>(.*?)</a>\s*</h2>\s*<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
                link_pattern = re.findall(r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL)
                
                for i, (title_html, snippet_html) in enumerate(result_blocks[:num_results]):
                    title = re.sub(r'<[^>]+>', '', title_html).strip()
                    snippet = re.sub(r'<[^>]+>', '', snippet_html).strip()
                    url = link_pattern[i][0] if i < len(link_pattern) else ""
                    
                    results.append({
                        "title": title[:200],
                        "url": url,
                        "snippet": snippet[:300],
                    })
                
                if results:
                    return results[:num_results]
        except Exception:
            pass
        
        return results
    
    def web_search_ask(self, question, model=None, temp=None, max_tokens=None, provider=None, num_results=3):
        """Search the web and then use AI to answer a question based on results.
        
        Combines web_search() and ask() into one call.
        """
        # Search the web
        search_results = self.web_search(question, num_results)
        
        if not search_results:
            return self.ask(question, model, temp, max_tokens, provider)
        
        # Build context from search results
        context_parts = []
        for i, result in enumerate(search_results):
            context_parts.append(f"[{i+1}] {result['title']}\n{result['snippet']}\nSource: {result['url']}")
        
        context = "\n\n".join(context_parts)
        
        # Ask with context
        prompt = f"""Based on the following web search results, answer the question.
If the search results don't contain the answer, use your knowledge.

Search results:
{context}

Question: {question}

Answer:"""
        
        return self.ask(prompt, model, temp, max_tokens, provider)
    
    def news_search(self, query, num_results=5):
        """Search for recent news articles.
        
        Uses DuckDuckGo news search (free, no key required).
        
        Returns a list of dicts with title, url, source, and snippet.
        """
        import re
        
        results = []
        
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(str(query))}&iar=news&ia=news"
            req = urllib.request.Request(url, headers={"User-Agent": "ViGo/3.7"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                
                # Extract news results
                result_blocks = re.findall(r'class="result__body"[^>]*>(.*?)</a>', html, re.DOTALL)
                snippet_blocks = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
                source_blocks = re.findall(r'class="result__url"[^>]*>(.*?)</a>', html, re.DOTALL)
                
                for i in range(min(num_results, len(result_blocks))):
                    title = re.sub(r'<[^>]+>', '', result_blocks[i] if i < len(result_blocks) else "").strip()
                    snippet = re.sub(r'<[^>]+>', '', snippet_blocks[i] if i < len(snippet_blocks) else "").strip()
                    source = re.sub(r'<[^>]+>', '', source_blocks[i] if i < len(source_blocks) else "").strip()
                    
                    if title:
                        results.append({
                            "title": title[:200],
                            "url": "",
                            "source": source,
                            "snippet": snippet[:300],
                        })
        except Exception:
            pass
        
        return results

    def get_stats(self):
        return {"total_tokens": self.total_tokens, "call_count": self.call_count, "cache_size": len(self.cache)}
    
    def count_tokens(self, text, model=None):
        """Estimate the number of tokens in a text for a given model.
        
        Uses a simple character-based estimation (4 chars ≈ 1 token) as default,
        which works reasonably well for English text across most models.
        
        For more accurate counts with specific tokenizers, install tiktoken:
            pip install tiktoken
        
        Supported model families for accurate counting:
        - OpenAI (gpt-*, text-embedding-*)
        - Claude (claude-*)
        """
        m = model or self.default_model or "gpt-3.5-turbo"
        
        # Try tiktoken for OpenAI models
        try:
            import tiktoken
            
            # Map model to encoding
            if m.startswith("gpt-4") or m.startswith("o1") or m.startswith("o3"):
                encoding_name = "o200k_base"
            elif m.startswith("gpt-3.5"):
                encoding_name = "cl100k_base"
            elif "embedding" in m:
                encoding_name = "cl100k_base"
            else:
                encoding_name = "o200k_base"  # Default for newer models
            
            encoding = tiktoken.get_encoding(encoding_name)
            return len(encoding.encode(str(text)))
        except ImportError:
            pass
        
        # Try Anthropic's tokenizer for Claude models
        if m.startswith("claude"):
            try:
                # Claude uses roughly 3.5 chars per token for English
                words = str(text).split()
                return len(words) + int(len(str(text)) * 0.3)
            except:
                pass
        
        # Default: character-based estimation
        # Most models average 4 characters per token for English
        return max(1, len(str(text)) // 4)
    
    def count_tokens_batch(self, texts, model=None):
        """Count tokens for multiple texts.
        
        Returns a list of token counts in the same order as the input texts.
        """
        return [self.count_tokens(text, model) for text in texts]
    
    def token_cost_estimate(self, token_count, model=None):
        """Estimate the cost in USD for a given number of tokens.
        
        Returns a dict with input_cost, output_cost, and total_cost.
        Costs are approximate and based on published pricing as of 2025.
        """
        m = model or self.default_model or "gpt-3.5-turbo"
        
        # Approximate costs per 1K tokens (input, output)
        pricing = {
            # OpenAI
            "gpt-4o": (0.0025, 0.01),
            "gpt-4o-mini": (0.00015, 0.0006),
            "gpt-4-turbo": (0.01, 0.03),
            "gpt-4": (0.03, 0.06),
            "gpt-3.5-turbo": (0.0005, 0.0015),
            # Claude
            "claude-3-5-sonnet": (0.003, 0.015),
            "claude-3-opus": (0.015, 0.075),
            "claude-3-haiku": (0.00025, 0.00125),
            # DeepSeek
            "deepseek-chat": (0.00014, 0.00028),
            "deepseek-coder": (0.00014, 0.00028),
            # Others
            "gemini-2.0-flash": (0.0001, 0.0004),
            "gemini-1.5-pro": (0.00125, 0.005),
            "mistral-large": (0.002, 0.006),
            "command-r-plus": (0.003, 0.015),
            "llama-3.3-70b": (0.00059, 0.00079),
        }
        
        # Find matching pricing
        input_price, output_price = 0.001, 0.002  # Default fallback
        for key, (ip, op) in pricing.items():
            if key in m.lower():
                input_price, output_price = ip, op
                break
        
        input_cost = (token_count / 1000) * input_price
        output_cost = (token_count / 1000) * output_price
        
        return {
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "total_cost": round(input_cost + output_cost, 6),
            "price_per_1k_input": input_price,
            "price_per_1k_output": output_price,
        }

    def clear_cache(self): self.cache = {}; return True

    def extract(self, prompt, text, fields, model=None, temp=None, provider=None):
        """Extract structured data from text based on field descriptions.

        fields: a dict mapping field names to descriptions.
        Example: {"name": "person's full name", "age": "person's age as integer"}

        Returns a dict with the extracted values, or None for missing fields.
        """
        import re

        field_list = "\n".join(f"- {name}: {desc}" for name, desc in fields.items())

        system_prompt = f"""You are a data extraction tool. Extract the requested fields from the text.
        Return ONLY valid JSON with exactly these fields:
        {field_list}

        If a field is not found, use null for its value.
        Do not include any text outside the JSON object.
        Do not wrap the JSON in markdown code blocks."""

        full_prompt = f"Text to extract from:\n\n{text}\n\nExtract the fields and return the JSON object."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_prompt},
        ]

        response = self.chat(messages, model=model, temp=temp or 0.0, 
                           max_tokens=2000, provider=provider)

        # Try to parse the response as JSON
        # First, try to find a JSON object in the response
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                # Ensure all requested fields are present
                extracted = {}
                for name in fields:
                    extracted[name] = result.get(name)
                return extracted
            except json.JSONDecodeError:
                pass

        # If direct parsing fails, return raw response
        return {"_raw": response}

        # ═══════════════════════════════════════════════
        #  Embeddings
        # ═══════════════════════════════════════════════

    def embed(self, text, model=None, provider=None):
        p = self._provider(provider)
        config, _ = get_provider_config(p, self.base_url)
        embed_url = config.get("embedding_url")
        if not embed_url:
            raise ViGoError(f"Provider '{p}' does not support embeddings")
        embed_model = model or config.get("embedding_model", "text-embedding-ada-002")
        if p == "ollama":
            return self._embed_ollama(text, embed_model, embed_url)
        if config.get("message_format") == "cohere":
            return self._embed_cohere(text, embed_model, embed_url, config)
        return self._embed_openai(text, embed_model, embed_url, config)

    def embed_batch(self, texts, model=None, provider=None):
        p = self._provider(provider)
        config, _ = get_provider_config(p, self.base_url)
        embed_url = config.get("embedding_url")
        if not embed_url:
            raise ViGoError(f"Provider '{p}' does not support embeddings")
        embed_model = model or config.get("embedding_model", "text-embedding-ada-002")
        if p == "ollama":
            return [self._embed_ollama(t, embed_model, embed_url) for t in texts]
        if config.get("message_format") == "cohere":
            return [self._embed_cohere(t, embed_model, embed_url, config) for t in texts]
        return self._embed_openai_batch(texts, embed_model, embed_url, config)

    def _embed_ollama(self, text, model, base_url):
        url = base_url.rstrip('/') + "/api/embeddings" if "/api/embeddings" not in base_url else base_url
        data = json.dumps({"model": model, "prompt": str(text)}).encode('utf-8')
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=120) as resp:
                    result = json.loads(resp.read().decode('utf-8'))
                    self.total_tokens += result.get("total_tokens", len(text) // 4)
                    self.call_count += 1
                    return result.get("embedding", [])
            except (urllib.error.URLError, ConnectionResetError, TimeoutError) as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
            except Exception as e:
                raise ViGoError(f"Embedding error: {e}")
        raise ViGoError(f"Embedding failed after {self.max_retries+1} attempts: {last_error}")

    def _embed_openai(self, text, model, url, config):
        headers = {"Content-Type": "application/json"}
        if config.get("auth_header") and self.api_key:
            headers[config["auth_header"]] = config.get("auth_prefix", "Bearer ") + self.api_key
        body = {"model": model, "input": str(text)}
        data = json.dumps(body).encode('utf-8')
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                req = urllib.request.Request(url, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=120) as resp:
                    result = json.loads(resp.read().decode('utf-8'))
                    self.total_tokens += result.get("usage", {}).get("total_tokens", 0)
                    self.call_count += 1
                    return result.get("data", [{}])[0].get("embedding", [])
            except urllib.error.HTTPError as e:
                if 400 <= e.code < 500:
                    error_body = e.read().decode('utf-8', errors='ignore') if e.fp else str(e)
                    raise ViGoError(f"Embedding API error ({e.code}): {error_body[:500]}")
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
            except (urllib.error.URLError, ConnectionResetError, TimeoutError) as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
            except Exception as e:
                raise ViGoError(f"Embedding error: {e}")
        raise ViGoError(f"Embedding failed after {self.max_retries+1} attempts: {last_error}")

    def _embed_openai_batch(self, texts, model, url, config):
        headers = {"Content-Type": "application/json"}
        if config.get("auth_header") and self.api_key:
            headers[config["auth_header"]] = config.get("auth_prefix", "Bearer ") + self.api_key
        body = {"model": model, "input": [str(t) for t in texts]}
        data = json.dumps(body).encode('utf-8')
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                req = urllib.request.Request(url, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=300) as resp:
                    result = json.loads(resp.read().decode('utf-8'))
                    items = sorted(result.get("data", []), key=lambda x: x.get("index", 0))
                    self.total_tokens += result.get("usage", {}).get("total_tokens", 0)
                    self.call_count += 1
                    return [item.get("embedding", []) for item in items]
            except urllib.error.HTTPError as e:
                if 400 <= e.code < 500:
                    error_body = e.read().decode('utf-8', errors='ignore') if e.fp else str(e)
                    raise ViGoError(f"Embedding API error ({e.code}): {error_body[:500]}")
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
            except (urllib.error.URLError, ConnectionResetError, TimeoutError) as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
            except Exception as e:
                raise ViGoError(f"Embedding error: {e}")
        raise ViGoError(f"Embedding failed after {self.max_retries+1} attempts: {last_error}")

    def _embed_cohere(self, text, model, url, config):
        headers = {"Content-Type": "application/json"}
        if config.get("auth_header") and self.api_key:
            headers[config["auth_header"]] = config.get("auth_prefix", "Bearer ") + self.api_key
        body = {"model": model, "texts": [str(text)], "input_type": "search_document"}
        data = json.dumps(body).encode('utf-8')
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                req = urllib.request.Request(url, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=120) as resp:
                    result = json.loads(resp.read().decode('utf-8'))
                    self.total_tokens += result.get("meta", {}).get("billed_units", {}).get("input_tokens", 0)
                    self.call_count += 1
                    return result.get("embeddings", [[]])[0]
            except urllib.error.HTTPError as e:
                if 400 <= e.code < 500:
                    error_body = e.read().decode('utf-8', errors='ignore') if e.fp else str(e)
                    raise ViGoError(f"Embedding API error ({e.code}): {error_body[:500]}")
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
            except (urllib.error.URLError, ConnectionResetError, TimeoutError) as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
            except Exception as e:
                raise ViGoError(f"Embedding error: {e}")
        raise ViGoError(f"Embedding failed after {self.max_retries+1} attempts: {last_error}")

    def debate(self, question, models, rounds=2, provider=None):
        responses = {}
        for model in models:
            responses[model] = self.ask(f"Answer this question with your best reasoning:\n{question}", model, provider=provider)
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
    
    def rag_ask(self, prompt, knowledge_base, model=None, temp=None, max_tokens=None, provider=None, top_k=3):
        """Ask a question with automatic knowledge retrieval from a knowledge base.
        
        knowledge_base: a list of text chunks, or a path to a ChromaDB collection.
        top_k: number of most relevant chunks to inject into the prompt.
        
        Automatically retrieves relevant context and injects it into the prompt.
        """
        # Retrieve relevant chunks
        if isinstance(knowledge_base, list):
            # Simple keyword-based retrieval for list knowledge bases
            context_chunks = self._retrieve_keywords(prompt, knowledge_base, top_k)
        elif isinstance(knowledge_base, str):
            # Try ChromaDB collection
            context_chunks = self._retrieve_chromadb(prompt, knowledge_base, top_k)
        else:
            context_chunks = []
        
        # Build augmented prompt
        if context_chunks:
            context_text = "\n\n---\n\n".join(context_chunks)
            augmented_prompt = f"""Use the following context to answer the question.
If the context doesn't contain the answer, say so.

Context:
{context_text}

Question: {prompt}

Answer:"""
        else:
            augmented_prompt = prompt
        
        return self.ask(augmented_prompt, model, temp, max_tokens, provider)
    
    def rag_chat(self, messages, knowledge_base, model=None, temp=None, max_tokens=None, provider=None, top_k=3):
        """Multi-turn chat with automatic knowledge retrieval.
        
        The last user message is used for retrieval. Context is injected
        as a system message before the last user message.
        """
        if not messages:
            return ""
        
        # Extract the last user message for retrieval
        last_user_msg = ""
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break
            elif isinstance(msg, (list, tuple)) and len(msg) >= 2 and msg[0] == "user":
                last_user_msg = str(msg[1])
                break
        
        if not last_user_msg:
            return self.chat(messages, model, temp, max_tokens, provider)
        
        # Retrieve relevant chunks
        if isinstance(knowledge_base, list):
            context_chunks = self._retrieve_keywords(last_user_msg, knowledge_base, top_k)
        elif isinstance(knowledge_base, str):
            context_chunks = self._retrieve_chromadb(last_user_msg, knowledge_base, top_k)
        else:
            context_chunks = []
        
        # Inject context as a system message before the last user message
        if context_chunks:
            context_text = "\n\n---\n\n".join(context_chunks)
            context_msg = {"role": "system", "content": f"Use the following context to answer:\n\n{context_text}"}
            
            # Insert context message before the last message
            augmented_messages = list(messages)
            augmented_messages.insert(-1, context_msg)
        else:
            augmented_messages = messages
        
        return self.chat(augmented_messages, model, temp, max_tokens, provider)
    
    def _retrieve_keywords(self, query, chunks, top_k=3):
        """Simple keyword-based retrieval using word overlap scoring."""
        if not chunks:
            return []
        
        query_words = set(str(query).lower().split())
        if not query_words:
            return chunks[:top_k]
        
        scored = []
        for i, chunk in enumerate(chunks):
            chunk_words = set(str(chunk).lower().split())
            if not chunk_words:
                continue
            # Jaccard similarity
            intersection = query_words & chunk_words
            union = query_words | chunk_words
            score = len(intersection) / len(union) if union else 0
            scored.append((score, i))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        top_indices = [i for _, i in scored[:top_k]]
        return [chunks[i] for i in top_indices if i < len(chunks)]
    
    def _retrieve_chromadb(self, query, collection_path, top_k=3):
        """Retrieve relevant chunks from a ChromaDB collection."""
        try:
            import chromadb
            from chromadb.config import Settings
            
            client = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=collection_path,
                anonymized_telemetry=False,
            ))
            
            collection = client.get_or_create_collection(name="vigo_rag")
            
            results = collection.query(
                query_texts=[str(query)],
                n_results=min(top_k, collection.count()),
            )
            
            documents = results.get("documents", [[]])
            if documents and documents[0]:
                return documents[0]
        except ImportError:
            pass
        except Exception:
            pass
        
        return []
    
    def create_knowledge_base(self, texts, collection_name="vigo_rag", persist_dir="./vigo_knowledge"):
        """Create a ChromaDB knowledge base from a list of texts.
        
        Returns the persist directory path for use with rag_ask/rag_chat.
        """
        try:
            import chromadb
            from chromadb.config import Settings
            
            os.makedirs(persist_dir, exist_ok=True)
            
            client = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=persist_dir,
                anonymized_telemetry=False,
            ))
            
            collection = client.get_or_create_collection(name=collection_name)
            
            # Add texts with auto-generated IDs
            ids = [f"chunk_{i}" for i in range(len(texts))]
            metadatas = [{"source": "vigo", "index": i} for i in range(len(texts))]
            
            collection.add(
                documents=[str(t) for t in texts],
                ids=ids,
                metadatas=metadatas,
            )
            
            client.persist()
            return persist_dir
        except ImportError:
            raise ViGoError("ChromaDB not installed. Run: pip install chromadb")
        except Exception as e:
            raise ViGoError(f"Failed to create knowledge base: {e}")
    
    def add_to_knowledge_base(self, texts, persist_dir="./vigo_knowledge", collection_name="vigo_rag"):
        """Add more texts to an existing ChromaDB knowledge base."""
        try:
            import chromadb
            from chromadb.config import Settings
            
            client = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=persist_dir,
                anonymized_telemetry=False,
            ))
            
            collection = client.get_or_create_collection(name=collection_name)
            existing_count = collection.count()
            
            ids = [f"chunk_{existing_count + i}" for i in range(len(texts))]
            metadatas = [{"source": "vigo", "index": existing_count + i} for i in range(len(texts))]
            
            collection.add(
                documents=[str(t) for t in texts],
                ids=ids,
                metadatas=metadatas,
            )
            
            client.persist()
            return len(texts)
        except ImportError:
            raise ViGoError("ChromaDB not installed. Run: pip install chromadb")
        except Exception as e:
            raise ViGoError(f"Failed to add to knowledge base: {e}")

    def describe_image(self, image_path, model=None, host=None):
        import base64
        m = model or "llava"
        h = host or _env("OLLAMA_HOST", "http://localhost:11434")
        try:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            return f"Image read error: {e}"
        url = f"{h}/api/generate"
        data = json.dumps({"model": m, "prompt": "Describe this image in detail.", "images": [img_b64], "stream": False}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result.get("response", "No description generated.")
        except Exception as e:
            return f"Multimodal error: {e}. Make sure {m} model is loaded in Ollama."
        
    def vision(self, image_path, prompt, model=None, host=None, provider=None):
        """Analyze an image with a custom prompt using a vision-capable model.
        
        For cloud providers (OpenAI, DeepSeek, etc.), sends the image as base64
        in an OpenAI-compatible vision request.
        For Ollama, uses the local API with the specified vision model.
        """
        import base64
        
        # Read and encode image
        try:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            return f"Image read error: {e}"
        
        p = self._provider(provider)
        
        # Try Ollama first (most common for vision)
        if p == "ollama" or provider == "ollama":
            m = model or "llava"
            h = host or _env("OLLAMA_HOST", "http://localhost:11434")
            url = f"{h}/api/generate"
            data = json.dumps({
                "model": m,
                "prompt": str(prompt),
                "images": [img_b64],
                "stream": False,
            }).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    result = json.loads(resp.read().decode('utf-8'))
                    return result.get("response", "No response generated.")
            except Exception as e:
                return f"Vision error: {e}. Make sure {m} model is loaded in Ollama."
        
        # Cloud provider: OpenAI-compatible vision API
        config, _ = get_provider_config(p, self.base_url)
        m = model or "gpt-4o"
        
        url = config.get("url", "").replace("/chat/completions", "/chat/completions")
        headers = {"Content-Type": "application/json"}
        if config.get("auth_header") and self.api_key:
            headers[config["auth_header"]] = config.get("auth_prefix", "Bearer ") + self.api_key
        if config.get("api_version"):
            headers["anthropic-version"] = config["api_version"]
        
        body = {
            "model": m,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": str(prompt)},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                ]
            }],
            "max_tokens": 2000,
        }
        
        data = json.dumps(body).encode('utf-8')
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                req = urllib.request.Request(url, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=120) as resp:
                    result = json.loads(resp.read().decode('utf-8'))
                    choices = result.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "")
                    return "No response content"
            except urllib.error.HTTPError as e:
                if 400 <= e.code < 500:
                    error_body = e.read().decode('utf-8', errors='ignore') if e.fp else str(e)
                    raise ViGoError(f"Vision API error ({e.code}): {error_body[:500]}")
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
            except (urllib.error.URLError, ConnectionResetError, TimeoutError) as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
            except Exception as e:
                raise ViGoError(f"Vision error: {e}")
        raise ViGoError(f"Vision request failed after {self.max_retries+1} attempts: {last_error}")
    
    def list_vision_models(self):
        """Return a list of known vision-capable models."""
        return [
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo",  # OpenAI
            "claude-3-5-sonnet-20241022", "claude-3-opus-20240229",  # Anthropic
            "gemini-2.0-flash", "gemini-1.5-pro",  # Google
            "llava", "llava:13b", "bakllava", "llava-llama3",  # Ollama
        ]

    # ═══════════════════════════════════════════════
    #  Function Calling / Tool Use
    # ═══════════════════════════════════════════════

    def _build_tools_schema(self, tools):
        schema = []
        for name, info in tools.items():
            if callable(info) or isinstance(info, BuiltinFunction):
                schema.append({"type": "function", "function": {
                    "name": name,
                    "description": getattr(info, '__doc__', '') or f"Call the {name} function",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                }})
            elif isinstance(info, dict):
                schema.append({"type": "function", "function": {
                    "name": name,
                    "description": info.get("description", info.get("desc", "")),
                    "parameters": info.get("parameters", {"type": "object", "properties": {}, "required": []}),
                }})
        return schema

    def ask_with_tools(self, prompt, tools, model=None, temp=None, max_tokens=None, provider=None):
        clean_prompt, ok = self._apply_guardrails(prompt, "input")
        if not ok:
            return clean_prompt
        tools_schema = self._build_tools_schema(tools)
        if not tools_schema:
            return self.ask(prompt, model, temp, max_tokens, provider)
        m = self._model(model)
        p = self._provider(provider)
        config, _ = get_provider_config(p, self.base_url)
        url = config["url"]
        if self.base_url:
            url = self.base_url if any(x in self.base_url for x in ["/v1/chat/completions", "/v1/messages", "/v2/chat"]) else self.base_url.rstrip("/") + "/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if config.get("auth_header") and self.api_key:
            headers[config["auth_header"]] = config.get("auth_prefix", "Bearer ") + self.api_key
        if config.get("api_version"):
            headers["anthropic-version"] = config["api_version"]
        body = {"model": m, "messages": [{"role": "user", "content": str(clean_prompt)}],
            "temperature": temp if temp is not None else self.default_temp,
            "max_tokens": max_tokens or self.default_max_tokens,
            "tools": tools_schema, "tool_choice": "auto"}
        data = json.dumps(body).encode('utf-8')
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                req = urllib.request.Request(url, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=120) as resp:
                    response_data = json.loads(resp.read().decode('utf-8'))
                break
            except urllib.error.HTTPError as e:
                if 400 <= e.code < 500:
                    raise ViGoError(f"API error ({e.code}): {e.read().decode('utf-8', errors='ignore')[:500]}")
                last_error = e
                if attempt < self.max_retries: time.sleep(self.retry_delay * (attempt + 1))
            except (urllib.error.URLError, ConnectionResetError, TimeoutError) as e:
                last_error = e
                if attempt < self.max_retries: time.sleep(self.retry_delay * (attempt + 1))
            except Exception as e:
                raise ViGoError(f"Unexpected error: {e}")
        else:
            raise ViGoError(f"API error after {self.max_retries+1} attempts")
        tool_calls = self._extract_tool_calls(response_data, config.get("message_format", "openai"))
        if tool_calls:
            result = {"type": "tool_call", "calls": []}
            for tc in tool_calls:
                try:
                    args = json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]
                except json.JSONDecodeError:
                    args = {}
                self._pending_tool_calls[tc["id"]] = {"name": tc["name"], "arguments": args, "tools": tools}
                result["calls"].append({"id": tc["id"], "name": tc["name"], "arguments": args})
            return result
        choices = response_data.get("choices", [])
        text = choices[0].get("message", {}).get("content", "") if choices else ""
        if not text:
            content = response_data.get("content", [])
            text = "".join([c.get("text", "") for c in content]) if isinstance(content, list) else str(content)
        self.total_tokens += response_data.get("usage", {}).get("total_tokens", 0)
        self.call_count += 1
        return text

    def _extract_tool_calls(self, response_data, message_format):
        if message_format == "openai":
            msg = response_data.get("choices", [{}])[0].get("message", {})
            tool_calls = msg.get("tool_calls", [])
            return [{"id": tc.get("id", f"call_{i}"), "name": tc.get("function", {}).get("name", ""),
                     "arguments": tc.get("function", {}).get("arguments", "{}")} for i, tc in enumerate(tool_calls)]
        elif message_format == "claude":
            return [{"id": b.get("id", ""), "name": b.get("name", ""),
                     "arguments": json.dumps(b.get("input", {}))} for b in response_data.get("content", []) if b.get("type") == "tool_use"]
        return []

    def chat_with_tools(self, messages, tools, model=None, temp=None, max_tokens=None, provider=None):
        tools_schema = self._build_tools_schema(tools)
        if not tools_schema:
            return self.chat(messages, model, temp, max_tokens, provider)
        m = self._model(model)
        p = self._provider(provider)
        clean_messages = []
        for msg in messages:
            if isinstance(msg, dict): clean_messages.append(msg)
            elif isinstance(msg, (list, tuple)) and len(msg) >= 2: clean_messages.append({"role": str(msg[0]), "content": str(msg[1])})
        config, _ = get_provider_config(p, self.base_url)
        url = config["url"]
        if self.base_url:
            url = self.base_url if any(x in self.base_url for x in ["/v1/chat/completions", "/v1/messages", "/v2/chat"]) else self.base_url.rstrip("/") + "/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if config.get("auth_header") and self.api_key: headers[config["auth_header"]] = config.get("auth_prefix", "Bearer ") + self.api_key
        if config.get("api_version"): headers["anthropic-version"] = config["api_version"]
        body = {"model": m, "messages": clean_messages,
            "temperature": temp if temp is not None else self.default_temp,
            "max_tokens": max_tokens or self.default_max_tokens,
            "tools": tools_schema, "tool_choice": "auto"}
        data = json.dumps(body).encode('utf-8')
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                req = urllib.request.Request(url, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=120) as resp:
                    response_data = json.loads(resp.read().decode('utf-8'))
                break
            except urllib.error.HTTPError as e:
                if 400 <= e.code < 500: raise ViGoError(f"API error ({e.code}): {e.read().decode('utf-8', errors='ignore')[:500]}")
                last_error = e
                if attempt < self.max_retries: time.sleep(self.retry_delay * (attempt + 1))
            except (urllib.error.URLError, ConnectionResetError, TimeoutError) as e:
                last_error = e
                if attempt < self.max_retries: time.sleep(self.retry_delay * (attempt + 1))
            except Exception as e: raise ViGoError(f"Unexpected error: {e}")
        else:
            raise ViGoError(f"API error after {self.max_retries+1} attempts")
        tool_calls = self._extract_tool_calls(response_data, config.get("message_format", "openai"))
        if tool_calls:
            result = {"type": "tool_call", "calls": []}
            for tc in tool_calls:
                try: args = json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]
                except json.JSONDecodeError: args = {}
                self._pending_tool_calls[tc["id"]] = {"name": tc["name"], "arguments": args, "tools": tools}
                result["calls"].append({"id": tc["id"], "name": tc["name"], "arguments": args})
            return result
        choices = response_data.get("choices", [])
        text = choices[0].get("message", {}).get("content", "") if choices else ""
        if not text:
            content = response_data.get("content", [])
            text = "".join([c.get("text", "") for c in content]) if isinstance(content, list) else str(content)
        self.total_tokens += response_data.get("usage", {}).get("total_tokens", 0)
        self.call_count += 1
        return text

    def execute_tool_call(self, call_id):
        if call_id not in self._pending_tool_calls:
            return {"error": f"Unknown call_id: {call_id}"}
        info = self._pending_tool_calls.pop(call_id)
        name, args, tools = info["name"], info["arguments"], info["tools"]
        if name not in tools:
            return {"call_id": call_id, "name": name, "result": f"Tool '{name}' not found"}
        func = tools[name]
        try:
            result = func(**args) if isinstance(args, dict) else func(args)
        except Exception as e:
            result = f"Tool error: {e}"
        return {"call_id": call_id, "name": name, "result": result}

    def resolve_tool_call(self, call_id, result):
        if call_id in self._pending_tool_calls:
            info = self._pending_tool_calls.pop(call_id)
            return {"call_id": call_id, "name": info["name"], "result": result}
        return {"error": f"Unknown call_id: {call_id}"}
    
    # ═══════════════════════════════════════════════
    #  AI Function Registration (standardized protocol)
    # ═══════════════════════════════════════════════

    def __init_registry(self):
        if not hasattr(self, '_function_registry'):
            self._function_registry = {}

    def register_function(self, name, func, description="", parameters=None):
        """Register a function for AI to call. Returns the function name on success."""
        self.__init_registry()
        self._function_registry[name] = {
            "func": func,
            "description": description,
            "parameters": parameters or {"type": "object", "properties": {}, "required": []},
        }
        return name

    def unregister_function(self, name):
        """Remove a registered function."""
        self.__init_registry()
        if name in self._function_registry:
            del self._function_registry[name]
            return True
        return False

    def list_functions(self):
        """List all registered AI-callable functions."""
        self.__init_registry()
        return {name: {"description": info["description"]} for name, info in self._function_registry.items()}

    def _get_registry_tools(self):
        """Get registered functions in tools schema format."""
        self.__init_registry()
        tools = {}
        for name, info in self._function_registry.items():
            tools[name] = {
                "func": info["func"],
                "description": info["description"],
                "parameters": info["parameters"],
            }
        return tools

    def ask_with_functions(self, prompt, model=None, temp=None, max_tokens=None, provider=None):
        """Ask AI with all registered functions available."""
        tools = self._get_registry_tools()
        if not tools:
            return self.ask(prompt, model, temp, max_tokens, provider)
        return self.ask_with_tools(prompt, tools, model, temp, max_tokens, provider)

    def call_function(self, name, **kwargs):
        """Call a registered function directly."""
        self.__init_registry()
        if name not in self._function_registry:
            raise ViGoError(f"Function '{name}' not registered")
        func = self._function_registry[name]["func"]
        try:
            return func(**kwargs) if kwargs else func()
        except Exception as e:
            raise ViGoError(f"Function '{name}' error: {e}")
        
    def ask_json(self, prompt, schema, model=None, temp=None, provider=None):
        """Ask AI and get structured JSON response matching a schema.
        
        schema: a dict describing expected fields and types.
        Example: {"sentiment": "string (positive/negative/neutral)", "score": "number 0-1"}
        """
        import re
        
        schema_desc = "\n".join(f"- {k}: {v}" for k, v in schema.items())
        system_prompt = f"""You are a JSON API. Respond ONLY with a valid JSON object.
The JSON must have these fields:
{schema_desc}

Do not include any text outside the JSON object.
Do not wrap in markdown code blocks.
If you cannot determine a field, use null."""

        full_prompt = f"{prompt}\n\nReturn the JSON object with these fields: {', '.join(schema.keys())}."
        
        response = self.chat(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": full_prompt}],
            model=model, temp=temp or 0.0, max_tokens=2000, provider=provider
        )
        
        # Parse JSON from response
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Try parsing the whole response
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass
        
        return {"_raw": response, "_error": "Failed to parse JSON"}
    
    def batch_async(self, prompts, model=None, temp=None, max_tokens=None, provider=None,
                    max_concurrent=5, on_progress=None):
        """Process prompts in parallel with progress callback.
        
        on_progress(completed, total) is called after each completion.
        Returns list of results in original order.
        """
        import concurrent.futures
        import threading
        
        m = self._model(model)
        p = self._provider(provider)
        t = temp if temp is not None else self.default_temp
        mt = max_tokens or self.default_max_tokens
        
        results = [None] * len(prompts)
        completed = [0]
        lock = threading.Lock()
        
        def process_one(idx, prompt):
            try:
                res = self.ask(prompt, m, t, mt, p)
            except Exception as e:
                res = f"Error: {e}"
            with lock:
                results[idx] = res
                completed[0] += 1
                if on_progress:
                    try:
                        on_progress(completed[0], len(prompts))
                    except Exception:
                        pass
        
        if p == "ollama":
            for i, prompt in enumerate(prompts):
                process_one(i, prompt)
            return results
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = [executor.submit(process_one, i, prompt) for i, prompt in enumerate(prompts)]
            concurrent.futures.wait(futures)
        
        return results
    
    def fine_tune(self, training_data, base_model=None, provider=None, 
                  epochs=3, learning_rate=0.0001, validation_split=0.1):
        """Initiate a fine-tuning job. Returns a job_id for tracking.
        
        training_data: list of {"prompt": "...", "completion": "..."} dicts.
        Currently supports OpenAI fine-tuning API.
        """
        p = self._provider(provider)
        m = base_model or self.default_model or "gpt-3.5-turbo"
        
        if p in ("openai", "deepseek"):
            config, _ = get_provider_config(p, self.base_url)
            url = config.get("url", "").replace("/chat/completions", "/fine-tunes")
            if not url.endswith("/fine-tunes"):
                url = "https://api.openai.com/v1/fine-tunes"
            
            headers = {"Content-Type": "application/json"}
            if config.get("auth_header") and self.api_key:
                headers[config["auth_header"]] = config.get("auth_prefix", "Bearer ") + self.api_key
            
            # Format training data as JSONL
            import tempfile
            tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8')
            for item in training_data:
                tmp.write(json.dumps({"prompt": str(item.get("prompt", "")), 
                                       "completion": str(item.get("completion", ""))}) + "\n")
            tmp.close()
            
            # Upload file
            with open(tmp.name, 'rb') as f:
                upload_req = urllib.request.Request(
                    "https://api.openai.com/v1/files",
                    data=f.read(),
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    method='POST'
                )
                # This is simplified; full implementation needs multipart upload
            
            os.unlink(tmp.name)
            return {"job_id": "ft_pending", "status": "not_implemented", 
                    "note": "Full fine-tuning requires multipart upload. Use OpenAI CLI for now."}
        
        return {"job_id": None, "status": "unsupported", 
                "note": f"Fine-tuning not supported for provider '{p}'"}

    def fine_tune_status(self, job_id, provider=None):
        """Check the status of a fine-tuning job."""
        return {"job_id": job_id, "status": "unknown", 
                "note": "Fine-tune tracking not yet implemented"}
    
    def evaluate(self, test_cases, model=None, provider=None, 
                 metrics=None, temp=0.0):
        """Evaluate AI performance on test cases.
        
        test_cases: list of {"input": "...", "expected": "..."} dicts.
        metrics: list of metric names. Default: ["exact_match", "contains", "token_count", "response_time"].
        
        Returns dict with per-case results and aggregate statistics.
        """
        if metrics is None:
            metrics = ["exact_match", "contains", "token_count", "response_time"]
        
        m = self._model(model)
        p = self._provider(provider)
        
        results = []
        total_tokens = 0
        total_time = 0.0
        passed = 0
        
        for i, case in enumerate(test_cases):
            prompt = str(case.get("input", case.get("prompt", "")))
            expected = str(case.get("expected", case.get("completion", "")))
            
            start = time.time()
            response = self.ask(prompt, m, temp, provider=p)
            elapsed = time.time() - start
            total_time += elapsed
            
            tokens = self.count_tokens(response, m)
            total_tokens += tokens
            
            case_result = {"index": i, "input": prompt[:200], "expected": expected[:200],
                          "response": response[:500], "time_ms": round(elapsed * 1000, 1),
                          "tokens": tokens}
            
            if "exact_match" in metrics:
                case_result["exact_match"] = response.strip() == expected.strip()
            if "contains" in metrics:
                case_result["contains"] = expected.strip().lower() in response.strip().lower()
            
            if case_result.get("exact_match") or case_result.get("contains"):
                passed += 1
            
            results.append(case_result)
        
        total_cases = len(test_cases)
        return {
            "model": m,
            "provider": p,
            "total_cases": total_cases,
            "passed": passed,
            "accuracy": round(passed / max(total_cases, 1), 4),
            "total_tokens": total_tokens,
            "avg_tokens": round(total_tokens / max(total_cases, 1), 1),
            "total_time_ms": round(total_time * 1000, 1),
            "avg_time_ms": round((total_time / max(total_cases, 1)) * 1000, 1),
            "results": results,
        }
        
    # ═══════════════════════════════════════════════
    #  Cross-Modal Understanding
    # ═══════════════════════════════════════════════

    def _extract_video_frames(self, video_path, max_frames=5, interval=None):
        """Extract key frames from a video file using ffmpeg.
        Returns a list of base64-encoded JPEG strings.
        """
        import subprocess
        import tempfile
        import base64 as b64

        # Get video duration
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path],
                capture_output=True, text=True, timeout=30
            )
            info = json.loads(result.stdout)
            duration = float(info.get("format", {}).get("duration", 30))
        except Exception:
            duration = 30

        if interval is None:
            interval = max(1, duration / (max_frames + 1))

        frames = []
        tmp_dir = tempfile.mkdtemp(prefix="vigo_frames_")

        for i in range(max_frames):
            timestamp = min(interval * (i + 1), duration - 0.1)
            if timestamp <= 0:
                break
            out_path = os.path.join(tmp_dir, f"frame_{i:03d}.jpg")
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-ss", str(timestamp), "-i", video_path,
                     "-vframes", "1", "-q:v", "2", out_path],
                    capture_output=True, timeout=30
                )
                if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                    with open(out_path, "rb") as f:
                        frames.append(b64.b64encode(f.read()).decode('utf-8'))
            except Exception:
                pass

        # Cleanup
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)

        return frames

    def ask(self, prompt, model=None, temp=None, max_tokens=None, provider=None,
            images=None, audio=None, video=None, stream=False):
        """Unified multimodal ask. Supports text + images + audio + video.
        
        images: list of image file paths.
        audio: path to an audio file.
        video: path to a video file (extracts key frames automatically).
        """
        has_media = images or audio or video

        if not has_media:
            # Pure text — use original path
            clean_prompt, ok = self._apply_guardrails(prompt, "input")
            if not ok:
                return clean_prompt
            m = self._model(model)
            p = self._provider(provider)
            if self.cache_enabled and not stream:
                key = self._cache_key(clean_prompt, m, p)
                if key in self.cache:
                    return self.cache[key]
            response = make_request(self, [{"role": "user", "content": str(clean_prompt)}],
                m, temp if temp is not None else self.default_temp,
                max_tokens or self.default_max_tokens, stream=stream, provider=p)
            if stream and not response:
                response = make_request(self, [{"role": "user", "content": str(clean_prompt)}],
                    m, temp if temp is not None else self.default_temp,
                    max_tokens or self.default_max_tokens, stream=False, provider=p)
            clean_response, ok = self._apply_guardrails(response, "output")
            if self.cache_enabled and not stream:
                key = self._cache_key(clean_prompt, m, p)
                self.cache[key] = clean_response
            return clean_response

        # Multimodal path
        return self.ask_multimodal(
            prompt=prompt,
            images=images,
            audio=audio,
            video=video,
            model=model,
            temp=temp,
            max_tokens=max_tokens,
            provider=provider,
        )

    def ask_multimodal(self, prompt, images=None, audio=None, video=None,
                       model=None, temp=None, max_tokens=None, provider=None):
        """Cross-modal ask with text + images + audio + video.
        
        images: list of image file paths.
        audio: path to audio file (WAV/MP3).
        video: path to video file (extracts key frames automatically).
        """
        import base64 as b64

        m = model or "gpt-4o"
        p = self._provider(provider)
        t = temp if temp is not None else self.default_temp
        mt = max_tokens or self.default_max_tokens

        content = [{"type": "text", "text": str(prompt)}]

        # ── Images ──
        if images:
            for img_path in images:
                try:
                    with open(img_path, "rb") as f:
                        img_b64 = b64.b64encode(f.read()).decode('utf-8')
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                    })
                except Exception as e:
                    content.append({"type": "text", "text": f"[Image error: {img_path} - {e}]"})

        # ── Audio ──
        if audio:
            try:
                with open(audio, "rb") as f:
                    audio_b64 = b64.b64encode(f.read()).decode('utf-8')
                fmt = audio.split(".")[-1].lower() if "." in audio else "wav"
                content.append({
                    "type": "input_audio",
                    "input_audio": {"data": audio_b64, "format": fmt}
                })
            except Exception as e:
                content.append({"type": "text", "text": f"[Audio error: {audio} - {e}]"})

        # ── Video → extracted frames as images ──
        if video:
            try:
                frames = self._extract_video_frames(video, max_frames=6)
                content.append({"type": "text", "text": f"[Video '{video}' — {len(frames)} key frames extracted]"})
                for i, frame_b64 in enumerate(frames):
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}"}
                    })
            except Exception as e:
                content.append({"type": "text", "text": f"[Video error: {video} - {e}]"})

        # ── Ollama fallback ──
        if p == "ollama":
            if images and len(images) == 1 and not audio and not video:
                return self.vision(images[0], prompt, model or "llava", provider=p)
            if video:
                frames = self._extract_video_frames(video, max_frames=4)
                if frames:
                    results = []
                    for frame_b64 in frames:
                        results.append(self.vision(None, prompt, model or "llava",
                                           provider=p, _frame_b64=frame_b64))
                    return "\n\n".join(f"[Frame {i+1}]: {r}" for i, r in enumerate(results))
            return self.ask(prompt, m, t, mt, p)

        # ── Cloud provider ──
        config, _ = get_provider_config(p, self.base_url)
        url = config.get("url", "")
        headers = {"Content-Type": "application/json"}
        if config.get("auth_header") and self.api_key:
            headers[config["auth_header"]] = config.get("auth_prefix", "Bearer ") + self.api_key
        if config.get("api_version"):
            headers["anthropic-version"] = config["api_version"]

        body = {
            "model": m,
            "messages": [{"role": "user", "content": content}],
            "temperature": t,
            "max_tokens": mt,
        }

        data = json.dumps(body).encode('utf-8')
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                req = urllib.request.Request(url, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=300) as resp:
                    result = json.loads(resp.read().decode('utf-8'))
                break
            except urllib.error.HTTPError as e:
                if 400 <= e.code < 500:
                    error_body = e.read().decode('utf-8', errors='ignore') if e.fp else str(e)
                    raise ViGoError(f"Multimodal API error ({e.code}): {error_body[:500]}")
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
            except (urllib.error.URLError, ConnectionResetError, TimeoutError) as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
            except Exception as e:
                raise ViGoError(f"Multimodal request error: {e}")
        else:
            raise ViGoError(f"Multimodal request failed after {self.max_retries+1} attempts: {last_error}")

        choices = result.get("choices", [])
        if choices:
            response_text = choices[0].get("message", {}).get("content", "")
        else:
            response_text = str(result)

        self.total_tokens += result.get("usage", {}).get("total_tokens", 0)
        self.call_count += 1
        return response_text

    # ═══════════════════════════════════════════════
    #  AI Chart Generation
    # ═══════════════════════════════════════════════

    def generate_chart(self, prompt, data, chart_type="auto", output_path="chart.png",
                       model=None, provider=None):
        """Ask AI to generate a chart from data and save it as an image.
        
        prompt: description of what the chart should show.
        data: a dict or list of data values.
        chart_type: "bar", "line", "pie", "scatter", or "auto".
        output_path: file path for the generated chart image.
        """
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
        except ImportError:
            raise ViGoError("matplotlib not installed. Run: pip install matplotlib")

        # Ask AI to decide chart type and parameters
        m = model or self.default_model or "gpt-4o"

        if chart_type == "auto":
            decision_prompt = f"""Given this data and prompt, choose a chart type.
Data: {json.dumps(data)[:500]}
Prompt: {prompt}

Respond with ONLY a JSON object:
{{"chart_type": "bar|line|pie|scatter", "title": "chart title", "xlabel": "x label", "ylabel": "y label"}}"""
            decision = self.ask(decision_prompt, m, temp=0.0, max_tokens=200, provider=provider)
            try:
                import re
                json_match = re.search(r'\{[^{}]*\}', decision, re.DOTALL)
                if json_match:
                    chart_config = json.loads(json_match.group())
                    chart_type = chart_config.get("chart_type", "bar")
                    title = chart_config.get("title", prompt[:50])
                    xlabel = chart_config.get("xlabel", "X")
                    ylabel = chart_config.get("ylabel", "Y")
            except Exception:
                chart_type = "bar"
                title = prompt[:50]
                xlabel = "X"
                ylabel = "Y"
        else:
            title = prompt[:50]
            xlabel = "X"
            ylabel = "Y"

        # Generate chart with matplotlib
        plt.figure(figsize=(10, 6))

        if chart_type == "bar":
            if isinstance(data, dict):
                plt.bar(list(data.keys()), list(data.values()), color='steelblue', edgecolor='white')
            elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                for d in data:
                    plt.bar(list(d.keys()), list(d.values()), alpha=0.7)
            else:
                plt.bar(range(len(data)) if isinstance(data, list) else [0], 
                       data if isinstance(data, list) else [data])

        elif chart_type == "line":
            if isinstance(data, dict):
                plt.plot(list(data.keys()), list(data.values()), marker='o', linewidth=2)
            elif isinstance(data, list):
                plt.plot(data, marker='o', linewidth=2)
            else:
                plt.plot([data], marker='o')

        elif chart_type == "pie":
            if isinstance(data, dict):
                plt.pie(list(data.values()), labels=list(data.keys()), autopct='%1.1f%%')
            elif isinstance(data, list):
                plt.pie(data)

        elif chart_type == "scatter":
            if isinstance(data, dict):
                x = list(data.keys())
                y = list(data.values())
                plt.scatter(x, y, alpha=0.7, c='coral', edgecolors='black')
            elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], (list, tuple)):
                for series in data:
                    if len(series) >= 2:
                        plt.scatter(series[0], series[1], alpha=0.7)
            else:
                plt.scatter(range(len(data)), data, alpha=0.7)

        plt.title(title, fontsize=14)
        if chart_type != "pie":
            plt.xlabel(xlabel)
            plt.ylabel(ylabel)
            plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_path, dpi=120)
        plt.close()

        return {"chart_type": chart_type, "output_path": output_path, "title": title}
        
    def stream(self, prompt, callback, model=None, temp=None, max_tokens=None, provider=None):
        """Stream AI response with callback(chunk_text) for each chunk.
        Returns a stream controller dict with pause/resume/cancel methods.
        """
        import threading
        
        m = self._model(model)
        p = self._provider(provider)
        
        controller = {"paused": False, "cancelled": False, "chunks": [], "lock": threading.Lock()}
        
        def pause():
            with controller["lock"]:
                controller["paused"] = True
        
        def resume():
            with controller["lock"]:
                controller["paused"] = False
        
        def cancel():
            with controller["lock"]:
                controller["cancelled"] = True
        
        controller["pause"] = pause
        controller["resume"] = resume
        controller["cancel"] = cancel
        
        def stream_thread():
            self.set_stream_callback(lambda chunk: None)
            response = self.ask(prompt, m, temp, max_tokens or self.default_max_tokens, p, stream=True)
            chunks = self.get_stream_chunks()
            for chunk in chunks:
                with controller["lock"]:
                    if controller["cancelled"]:
                        break
                    while controller["paused"] and not controller["cancelled"]:
                        time.sleep(0.05)
                    if controller["cancelled"]:
                        break
                    controller["chunks"].append(chunk)
                try:
                    callback(chunk)
                except Exception:
                    pass
        
        thread = threading.Thread(target=stream_thread, daemon=True)
        thread.start()
        controller["_thread"] = thread
        
        return controller

    def extend_conversation(self, conv):
        """Add conversation management extensions to an existing Conversation object."""
        # Add branch/rollback if not already present
        if not hasattr(conv, '_branches'):
            conv._branches = []  # Stack of message snapshots
            conv._original_messages = list(conv.messages)
        
        def branch(conv_self):
            """Save current state as a branch point."""
            conv_self._branches.append(list(conv_self.messages))
            return len(conv_self._branches)
        
        def rollback(conv_self, branch_id=None):
            """Roll back to a branch point. If branch_id is None, roll back to last branch."""
            if not conv_self._branches:
                return False
            if branch_id is None:
                conv_self.messages = conv_self._branches.pop()
            elif 0 <= branch_id < len(conv_self._branches):
                conv_self.messages = conv_self._branches[branch_id]
                conv_self._branches = conv_self._branches[:branch_id]
            return True
        
        def summarize(conv_self, model=None, max_length=200):
            """Generate a summary of the conversation."""
            if len(conv_self.messages) <= 2:
                return "Conversation too short to summarize."
            history = "\n".join(f"{m['role']}: {str(m['content'])[:300]}" 
                               for m in conv_self.messages[-20:])
            summary_prompt = f"Summarize this conversation in {max_length} chars:\n\n{history}"
            return self.ask(summary_prompt, model or self.default_model, temp=0.3, max_tokens=max_length)
        
        def compress(conv_self, keep_last=5):
            """Compress conversation: summarize old messages, keep recent ones."""
            if len(conv_self.messages) <= keep_last:
                return False
            old_messages = conv_self.messages[:-keep_last]
            recent = conv_self.messages[-keep_last:]
            
            history = "\n".join(f"{m['role']}: {str(m['content'])[:200]}" for m in old_messages)
            summary = self.ask(f"Summarize this conversation history concisely:\n\n{history}",
                              temp=0.3, max_tokens=300)
            
            compressed = []
            if conv_self.system_prompt:
                compressed.append({"role": "system", "content": conv_self.system_prompt})
            compressed.append({"role": "system", "content": f"Previous conversation summary: {summary}"})
            compressed.extend(recent)
            conv_self.messages = compressed
            return True
        
        # Attach methods to the conversation instance
        import types
        conv.branch = types.MethodType(branch, conv)
        conv.rollback = types.MethodType(rollback, conv)
        conv.summarize = types.MethodType(summarize, conv)
        conv.compress = types.MethodType(compress, conv)
        
        return conv


class AIAgent:
    def __init__(self, model=None, max_steps=None, verbose=False, provider=None):
        self.model = model or _env("VIGO_AI_MODEL", "llama3")
        self.max_steps = max_steps or int(_env("VIGO_AGENT_MAX_STEPS", "5"))
        self.verbose = verbose
        self.provider = provider or _env("VIGO_AI_PROVIDER", "ollama")
        self.tools = {}
        self.memory = []
        self.long_term_memory = []
        self.retry_count = int(_env("VIGO_AGENT_RETRIES", "2"))
        self._register_builtin_tools()

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
            req = urllib.request.Request(url, headers={"User-Agent": "ViGo/3.7"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                import re
                snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
                return "\n".join(re.sub(r'<[^>]+>', '', s).strip()[:300] for s in snippets[:5]) if snippets else "No results."
        except Exception as e:
            return f"Search error: {e}"

    def _run_code(self, code):
        import sys, io
        old_stdout, captured = sys.stdout, io.StringIO()
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
        if len(parts) != 2: return "Format: path ||| content"
        try:
            with open(parts[0].strip(), "w", encoding="utf-8") as f:
                f.write(parts[1].strip())
            return "Written."
        except Exception as e:
            return f"Write error: {e}"

    def _list_files(self, path):
        try: return "\n".join(os.listdir(path.strip() or ".")[:50])
        except Exception as e: return f"List error: {e}"

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

    def _call_tool(self, name, input_str):
        if name not in self.tools: return f"Tool '{name}' not found"
        for _ in range(self.retry_count + 1):
            try: return str(self.tools[name]["func"](input_str.strip()))
            except Exception: continue
        return "Tool error"

    def run(self, task):
        self.memory = []
        ai = AIClient()
        prompt = f"You are a helpful AI assistant with tools.\n\nTools:\n" + \
                 "\n".join(f"- {n}: {i['desc']}" for n, i in self.tools.items()) + \
                 "\n\nTOOL: name\nINPUT: value\n\nTOOLS: a,b\nINPUTS: x|||y\n\nFINAL: answer\n\nTask: {task}"
        for step in range(self.max_steps):
            response = ai.ollama(prompt, self.model) if self.provider == "ollama" else ai.ask(prompt, self.model, provider=self.provider)
            self.memory.append({"step": step+1, "response": response})
            if "TOOLS:" in response and "INPUTS:" in response:
                ts = response.split("TOOLS:")[1].split("\n")[0].strip()
                ins = response.split("INPUTS:")[1].split("\n")[0].strip()
                results = []
                for i, n in enumerate(t.strip() for t in ts.split(",")):
                    inp = ins.split("|||")[i].strip() if i < len(ins.split("|||")) else ""
                    results.append(f"{n}: {self._call_tool(n, inp)}")
                prompt = f"{prompt}\n\nResults:\n" + "\n".join(results) + "\n\nContinue."
                continue
            if "TOOL:" in response:
                tn = response.split("TOOL:")[1].split("\n")[0].strip()
                ti = response.split("INPUT:")[1].split("\n")[0].strip() if "INPUT:" in response else ""
                prompt = f"{prompt}\n\nTool result: {self._call_tool(tn, ti)}\n\nContinue."
                continue
            if "FINAL:" in response:
                return response.split("FINAL:")[1].strip()
        return "Max steps reached."


class Conversation:
    """Multi-turn conversation manager with automatic history tracking."""

    def __init__(self, system_prompt=None, model=None, provider=None, max_history=100):
        self.system_prompt = system_prompt
        self.model = model
        self.provider = provider
        self.max_history = max_history
        self.messages = []
        self._ai = AIClient()
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})

    def add_message(self, role, content):
        """Add a message to the conversation history."""
        self.messages.append({"role": role, "content": str(content)})
        if len(self.messages) > self.max_history + (1 if self.system_prompt else 0):
            # Remove oldest non-system messages to stay within limit
            start = 1 if self.system_prompt else 0
            self.messages = self.messages[:start] + self.messages[-(self.max_history):]

    def get_history(self):
        """Return a copy of the conversation history."""
        return list(self.messages)

    def clear(self):
        """Reset the conversation, keeping the system prompt if set."""
        self.messages = []
        if self.system_prompt:
            self.messages.append({"role": "system", "content": self.system_prompt})

    def set_system_prompt(self, prompt):
        """Replace the system prompt."""
        self.system_prompt = prompt
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0] = {"role": "system", "content": prompt}
        else:
            self.messages.insert(0, {"role": "system", "content": prompt})

    def to_dict(self):
        """Export conversation as a dict for serialization."""
        return {
            "system_prompt": self.system_prompt,
            "model": self.model,
            "provider": self.provider,
            "messages": self.messages,
        }

    @classmethod
    def from_dict(cls, data):
        """Restore a conversation from a dict."""
        conv = cls(
            system_prompt=data.get("system_prompt"),
            model=data.get("model"),
            provider=data.get("provider"),
        )
        conv.messages = data.get("messages", [])
        return conv

_ai = AIClient()


def register(env):
    env.define('ai_ask', BuiltinFunction(lambda p, m=None, t=None, mt=None, prv=None, stream=False: _ai.ask(p, m, t, mt, prv, stream), 'ai_ask'))
    env.define('ai_chat', BuiltinFunction(lambda msgs, m=None, t=None, mt=None, prv=None: _ai.chat(msgs, m, t, mt, prv), 'ai_chat'))
    env.define('ai_on_chunk', BuiltinFunction(lambda callback: _ai.set_stream_callback(callback) and True, 'ai_on_chunk'))
    env.define('ai_stream_chunks', BuiltinFunction(lambda: _ai.get_stream_chunks(), 'ai_stream_chunks'))
    env.define('ai_ollama', BuiltinFunction(lambda p, m=None, h=None: _ai.ollama(p, m, h), 'ai_ollama'))
    env.define('ai_set_provider', BuiltinFunction(lambda p: _ai.set_provider(p) and True, 'ai_set_provider'))
    env.define('ai_list_providers', BuiltinFunction(lambda: _ai.list_providers(), 'ai_list_providers'))
    env.define('ai_list_models', BuiltinFunction(lambda p=None: _ai.list_models(p), 'ai_list_models'))
    env.define('ai_chain', BuiltinFunction(lambda steps, dm=None, p=None: _ai.chain(steps, dm, p), 'ai_chain'))
    env.define('ai_compare', BuiltinFunction(lambda prompt, models, p=None: _ai.compare(prompt, models, p), 'ai_compare'))
    env.define('ai_debate', BuiltinFunction(lambda q, models, r=2, p=None: _ai.debate(q, models, r, p), 'ai_debate'))
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
    env.define('ai_describe_image', BuiltinFunction(lambda path, m=None, h=None: _ai.describe_image(path, m, h), 'ai_describe_image'))
    env.define('ai_embed', BuiltinFunction(lambda text, m=None, p=None: _ai.embed(text, m, p), 'ai_embed'))
    env.define('ai_embed_batch', BuiltinFunction(lambda texts, m=None, p=None: _ai.embed_batch(texts, m, p), 'ai_embed_batch'))
    env.define('ai_ask_with_tools', BuiltinFunction(lambda prompt, tools, m=None, t=None, mt=None, p=None: _ai.ask_with_tools(prompt, tools, m, t, mt, p), 'ai_ask_with_tools'))
    env.define('ai_chat_with_tools', BuiltinFunction(lambda msgs, tools, m=None, t=None, mt=None, p=None: _ai.chat_with_tools(msgs, tools, m, t, mt, p), 'ai_chat_with_tools'))
    env.define('ai_execute_tool_call', BuiltinFunction(lambda call_id: _ai.execute_tool_call(call_id), 'ai_execute_tool_call'))
    env.define('ai_resolve_tool_call', BuiltinFunction(lambda call_id, result: _ai.resolve_tool_call(call_id, result), 'ai_resolve_tool_call'))
    env.define('ai_batch', BuiltinFunction(lambda prompts, m=None, t=None, mt=None, p=None: _ai.batch(prompts, m, t, mt, p),'ai_batch'))
    env.define('ai_batch_with_tools', BuiltinFunction(lambda prompts, tools, m=None, t=None, mt=None, p=None: _ai.batch_with_tools(prompts, tools, m, t, mt, p),'ai_batch_with_tools'))
    env.define('ai_count_tokens', BuiltinFunction(lambda text, m=None: _ai.count_tokens(text, m), 'ai_count_tokens'))
    env.define('ai_count_tokens_batch', BuiltinFunction(lambda texts, m=None: _ai.count_tokens_batch(texts, m), 'ai_count_tokens_batch'))
    env.define('ai_token_cost', BuiltinFunction(lambda tokens, m=None: _ai.token_cost_estimate(tokens, m), 'ai_token_cost'))
    env.define('ai_list_models_live', BuiltinFunction(lambda p=None: _ai.list_models_live(p), 'ai_list_models_live'))
    env.define('ai_model_info', BuiltinFunction(lambda model, p=None: _ai.model_info(model, p), 'ai_model_info'))
    env.define('ai_enable_semantic_cache', BuiltinFunction(lambda e=True, t=0.95: _ai.enable_semantic_cache(e, t), 'ai_enable_semantic_cache'))
    env.define('ai_clear_semantic_cache', BuiltinFunction(lambda: _ai.clear_semantic_cache(), 'ai_clear_semantic_cache'))
    env.define('ai_get_semantic_cache_stats', BuiltinFunction(lambda: _ai.get_semantic_cache_stats(), 'ai_get_semantic_cache_stats'))
    env.define('ai_deduplicate_prompts', BuiltinFunction(lambda prompts, m=None, t=0.95: _ai.deduplicate_prompts(prompts, m, t), 'ai_deduplicate_prompts'))
    env.define('ai_rag_ask', BuiltinFunction(lambda prompt, kb, m=None, t=None, mt=None, p=None, k=3: _ai.rag_ask(prompt, kb, m, t, mt, p, k),'ai_rag_ask'))
    env.define('ai_rag_chat', BuiltinFunction(lambda msgs, kb, m=None, t=None, mt=None, p=None, k=3: _ai.rag_chat(msgs, kb, m, t, mt, p, k),'ai_rag_chat'))
    env.define('ai_create_knowledge_base', BuiltinFunction(lambda texts, name="vigo_rag", dir="./vigo_knowledge": _ai.create_knowledge_base(texts, name, dir),'ai_create_knowledge_base'))
    env.define('ai_add_to_knowledge_base', BuiltinFunction(lambda texts, dir="./vigo_knowledge", name="vigo_rag": _ai.add_to_knowledge_base(texts, dir, name),'ai_add_to_knowledge_base'))
    env.define('ai_web_search', BuiltinFunction(lambda query, n=5, p=None: _ai.web_search(query, n, p), 'ai_web_search'))
    env.define('ai_web_search_ask', BuiltinFunction(lambda question, m=None, t=None, mt=None, p=None, n=3: _ai.web_search_ask(question, m, t, mt, p, n),'ai_web_search_ask'))
    env.define('ai_news_search', BuiltinFunction(lambda query, n=5: _ai.news_search(query, n), 'ai_news_search'))
    env.define('ai_register_function', BuiltinFunction(lambda name, func, desc="", params=None: _ai.register_function(name, func, desc, params),'ai_register_function'))
    env.define('ai_unregister_function', BuiltinFunction(lambda name: _ai.unregister_function(name), 'ai_unregister_function'))
    env.define('ai_list_functions', BuiltinFunction(lambda: _ai.list_functions(), 'ai_list_functions'))
    env.define('ai_call_function', BuiltinFunction(lambda name, **kw: _ai.call_function(name, **kw), 'ai_call_function'))
    env.define('ai_ask_json', BuiltinFunction(lambda prompt, schema, m=None, t=None, p=None: _ai.ask_json(prompt, schema, m, t, p),'ai_ask_json'))
    env.define('ai_batch_async', BuiltinFunction(lambda prompts, m=None, t=None, mt=None, p=None, mc=5, cb=None: _ai.batch_async(prompts, m, t, mt, p, mc, cb),'ai_batch_async'))
    env.define('ai_fine_tune', BuiltinFunction(lambda data, base_m=None, p=None, ep=3, lr=0.0001: _ai.fine_tune(data, base_m, p, ep, lr),'ai_fine_tune'))
    env.define('ai_fine_tune_status', BuiltinFunction(lambda job_id, p=None: _ai.fine_tune_status(job_id, p), 'ai_fine_tune_status'))
    env.define('ai_evaluate', BuiltinFunction(lambda cases, m=None, p=None, metrics=None: _ai.evaluate(cases, m, p, metrics),'ai_evaluate'))
    env.define('ai_ask_multimodal', BuiltinFunction(lambda prompt, images=None, audio=None, m=None, p=None: _ai.ask_multimodal(prompt, images, audio, m, p),'ai_ask_multimodal'))
    env.define('ai_stream', BuiltinFunction(lambda prompt, cb, m=None, t=None, mt=None, p=None: _ai.stream(prompt, cb, m, t, mt, p),'ai_stream'))
    env.define('ai_extend_conversation', BuiltinFunction(lambda conv: _ai.extend_conversation(conv), 'ai_extend_conversation'))
    env.define('ai_generate_chart', BuiltinFunction(lambda prompt, data, ct="auto", out="chart.png", m=None, p=None: _ai.generate_chart(prompt, data, ct, out, m, p),'ai_generate_chart'))

    def _create_agent(m=None, ms=None, v=False, p=None): return AIAgent(m, ms, v, p)
    def _agent_add_tool(agent, name, func, desc):
        if isinstance(agent, AIAgent): agent.add_tool(name, func, desc); return agent
    def _agent_run(agent, task): return agent.run(task) if isinstance(agent, AIAgent) else "Invalid agent"
    env.define('ai_agent', BuiltinFunction(_create_agent, 'ai_agent'))
    env.define('ai_agent_add_tool', BuiltinFunction(_agent_add_tool, 'ai_agent_add_tool'))
    env.define('ai_agent_run', BuiltinFunction(_agent_run, 'ai_agent_run'))
    def _create_conversation(system_prompt=None, model=None, provider=None, max_history=100):
        return Conversation(system_prompt, model, provider, max_history)
    env.define('ai_conversation', BuiltinFunction(_create_conversation, 'ai_conversation'))
    env.define('ai_extract', BuiltinFunction(
    lambda prompt, text, fields, m=None, t=None, p=None: _ai.extract(prompt, text, fields, m, t, p),
    'ai_extract'))
    env.define('ai_vision', BuiltinFunction(
    lambda path, prompt, m=None, h=None, p=None: _ai.vision(path, prompt, m, h, p),
    'ai_vision'))
    env.define('ai_list_vision_models', BuiltinFunction(
        lambda: _ai.list_vision_models(), 'ai_list_vision_models'))