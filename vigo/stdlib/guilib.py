"""ViGo GUI Library v4.1 - Canvas Watermark + Terminal"""
import tkinter as tk
from tkinter import messagebox, scrolledtext
import io
import sys


class ViGoGUI:
    def __init__(self):
        self.root = None
        self.canvas = None
        self.watermark_text_id = None
        self.term_frame = None
        self.widgets = {}
        self._next_id = 0
        self._resize_job = None
        self._fg_color = "#e0e0e0"
        self._accent_color = "#4fc3f7"
        self._bg_color = "#0d0d1a"
        self._btn_bg = "#1a1a3e"
        self._btn_hover = "#252550"
        self._term_bg = "#0d0d1a"
        self._term_fg = "#c0c0c0"
        self._separator_color = "#2a2a4a"
        self._font = ("Microsoft YaHei", 11)
        self._font_bold = ("Microsoft YaHei", 11, "bold")
        self._font_mono = ("Consolas", 11)

        self.terminal = None
        self.term_input = None
        self._term_history = []
        self._term_history_idx = -1
        self._term_callback = None

        self.interpreter = None
        self.interpreter_env = None

    def _get_id(self):
        self._next_id += 1
        return str(self._next_id)

    def _blend_color(self, bg_hex, fg_hex, alpha):
        bg_r = int(bg_hex[1:3], 16)
        bg_g = int(bg_hex[3:5], 16)
        bg_b = int(bg_hex[5:7], 16)
        fg_r = int(fg_hex[1:3], 16)
        fg_g = int(fg_hex[3:5], 16)
        fg_b = int(fg_hex[5:7], 16)
        r = int(bg_r + (fg_r - bg_r) * alpha)
        g = int(bg_g + (fg_g - bg_g) * alpha)
        b = int(bg_b + (fg_b - bg_b) * alpha)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _create_terminal(self, parent):
        self.term_frame = tk.Frame(parent, bg=self._term_bg)

        output_frame = tk.Frame(self.term_frame, bg=self._term_bg)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self.terminal = scrolledtext.ScrolledText(
            output_frame,
            bg=self._term_bg, fg=self._term_fg,
            insertbackground=self._term_fg,
            font=self._font_mono, relief=tk.FLAT,
            borderwidth=0, state='disabled', wrap=tk.WORD,
        )
        self.terminal.pack(fill=tk.BOTH, expand=True, padx=8, pady=(6, 0))

        separator = tk.Frame(self.term_frame, height=2, bg=self._separator_color)
        separator.pack(fill=tk.X, padx=12, pady=(4, 0))

        input_outer = tk.Frame(self.term_frame, bg=self._term_bg)
        input_outer.pack(fill=tk.X, padx=8, pady=(2, 6))

        input_frame = tk.Frame(input_outer, bg=self._term_bg,
                               highlightbackground=self._separator_color,
                               highlightthickness=1)
        input_frame.pack(fill=tk.X, ipady=2)

        prompt_label = tk.Label(input_frame, text=" >>> ",
                                bg=self._term_bg, fg=self._accent_color,
                                font=self._font_mono)
        prompt_label.pack(side=tk.LEFT, padx=(4, 0))

        self.term_input = tk.Entry(
            input_frame, bg=self._term_bg, fg=self._term_fg,
            insertbackground=self._term_fg, font=self._font_mono,
            relief=tk.FLAT, borderwidth=0,
        )
        self.term_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4), pady=4)
        self.term_input.bind("<Return>", self._on_term_enter)
        self.term_input.bind("<Up>", self._on_term_up)
        self.term_input.bind("<Down>", self._on_term_down)
        self.term_input.focus_set()

        return self.term_frame

    def _term_print(self, text):
        if self.terminal is None: return
        self.terminal.config(state='normal')
        self.terminal.insert(tk.END, str(text) + "\n")
        self.terminal.see(tk.END)
        self.terminal.config(state='disabled')

    def _init_interpreter(self):
        if self.interpreter is not None: return
        from ..runtime.interpreter import Interpreter
        self.interpreter = Interpreter(source_file='<terminal>')
        self.interpreter_env = self.interpreter.global_env

    def _on_term_enter(self, event):
        cmd = self.term_input.get()
        self.term_input.delete(0, tk.END)
        if not cmd.strip(): return
        self._term_history.append(cmd)
        self._term_history_idx = len(self._term_history)
        self._term_print(">>> " + cmd)
        self._init_interpreter()
        old_stdout, captured = sys.stdout, io.StringIO()
        sys.stdout = captured
        try:
            from ..lexer.lexer import Lexer
            from ..parser.parser import Parser
            lexer = Lexer(cmd); parser = Parser(lexer); ast = parser.parse_program()
            result = None
            for stmt in ast.statements:
                result = self.interpreter.eval(stmt, self.interpreter_env)
            output = captured.getvalue()
            if output: self._term_print(output.rstrip())
            if result is not None: self._term_print(str(result))
        except Exception as e:
            output = captured.getvalue()
            if output: self._term_print(output.rstrip())
            self._term_print(f"ViGo Error: {e}")
        finally:
            sys.stdout = old_stdout

    def _on_term_up(self, event):
        if not self._term_history: return
        self._term_history_idx = max(0, self._term_history_idx - 1)
        self.term_input.delete(0, tk.END)
        self.term_input.insert(0, self._term_history[self._term_history_idx])

    def _on_term_down(self, event):
        if not self._term_history: return
        self._term_history_idx = min(len(self._term_history), self._term_history_idx + 1)
        self.term_input.delete(0, tk.END)
        if self._term_history_idx < len(self._term_history):
            self.term_input.insert(0, self._term_history[self._term_history_idx])

    def term_print(self, text): self._term_print(text)

    def term_clear(self):
        if self.terminal is None: return
        self.terminal.config(state='normal')
        self.terminal.delete('1.0', tk.END)
        self.terminal.config(state='disabled')

    def _style_button(self, btn):
        btn.config(bg=self._btn_bg, fg=self._fg_color,
                   activebackground=self._btn_hover, activeforeground="#ffffff",
                   relief=tk.FLAT, font=self._font_bold, cursor="hand2",
                   padx=16, pady=6, borderwidth=0,
                   highlightthickness=1, highlightbackground=self._accent_color,
                   highlightcolor=self._accent_color)
        def on_enter(e): btn.config(bg=self._btn_hover, highlightbackground="#ffffff")
        def on_leave(e): btn.config(bg=self._btn_bg, highlightbackground=self._accent_color)
        btn.bind("<Enter>", on_enter); btn.bind("<Leave>", on_leave)

    def create_window(self, title="ViGo", width=700, height=500):
        if self.root is not None: raise Exception("Windowalready exists")
        self.root = tk.Tk()
        self.root.title(str(title))
        self.root.geometry(f"{int(width)}x{int(height)}")
        self.root.configure(bg=self._bg_color)

        # Canvas Watermark layer (bottom)
        self.canvas = tk.Canvas(self.root, bg=self._bg_color, highlightthickness=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)

        # Terminal layer (on Canvas top)
        tf = self._create_terminal(self.root)
        tf.place(x=0, y=0, relwidth=1, relheight=1)
        tf.lift()

        def draw(e=None):
            w = self.root.winfo_width() if e is None else e.width
            h = self.root.winfo_height() if e is None else e.height
            if w <= 1 or h <= 1: return
            self.canvas.delete("all")
            color = self._blend_color(self._bg_color, "#ffffff", 0.05)
            size = min(w, h) // 2
            self.canvas.create_text(w // 2, h // 2, text="ViGo",
                                    font=("Microsoft YaHei", size, "bold"),
                                    fill=color)

        self.root.bind("<Configure>", lambda e: (self.root.after_cancel(self._resize_job) if self._resize_job else None, setattr(self, '_resize_job', self.root.after(100, lambda: draw(e)))))
        self.root.after(300, draw)
        return True

    def run(self):
        if self.root is None: raise Exception("No window")
        self.root.mainloop()
        return True

    def close(self):
        if self.root is not None:
            try: self.root.destroy()
            except: pass
            self.root = self.canvas = self.term_frame = self.terminal = self.term_input = self.interpreter = self.interpreter_env = None

    def add_button(self, text, x, y, callback):
        wid = self._get_id()
        btn = tk.Button(self.root, text=str(text), command=lambda c=callback: self._on_click(c))
        self._style_button(btn); btn.place(x=int(x), y=int(y))
        self.widgets[wid] = {'widget': btn, 'type': 'button'}; return wid

    def add_label(self, text, x, y):
        wid = self._get_id()
        lbl = tk.Label(self.root, text=str(text), bg=self._bg_color, fg=self._fg_color, font=self._font)
        lbl.place(x=int(x), y=int(y)); self.widgets[wid] = {'widget': lbl, 'type': 'label'}; return wid

    def add_input(self, x, y, width=200):
        wid = self._get_id()
        entry = tk.Entry(self.root, width=int(width), bg="#1a1a3e", fg=self._fg_color,
                         insertbackground=self._fg_color, font=self._font,
                         relief=tk.FLAT, highlightthickness=1,
                         highlightbackground=self._accent_color, highlightcolor=self._accent_color)
        entry.place(x=int(x), y=int(y)); self.widgets[wid] = {'widget': entry, 'type': 'input'}; return wid

    def get_input(self, wid):
        if wid in self.widgets and self.widgets[wid]['type'] == 'input':
            return self.widgets[wid]['widget'].get()
        return ""

    def set_label(self, wid, text):
        if wid in self.widgets and self.widgets[wid]['type'] == 'label':
            self.widgets[wid]['widget'].config(text=str(text)); return True
        return False

    def alert(self, msg):
        if self.root is not None: messagebox.showinfo("ViGo", str(msg))
        else: print(f"[ViGo Alert] {msg}")
        return True

    def _on_click(self, callback):
        if callback is not None and callable(callback): callback()


_gui = ViGoGUI()


def register(env):
    from ..runtime.objects import BuiltinFunction
    env.define('window_create',  BuiltinFunction(lambda t="ViGo", w=700, h=500: _gui.create_window(t, w, h), 'window_create'))
    env.define('window_run',     BuiltinFunction(lambda: _gui.run(), 'window_run'))
    env.define('window_close',   BuiltinFunction(lambda: _gui.close(), 'window_close'))
    env.define('term_print',     BuiltinFunction(lambda text: _gui.term_print(text), 'term_print'))
    env.define('term_clear',     BuiltinFunction(lambda: _gui.term_clear(), 'term_clear'))
    env.define('term_on_input',  BuiltinFunction(lambda cb: setattr(_gui, '_term_callback', cb), 'term_on_input'))
    env.define('button_add',     BuiltinFunction(lambda text, x, y, cb: _gui.add_button(text, x, y, cb), 'button_add'))
    env.define('label_add',      BuiltinFunction(lambda text, x, y: _gui.add_label(text, x, y), 'label_add'))
    env.define('label_set',      BuiltinFunction(lambda wid, text: _gui.set_label(wid, text), 'label_set'))
    env.define('input_add',      BuiltinFunction(lambda x, y, w=200: _gui.add_input(x, y, w), 'input_add'))
    env.define('input_get',      BuiltinFunction(lambda wid: _gui.get_input(wid), 'input_get'))
    env.define('alert',          BuiltinFunction(lambda msg: _gui.alert(msg), 'alert'))