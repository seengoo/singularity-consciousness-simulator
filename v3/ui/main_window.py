"""
主窗口 — tkinter 多奇点可视化

深色背景 + 亮色奇点 + 彩色资源
"""
import tkinter as tk
from tkinter import ttk
import math
import random


# === 颜色：深色背景 + 高对比 ===
COLOR_BG = "#0a0a0f"
COLOR_PANEL_BG = "#111118"
COLOR_GRID_LINE = "#1a1a25"
COLOR_TEXT = "#d0d0dd"
COLOR_TEXT_DIM = "#666680"
COLOR_HIGHLIGHT = "#ff4488"
COLOR_ACCENT = "#222244"

COLOR_EMPTY_BASE = (13, 13, 20)

# 地形底色
TERRAIN_COLORS = {
    0: (13, 13, 20),   # 荒原
    1: (10, 21, 16),   # 绿洲
    2: (14, 10, 24),   # 裂谷
    3: (18, 16, 10),   # 高地
}

# 奇点颜色
COLOR_PC = "#ffffff"       # PC = 纯白
COLOR_PC_GLOW = "#4444ff"
COLOR_NPC_BASE = "#aaaacc"


class EmergenceUI:
    def __init__(self, engine, world_size=60):
        self.engine = engine
        self.world_size = world_size
        self.paused = False
        self.speed = 1.0
        self.running = False
        self._create_window()

    def _create_window(self):
        self.root = tk.Tk()
        self.root.title("微型文明演化沙盒 — 森谷智创")
        self.root.configure(bg=COLOR_BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = min(1400, screen_w - 100)
        win_h = min(860, screen_h - 100)
        self.root.geometry(f"{win_w}x{win_h}")
        self.root.minsize(1000, 680)

        self.world_view_size = min(win_h - 100, win_w - 420, 650)

        self._build_ui()
        self.root.bind("<Key>", self._on_key)
        self.root.bind("<space>", lambda e: self._toggle_pause())
        self.root.bind("<r>", lambda e: self._reset())
        self.root.bind("<q>", lambda e: self._on_close())
        self.root.bind("<s>", lambda e: self._step_once())
        self.root.bind("<plus>", lambda e: self._change_speed(0.5))
        self.root.bind("<equal>", lambda e: self._change_speed(0.5))
        self.root.bind("<minus>", lambda e: self._change_speed(-0.5))

    def _build_ui(self):
        # 顶部
        title_f = tk.Frame(self.root, bg=COLOR_BG, height=36)
        title_f.pack(fill="x", padx=10, pady=(6, 2))
        title_f.pack_propagate(False)

        tk.Label(title_f, text="◆ 微型文明演化沙盒 v1.0",
                 font=("Microsoft YaHei", 13, "bold"),
                 fg=COLOR_HIGHLIGHT, bg=COLOR_BG).pack(side="left")

        self.cycle_label = tk.Label(title_f, text="周期: 0",
                                     font=("Consolas", 11), fg=COLOR_TEXT, bg=COLOR_BG)
        self.cycle_label.pack(side="right", padx=8)

        self.status_label = tk.Label(title_f, text="就绪",
                                      font=("Microsoft YaHei", 10), fg=COLOR_TEXT_DIM, bg=COLOR_BG)
        self.status_label.pack(side="right", padx=8)

        self.pop_label = tk.Label(title_f, text="种群: 0",
                                   font=("Consolas", 10), fg=COLOR_TEXT_DIM, bg=COLOR_BG)
        self.pop_label.pack(side="right", padx=8)

        self.res_label = tk.Label(title_f, text="资源: 0",
                                   font=("Consolas", 10), fg="#88cc88", bg=COLOR_BG)
        self.res_label.pack(side="right", padx=8)

        # 主区域
        main_f = tk.Frame(self.root, bg=COLOR_BG)
        main_f.pack(fill="both", expand=True, padx=10, pady=2)

        # -- 左：世界视图 --
        left_f = tk.Frame(main_f, bg=COLOR_BG)
        left_f.pack(side="left", fill="both", expand=True)

        canvas_f = tk.Frame(left_f, bg=COLOR_PANEL_BG,
                             highlightbackground="#222233", highlightthickness=1)
        canvas_f.pack(pady=4)

        self.canvas = tk.Canvas(
            canvas_f,
            width=self.world_view_size,
            height=self.world_view_size,
            bg="#08080e",
            highlightthickness=0,
        )
        self.canvas.pack(padx=2, pady=2)

        # 图例
        leg_f = tk.Frame(left_f, bg=COLOR_BG)
        leg_f.pack(fill="x", pady=2)
        legends = [
            ("⬟", COLOR_PC, "实验对象(PC)"),
            ("⬟", COLOR_NPC_BASE, "NPC"),
            ("●", "#ff5050", "赤焰"),
            ("●", "#3c8cff", "深水"),
            ("●", "#46dc64", "翡翠"),
            ("●", "#ffd22e", "玄金"),
            ("●", "#be46e6", "紫晶"),
        ]
        for sym, c, label in legends:
            f = tk.Frame(leg_f, bg=COLOR_BG)
            f.pack(side="left", padx=6)
            tk.Label(f, text=sym, fg=c, bg=COLOR_BG,
                     font=("Consolas", 10)).pack(side="left")
            tk.Label(f, text=label, fg=COLOR_TEXT, bg=COLOR_BG,
                     font=("Microsoft YaHei", 8)).pack(side="left", padx=1)

        # -- 右：信息面板 --
        right_f = tk.Frame(main_f, bg=COLOR_PANEL_BG, width=360)
        right_f.pack(side="right", fill="y", padx=(6, 0))
        right_f.pack_propagate(False)

        self._build_arch_info(right_f)
        self._build_state_bars(right_f)
        self._build_npc_list(right_f)
        self._build_event_log(right_f)

        # -- 底部控制 --
        bot_f = tk.Frame(self.root, bg=COLOR_BG, height=40)
        bot_f.pack(fill="x", padx=10, pady=(2, 6))
        bot_f.pack_propagate(False)

        for text, cmd, color in [
            ("⏸ 暂停", self._toggle_pause, COLOR_ACCENT),
            ("⏭ 单步", self._step_once, COLOR_ACCENT),
            ("🔄 重置", self._reset, "#331122"),
            ("➕ 加速", lambda: self._change_speed(0.5), COLOR_ACCENT),
            ("➖ 减速", lambda: self._change_speed(-0.5), COLOR_ACCENT),
        ]:
            tk.Button(bot_f, text=text, command=cmd,
                     bg=color, fg=COLOR_TEXT, font=("Microsoft YaHei", 9),
                     relief="flat", padx=10, cursor="hand2").pack(side="left", padx=3)

        self.speed_label = tk.Label(bot_f, text="速度: 1.0x",
                                     font=("Consolas", 10), fg=COLOR_TEXT, bg=COLOR_BG)
        self.speed_label.pack(side="right", padx=10)

        tk.Label(bot_f, text="[Space]暂停 [S]步进 [+/-]速度 [R]重置 [Q]退出",
                 font=("Consolas", 9), fg=COLOR_TEXT_DIM, bg=COLOR_BG
                 ).pack(side="right", padx=10)

    def _build_arch_info(self, parent):
        f = tk.Frame(parent, bg=COLOR_PANEL_BG)
        f.pack(fill="x", padx=10, pady=(8, 2))

        tk.Label(f, text="◆ 实验对象状态",
                 font=("Microsoft YaHei", 10, "bold"),
                 fg=COLOR_HIGHLIGHT, bg=COLOR_PANEL_BG).pack(anchor="w")

        self.arch_label = tk.Label(f, text="架构: -",
                                    font=("Consolas", 10), fg=COLOR_TEXT, bg=COLOR_PANEL_BG)
        self.arch_label.pack(anchor="w", pady=1)

        self.pos_label = tk.Label(f, text="位置: -",
                                   font=("Consolas", 10), fg=COLOR_TEXT, bg=COLOR_PANEL_BG)
        self.pos_label.pack(anchor="w", pady=1)

        self.energy_label = tk.Label(f, text="",
                                      font=("Consolas", 10), fg=COLOR_TEXT, bg=COLOR_PANEL_BG)
        self.energy_label.pack(anchor="w", pady=1)

        self.state_desc_label = tk.Label(f, text="",
                                          font=("Microsoft YaHei", 9), fg=COLOR_TEXT_DIM, bg=COLOR_PANEL_BG)
        self.state_desc_label.pack(anchor="w", pady=1)

        self.area_label = tk.Label(f, text="",
                                    font=("Consolas", 9), fg=COLOR_TEXT_DIM, bg=COLOR_PANEL_BG)
        self.area_label.pack(anchor="w", pady=1)

        tk.Frame(f, height=1, bg="#222244").pack(fill="x", pady=4)

    def _build_state_bars(self, parent):
        f = tk.Frame(parent, bg=COLOR_PANEL_BG)
        f.pack(fill="x", padx=10, pady=2)

        tk.Label(f, text="■ 内部状态",
                 font=("Microsoft YaHei", 10, "bold"),
                 fg="#6666aa", bg=COLOR_PANEL_BG).pack(anchor="w")

        self.state_bars_frame = tk.Frame(f, bg=COLOR_PANEL_BG)
        self.state_bars_frame.pack(fill="x", pady=2)

        tk.Frame(f, height=1, bg="#222244").pack(fill="x", pady=4)

    def _build_npc_list(self, parent):
        f = tk.Frame(parent, bg=COLOR_PANEL_BG)
        f.pack(fill="x", padx=10, pady=2)

        tk.Label(f, text="● 种群列表",
                 font=("Microsoft YaHei", 10, "bold"),
                 fg="#66aa66", bg=COLOR_PANEL_BG).pack(anchor="w")

        self.npc_frame = tk.Frame(f, bg=COLOR_PANEL_BG)
        self.npc_frame.pack(fill="x", pady=2)

        tk.Frame(f, height=1, bg="#222244").pack(fill="x", pady=4)

    def _build_event_log(self, parent):
        f = tk.Frame(parent, bg=COLOR_PANEL_BG)
        f.pack(fill="both", expand=True, padx=10, pady=2)

        tk.Label(f, text="≈ 世界事件",
                 font=("Microsoft YaHei", 10, "bold"),
                 fg="#aa8844", bg=COLOR_PANEL_BG).pack(anchor="w")

        log_f = tk.Frame(f, bg=COLOR_PANEL_BG)
        log_f.pack(fill="both", expand=True)

        self.event_log = tk.Text(log_f, height=8, width=38,
                                  bg="#08080e", fg=COLOR_TEXT,
                                  font=("Consolas", 9),
                                  relief="flat", state="disabled")
        self.event_log.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(log_f, command=self.event_log.yview)
        scrollbar.pack(side="right", fill="y")
        self.event_log.config(yscrollcommand=scrollbar.set)

    # === 渲染 ===
    def render_frame(self):
        if self.running:
            return
        self.running = True
        self._do_render()
        self.running = False

    def _do_render(self):
        if not hasattr(self, 'root') or not self.root.winfo_exists():
            return
        try:
            pop = self.engine.population
            world = self.engine.world
            obs = self.engine.observer
            pc = pop.pc_singularity if pop else None

            if not pc:
                return

            cell_size = max(2, self.world_view_size / world.size)
            self.canvas.delete("all")

            self._render_world(world, pop, cell_size)
            self._update_info(pc, obs, pop)
            self._update_state_bars(pc)
            self._update_npc_list(pop)

            self.cycle_label.config(text=f"周期: {world.cycle}")
            self.status_label.config(text="⏸ 暂停" if self.paused else "▶ 运行")
            self.res_label.config(text=f"资源: {world.total_resources}")

        except Exception as e:
            import traceback
            traceback.print_exc()

    def _render_world(self, world, population, cell_size):
        """渲染世界 — 先地形，再资源，再奇点（保证奇点在最上层）"""
        s = world.size

        # 1. 底色 + 足迹染色
        for y in range(s):
            for x in range(s):
                cell = world.get_cell(x, y)
                if cell is None:
                    continue

                # 足迹染色：访问次数越多颜色越深
                if cell.stain_color and cell.visit_count > 0:
                    intensity = min(1.0, cell.visit_count / 10)
                    sr, sg, sb = cell.stain_color
                    tr, tg, tb = TERRAIN_COLORS.get(cell.terrain, COLOR_EMPTY_BASE)
                    # 混合足迹颜色和底色
                    mix = max(0.15, intensity * 0.5)
                    r = int(sr * mix + tr * (1 - mix))
                    g = int(sg * mix + tg * (1 - mix))
                    b = int(sb * mix + tb * (1 - mix))
                    bg = "#%02x%02x%02x" % (min(255,r), min(255,g), min(255,b))
                else:
                    tc = TERRAIN_COLORS.get(cell.terrain, COLOR_EMPTY_BASE)
                    bg = "#%02x%02x%02x" % tc

                px = x * cell_size
                py = y * cell_size
                self.canvas.create_rectangle(
                    px, py, px + cell_size + 1, py + cell_size + 1,
                    fill=bg, outline=""
                )

                # ★ 领地边框：被占领的格子画边框
                if world.is_claimed(x, y):
                    claim_color = world.get_claim_color(x, y)
                    if claim_color:
                        cc = "#%02x%02x%02x" % claim_color
                        border = max(1, cell_size * 0.1)
                        self.canvas.create_rectangle(
                            px, py, px + cell_size, py + cell_size,
                            outline=cc, width=int(border),
                        )

        # 2. 资源圆点（在染色之上，放大+发光）
        for y in range(s):
            for x in range(s):
                cell = world.get_cell(x, y)
                if cell is None or cell.type != "resource":
                    continue
                c = "#%02x%02x%02x" % cell.color
                px = x * cell_size
                py = y * cell_size
                r = max(3, cell_size * 0.45)  # 放大资源点
                cx = px + cell_size / 2
                cy = py + cell_size / 2
                # 实心圆（带白色边框确保可见）
                self.canvas.create_oval(
                    cx - r, cy - r, cx + r, cy + r,
                    fill=c, outline="#ffffff", width=max(1, cell_size*0.08)
                )

        # 3. 所有奇点（NPC先画，PC最后在最上层）
        all_s = population.get_all_singularities()
        npcs = [s for s in all_s if not getattr(s, '_is_pc', False)]
        pc = population.pc_singularity

        for s in npcs:
            self._draw_singularity(s, cell_size, is_pc=False, population=population)

        if pc and pc.alive:
            self._draw_singularity(pc, cell_size, is_pc=True)

    def _draw_singularity(self, singularity, cell_size, is_pc=False, population=None):
        """画一个奇点"""
        px = singularity.x * cell_size
        py = singularity.y * cell_size
        cx = px + cell_size / 2
        cy = py + cell_size / 2

        if is_pc:
            # PC: 白色 + 蓝色光晕
            glow_r = cell_size * 2
            self.canvas.create_oval(
                cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r,
                fill="", outline=COLOR_PC_GLOW, width=1,
                stipple="gray25",
            )
            r = max(2, cell_size * 0.6)
            self.canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill=COLOR_PC, outline="#8888ff", width=1,
            )
        else:
            # NPC: 原型颜色
            arch = getattr(singularity, 'archetype', None)
            npc_color = COLOR_NPC_BASE
            if population:
                a = population.get_npc_archetype(singularity)
                if a:
                    from core.population import NPC_ARCHETYPES
                    if a in NPC_ARCHETYPES:
                        col = NPC_ARCHETYPES[a]["color"]
                        npc_color = "#%02x%02x%02x" % col
            r = max(1.5, cell_size * 0.4)
            self.canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill=npc_color, outline="#444", width=1,
            )

    def _update_info(self, pc, observer, population):
        """更新状态面板"""
        self.arch_label.config(text=f"架构: {pc.arch.name} {'★ PC' if pc._is_pc else ''}")
        self.pos_label.config(text=f"位置: ({pc.x}, {pc.y})")
        self.energy_label.config(text=f"能量: {pc.energy:.3f}/{pc.max_energy:.1f}")

        desc = pc.arch.describe_state(pc.internal_state)
        self.state_desc_label.config(text=desc)

        if observer:
            explored = len(observer.explored_positions)
            total = population.world.size * population.world.size
            pct = explored / total * 100
            self.area_label.config(text=f"探索: {explored}/{total} ({pct:.1f}%)")

        # 领地统计
        world = self.engine.world
        if world:
            pc_claimed = world.get_claimed_count("pc")
            npc_claimed = sum(
                world.get_claimed_count(f"npc_{s._npc_id}")
                for s in self.engine.population.get_all_singularities()
                if not getattr(s, '_is_pc', False)
            ) if self.engine.population else 0
            total_claimed = pc_claimed + npc_claimed
            self.energy_label.config(
                text=f"能量: {pc.energy:.3f} | 领地: {pc_claimed}(+{npc_claimed})"
            )

        # 种群数
        total = len(population.get_all_singularities())
        alive = sum(1 for s in population.get_all_singularities() if s.alive)
        self.pop_label.config(text=f"种群: {alive}/{total}")

    def _update_state_bars(self, singularity):
        for w in self.state_bars_frame.winfo_children():
            w.destroy()

        summaries = singularity.arch.get_state_summary(singularity.internal_state)
        if not summaries:
            tk.Label(self.state_bars_frame, text="(无内部状态)",
                     fg=COLOR_TEXT_DIM, bg=COLOR_PANEL_BG,
                     font=("Consolas", 9)).pack(anchor="w")
            return

        bar_w = 200
        for name, value, baseline in summaries:
            f = tk.Frame(self.state_bars_frame, bg=COLOR_PANEL_BG)
            f.pack(fill="x", pady=1)
            tk.Label(f, text=name, width=8, anchor="w",
                     fg=COLOR_TEXT, bg=COLOR_PANEL_BG,
                     font=("Consolas", 9)).pack(side="left")
            canvas_bar = tk.Canvas(f, width=bar_w, height=12,
                                    bg="#0a0a12", highlightthickness=0)
            canvas_bar.pack(side="left", padx=2)
            fill_w = int(bar_w * max(0, min(1, value)))
            fill_color = "#ff4466" if value < baseline * 0.5 else \
                         "#44cc88" if value > baseline * 1.5 else "#ffcc44"
            canvas_bar.create_rectangle(0, 0, fill_w, 12, fill=fill_color, outline="")
            tk.Label(f, text=f"{value:.2f}", width=5, anchor="w",
                     fg=COLOR_TEXT_DIM, bg=COLOR_PANEL_BG,
                     font=("Consolas", 8)).pack(side="left")

    def _update_npc_list(self, population):
        for w in self.npc_frame.winfo_children():
            w.destroy()

        npcs = [s for s in population.get_all_singularities() if not getattr(s, '_is_pc', False)]

        if not npcs:
            tk.Label(self.npc_frame, text="(无其他奇点)",
                     fg=COLOR_TEXT_DIM, bg=COLOR_PANEL_BG,
                     font=("Consolas", 9)).pack(anchor="w")
            return

        for s in npcs[:6]:  # 最多显示6个
            arch = getattr(s, 'archetype', '?')
            status = "●" if s.alive else "○"
            f = tk.Frame(self.npc_frame, bg=COLOR_PANEL_BG)
            f.pack(fill="x", pady=1)
            tk.Label(f, text=f"{status} NPC#{getattr(s, '_npc_id', 0)}",
                     fg="#66cc66" if s.alive else "#666",
                     bg=COLOR_PANEL_BG, font=("Consolas", 9)).pack(side="left")
            tk.Label(f, text=f"E:{s.energy:.2f}",
                     fg=COLOR_TEXT_DIM, bg=COLOR_PANEL_BG,
                     font=("Consolas", 8)).pack(side="right")

    def log_event(self, message):
        try:
            self.event_log.config(state="normal")
            self.event_log.insert("end", message + "\n")
            self.event_log.see("end")
            self.event_log.config(state="disabled")
        except:
            pass

    # === 控制 ===
    def _toggle_pause(self):
        self.paused = not self.paused

    def _step_once(self):
        self.paused = True
        if self.engine.is_running:
            self.engine.step()
            self.render_frame()

    def _reset(self):
        self.paused = True
        self.event_log.config(state="normal")
        self.event_log.delete("1.0", "end")
        self.event_log.config(state="disabled")
        self.engine.reset()
        self.render_frame()
        self.log_event("[系统] 重置完成")

    def _change_speed(self, delta):
        self.speed = max(0.25, min(5.0, self.speed + delta))
        self.speed_label.config(text=f"速度: {self.speed:.1f}x")

    def _on_key(self, event):
        k = event.keysym.lower()
        if k == "space": self._toggle_pause()
        elif k == "s": self._step_once()
        elif k == "r": self._reset()
        elif k == "q": self._on_close()
        elif k in ("plus", "equal"): self._change_speed(0.5)
        elif k == "minus": self._change_speed(-0.5)

    def _on_close(self):
        self.engine.stop()
        try: self.root.destroy()
        except: pass

    def show_run_report(self, report_text):
        top = tk.Toplevel(self.root)
        top.title("本次演化报告")
        top.configure(bg=COLOR_BG)
        top.geometry("650x550")
        text_w = tk.Text(top, bg="#08080e", fg=COLOR_TEXT,
                          font=("Consolas", 10), relief="flat", padx=10, pady=10)
        text_w.pack(fill="both", expand=True, padx=10, pady=10)
        text_w.insert("1.0", report_text)
        text_w.config(state="disabled")
        tk.Button(top, text="关闭", command=top.destroy,
                  bg=COLOR_ACCENT, fg=COLOR_TEXT, relief="flat").pack(pady=5)

    # === 主循环 ===
    def run(self):
        self.root.after(100, self._run_loop)
        self.root.mainloop()

    def _run_loop(self):
        if not hasattr(self, 'root') or not self.root.winfo_exists():
            return
        try:
            if not self.paused and self.engine.is_running:
                steps = max(1, int(self.speed * 2))
                for _ in range(steps):
                    if not self.engine.is_running:
                        break
                    self.engine.step()
                self._do_render()

                if not self.engine.is_running and self.engine.run_completed:
                    self.show_run_report(self.engine.last_report)

            delay = max(16, int(50 / self.speed))
            self.root.after(delay, self._run_loop)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.root.after(100, self._run_loop)
