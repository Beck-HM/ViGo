"""ViGo Memory Library - RAG-based long-term memory with AI fact extraction"""
import os
import time
import sqlite3
import json
import urllib.request
from collections import defaultdict
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


class MemoryStore:
    """Persistent memory with ChromaDB vector search and AI-powered fact extraction."""

    def __init__(self, db_path=None, embedding_model="nomic-embed-text"):
        if db_path is None:
            db_path = os.path.join(os.path.expanduser("~"), ".vigo_memory.db")
        self.db_path = db_path
        self._chroma_client = None
        self._chroma_collection = None
        self._use_chromadb = False
        self.embedding_model = embedding_model
        self._init_db()
        self._init_chromadb()

    # ═══════════════════════════════════════
    #  SQLite (always active)
    # ═══════════════════════════════════════

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    created_at REAL,
                    accessed_at REAL,
                    access_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_key ON memory(key)")

    # ═══════════════════════════════════════
    #  ChromaDB (optional)
    # ═══════════════════════════════════════

    def _init_chromadb(self):
        try:
            import chromadb
            self._chroma_client = chromadb.PersistentClient(
                path=os.path.join(os.path.dirname(self.db_path), ".vigo_chromadb")
            )
            self._chroma_collection = self._chroma_client.get_or_create_collection(
                name="vigo_memory",
                metadata={"hnsw:space": "cosine"}
            )
            self._use_chromadb = True
        except Exception:
            self._use_chromadb = False

    def _get_embedding(self, text):
        """Generate embedding via Ollama embedding model."""
        try:
            data = json.dumps({
                "model": self.embedding_model,
                "prompt": str(text)[:512]
            }).encode('utf-8')
            req = urllib.request.Request(
                "http://localhost:11434/api/embeddings",
                data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result.get("embedding", [])
        except Exception:
            return []

    # ═══════════════════════════════════════
    #  AI helpers (use _ai singleton from ailib)
    # ═══════════════════════════════════════

    def _ai_ask(self, prompt, model="gemma-4b", provider=None):
        """Call AI via ailib's singleton, respecting configured provider."""
        from .ailib import _ai
        if provider is None:
            provider = _ai.provider or "ollama"
        return _ai.ask(prompt, model, provider=provider)

    def _extract_facts(self, content):
        """Use AI to extract key facts from content. Falls back to regex, then empty list."""
        prompt = f"""Extract key facts from the following content. Return ONLY a JSON array of strings, each string is one key fact. Do not include any other text.

Content:
{content[:2000]}

Output format example:
["fact 1", "fact 2", "fact 3"]"""
        response = self._ai_ask(prompt)
        try:
            # Try to parse JSON from response
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                facts = json.loads(response[start:end])
                if isinstance(facts, list) and len(facts) > 0:
                    return facts
        except Exception:
            pass

        # Fallback: regex extract key sentences (capitalized, with key verbs, reasonable length)
        import re
        sentences = re.findall(r'[A-Z][^.!?]{20,}', str(content))
        if sentences:
            return [s.strip() for s in sentences[:5]]

        # Final fallback: return empty, don't pollute memory with raw truncation
        return []

    # ═══════════════════════════════════════
    #  Public API
    # ═══════════════════════════════════════

    def save(self, key, content, threshold=0.85):
        """Save a memory. AI extracts key facts. Duplicates are merged if similarity > threshold."""
        now = time.time()

        # Check for existing similar memories
        if self._use_chromadb:
            existing = self._similar_memory(key, content)
            if existing:
                similarity = existing["similarity"]
                existing_key = existing["key"]
                if similarity >= threshold:
                    # Merge: overwrite old memory with new content
                    return self._update(existing_key, content, now)

        # AI fact extraction
        facts = self._extract_facts(content)
        value = json.dumps({"content": str(content), "facts": facts}, ensure_ascii=False)

        # Store in SQLite
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memory (key, value, weight, created_at, accessed_at, access_count)
                VALUES (?, ?, 1.0, ?, ?, 0)
            """, (key, value, now, now))
            conn.commit()

        # Store embedding in ChromaDB
        if self._use_chromadb:
            try:
                embedding = self._get_embedding(str(content))
                if embedding:
                    self._chroma_collection.upsert(
                        ids=[key],
                        embeddings=[embedding],
                        metadatas=[{"key": key, "weight": 1.0, "created_at": now}]
                    )
            except Exception:
                pass

        return {"status": "saved", "key": key, "facts": len(facts)}

    def _similar_memory(self, key, content):
        """Check if a similar memory already exists in ChromaDB."""
        if not self._use_chromadb:
            return None
        try:
            embedding = self._get_embedding(str(content))
            if not embedding:
                return None
            results = self._chroma_collection.query(
                query_embeddings=[embedding],
                n_results=1
            )
            ids = results.get("ids", [[]])[0]
            distances = results.get("distances", [[]])[0]
            if ids and distances:
                similarity = 1 - distances[0]  # cosine distance → similarity
                return {"key": ids[0], "similarity": similarity}
        except Exception:
            pass
        return None

    def _update(self, key, content, now):
        """Update an existing memory."""
        facts = self._extract_facts(content)
        value = json.dumps({"content": str(content), "facts": facts}, ensure_ascii=False)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE memory SET value=?, accessed_at=?, access_count=access_count+1 WHERE key=?",
                (value, now, key)
            )
            conn.commit()
        if self._use_chromadb:
            try:
                embedding = self._get_embedding(str(content))
                if embedding:
                    self._chroma_collection.upsert(
                        ids=[key],
                        embeddings=[embedding],
                        metadatas=[{"key": key, "weight": 1.0, "created_at": now}]
                    )
            except Exception:
                pass
        return {"status": "merged", "key": key, "facts": len(facts)}

    def recall(self, query, limit=10, hours=None):
        """Search memories by semantic similarity. Optionally filter by time window."""
        if not self._use_chromadb:
            return []

        embedding = self._get_embedding(query)
        if not embedding:
            return []

        try:
            where_filter = None
            if hours is not None:
                cutoff = time.time() - (hours * 3600)
                where_filter = {"created_at": {"$gte": cutoff}}

            results = self._chroma_collection.query(
                query_embeddings=[embedding],
                n_results=limit,
                where=where_filter
            )
            keys = results.get("ids", [[]])[0]
            distances = results.get("distances", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]

            return self._fetch_by_keys_with_scores(keys, distances, metadatas)
        except Exception:
            return []

    def enhanced_ask(self, prompt, model="gemma-4b", memory_limit=5, hours=None, provider=None):
        """Ask AI with relevant memories injected into the prompt."""
        memories = self.recall(prompt, limit=memory_limit, hours=hours)

        if memories:
            memory_text = "Relevant memories:\n"
            for m in memories:
                memory_text += f"- [{m.get('created_at', '?')}] {m.get('key')}: {m.get('value', '')[:300]}\n"
            enhanced_prompt = f"{memory_text}\nUser question: {prompt}"
        else:
            enhanced_prompt = prompt

        return self._ai_ask(enhanced_prompt, model, provider=provider)

    def snapshot(self):
        """Return a summary of all stored memories."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM memory").fetchone()
            count = row[0]
            min_time = row[1]
            max_time = row[2]
        return {
            "total": count,
            "oldest": time.strftime("%Y-%m-%d %H:%M", time.localtime(min_time)) if min_time else None,
            "newest": time.strftime("%Y-%m-%d %H:%M", time.localtime(max_time)) if max_time else None,
            "chromadb": self._use_chromadb,
            "db_path": self.db_path,
        }

    def get(self, key):
        """Retrieve a single memory by key."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT key, value, weight, created_at, access_count FROM memory WHERE key=?", (key,)
            ).fetchone()
            if row:
                return {"key": row[0], "value": row[1], "weight": row[2],
                        "created_at": row[3], "access_count": row[4]}
            return None

    def forget(self, key):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM memory WHERE key=?", (key,))
            conn.commit()
        if self._use_chromadb:
            try:
                self._chroma_collection.delete(ids=[key])
            except Exception:
                pass
        return True

    def clear(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM memory")
            conn.commit()
        if self._use_chromadb:
            try:
                all_ids = self._chroma_collection.get()["ids"]
                if all_ids:
                    self._chroma_collection.delete(ids=all_ids)
            except Exception:
                pass
        return True

    def size(self):
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM memory").fetchone()
            return row[0]

    def list_keys(self):
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT key FROM memory ORDER BY key").fetchall()
            return [r[0] for r in rows]

    def set_embedding_model(self, model_name):
        """Change the embedding model used for vector search."""
        self.embedding_model = model_name
        return True

    def _fetch_by_keys_with_scores(self, keys, distances, metadatas):
        if not keys:
            return []
        placeholders = ",".join(["?" for _ in keys])
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                f"SELECT key, value, weight, created_at, access_count FROM memory WHERE key IN ({placeholders})",
                keys
            ).fetchall()
        result_map = {}
        for r in rows:
            result_map[r[0]] = {
                "key": r[0], "value": r[1], "weight": r[2],
                "created_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(r[3])) if r[3] else "?",
                "access_count": r[4],
            }
        results = []
        for i, k in enumerate(keys):
            if k in result_map:
                entry = result_map[k]
                entry["similarity"] = round(1 - distances[i], 4) if i < len(distances) else 0
                results.append(entry)
        return results


_mem = None


def _get_store():
    global _mem
    if _mem is None:
        _mem = MemoryStore()
    return _mem


def register(env):
    _store = _get_store()

    env.define('mem_save', BuiltinFunction(
        lambda key, content, threshold=0.85: _store.save(key, content, threshold), 'mem_save'))
    env.define('mem_recall', BuiltinFunction(
        lambda query, limit=10, hours=None: _store.recall(query, limit, hours), 'mem_recall'))
    env.define('mem_enhanced_ask', BuiltinFunction(
        lambda prompt, model="gemma-4b", memory_limit=5, hours=None, provider=None:
            _store.enhanced_ask(prompt, model, memory_limit, hours, provider), 'mem_enhanced_ask'))
    env.define('mem_snapshot', BuiltinFunction(
        lambda: _store.snapshot(), 'mem_snapshot'))
    env.define('mem_get', BuiltinFunction(
        lambda key: _store.get(key), 'mem_get'))
    env.define('mem_forget', BuiltinFunction(
        lambda key: _store.forget(key), 'mem_forget'))
    env.define('mem_clear', BuiltinFunction(
        lambda: _store.clear(), 'mem_clear'))
    env.define('mem_size', BuiltinFunction(
        lambda: _store.size(), 'mem_size'))
    env.define('mem_list', BuiltinFunction(
        lambda: _store.list_keys(), 'mem_list'))
    env.define('mem_set_embedding_model', BuiltinFunction(
        lambda model_name: _store.set_embedding_model(model_name), 'mem_set_embedding_model'))
    env.define('mem_init_project', BuiltinFunction(
        lambda project_path: str(mem_init_project(project_path)), 'mem_init_project'))
    env.define('mem_save_project', BuiltinFunction(
        lambda project_path, key, content: _get_project_store(project_path).save(key, content), 'mem_save_project'))
    env.define('mem_recall_project', BuiltinFunction(
        lambda project_path, query, limit=10: _get_project_store(project_path).recall(query, limit), 'mem_recall_project'))

_project_stores = {}


def mem_init_project(project_path):
    """Initialize a project-level memory store."""
    db_path = os.path.join(project_path, ".vigo_memory", "project_memory.db")
    store = MemoryStore(db_path)
    _project_stores[project_path] = store
    return store


def _get_project_store(project_path):
    """Get or create a project-level memory store."""
    if project_path not in _project_stores:
        return mem_init_project(project_path)
    return _project_stores[project_path]