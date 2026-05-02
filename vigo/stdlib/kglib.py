"""ViGo Knowledge Graph Library"""
from ..runtime.objects import BuiltinFunction


class KnowledgeGraph:
    def __init__(self):
        self.entities = {}
        self.relations = []

    def add_entity(self, name, entity_type, properties=None):
        self.entities[name] = {"type": entity_type, "props": properties or {}}
        return True

    def add_relation(self, source, relation, target):
        self.relations.append({"source": source, "relation": relation, "target": target})
        if source not in self.entities: self.entities[source] = {"type": "unknown", "props": {}}
        if target not in self.entities: self.entities[target] = {"type": "unknown", "props": {}}
        return True

    def query_entity(self, name):
        return self.entities.get(name, {})

    def query_relations(self, name):
        result = []
        for r in self.relations:
            if r["source"] == name: result.append(f"{r['source']} --{r['relation']}--> {r['target']}")
            if r["target"] == name: result.append(f"{r['source']} --{r['relation']}--> {r['target']}")
        return result

    def get_all(self):
        return {"entities": self.entities, "relations": self.relations}

    def extract_from_text(self, text, model="gemma-4b"):
        from .ailib import AIClient
        prompt = f"""Extract entities and relations from the text as JSON.
Format: {{"entities": [{{"name": "...", "type": "person/place/organization/other"}}], "relations": [{{"source": "...", "relation": "...", "target": "..."}}]}}

Text: {text}

Return only valid JSON:"""
        result = AIClient().ollama(prompt, model)
        try:
            import json
            data = json.loads(result)
            for e in data.get("entities", []):
                self.add_entity(e["name"], e.get("type", "unknown"), e.get("props", {}))
            for r in data.get("relations", []):
                self.add_relation(r["source"], r["relation"], r["target"])
            return len(data.get("entities", []))
        except:
            return 0


_kg = KnowledgeGraph()


def register(env):
    env.define('kg_add_entity', BuiltinFunction(lambda n, t, p=None: _kg.add_entity(n, t, p), 'kg_add_entity'))
    env.define('kg_add_relation', BuiltinFunction(lambda s, r, t: _kg.add_relation(s, r, t), 'kg_add_relation'))
    env.define('kg_query_entity', BuiltinFunction(lambda n: _kg.query_entity(n), 'kg_query_entity'))
    env.define('kg_query_relations', BuiltinFunction(lambda n: _kg.query_relations(n), 'kg_query_relations'))
    env.define('kg_get_all', BuiltinFunction(lambda: _kg.get_all(), 'kg_get_all'))
    env.define('kg_extract', BuiltinFunction(lambda t, m="gemma-4b": _kg.extract_from_text(t, m), 'kg_extract'))