"""ViGo Standard Library: Semantic Cache (cachelib)
Provides semantic caching for AI responses using embedding similarity.
Depends on ailib for embeddings and memlib for ChromaDB.
"""
import json
import time
import os
import math
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


class CacheResult:
    """Result from a cache recall operation."""
    def __init__(self, hit=False, response=None, similarity=0.0, source=None):
        self.hit = hit
        self.response = response
        self.similarity = similarity
        self.source = source
    
    def to_dict(self):
        return {
            "hit": self.hit,
            "response": self.response,
            "similarity": self.similarity,
            "source": self.source,
        }


class Cache:
    """Semantic cache for AI responses using embedding similarity."""
    
    def __init__(self, threshold=0.85, model=None, ttl=0, persist_dir=None):
        self.threshold = threshold
        self.model = model or "nomic-embed-text"
        self.ttl = ttl
        self.persist_dir = persist_dir or os.path.join(os.getcwd(), ".vigo_cache")
        
        self.hit_count = 0
        self.miss_count = 0
        self.tokens_saved = 0
        
        self._entries = []  # List of dicts: {prompt, response, embedding, created_at, hits}
        self._init_storage()
    
    def _init_storage(self):
        """Initialize ChromaDB or fallback to in-memory storage."""
        try:
            import chromadb
            from chromadb.config import Settings
            
            os.makedirs(self.persist_dir, exist_ok=True)
            
            self._client = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=self.persist_dir,
                anonymized_telemetry=False,
            ))
            self._collection = self._client.get_or_create_collection(name="vigo_semantic_cache")
            self._use_chromadb = True
        except ImportError:
            self._use_chromadb = False
        except Exception:
            self._use_chromadb = False
    
    def _get_embedding(self, text):
        """Get embedding vector for text via ailib."""
        try:
            from ..ailib import _ai
            return _ai.embed(text, model=self.model)
        except Exception:
            return None
    
    def _cosine_similarity(self, vec1, vec2):
        """Compute cosine similarity between two vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)
    
    def store(self, prompt, response):
        """Store a prompt-response pair in the cache.
        If embedding is unavailable, still store for exact matching."""
        embedding = self._get_embedding(prompt)
        
        entry = {
            "prompt": str(prompt),
            "response": str(response),
            "embedding": embedding or [],  # Empty list if embedding failed
            "created_at": time.time(),
            "hits": 0,
        }
        
        if self._use_chromadb and embedding:
            try:
                entry_id = f"cache_{len(self._entries)}"
                self._collection.add(
                    documents=[str(prompt)],
                    embeddings=[embedding],
                    metadatas=[{"response": str(response), "created_at": entry["created_at"], "hits": 0}],
                    ids=[entry_id],
                )
                self._client.persist()
            except Exception:
                pass
        
        self._entries.append(entry)
        return True
    
    def recall(self, prompt):
        """Search for a semantically similar cached response."""
        embedding = self._get_embedding(prompt)
        if not embedding or not self._entries:
            self.miss_count += 1
            return CacheResult(hit=False)
        
        best_similarity = 0
        best_entry = None
        
        # Check TTL
        now = time.time()
        for entry in self._entries:
            if self.ttl > 0 and (now - entry["created_at"]) > self.ttl:
                continue
            sim = self._cosine_similarity(embedding, entry["embedding"])
            if sim > best_similarity:
                best_similarity = sim
                best_entry = entry
        
        if best_similarity >= self.threshold and best_entry:
            best_entry["hits"] += 1
            self.hit_count += 1
            self.tokens_saved += len(best_entry["response"]) // 4
            return CacheResult(
                hit=True,
                response=best_entry["response"],
                similarity=best_similarity,
                source=best_entry["prompt"],
            )
        
        self.miss_count += 1
        return CacheResult(hit=False)
    
    def clear(self):
        """Clear all cached entries."""
        self._entries = []
        self.hit_count = 0
        self.miss_count = 0
        self.tokens_saved = 0
        if self._use_chromadb:
            try:
                self._client.delete_collection(name="vigo_semantic_cache")
                self._collection = self._client.get_or_create_collection(name="vigo_semantic_cache")
            except Exception:
                pass
        return True
    
    def remove(self, prompt):
        """Remove a specific prompt from the cache."""
        embedding = self._get_embedding(prompt)
        if not embedding:
            return False
        for i, entry in enumerate(self._entries):
            sim = self._cosine_similarity(embedding, entry["embedding"])
            if sim > 0.99:
                del self._entries[i]
                return True
        return False
    
    def stats(self):
        """Return cache statistics."""
        total = self.hit_count + self.miss_count
        return {
            "total_entries": len(self._entries),
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": round(self.hit_count / max(total, 1), 4),
            "tokens_saved": self.tokens_saved,
        }
    
    def similar(self, prompt, limit=5):
        """Find the most similar cached prompts."""
        embedding = self._get_embedding(prompt)
        if not embedding:
            return []
        scored = []
        for entry in self._entries:
            sim = self._cosine_similarity(embedding, entry["embedding"])
            scored.append((sim, entry["prompt"], entry["response"][:200]))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"similarity": round(s, 4), "prompt": p, "snippet": r} for s, p, r in scored[:int(limit)]]
    
    def warmup(self, prompts):
        """Pre-warm the cache with common prompts."""
        for prompt in prompts:
            try:
                from ..ailib import _ai
                response = _ai.ask(str(prompt))
                self.store(str(prompt), response)
            except Exception:
                pass
        return len(prompts)
    
    def export_cache(self, filepath):
        """Export cache entries to a JSON file."""
        data = []
        for entry in self._entries:
            data.append({
                "prompt": entry["prompt"],
                "response": entry["response"],
                "created_at": entry["created_at"],
                "hits": entry["hits"],
            })
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return len(data)
    
    def import_cache(self, filepath):
        """Import cache entries from a JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        count = 0
        for item in data:
            self.store(item["prompt"], item["response"])
            count += 1
        return count


def register(env):
    def _create_cache(threshold=0.85, model=None, ttl=0, persist_dir=None):
        return Cache(threshold=threshold, model=model, ttl=ttl, persist_dir=persist_dir)
    
    def _cache_store(cache, prompt, response):
        return cache.store(prompt, response)
    
    def _cache_recall(cache, prompt):
        return cache.recall(prompt).to_dict()
    
    def _cache_clear(cache):
        return cache.clear()
    
    def _cache_stats(cache):
        return cache.stats()
    
    def _cache_similar(cache, prompt, limit=5):
        return cache.similar(prompt, limit)
    
    def _cache_remove(cache, prompt):
        return cache.remove(prompt)
    
    def _cache_warmup(cache, prompts):
        return cache.warmup(prompts)
    
    def _cache_export(cache, filepath):
        return cache.export_cache(filepath)
    
    def _cache_import(cache, filepath):
        return cache.import_cache(filepath)
    
    env.define("Cache", BuiltinFunction(_create_cache, "Cache"))
    env.define("cache_store", BuiltinFunction(_cache_store, "cache_store"))
    env.define("cache_recall", BuiltinFunction(_cache_recall, "cache_recall"))
    env.define("cache_clear", BuiltinFunction(_cache_clear, "cache_clear"))
    env.define("cache_stats", BuiltinFunction(_cache_stats, "cache_stats"))
    env.define("cache_similar", BuiltinFunction(_cache_similar, "cache_similar"))
    env.define("cache_remove", BuiltinFunction(_cache_remove, "cache_remove"))
    env.define("cache_warmup", BuiltinFunction(_cache_warmup, "cache_warmup"))
    env.define("cache_export", BuiltinFunction(_cache_export, "cache_export"))
    env.define("cache_import", BuiltinFunction(_cache_import, "cache_import"))