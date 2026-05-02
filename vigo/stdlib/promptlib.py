"""ViGo Prompt Template Library + A/B Testing"""
import time
from ..runtime.objects import BuiltinFunction


class PromptLibrary:
    def __init__(self):
        self.templates = {
            "translate": "Translate the following text to __LANGUAGE__:\n\n__TEXT__",
            "summarize": "Summarize the following in __WORDS__ words:\n\n__TEXT__",
            "code_review": "Review this code for bugs and improvements:\n\n__CODE__",
            "explain": "Explain __TOPIC__ in simple terms for a beginner.",
            "email": "Write a __TONE__ email about __TOPIC__.\n\nDetails: __DETAILS__",
            "brainstorm": "Brainstorm __COUNT__ ideas for __TOPIC__.",
            "compare": "Compare and contrast __ITEM1__ and __ITEM2__.",
            "fix_code": "Fix the bug in this code:\n\n__CODE__\n\nError: __ERROR__",
            "interview": "You are interviewing for __ROLE__. Answer: __QUESTION__",
            "teach": "Create a lesson plan for teaching __TOPIC__ to __AUDIENCE__.",
        }

    def get(self, name):
        return self.templates.get(name, "Template not found: " + str(name))

    def list_all(self):
        return list(self.templates.keys())

    def fill(self, name, values):
        template = self.templates.get(name, "")
        result = template
        for key, val in values.items():
            result = result.replace("__" + str(key).upper() + "__", str(val))
        return result

    def add(self, name, template):
        self.templates[name] = template
        return True

    def remove(self, name):
        if name in self.templates:
            del self.templates[name]
            return True
        return False

    def auto_optimize(self, name, task, test_input, expected_output, model="gemma-4b", iterations=3):
        """Automatically optimize a prompt template by iterating with AI"""
        from .ailib import AIClient
        ai = AIClient()

        current = self.templates.get(name, "")
        if not current:
            return "Template not found."

        for i in range(iterations):
            filled = current
            for k, v in test_input.items():
                filled = filled.replace("__" + k.upper() + "__", str(v))

            result = ai.ollama(filled, model)

            optimize_prompt = f"""Task: {task}
Current prompt template: {current}
Test input: {json.dumps(test_input)}
Expected output: {expected_output}
Actual output: {result}

Improve the prompt template to get closer to the expected output.
Return ONLY the improved template, nothing else."""

            current = ai.ollama(optimize_prompt, model)
            # Clean up AI response
            current = current.strip().strip('"').strip("'")
            self.templates[name] = current

        return current


class ABTester:
    """A/B Test different prompts or models"""

    def __init__(self):
        self.tests = []

    def run_single(self, prompt, model_a, model_b):
        """Compare two models on the same prompt"""
        from .ailib import AIClient
        ai = AIClient()
        start = time.time()
        result_a = ai.ollama(prompt, model_a)
        time_a = time.time() - start

        start = time.time()
        result_b = ai.ollama(prompt, model_b)
        time_b = time.time() - start

        return {
            "prompt": prompt[:100],
            "model_a": {"name": model_a, "time": round(time_a, 2), "result": result_a[:300], "tokens": len(result_a) // 4},
            "model_b": {"name": model_b, "time": round(time_b, 2), "result": result_b[:300], "tokens": len(result_b) // 4},
            "winner": model_a if time_a < time_b else model_b,
        }

    def run_prompts(self, prompts, model):
        """Compare multiple prompts on the same model"""
        from .ailib import AIClient
        ai = AIClient()
        results = []
        for prompt in prompts:
            start = time.time()
            result = ai.ollama(prompt, model)
            elapsed = time.time() - start
            results.append({"prompt": prompt[:100], "time": round(elapsed, 2), "result": result[:300]})
        return results


_prompt_lib = PromptLibrary()
_ab_tester = ABTester()


def register(env):
    env.define('prompt_list', BuiltinFunction(lambda: _prompt_lib.list_all(), 'prompt_list'))
    env.define('prompt_get', BuiltinFunction(lambda name: _prompt_lib.get(name), 'prompt_get'))
    env.define('prompt_fill', BuiltinFunction(lambda name, values: _prompt_lib.fill(name, values), 'prompt_fill'))
    env.define('prompt_add', BuiltinFunction(lambda name, template: _prompt_lib.add(name, template), 'prompt_add'))
    env.define('prompt_remove', BuiltinFunction(lambda name: _prompt_lib.remove(name), 'prompt_remove'))
    env.define('ab_models', BuiltinFunction(lambda prompt, ma, mb: _ab_tester.run_single(prompt, ma, mb), 'ab_models'))
    env.define('ab_prompts', BuiltinFunction(lambda prompts, model: _ab_tester.run_prompts(prompts, model), 'ab_prompts'))
    env.define('prompt_optimize', BuiltinFunction(
        lambda name, task, test_input, expected, model="gemma-4b", iters=3:
            _prompt_lib.auto_optimize(name, task, test_input, expected, model, iters),
        'prompt_optimize'))