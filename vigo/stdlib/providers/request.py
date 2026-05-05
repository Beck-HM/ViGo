"""Provider-agnostic request building and execution"""
import json
import time
import urllib.request
import urllib.error
from ...runtime.errors import ViGoError
from . import get_provider_config
from .openai_format import parse_response, build_openai_body, extract_stream_delta
from .claude_format import build_claude_body
from .cohere_format import build_cohere_body


def build_url(client):
    """Build the API endpoint URL for a provider."""
    config, _ = get_provider_config(client.provider, client.base_url)
    if client.base_url:
        if "/v1/chat/completions" in client.base_url or "/v1/messages" in client.base_url or "/v2/chat" in client.base_url:
            return client.base_url
        return client.base_url.rstrip("/") + "/v1/chat/completions"
    return config["url"]


def build_headers(client):
    """Build HTTP headers for a provider."""
    config, _ = get_provider_config(client.provider, client.base_url)
    headers = {"Content-Type": "application/json"}
    if config["auth_header"] and client.api_key:
        headers[config["auth_header"]] = config["auth_prefix"] + client.api_key
    if config.get("api_version"):
        headers["anthropic-version"] = config["api_version"]
    return headers


def make_request(client, messages, model, temp, max_tokens, stream=False, provider=None):
    config, provider_name = get_provider_config(provider or client.provider, client.base_url)
    """Execute an API request against the configured provider."""
    config, provider_name = get_provider_config(client.provider, client.base_url)
    url = build_url(client)
    headers = build_headers(client)

    # Build request body based on message format
    if config["message_format"] == "claude":
        body = build_claude_body(messages, model, temp, max_tokens)
    elif config["message_format"] == "cohere":
        body = build_cohere_body(messages, model, temp, max_tokens)
    else:
        body = build_openai_body(messages, model, temp, max_tokens)

    if stream:
        body["stream"] = True
        return stream_request(client, url, headers, body, config["message_format"])

    data = json.dumps(body).encode('utf-8')
    last_error = None
    for attempt in range(client.max_retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as resp:
                response_data = json.loads(resp.read().decode('utf-8'))
                return parse_response(client, response_data, config["message_format"])
        except urllib.error.HTTPError as e:
            if 400 <= e.code < 500:
                error_body = e.read().decode('utf-8', errors='ignore') if e.fp else str(e)
                raise ViGoError(f"API error ({e.code}): {error_body[:500]}")
            last_error = e
            if attempt < client.max_retries:
                time.sleep(client.retry_delay * (attempt + 1))
        except (urllib.error.URLError, ConnectionResetError, TimeoutError) as e:
            last_error = e
            if attempt < client.max_retries:
                time.sleep(client.retry_delay * (attempt + 1))
        except Exception as e:
            raise ViGoError(f"Unexpected error: {e}")

    if isinstance(last_error, urllib.error.HTTPError):
        raise ViGoError(f"API error ({last_error.code}) after {client.max_retries+1} attempts")
    raise ViGoError(f"Connection error after {client.max_retries+1} attempts: {last_error.reason if hasattr(last_error, 'reason') else str(last_error)}")


def stream_request(client, url, headers, body, message_format):
    """Handle streaming SSE response, collecting chunks into client.stream_chunks."""
    data = json.dumps(body).encode('utf-8')
    full_text = ""
    client.stream_chunks = []
    last_error = None
    for attempt in range(client.max_retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=300) as resp:
                buffer = ""
                while True:
                    chunk = resp.read(1)
                    if not chunk:
                        break
                    buffer += chunk.decode('utf-8', errors='ignore')
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if line.startswith("data: "):
                            json_str = line[6:]
                            if json_str == "[DONE]":
                                break
                            try:
                                obj = json.loads(json_str)
                                delta = extract_stream_delta(obj, message_format)
                                if delta:
                                    full_text += delta
                                    client.stream_chunks.append(delta)
                            except json.JSONDecodeError:
                                pass
                client.total_tokens += len(full_text) // 4
                client.call_count += 1

                # Fallback: if no chunks parsed, try parsing as complete response
                if not full_text and buffer.strip():
                    try:
                        obj = json.loads(buffer.strip())
                        full_text = parse_response(client, obj, message_format)
                        if full_text:
                            client.stream_chunks.append(full_text)
                    except json.JSONDecodeError:
                        pass

                return full_text
        except (urllib.error.URLError, ConnectionResetError, TimeoutError) as e:
            last_error = e
            if attempt < client.max_retries:
                time.sleep(client.retry_delay * (attempt + 1))
        except Exception as e:
            raise ViGoError(f"Stream error: {e}")

    raise ViGoError(f"Stream connection failed after {client.max_retries+1} attempts: {last_error}")