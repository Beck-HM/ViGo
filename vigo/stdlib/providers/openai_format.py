"""OpenAI-compatible format handlers (response parsing + body building)"""


def parse_response(client, data, message_format):
    """Parse a complete API response, updating token counters."""
    client.total_tokens += data.get("usage", {}).get("total_tokens", 0)
    client.call_count += 1
    choices = data.get("choices", [])
    if choices:
        return choices[0].get("message", {}).get("content", "")
    return ""


def build_openai_body(messages, model, temp, max_tokens):
    """Build a standard OpenAI-compatible request body."""
    return {
        "model": model,
        "messages": messages,
        "temperature": temp,
        "max_tokens": max_tokens,
    }


def extract_stream_delta(obj, message_format):
    """Extract text delta from a streaming SSE chunk."""
    choices = obj.get("choices", [])
    if choices:
        delta = choices[0].get("delta", {})
        return delta.get("content", "")
    return ""