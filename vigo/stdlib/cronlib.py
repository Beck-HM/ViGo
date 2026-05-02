"""ViGo Cron Library - Scheduled Tasks"""
import time
import threading
from ..runtime.objects import BuiltinFunction


class CronScheduler:
    def __init__(self):
        self.jobs = {}
        self._running = False
        self._thread = None
        self._job_id = 0

    def add_interval(self, name, func, seconds):
        """Run a function every N seconds"""
        self._job_id += 1
        job_id = self._job_id
        self.jobs[job_id] = {
            "name": name,
            "func": func,
            "interval": seconds,
            "last_run": 0,
            "type": "interval",
        }
        return job_id

    def add_timeout(self, name, func, seconds):
        """Run a function once after N seconds"""
        self._job_id += 1
        job_id = self._job_id
        self.jobs[job_id] = {
            "name": name,
            "func": func,
            "interval": seconds,
            "last_run": time.time(),
            "type": "timeout",
            "done": False,
        }
        return job_id

    def remove(self, job_id):
        if job_id in self.jobs:
            del self.jobs[job_id]
            return True
        return False

    def list_jobs(self):
        result = []
        for jid, job in self.jobs.items():
            result.append(f"{jid}: {job['name']} ({job['type']}, {job['interval']}s)")
        return result

    def start(self):
        if self._running:
            return "Already running."
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return "Scheduler started."

    def stop(self):
        self._running = False
        return "Scheduler stopped."

    def _loop(self):
        while self._running:
            now = time.time()
            to_remove = []
            for jid, job in list(self.jobs.items()):
                if job["type"] == "timeout" and job.get("done"):
                    if now - job["last_run"] >= job["interval"] + 5:
                        to_remove.append(jid)
                    continue
                if now - job["last_run"] >= job["interval"]:
                    try:
                        if hasattr(job["func"], "func"):
                            job["func"].func()
                        elif callable(job["func"]):
                            job["func"]()
                    except Exception:
                        pass
                    job["last_run"] = now
                    if job["type"] == "timeout":
                        job["done"] = True
                        to_remove.append(jid)
            for jid in to_remove:
                self.jobs.pop(jid, None)
            time.sleep(0.5)


_cron = CronScheduler()


def register(env):
    env.define('cron_interval', BuiltinFunction(
        lambda name, func, sec: _cron.add_interval(name, func, sec),
        'cron_interval'))
    env.define('cron_timeout', BuiltinFunction(
        lambda name, func, sec: _cron.add_timeout(name, func, sec),
        'cron_timeout'))
    env.define('cron_remove', BuiltinFunction(
        lambda jid: _cron.remove(jid),
        'cron_remove'))
    env.define('cron_list', BuiltinFunction(
        lambda: _cron.list_jobs(),
        'cron_list'))
    env.define('cron_start', BuiltinFunction(
        lambda: _cron.start(),
        'cron_start'))
    env.define('cron_stop', BuiltinFunction(
        lambda: _cron.stop(),
        'cron_stop'))