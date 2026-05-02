"""ViGo Chart Library - Data Visualization"""
from ..runtime.objects import BuiltinFunction


class ChartGenerator:
    def __init__(self):
        pass

    def bar_chart(self, data, labels, title="Bar Chart", filename="chart.png"):
        """Generate a bar chart using matplotlib"""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt

            plt.figure(figsize=(10, 6))
            plt.bar(labels, data, color='#4fc3f7', edgecolor='#2b2b2b')
            plt.title(title, color='white', fontsize=14)
            plt.xlabel('Category', color='#aaa')
            plt.ylabel('Value', color='#aaa')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(filename, dpi=100, bbox_inches='tight', facecolor='#2b2b2b')
            plt.close()
            return f"Chart saved: {filename}"
        except ImportError:
            return "matplotlib not installed. Run: pip install matplotlib"
        except Exception as e:
            return f"Chart error: {e}"

    def line_chart(self, x_data, y_data, title="Line Chart", filename="line_chart.png"):
        """Generate a line chart"""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt

            plt.figure(figsize=(10, 6))
            plt.plot(x_data, y_data, color='#4fc3f7', linewidth=2, marker='o')
            plt.title(title, color='white', fontsize=14)
            plt.xlabel('X', color='#aaa')
            plt.ylabel('Y', color='#aaa')
            plt.grid(alpha=0.3)
            plt.tight_layout()
            plt.savefig(filename, dpi=100, bbox_inches='tight', facecolor='#2b2b2b')
            plt.close()
            return f"Chart saved: {filename}"
        except Exception as e:
            return f"Chart error: {e}"

    def pie_chart(self, data, labels, title="Pie Chart", filename="pie_chart.png"):
        """Generate a pie chart"""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt

            colors = ['#4fc3f7', '#ff8a65', '#81c784', '#ffd54f', '#ce93d8', '#90a4ae']
            plt.figure(figsize=(8, 8))
            plt.pie(data, labels=labels, colors=colors[:len(data)], autopct='%1.1f%%',
                    startangle=140, textprops={'color': 'white'})
            plt.title(title, color='white', fontsize=14)
            plt.tight_layout()
            plt.savefig(filename, dpi=100, bbox_inches='tight', facecolor='#2b2b2b')
            plt.close()
            return f"Chart saved: {filename}"
        except Exception as e:
            return f"Chart error: {e}"


_chart = ChartGenerator()


def register(env):
    env.define('chart_bar', BuiltinFunction(
        lambda data, labels, title="Bar Chart", f="chart.png":
            _chart.bar_chart(data, labels, title, f), 'chart_bar'))
    env.define('chart_line', BuiltinFunction(
        lambda x, y, title="Line Chart", f="line_chart.png":
            _chart.line_chart(x, y, title, f), 'chart_line'))
    env.define('chart_pie', BuiltinFunction(
        lambda data, labels, title="Pie Chart", f="pie_chart.png":
            _chart.pie_chart(data, labels, title, f), 'chart_pie'))