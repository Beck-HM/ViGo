"""Auto Agent Manager — Project Manager CRUD and execution engine."""
import os
import json
import uuid
from datetime import datetime


def _get_managers_path():
    """Get path to project managers config file."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    memory_dir = os.path.join(base, "vigo-dev", "memory")
    os.makedirs(memory_dir, exist_ok=True)
    return os.path.join(memory_dir, "project_managers.json")


def _load_managers():
    path = _get_managers_path()
    if not os.path.exists(path):
        return {"project_managers": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"project_managers": []}


def _save_managers(data):
    path = _get_managers_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def create_project_manager(name, system_prompt, default_provider="gemma-4b",
                           max_masters=3, max_workers_per_master=2,
                           model_preferences=None):
    """Create a new project manager configuration."""
    data = _load_managers()
    pm = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "system_prompt": system_prompt,
        "default_provider": default_provider,
        "max_masters": max_masters,
        "max_workers_per_master": max_workers_per_master,
        "model_preferences": model_preferences or {"default": "gemma-4b"},
        "created_at": datetime.now().isoformat(),
    }
    data["project_managers"].append(pm)
    _save_managers(data)
    return pm


def update_project_manager(pm_id, **kwargs):
    """Update an existing project manager."""
    data = _load_managers()
    for pm in data["project_managers"]:
        if pm["id"] == pm_id:
            for key, value in kwargs.items():
                if key in pm:
                    pm[key] = value
            _save_managers(data)
            return pm
    return None


def delete_project_manager(pm_id):
    """Delete a project manager."""
    data = _load_managers()
    data["project_managers"] = [pm for pm in data["project_managers"] if pm["id"] != pm_id]
    _save_managers(data)
    return True


def list_project_managers():
    """List all project managers."""
    return _load_managers().get("project_managers", [])


def get_project_manager(pm_id):
    """Get a single project manager by ID."""
    for pm in list_project_managers():
        if pm["id"] == pm_id:
            return pm
    return None


# Preset templates
PRESET_TEMPLATES = [
    {
        "name": "Full-Stack Web Dev",
        "system_prompt": "You are a Project Manager for full-stack web development. "
                         "Break the user's goal into teams: Frontend, Backend, and Database. "
                         "Each team gets 1 Master and 1-2 Workers. "
                         "Output ONLY a JSON object with a 'teams' array. "
                         "Each team: {name, master: {task}, workers: [{task}]}."
    },
    {
        "name": "Bug Fixer",
        "system_prompt": "You are a Project Manager for bug fixing. "
                         "Analyze the bug and create 1 Master to investigate, "
                         "and 1 Worker to apply the fix. "
                         "Output ONLY a JSON object with a 'teams' array."
    },
    {
        "name": "Code Refactor",
        "system_prompt": "You are a Project Manager for code refactoring. "
                         "Identify modules to refactor. For each module, "
                         "create 1 Master to analyze and 1 Worker to rewrite. "
                         "Output ONLY a JSON object with a 'teams' array."
    },
    {
        "name": "Test Writer",
        "system_prompt": "You are a Project Manager for writing tests. "
                         "For each source file, create 1 Master to read the code "
                         "and 1 Worker to write tests. "
                         "Output ONLY a JSON object with a 'teams' array."
    },
]


def build_agent_pipeline(pm, goal, plan_json=None):
    """
    Build a pipeline from a project manager config and user goal.
    Calls the AI with PM's system prompt to decompose the goal into steps.
    """
    if plan_json:
        try:
            plan = json.loads(plan_json)
            return plan
        except:
            pass

    system_prompt = pm.get("system_prompt", "You are a project manager. Break the user's goal into structured steps.")

    prompt = f"""{system_prompt}

User's goal: {goal}

Output ONLY a valid JSON object. No markdown, no explanation. Use this exact structure:
{{
  "mode": "manager",
  "steps": [
    {{"assignee": "master", "desc": "step description"}},
    {{"assignee": "master", "desc": "step description"}}
  ]
}}

The 'assignee' must be "master". Each 'desc' is one concrete task step.
Reply with ONLY the JSON object, nothing else."""

    ai_response = ""
    try:
        import urllib.request
        data = json.dumps({
            "model": pm.get("default_provider", "gemma-4b"),
            "prompt": prompt,
            "stream": False,
        }).encode('utf-8')
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            ai_response = result.get("response", "")

        ai_response = ai_response.strip()
        if ai_response.startswith("```"):
            lines = ai_response.split('\n')
            ai_response = '\n'.join(lines[1:-1]) if len(lines) > 2 else ai_response
            ai_response = ai_response.strip()

        start = ai_response.find('{')
        end = ai_response.rfind('}') + 1
        if start >= 0 and end > start:
            json_str = ai_response[start:end]
            pipeline = json.loads(json_str)
            if "teams" in pipeline:
                steps = []
                max_masters = pm.get("max_masters", 3)
                max_workers = pm.get("max_workers_per_master", 2)
                for team in pipeline["teams"][:max_masters]:
                    team_name = team.get("name", "Team").replace(" ", "_")
                    steps.append({"assignee": "master", "desc": f"[{team_name}] {team['master']['task']}"})
                    workers = team.get("workers", [])
                    for i, worker in enumerate(workers[:max_workers]):
                        worker_name = f"{team_name}_worker_{i+1}"
                        steps.append({"assignee": worker_name, "desc": f"[{team_name}] {worker['task']}"})
                return {"mode": "manager", "steps": steps}
            if "steps" in pipeline and len(pipeline["steps"]) > 0:
                return pipeline
    except Exception:
        pass

    steps = []
    lines = goal.split('\n')
    for line in lines:
        line = line.strip()
        if line and len(line) > 5:
            steps.append({"assignee": "master", "desc": line})

    if len(steps) <= 1:
        steps = [{"assignee": "master", "desc": goal}]

    return {"mode": "manager", "steps": steps}