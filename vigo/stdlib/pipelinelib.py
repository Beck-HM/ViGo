"""ViGo Standard Library: Data Pipeline (pipelinelib)
ETL-style chainable data pipelines for AI workflows.
Complements workflowlib for micro-level data flow.
Pure Python stdlib — zero external dependencies.
"""
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


class Pipeline:
    def __init__(self):
        self._stages = []
        self._branches = []
    
    def source(self, func):
        """Set the data source."""
        self._stages.append(("source", func))
        return self
    
    def transform(self, func):
        """Add a transform stage."""
        self._stages.append(("transform", func))
        return self
    
    def filter(self, func):
        """Add a filter stage."""
        self._stages.append(("filter", func))
        return self
    
    def sink(self, func):
        """Set the data sink (terminal stage)."""
        self._stages.append(("sink", func))
        return self
    
    def branch(self, *pipelines):
        """Branch into multiple sub-pipelines."""
        self._branches = list(pipelines)
        return self
    
    def merge(self, *pipelines):
        """Merge multiple pipelines."""
        self._branches = list(pipelines)
        return self
    
    def run(self, input_data=None):
        """Execute the pipeline."""
        data = input_data
        
        for stage_type, func in self._stages:
            if stage_type == "source":
                data = func()
            elif stage_type == "transform":
                data = func(data)
            elif stage_type == "filter":
                data = func(data)
                if not data:
                    return None
            elif stage_type == "sink":
                func(data)
                return None
        
        # Handle branches
        if self._branches:
            results = []
            for pipeline in self._branches:
                results.append(pipeline.run(data))
            return results
        
        return data
    
    def schedule(self, cron=None, interval=None):
        """Schedule the pipeline to run periodically (placeholder)."""
        return {
            "scheduled": True,
            "cron": cron,
            "interval": interval,
            "note": "Use cronlib for actual scheduling",
        }


def register(env):
    env.define("Pipeline", BuiltinFunction(lambda: Pipeline(), "Pipeline"))