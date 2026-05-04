"""Cohere format handlers"""


def build_cohere_body(messages, model, temp, max_tokens):
    """Build a Cohere-compatible request body."""
    cohere_messages = []
    for msg in messages:
        cohere_messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", ""),
        })
    return {
        "model": model,
        "messages": cohere_messages,
        "temperature": temp,
        "max_tokens": max_tokens,
    }


def parse_response(client, data, message_format):
    """Parse a Cohere API response."""
    client.total_tokens += data.get("usage", {}).get("total_tokens", 0)
    client.call_count += 1
    message = data.get("message", {})
    content = message.get("content", [])
    if isinstance(content, list) and len(content) > 0:
        return content[0].get("text", "")
    return str(message.get("text", ""))


def extract_stream_delta(obj, message_format):
    """Extract text delta from a Cohere streaming chunk."""
    delta = obj.get("delta", {})
    content = delta.get("content", {})
    return content.get("text", "")