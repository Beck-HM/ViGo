"""Anthropic Claude format handlers"""


def build_claude_body(messages, model, temp, max_tokens):
    """Build a Claude-compatible request body."""
    system_msg = None
    claude_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            system_msg = content
        else:
            claude_messages.append({"role": role, "content": content})
    body = {
        "model": model,
        "messages": claude_messages,
        "max_tokens": max_tokens,
        "temperature": temp,
    }
    if system_msg:
        body["system"] = system_msg
    return body


def parse_response(client, data, message_format):
    """Parse a Claude API response."""
    client.total_tokens += data.get("usage", {}).get("total_tokens", 0)
    client.call_count += 1
    content = data.get("content", [])
    if isinstance(content, list):
        return "".join([c.get("text", "") for c in content])
    return str(content)


def extract_stream_delta(obj, message_format):
    """Extract text delta from a Claude streaming chunk."""
    delta = obj.get("delta", {})
    return delta.get("text", "")