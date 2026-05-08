"""Conversation archiving for ViGo Dev - saves dialogues to project memory."""
import os
import json
import time
from datetime import datetime


def save_conversation(project_path, conv_id, conv_type, messages, model_name, task_description=""):
    """
    Archive a conversation to project memory.
    
    Args:
        project_path: Path to the project root
        conv_id: Conversation ID
        conv_type: "master" or "worker"
        messages: List of {role: "user"|"ai", content: "..."}
        model_name: Model used for this conversation
        task_description: Optional description of the task
    """
    # Ensure directories exist
    memory_dir = os.path.join(project_path, ".vigo_memory")
    conv_dir = os.path.join(memory_dir, "conversations", conv_id)
    os.makedirs(conv_dir, exist_ok=True)

    # Extract key decisions using AI
    decisions = _extract_decisions(messages)

    # Build Markdown file
    md_content = _build_conversation_markdown(conv_id, conv_type, model_name, task_description, messages, decisions)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = os.path.join(conv_dir, f"conversation_{timestamp}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    # Build JSON summary
    summary = {
        "conv_id": conv_id,
        "type": conv_type,
        "model": model_name,
        "task_description": task_description,
        "message_count": len(messages),
        "key_decisions": decisions,
        "timestamp": datetime.now().isoformat(),
    }
    json_path = os.path.join(conv_dir, "summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Store in project ChromaDB
    try:
        from .memlib import _get_project_store
        store = _get_project_store(project_path)
        full_text = f"Task: {task_description}\n" + "\n".join(
            [f"{m['role']}: {m['content'][:300]}" for m in messages[-20:]]
        )
        store.save(f"conv_{conv_id}", full_text)
    except Exception:
        pass

    return {"status": "ok", "path": conv_dir, "decisions": len(decisions)}


def _extract_decisions(messages):
    """
    Extract key decisions from conversation messages.
    Uses regex fallback if AI is not available.
    """
    decisions = []
    full_text = " ".join([m.get("content", "") for m in messages if m.get("role") == "ai"])

    # Regex: find sentences that indicate decisions
    import re
    patterns = [
        r'(?:I will|I\'ll|I have decided to|The plan is|Let\'s|We should|I recommend|I suggest) ([^.!?]+[.!?])',
        r'(?:Modified|Updated|Created|Deleted|Refactored|Fixed|Added|Removed) ([^.!?]+[.!?])',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, full_text, re.IGNORECASE)
        for m in matches:
            clean = m.strip()
            if len(clean) > 20 and clean not in decisions:
                decisions.append(clean)
                if len(decisions) >= 10:
                    break
        if len(decisions) >= 10:
            break

    if not decisions:
        decisions.append("Conversation archived without extracted decisions.")

    return decisions


def _build_conversation_markdown(conv_id, conv_type, model_name, task_description, messages, decisions):
    """Generate a readable Markdown file for the conversation."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md = f"""# Conversation: {conv_id}

**Type:** {conv_type}
**Model:** {model_name}
**Archived:** {timestamp}
**Task:** {task_description or 'N/A'}

---

## Key Decisions

"""
    for i, d in enumerate(decisions, 1):
        md += f"{i}. {d}\n"

    md += "\n---\n\n## Full Conversation\n\n"
    for m in messages:
        role_label = "🧑 User" if m.get("role") == "user" else "🤖 AI"
        md += f"### {role_label}\n\n{m.get('content', '')}\n\n"

    return md


def load_conversation(project_path, conv_id):
    """Load a conversation summary from project memory."""
    json_path = os.path.join(project_path, ".vigo_memory", "conversations", conv_id, "summary.json")
    if not os.path.exists(json_path):
        return None
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_conversations(project_path):
    """List all archived conversations in the project."""
    conv_root = os.path.join(project_path, ".vigo_memory", "conversations")
    if not os.path.exists(conv_root):
        return []
    result = []
    for conv_id in sorted(os.listdir(conv_root), reverse=True):
        summary = load_conversation(project_path, conv_id)
        if summary:
            result.append(summary)
    return result