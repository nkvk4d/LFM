from decimal import DefaultContext
from sys import thread_info
import customtkinter as ctk
from tkinter import Menu, ttk, messagebox, filedialog
import math
import json
import asyncio
import threading
import time
from typing import Dict, List, Any
import zmq
import lfm_lib

lfm_lib.init()

class EngineHook:
    def __init__(self):




        context = zmq.Context()
        self.socket = context.socket(zmq.REQ)
        self.socket.connect("tcp://localhost:5555")

class EngineOrchestrator:
    def __init__(self):
        self.entities: Dict[str, Any] = {}
        self.is_dirty = False

    def update_bone_transform(self, bone_name: str, frame: int, value: float):
        print(f"Bones Sync: {bone_name} at {frame} -> {value}")
        self.is_dirty = True

    async def render_request(self, frame: int):
        await asyncio.sleep(0.002)
        return True


class GraphCanvas(ctk.CTkCanvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg="#181818", highlightthickness=0, **kwargs)
        self.points = [(0, 100), (120, 50), (240, 150)]

    def draw_bezier(self, usable_w, padding_left, max_frames):
        self.delete("curve")
        coords = []
        for f, val in self.points:
            x = (f / max_frames) * usable_w + padding_left
            y = val
            coords.extend([x, y])

        if len(coords) >= 4:
            self.create_line(coords, fill="#50a0ff", smooth=True, width=2, tags="curve")

class LFMApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LFM - Light Film Maker (Beta Ready)")
        self.geometry("1400x900")

        self.engine = EngineOrchestrator()

        EngineHook()

        self.is_playing = False
        self.current_frame = 0
        self.max_frames = 240
        self.selection = {"start": 20, "end": 80, "falloff": 10}
        self.keyframes = {"head": [10, 50, 110], "spine_01": [0, 120]}

        self.setup_ui()
        self.start_async_worker()

    def setup_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=3)
        self.grid_columnconfigure(0, weight=1)

        self.setup_timeline()

        self.main_container = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=0)
        self.main_container.grid(row=1, column=0, sticky="nsew")
        self.main_container.grid_columnconfigure(1, weight=4)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.setup_hierarchy()
        self.setup_viewports()
        self.setup_inspector()

    def setup_timeline(self):
        self.tm_frame = ctk.CTkFrame(self, height=220, corner_radius=0, border_width=1, border_color="#333")
        self.tm_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=(0, 2))

        self.tm_tools = ctk.CTkFrame(self.tm_frame, height=35, fg_color="#252525")
        self.tm_tools.pack(fill="x")

        ctk.CTkLabel(self.tm_tools, text="MODE:", font=("Arial", 10, "bold")).pack(side="left", padx=10)
        self.mode_var = ctk.StringVar(value="Motion Editor")
        for m in ["Clip", "Motion", "Graph"]:
            ctk.CTkRadioButton(self.tm_tools, text=m, variable=self.mode_var,
                               command=self.redraw_timeline, width=80, font=("Arial", 11)).pack(side="left")

        self.play_btn = ctk.CTkButton(self.tm_tools, text="▶", width=50, command=self.toggle_play, fg_color="#d48221")
        self.play_btn.pack(side="right", padx=10)

        self.tm_canvas = ctk.CTkCanvas(self.tm_frame, bg="#121212", highlightthickness=0)
        self.tm_canvas.pack(fill="both", expand=True)
        self.tm_canvas.bind("<Button-1>", self.on_timeline_click)
        self.tm_canvas.bind("<B1-Motion>", self.on_timeline_click)

    def setup_viewports(self):
        vp_box = ctk.CTkFrame(self.main_container, fg_color="transparent")
        vp_box.grid(row=0, column=1, sticky="nsew", padx=4)
        vp_box.grid_rowconfigure((0, 1), weight=1)
        vp_box.grid_columnconfigure(0, weight=1)

        f1 = ctk.CTkFrame(vp_box, fg_color="#050505", border_width=1, border_color="#333")
        f1.grid(row=0, column=0, sticky="nsew", pady=(0,2))
        ctk.CTkLabel(f1, text="PERSPECTIVE", text_color="#555").place(x=10, y=5)

        f2 = ctk.CTkFrame(vp_box, fg_color="#000", border_width=2, border_color="#d48221")
        f2.grid(row=1, column=0, sticky="nsew", pady=(2,0))
        ctk.CTkLabel(f2, text="CAMERA RENDER (RUST)", text_color="#d48221").place(x=10, y=5)

    def setup_inspector(self):
        self.inspector = ctk.CTkTabview(self.main_container, width=300)
        self.inspector.grid(row=0, column=2, sticky="nsew", padx=2)

        proc = self.inspector.add("Procedural")
        for p in ["Jiggle", "Smooth", "Stagger"]:
            f = ctk.CTkFrame(proc, fg_color="transparent")
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=p, width=60).pack(side="left")
            s = ctk.CTkSlider(f, from_=0, to=1, command=lambda v, n=p: self.engine.update_bone_transform(n, self.current_frame, v))
            s.pack(side="right", fill="x", expand=True)
            s.set(0)

    def toggle_play(self):
        self.is_playing = not self.is_playing
        self.play_btn.configure(text="⏸" if self.is_playing else "▶")

    def on_timeline_click(self, event):
        padding = 120
        w = self.tm_canvas.winfo_width() - padding - 50
        rel_x = event.x - padding
        if 0 <= rel_x <= w:
            self.current_frame = int((rel_x / w) * self.max_frames)
            self.redraw_timeline()

    def redraw_timeline(self):
        self.tm_canvas.delete("all")
        w = self.tm_canvas.winfo_width()
        if w < 100: return

        pad = 120
        usable_w = w - pad - 50

        for i in range(0, self.max_frames + 1, 24):
            x = (i / self.max_frames) * usable_w + pad
            self.tm_canvas.create_line(x, 0, x, 200, fill="#222")
            self.tm_canvas.create_text(x, 190, text=str(i), fill="#444", font=("Arial", 8))

        sel_x1 = (self.selection["start"] / self.max_frames) * usable_w + pad
        sel_x2 = (self.selection["end"] / self.max_frames) * usable_w + pad
        self.tm_canvas.create_rectangle(sel_x1, 0, sel_x2, 180, fill="#2a1f0a", outline="#d48221")

        y_pos = 40
        for bone, keys in self.keyframes.items():
            self.tm_canvas.create_text(10, y_pos, text=bone, anchor="w", fill="#888", font=("Arial", 10))
            for k in keys:
                kx = (k / self.max_frames) * usable_w + pad
                self.tm_canvas.create_oval(kx-4, y_pos-4, kx+4, y_pos+4, fill="#d48221", outline="white")
            y_pos += 30

        px = (self.current_frame / self.max_frames) * usable_w + pad
        self.tm_canvas.create_line(px, 0, px, 200, fill="#ff4444", width=2)

    def start_async_worker(self):
        def run_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def heartbeat():
                while True:
                    if self.is_playing:
                        self.current_frame = (self.current_frame + 1) % self.max_frames
                        await self.engine.render_request(self.current_frame)
                        self.redraw_timeline()
                    await asyncio.sleep(0.033)

            loop.run_until_complete(heartbeat())

        threading.Thread(target=run_loop, daemon=True).start()

    def setup_hierarchy(self):
        self.hier_frame = ctk.CTkFrame(self.main_container, width=250, fg_color="#2b2b2b")
        self.hier_frame.grid(row=0, column=0, sticky="nsew", padx=2)
        ctk.CTkLabel(self.hier_frame, text="ANIMATION SETS", font=("Arial", 11, "bold")).pack(pady=5)

        self.tree = ttk.Treeview(self.hier_frame, show="tree")
        self.tree.pack(fill="both", expand=True)
        mdl = self.tree.insert("", "end", text="📦 player_model.mdl", open=True)
        self.tree.insert(mdl, "end", text="🦴 head")
        self.tree.insert(mdl, "end", text="🦴 arm_left")

if __name__ == "__main__":
    app = LFMApp()
    app.after(200, app.redraw_timeline)
    app.mainloop()
