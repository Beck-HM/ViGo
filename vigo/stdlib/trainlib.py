"""ViGo Training Library - AI Training Scheduler + LoRA Fine-tuning"""
import os
import json
import subprocess
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


class TrainingScheduler:
    def __init__(self):
        self.jobs = {}

    def schedule(self, name, config):
        """Schedule a training job with a config dict"""
        self.jobs[name] = {
            "config": config,
            "status": "scheduled",
            "pid": None,
        }
        return f"Job '{name}' scheduled."

    def start(self, name):
        """Start a scheduled training job"""
        if name not in self.jobs:
            raise ViGoError(f"Job '{name}' not found.")

        config = self.jobs[name]["config"]
        script = config.get("script", "train.py")
        args = config.get("args", "")

        cmd = f"python {script} {args}"
        try:
            proc = subprocess.Popen(cmd, shell=True)
            self.jobs[name]["status"] = "running"
            self.jobs[name]["pid"] = proc.pid
            return f"Job '{name}' started (PID: {proc.pid})."
        except Exception as e:
            self.jobs[name]["status"] = "failed"
            return f"Job '{name}' failed: {e}"

    def status(self, name):
        if name not in self.jobs:
            return "Not found."
        return json.dumps(self.jobs[name], default=str)

    def list_jobs(self):
        return list(self.jobs.keys())

    def stop(self, name):
        if name not in self.jobs:
            return "Not found."
        if self.jobs[name]["pid"]:
            try:
                import signal
                os.kill(self.jobs[name]["pid"], signal.SIGTERM)
            except:
                pass
        self.jobs[name]["status"] = "stopped"
        return f"Job '{name}' stopped."


class FineTuner:
    def __init__(self):
        self.base_model = None
        self.lora_config = {
            "r": 16,
            "alpha": 32,
            "dropout": 0.05,
            "target_modules": ["q_proj", "v_proj"],
        }

    def configure(self, base_model, r=16, alpha=32, dropout=0.05):
        """Configure LoRA fine-tuning parameters"""
        self.base_model = base_model
        self.lora_config = {"r": r, "alpha": alpha, "dropout": dropout,
                            "target_modules": ["q_proj", "v_proj"]}
        return f"LoRA configured: r={r}, alpha={alpha}, dropout={dropout}"

    def generate_script(self, dataset_path, output_dir, epochs=3, learning_rate=0.0002):
        """Generate a fine-tuning Python script using Unsloth or PEFT"""
        script = f'''
# Auto-generated ViGo fine-tuning script
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from peft import LoraConfig, get_peft_model, TaskType
from datasets import load_dataset
import os

base_model = "{self.base_model or 'meta-llama/Llama-3.2-3B'}"
dataset_path = "{dataset_path}"
output_dir = "{output_dir}"

print(f"Loading model: {{base_model}}")
tokenizer = AutoTokenizer.from_pretrained(base_model)
tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    base_model,
    torch_dtype=torch.float16,
    device_map="auto",
)

lora_config = LoraConfig(
    r={self.lora_config['r']},
    lora_alpha={self.lora_config['alpha']},
    lora_dropout={self.lora_config['dropout']},
    target_modules={self.lora_config['target_modules']},
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)

model = get_peft_model(model, lora_config)
print("LoRA applied.")

dataset = load_dataset("json", data_files=dataset_path, split="train")

def tokenize(examples):
    return tokenizer(examples["text"], truncation=True, padding="max_length", max_length=512)

dataset = dataset.map(tokenize, batched=True)

training_args = TrainingArguments(
    output_dir=output_dir,
    num_train_epochs={epochs},
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    learning_rate={learning_rate},
    fp16=True,
    save_steps=100,
    logging_steps=10,
)

from transformers import Trainer
trainer = Trainer(model=model, args=training_args, train_dataset=dataset)
print("Starting training...")
trainer.train()
model.save_pretrained(output_dir)
tokenizer.save_pretrained(output_dir)
print(f"Model saved to {{output_dir}}")
'''
        return script

    def export_config(self):
        return json.dumps({
            "base_model": self.base_model,
            "lora_config": self.lora_config,
        }, indent=2)


_train = TrainingScheduler()
_finetune = FineTuner()


def register(env):
    env.define('train_schedule', BuiltinFunction(
        lambda name, config: _train.schedule(name, config), 'train_schedule'))
    env.define('train_start', BuiltinFunction(
        lambda name: _train.start(name), 'train_start'))
    env.define('train_status', BuiltinFunction(
        lambda name: _train.status(name), 'train_status'))
    env.define('train_list', BuiltinFunction(
        lambda: _train.list_jobs(), 'train_list'))
    env.define('train_stop', BuiltinFunction(
        lambda name: _train.stop(name), 'train_stop'))
    env.define('tune_configure', BuiltinFunction(
        lambda model, r=16, alpha=32, dropout=0.05:
            _finetune.configure(model, r, alpha, dropout), 'tune_configure'))
    env.define('tune_generate', BuiltinFunction(
        lambda dataset, output, epochs=3, lr=0.0002:
            _finetune.generate_script(dataset, output, epochs, lr), 'tune_generate'))
    env.define('tune_config', BuiltinFunction(
        lambda: _finetune.export_config(), 'tune_config'))