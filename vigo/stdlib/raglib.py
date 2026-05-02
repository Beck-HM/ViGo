"""ViGo RAG Library - Retrieval Augmented Generation with Semantic Search"""
import os
import json
import re
import urllib.request
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


class RAGEngine:
    """RAG engine with TF-IDF and semantic embedding support"""

    def __init__(self):
        self.documents = []
        self.chunks = []
        self.embeddings = []
        self.use_chromadb = False
        self.chroma_collection = None

    def load_file(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        if ext == '.pdf':
            text = self._read_pdf(filepath)
        elif ext in ('.docx', '.doc'):
            text = self._read_docx(filepath)
        elif ext == '.html':
            text = self._read_html(filepath)
        else:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read()
            except UnicodeDecodeError:
                with open(filepath, "r", encoding="gbk") as f:
                    text = f.read()
        self.documents.append({"path": filepath, "content": text})
        return len(text)

    def _read_pdf(self, path):
        try:
            import subprocess
            result = subprocess.run(
                ["python", "-c",
                 f"import PyPDF2; r=PyPDF2.PdfReader(open('{path}','rb')); print(''.join(p.extract_text() or '' for p in r.pages))"],
                capture_output=True, text=True, timeout=30)
            return result.stdout or f"PDF read error: {result.stderr}"
        except:
            return f"Could not read PDF: {path}"

    def _read_docx(self, path):
        try:
            import subprocess
            result = subprocess.run(
                ["python", "-c",
                 f"from docx import Document; print('\\n'.join(p.text for p in Document('{path}').paragraphs))"],
                capture_output=True, text=True, timeout=30)
            return result.stdout or f"DOCX read error: {result.stderr}"
        except:
            return f"Could not read DOCX: {path}"

    def _read_html(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                html = f.read()
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        except:
            return f"Could not read HTML: {path}"

    def load_directory(self, dirpath, pattern="*.*"):
        import glob
        total = 0
        for fp in glob.glob(os.path.join(dirpath, pattern)):
            total += self.load_file(fp)
        return total

    def chunk(self, size=500, overlap=50):
        self.chunks = []
        for doc in self.documents:
            text = doc["content"]
            start = 0
            while start < len(text):
                end = min(start + size, len(text))
                chunk_text = text[start:end]
                self.chunks.append({
                    "source": doc["path"],
                    "start": start,
                    "end": end,
                    "text": chunk_text,
                })
                start += size - overlap
        return len(self.chunks)

    def init_chromadb(self, collection_name="vigo_rag"):
        try:
            import chromadb
            client = chromadb.Client()
            self.chroma_collection = client.create_collection(name=collection_name, get_or_create=True)
            self.use_chromadb = True
            return f"ChromaDB initialized: {collection_name}"
        except ImportError:
            return "ChromaDB not installed. Run: pip install chromadb"
        except Exception as e:
            return f"ChromaDB error: {e}"

    def embed_chunks(self):
        if not self.chunks:
            return 0
        if self.use_chromadb and self.chroma_collection is not None:
            for i, chunk in enumerate(self.chunks):
                self.chroma_collection.add(
                    documents=[chunk["text"]],
                    ids=[f"chunk_{i}"],
                    metadatas=[{"source": chunk["source"]}]
                )
        return len(self.chunks)

    def embed_with_model(self, model="nomic-embed-text", host="http://localhost:11434"):
        """Embed chunks using Ollama embedding model"""
        try:
            import numpy as np
        except ImportError:
            return 0
        self.embeddings = []
        for chunk in self.chunks:
            url = f"{host}/api/embeddings"
            data = json.dumps({"model": model, "prompt": chunk["text"][:500]}).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read().decode('utf-8'))
                    self.embeddings.append(np.array(result["embedding"]))
            except Exception:
                self.embeddings.append(np.zeros(384))
        return len(self.embeddings)

    def search_semantic(self, query, top_k=3, host="http://localhost:11434"):
        """Search using cosine similarity on embeddings"""
        try:
            import numpy as np
        except ImportError:
            return self.search(query, top_k)

        if not self.embeddings:
            self.embed_with_model(host=host)

        url = f"{host}/api/embeddings"
        data = json.dumps({"model": "nomic-embed-text", "prompt": query}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                query_emb = np.array(result["embedding"])
        except Exception:
            return self.search(query, top_k)

        scores = []
        for i, emb in enumerate(self.embeddings):
            sim = np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb) + 1e-8)
            scores.append((sim, i))
        scores.sort(key=lambda x: x[0], reverse=True)
        return [self.chunks[s[1]] for s in scores[:top_k]]

    def _tokenize(self, text):
        return set(re.findall(r'\b[a-zA-Z]+\b', text.lower()))

    def _tfidf_score(self, query_words, chunk_words):
        if not chunk_words: return 0
        overlap = query_words & chunk_words
        return len(overlap) / len(query_words) if query_words else 0

    def search(self, query, top_k=3):
        if self.use_chromadb and self.chroma_collection is not None:
            try:
                results = self.chroma_collection.query(query_texts=[query], n_results=top_k)
                chunks = []
                for docs in results.get("documents", [[]]):
                    for doc in docs:
                        chunks.append({"source": "chromadb", "text": doc})
                return chunks
            except:
                pass

        if not self.chunks: return []
        query_words = self._tokenize(query)
        scored = []
        for i, chunk in enumerate(self.chunks):
            score = self._tfidf_score(query_words, self._tokenize(chunk["text"]))
            if score > 0: scored.append((score, i, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[2] for s in scored[:top_k]]

    def generate_context(self, query, top_k=3):
        results = self.search(query, top_k)
        if not results: return "No relevant documents found."
        parts = []
        for i, chunk in enumerate(results):
            parts.append(f"[Source {i+1}: {chunk.get('source', 'unknown')}]\n{chunk['text']}")
        return "\n\n---\n\n".join(parts)

    def ask(self, query, model="gemma-4b", top_k=3):
        from .ailib import AIClient
        context = self.generate_context(query, top_k)
        prompt = f"Answer based on context.\n\nContext:\n{context}\n\nQuestion: {query}\n\nAnswer:"
        return AIClient().ollama(prompt, model)


_rag = RAGEngine()


def register(env):
    env.define('rag_load_file', BuiltinFunction(lambda p: _rag.load_file(p), 'rag_load_file'))
    env.define('rag_load_dir', BuiltinFunction(lambda p, pat="*.*": _rag.load_directory(p, pat), 'rag_load_dir'))
    env.define('rag_chunk', BuiltinFunction(lambda s=500, o=50: _rag.chunk(s, o), 'rag_chunk'))
    env.define('rag_search', BuiltinFunction(lambda q, k=3: _rag.search(q, k), 'rag_search'))
    env.define('rag_context', BuiltinFunction(lambda q, k=3: _rag.generate_context(q, k), 'rag_context'))
    env.define('rag_ask', BuiltinFunction(lambda q, m="gemma-4b", k=3: _rag.ask(q, m, k), 'rag_ask'))
    env.define('rag_init_chromadb', BuiltinFunction(lambda name="vigo_rag": _rag.init_chromadb(name), 'rag_init_chromadb'))
    env.define('rag_embed', BuiltinFunction(lambda: _rag.embed_chunks(), 'rag_embed'))
    env.define('rag_embed_model', BuiltinFunction(
        lambda m="nomic-embed-text", h="http://localhost:11434": _rag.embed_with_model(m, h),
        'rag_embed_model'))
    env.define('rag_search_semantic', BuiltinFunction(
        lambda q, k=3: _rag.search_semantic(q, k), 'rag_search_semantic'))