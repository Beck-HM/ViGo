"""ViGo Standard Library: Data Visualization (vislib)
Provides chart generation using matplotlib (optional).
"""
import os
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


def register(env):
    """Register all vislib functions into the given ViGo environment."""

    def _require_mpl():
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            return plt
        except ImportError:
            raise ViGoError("matplotlib not installed. Run: pip install matplotlib")

    def chart_line(x, y, title="Line Chart", xlabel="X", ylabel="Y", filepath="chart.png"):
        plt = _require_mpl()
        plt.figure(figsize=(8, 5))
        plt.plot(x, y, marker='o', linewidth=2)
        plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(filepath, dpi=100)
        plt.close()
        return filepath

    def chart_bar(labels, values, title="Bar Chart", xlabel="Category", ylabel="Value", filepath="chart.png"):
        plt = _require_mpl()
        plt.figure(figsize=(8, 5))
        plt.bar(labels, values, color='steelblue', edgecolor='white')
        plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.tight_layout()
        plt.savefig(filepath, dpi=100)
        plt.close()
        return filepath

    def chart_pie(labels, values, title="Pie Chart", filepath="chart.png"):
        plt = _require_mpl()
        plt.figure(figsize=(7, 7))
        plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
        plt.title(title)
        plt.tight_layout()
        plt.savefig(filepath, dpi=100)
        plt.close()
        return filepath

    def chart_scatter(x, y, title="Scatter Plot", xlabel="X", ylabel="Y", filepath="chart.png"):
        plt = _require_mpl()
        plt.figure(figsize=(8, 5))
        plt.scatter(x, y, alpha=0.7, c='coral', edgecolors='black')
        plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(filepath, dpi=100)
        plt.close()
        return filepath

    def chart_histogram(data, bins=10, title="Histogram", xlabel="Value", ylabel="Frequency", filepath="chart.png"):
        plt = _require_mpl()
        plt.figure(figsize=(8, 5))
        plt.hist(data, bins=int(bins), color='steelblue', edgecolor='white', alpha=0.8)
        plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.tight_layout()
        plt.savefig(filepath, dpi=100)
        plt.close()
        return filepath

    def chart_multi_line(x, y_dict, title="Multi-Line Chart", xlabel="X", ylabel="Y", filepath="chart.png"):
        plt = _require_mpl()
        plt.figure(figsize=(8, 5))
        for name, y in y_dict.items():
            plt.plot(x, y, marker='o', linewidth=2, label=str(name))
        plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(filepath, dpi=100)
        plt.close()
        return filepath

    env.define("chart_line", BuiltinFunction(chart_line, "chart_line"))
    env.define("chart_bar", BuiltinFunction(chart_bar, "chart_bar"))
    env.define("chart_pie", BuiltinFunction(chart_pie, "chart_pie"))
    env.define("chart_scatter", BuiltinFunction(chart_scatter, "chart_scatter"))
    env.define("chart_histogram", BuiltinFunction(chart_histogram, "chart_histogram"))
    env.define("chart_multi_line", BuiltinFunction(chart_multi_line, "chart_multi_line"))