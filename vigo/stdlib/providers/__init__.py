"""ViGo AI Provider Registry"""
PROVIDERS = {
    # -- Tier 1: Cloud Providers --
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "message_format": "openai",
        "embedding_url": "https://api.openai.com/v1/embeddings",
        "embedding_model": "text-embedding-ada-002",
    },
    "deepseek": {
        "url": "https://api.deepseek.com/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "message_format": "openai",
        "embedding_url": "https://api.deepseek.com/v1/embeddings",
        "embedding_model": "deepseek-embedding",
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "message_format": "openai",
    },
    "claude": {
        "url": "https://api.anthropic.com/v1/messages",
        "auth_header": "x-api-key",
        "auth_prefix": "",
        "message_format": "claude",
        "api_version": "2023-06-01",
    },
    "mistral": {
        "url": "https://api.mistral.ai/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "message_format": "openai",
        "embedding_url": "https://api.mistral.ai/v1/embeddings",
        "embedding_model": "mistral-embed",
    },
    "together": {
        "url": "https://api.together.xyz/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "message_format": "openai",
        "embedding_url": "https://api.together.xyz/v1/embeddings",
        "embedding_model": "togethercomputer/m2-bert-80M-8k-retrieval",
    },
    "fireworks": {
        "url": "https://api.fireworks.ai/inference/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "message_format": "openai",
    },
    "perplexity": {
        "url": "https://api.perplexity.ai/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "message_format": "openai",
    },
    "cohere": {
        "url": "https://api.cohere.com/v2/chat",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "message_format": "cohere",
        "embedding_url": "https://api.cohere.com/v1/embed",
        "embedding_model": "embed-english-v3.0",
    },
    "grok": {
        "url": "https://api.x.ai/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "message_format": "openai",
    },
    "cerebras": {
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "message_format": "openai",
    },
    "sambanova": {
        "url": "https://api.sambanova.ai/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "message_format": "openai",
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "message_format": "openai",
        "embedding_url": "https://generativelanguage.googleapis.com/v1beta/openai/embeddings",
        "embedding_model": "text-embedding-004",
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "message_format": "openai",
    },
    # -- Tier 2: Local / Edge Providers --
    "ollama": {
        "url": "http://localhost:11434/v1/chat/completions",
        "auth_header": None,
        "auth_prefix": None,
        "message_format": "openai",
        "embedding_url": "http://localhost:11434/api/embeddings",
        "embedding_model": "nomic-embed-text",
    },
    "lmstudio": {
        "url": "http://localhost:1234/v1/chat/completions",
        "auth_header": None,
        "auth_prefix": None,
        "message_format": "openai",
    },
    "vllm": {
        "url": "http://localhost:8000/v1/chat/completions",
        "auth_header": None,
        "auth_prefix": None,
        "message_format": "openai",
    },
    "localai": {
        "url": "http://localhost:8080/v1/chat/completions",
        "auth_header": None,
        "auth_prefix": None,
        "message_format": "openai",
    },
    "textgen": {
        "url": "http://localhost:5000/v1/chat/completions",
        "auth_header": None,
        "auth_prefix": None,
        "message_format": "openai",
    },
    "llamacpp": {
        "url": "http://localhost:8080/v1/chat/completions",
        "auth_header": None,
        "auth_prefix": None,
        "message_format": "openai",
    },
}


def get_provider_config(provider_name, base_url=None):
    """Look up a provider config by name. Falls back to base_url or OpenAI defaults."""
    if provider_name in PROVIDERS:
        return PROVIDERS[provider_name], provider_name
    return {
        "url": base_url or "https://api.openai.com/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "message_format": "openai",
    }, "custom"