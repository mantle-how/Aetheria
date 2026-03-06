from __future__ import annotations

"""Legacy Tkinter visualizer (deprecated). Use Web UI at apps.api.main instead."""

from collections.abc import Callable, Hashable
import threading
import time
import tkinter as tk


class TopDownVisualizer:
    """
    使用 tkinter 的俯視圖視覺化工具。

    live 模式會同步開啟：
    - 上帝視角俯視圖
    - 代理人儀表板（需求線圖 + 生命值 HP）
    """

    FONT_FAMILY = "Microsoft JhengHei UI"

    COLOR_MAP = {
        "Agent": "#E53935",
        "InteractiveEntity": "#1E88E5",
        "Entity": "#9E9E9E",
    }
    LEGEND_LABELS = {
        "Agent": "代理人",
        "InteractiveEntity": "互動地點",
        "Entity": "一般實體",
    }

    NEED_COLORS = {
        "hunger": "#FB8C00",
        "energy": "#43A047",
        "mood": "#3949AB",
    }
    NEED_LABELS = {
        "hunger": "飢餓",
        "energy": "精力",
        "mood": "心情",
    }

    ACTION_LABELS = {
        "move": "移動",
        "eat": "進食",
        "rest": "休息",
        "work": "工作",
        "socialize": "社交",
        "idle": "待機",
    }

    DASHBOARD_WIDTH = 840
    DASHBOARD_MIN_CARD_WIDTH = 360
    DASHBOARD_CARD_HEIGHT = 190
    DASHBOARD_GAP = 12
    DASHBOARD_OUTER_MARGIN = 16
    DASHBOARD_ROWS_PER_COLUMN = 5
    CHART_HISTORY_LIMIT = 60
    LIVE_UI_REFRESH_MS = 33
    DASHBOARD_RENDER_EVERY = 3

    def __init__(self, width: int = 800, height: int = 600, margin: float = 0.1):
        self.width = width
        self.height = height
        self.margin = margin
        self.scale: float | None = None

    def entity_color(self, entity) -> str:
        class_name = entity.__class__.__name__
        if class_name == "ABMAgent":
            class_name = "Agent"
        return self.COLOR_MAP.get(class_name, "#777777")

    def compute_bounds(self, entities) -> tuple[float, float, float, float]:
        if not entities:
            return (0.0, 10.0, 0.0, 10.0)

        xs = [entity.x for entity in entities]
        ys = [entity.y for entity in entities]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        if min_x == max_x:
            min_x -= 1
            max_x += 1
        if min_y == max_y:
            min_y -= 1
            max_y += 1

        width = max_x - min_x
        height = max_y - min_y
        min_x -= width * self.margin
        max_x += width * self.margin
        min_y -= height * self.margin
        max_y += height * self.margin
        return (min_x, max_x, min_y, max_y)

    def world_to_screen(
        self,
        x: float,
        y: float,
        bounds: tuple[float, float, float, float],
    ) -> tuple[float, float]:
        min_x, max_x, min_y, max_y = bounds
        world_w = max_x - min_x
        world_h = max_y - min_y

        scale_x = (self.width - 20) / world_w
        scale_y = (self.height - 20) / world_h
        self.scale = min(scale_x, scale_y)

        px = (x - min_x) * self.scale + 10
        py = self.height - (y - min_y) * self.scale - 10
        return (px, py)

    def draw_legend(self, canvas: tk.Canvas) -> None:
        legend_width = 150
        legend_height = 32 + len(self.COLOR_MAP) * 22
        x = self.width - legend_width
        y = 10

        canvas.create_rectangle(
            x - 6,
            y - 6,
            self.width - 6,
            y + legend_height,
            fill="#FFFFFF",
            outline="#000000",
        )

        offset_y = y
        for class_name, color in self.COLOR_MAP.items():
            canvas.create_rectangle(x, offset_y, x + 16, offset_y + 16, fill=color, outline="#222222")
            canvas.create_text(
                x + 24,
                offset_y + 8,
                text=self.LEGEND_LABELS.get(class_name, class_name),
                anchor="w",
                fill="#000000",
                font=(self.FONT_FAMILY, 10),
            )
            offset_y += 22

    def draw_status(self, canvas: tk.Canvas, status_text: str) -> None:
        if not status_text:
            return

        top = self.height - 42
        canvas.create_rectangle(
            10,
            top,
            self.width - 10,
            self.height - 10,
            fill="#FFFFFF",
            outline="#000000",
        )
        canvas.create_text(
            20,
            top + 11,
            text=status_text,
            anchor="w",
            fill="#111111",
            font=(self.FONT_FAMILY, 10),
        )

    def _entity_label(self, entity) -> str:
        name = str(getattr(entity, "name", getattr(entity, "entity_id", "")))
        action = getattr(getattr(entity, "last_action", None), "value", None)
        if action is None:
            return name
        action_text = self.ACTION_LABELS.get(str(action), str(action))
        return f"{name} {action_text}"

    def render(self, canvas: tk.Canvas, entities, status_text: str = "") -> None:
        canvas.delete("all")
        bounds = self.compute_bounds(entities)

        for entity in entities:
            screen_x, screen_y = self.world_to_screen(entity.x, entity.y, bounds)
            size = max(6, min(20, int((self.scale or 1.0) * 0.5)))
            color = self.entity_color(entity)
            canvas.create_rectangle(
                screen_x - size / 2,
                screen_y - size / 2,
                screen_x + size / 2,
                screen_y + size / 2,
                fill=color,
                outline="#222222",
            )
            canvas.create_text(
                screen_x + size + 4,
                screen_y - size - 2,
                text=self._entity_label(entity),
                anchor="sw",
                fill="#111111",
                font=(self.FONT_FAMILY, 10, "bold"),
            )

        self.draw_legend(canvas)
        self.draw_status(canvas, status_text)

    def _bind_navigation(self, root: tk.Misc, rerender: Callable[[], None]) -> None:
        def zoom_in(event=None):
            self.margin = max(0.0, self.margin - 0.02)
            rerender()

        def zoom_out(event=None):
            self.margin = min(0.5, self.margin + 0.02)
            rerender()

        root.bind("+", zoom_in)
        root.bind("-", zoom_out)
        root.bind("<Escape>", lambda _: root.destroy())

    def _agent_entities(self, entities) -> list:
        return sorted(
            [
                entity
                for entity in entities
                if hasattr(entity, "entity_id") and hasattr(getattr(entity, "needs", None), "as_dict")
            ],
            key=lambda entity: getattr(entity, "entity_id", 0),
        )

    def _record_agent_history(
        self,
        entities,
        history: dict[int, list[tuple[Hashable, dict[str, float]]]],
        frame_key: Hashable,
    ) -> list:
        agents = self._agent_entities(entities)
        active_ids = {int(getattr(agent, "entity_id")) for agent in agents}

        for obsolete_id in list(history):
            if obsolete_id not in active_ids:
                del history[obsolete_id]

        for agent in agents:
            agent_id = int(getattr(agent, "entity_id"))
            snapshot = agent.needs.as_dict()
            series = history.setdefault(agent_id, [])

            if series and series[-1][0] == frame_key:
                series[-1] = (frame_key, snapshot)
            else:
                series.append((frame_key, snapshot))
                if len(series) > self.CHART_HISTORY_LIMIT:
                    del series[:-self.CHART_HISTORY_LIMIT]

        return agents

    def _current_need_bounds(
        self,
        history: dict[int, list[tuple[Hashable, dict[str, float]]]],
    ) -> tuple[float, float]:
        minimum = 0.0
        maximum = 100.0

        for series in history.values():
            for _, snapshot in series:
                for value in snapshot.values():
                    numeric = float(value)
                    minimum = min(minimum, numeric)
                    maximum = max(maximum, numeric)

        if minimum == maximum:
            maximum = minimum + 1.0
        return minimum, maximum

    def _flatten_points(self, points: list[tuple[float, float]]) -> list[float]:
        flattened: list[float] = []
        for x, y in points:
            flattened.extend((x, y))
        return flattened

    def _create_scroll_window(
        self,
        root: tk.Tk,
        title: str,
        width: int,
        height: int,
        background: str = "#FAFAFA",
    ) -> tuple[tk.Toplevel, tk.Canvas]:
        window = tk.Toplevel(root)
        window.title(title)

        container = tk.Frame(window)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(
            container,
            width=width,
            height=height,
            bg=background,
            highlightthickness=0,
        )
        vertical_scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        horizontal_scrollbar = tk.Scrollbar(window, orient="horizontal", command=canvas.xview)
        canvas.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )

        canvas.pack(side="left", fill="both", expand=True)
        vertical_scrollbar.pack(side="right", fill="y")
        horizontal_scrollbar.pack(side="bottom", fill="x")

        def on_mousewheel(event):
            canvas.yview_scroll(int(-event.delta / 120), "units")

        canvas.bind("<MouseWheel>", on_mousewheel)
        return window, canvas

    def _dashboard_columns(self, agent_count: int) -> int:
        count = max(1, agent_count)
        rows_per_column = max(1, self.DASHBOARD_ROWS_PER_COLUMN)
        return max(1, (count + rows_per_column - 1) // rows_per_column)

    def render_dashboard(
        self,
        canvas: tk.Canvas,
        agents,
        history: dict[int, list[tuple[Hashable, dict[str, float]]]],
    ) -> None:
        canvas.delete("all")

        if not agents:
            canvas.create_text(
                20,
                20,
                text="目前沒有可顯示的代理人儀表板資料。",
                anchor="nw",
                fill="#333333",
                font=(self.FONT_FAMILY, 11),
            )
            return

        columns = self._dashboard_columns(len(agents))
        rows = min(len(agents), self.DASHBOARD_ROWS_PER_COLUMN)
        card_width = float(self.DASHBOARD_MIN_CARD_WIDTH)
        total_width = (
            (self.DASHBOARD_OUTER_MARGIN * 2)
            + (columns * card_width)
            + max(0, columns - 1) * self.DASHBOARD_GAP
        )
        total_height = 60 + rows * (self.DASHBOARD_CARD_HEIGHT + self.DASHBOARD_GAP)
        canvas.configure(scrollregion=(0, 0, total_width, total_height))

        canvas.create_text(
            18,
            16,
            text="代理人儀表板（需求線圖 + 生命值 HP）",
            anchor="nw",
            fill="#111111",
            font=(self.FONT_FAMILY, 12, "bold"),
        )

        legend_x = 18
        legend_y = 34
        for index, (key, color) in enumerate(self.NEED_COLORS.items()):
            item_x = legend_x + index * 72
            canvas.create_line(item_x, legend_y + 7, item_x + 18, legend_y + 7, fill=color, width=3)
            canvas.create_text(
                item_x + 24,
                legend_y + 7,
                text=self.NEED_LABELS[key],
                anchor="w",
                fill="#333333",
                font=(self.FONT_FAMILY, 9),
            )

        value_min, value_max = self._current_need_bounds(history)
        value_span = value_max - value_min
        if value_span <= 0:
            value_span = 1.0

        for index, agent in enumerate(agents):
            column = index // self.DASHBOARD_ROWS_PER_COLUMN
            row = index % self.DASHBOARD_ROWS_PER_COLUMN

            left = self.DASHBOARD_OUTER_MARGIN + column * (card_width + self.DASHBOARD_GAP)
            top = 46 + row * (self.DASHBOARD_CARD_HEIGHT + self.DASHBOARD_GAP)
            right = left + card_width
            bottom = top + self.DASHBOARD_CARD_HEIGHT

            card_left = left + 10
            card_right = right - 10
            hp_bar_top = top + 34
            hp_bar_bottom = top + 50
            plot_top = top + 64
            plot_bottom = bottom - 16
            plot_height = plot_bottom - plot_top

            agent_id = int(getattr(agent, "entity_id"))
            name = str(getattr(agent, "name", f"Agent {agent_id}"))
            current_needs = agent.needs.as_dict()
            health = float(getattr(agent, "health", 0.0))
            alive = bool(getattr(agent, "is_alive", True))
            alive_text = "存活" if alive else "死亡"
            action_value = getattr(getattr(agent, "last_action", None), "value", None)
            action_text = "-" if action_value is None else self.ACTION_LABELS.get(str(action_value), str(action_value))
            series = history.get(agent_id, [])

            canvas.create_rectangle(left, top, right, bottom, fill="#FFFFFF", outline="#CBD5E1")
            canvas.create_text(
                card_left,
                top + 14,
                text=f"{name} (#{agent_id})",
                anchor="w",
                fill="#111111",
                font=(self.FONT_FAMILY, 10, "bold"),
            )
            canvas.create_text(
                card_right,
                top + 14,
                text=f"動作: {action_text}  HP: {health:.2f}  狀態: {alive_text}",
                anchor="e",
                fill="#475569",
                font=(self.FONT_FAMILY, 9),
            )

            canvas.create_text(
                card_left,
                hp_bar_top - 10,
                text="生命值 HP",
                anchor="w",
                fill="#6B7280",
                font=(self.FONT_FAMILY, 8),
            )
            canvas.create_rectangle(
                card_left,
                hp_bar_top,
                card_right,
                hp_bar_bottom,
                fill="#EDF2F7",
                outline="#D7DCE3",
            )

            hp_ratio = max(0.0, min(1.0, health / 100.0))
            fill_width = (card_right - card_left) * hp_ratio
            if fill_width > 0:
                if hp_ratio >= 0.6:
                    hp_color = "#22C55E"
                elif hp_ratio >= 0.3:
                    hp_color = "#F59E0B"
                else:
                    hp_color = "#EF4444"
                canvas.create_rectangle(
                    card_left,
                    hp_bar_top,
                    card_left + fill_width,
                    hp_bar_bottom,
                    fill=hp_color,
                    outline=hp_color,
                )

            canvas.create_rectangle(
                card_left,
                plot_top,
                card_right,
                plot_bottom,
                fill="#F8FAFC",
                outline="#DEE3EA",
            )

            grid_lines = (
                (0.0, value_min),
                (0.5, value_min + value_span * 0.5),
                (1.0, value_max),
            )
            for ratio, label in grid_lines:
                y = plot_bottom - (plot_height * ratio)
                canvas.create_line(card_left, y, card_right, y, fill="#E6EAF0", dash=(2, 4))
                canvas.create_text(
                    card_left - 5,
                    y,
                    text=f"{label:.2f}",
                    anchor="e",
                    fill="#7A8088",
                    font=(self.FONT_FAMILY, 8),
                )

            if series:
                plot_series = series[-self.CHART_HISTORY_LIMIT :]
                series_count = len(plot_series)

                for need_key, color in self.NEED_COLORS.items():
                    points: list[tuple[float, float]] = []
                    for offset, (_, snapshot) in enumerate(plot_series):
                        if series_count == 1:
                            x = (card_left + card_right) / 2
                        else:
                            x = card_left + ((card_right - card_left) * offset / (series_count - 1))

                        value = float(snapshot.get(need_key, value_min))
                        normalized = (value - value_min) / value_span
                        y = plot_bottom - (plot_height * normalized)
                        points.append((x, y))

                    if len(points) == 1:
                        x, y = points[0]
                        canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=color, outline=color)
                    else:
                        canvas.create_line(*self._flatten_points(points), fill=color, width=2.0, smooth=False)
            else:
                canvas.create_text(
                    (card_left + card_right) / 2,
                    (plot_top + plot_bottom) / 2,
                    text="尚無歷史資料",
                    fill="#7A8088",
                    font=(self.FONT_FAMILY, 9),
                )

            canvas.create_text(
                card_left,
                plot_top + 10,
                text=(
                    f"飢餓 {current_needs['hunger']:6.2f}  "
                    f"精力 {current_needs['energy']:6.2f}  "
                    f"心情 {current_needs['mood']:6.2f}"
                ),
                anchor="nw",
                fill="#475569",
                font=(self.FONT_FAMILY, 8),
            )

    def show(self, entities, title: str = "俯視圖", status_text: str = "") -> None:
        root = tk.Tk()
        root.title(title)
        canvas = tk.Canvas(root, width=self.width, height=self.height, bg="#F0F0F0")
        canvas.pack()

        def rerender():
            self.render(canvas, entities, status_text=status_text)

        rerender()
        self._bind_navigation(root, rerender)
        root.mainloop()

    def show_live(
        self,
        get_entities: Callable[[], list],
        step_once: Callable[[], None],
        status_provider: Callable[[bool], str] | None = None,
        interval_ms: int = 500,
        max_steps: int | None = None,
        title: str = "俯視圖即時播放",
    ) -> None:
        root = tk.Tk()
        root.title(title)
        canvas = tk.Canvas(root, width=self.width, height=self.height, bg="#F0F0F0")
        canvas.pack()

        simulation_lock = threading.Lock()
        state_lock = threading.Lock()
        stop_event = threading.Event()

        def safe_get_entities():
            with simulation_lock:
                return get_entities()

        def safe_step_once():
            with simulation_lock:
                step_once()

        initial_entities = safe_get_entities()
        initial_agents = self._agent_entities(initial_entities)
        rows = min(max(1, len(initial_agents)), self.DASHBOARD_ROWS_PER_COLUMN)
        dashboard_height = min(760, 80 + rows * (self.DASHBOARD_CARD_HEIGHT + self.DASHBOARD_GAP))
        dashboard_window, dashboard_canvas = self._create_scroll_window(
            root=root,
            title="代理人儀表板",
            width=self.DASHBOARD_WIDTH,
            height=dashboard_height,
            background="#F8FAFC",
        )

        agent_history: dict[int, list[tuple[Hashable, dict[str, float]]]] = {}

        state = {
            "running": True,
            "steps": 0,
            "render_count": 0,
            "after_id": None,
            "worker_thread": None,
            "dashboard_window": dashboard_window,
            "dashboard_canvas": dashboard_canvas,
        }
        tick_interval_seconds = max(0.001, interval_ms / 1000.0)
        ui_interval_ms = max(16, min(66, self.LIVE_UI_REFRESH_MS))

        def read_running() -> bool:
            with state_lock:
                return bool(state["running"])

        def read_steps() -> int:
            with state_lock:
                return int(state["steps"])

        def current_status() -> str:
            if status_provider is None:
                return ""
            is_running = read_running()
            with simulation_lock:
                return status_provider(is_running)

        def simulation_loop() -> None:
            next_tick_time = time.perf_counter()
            while not stop_event.is_set():
                if not read_running():
                    next_tick_time = time.perf_counter()
                    time.sleep(0.01)
                    continue

                if max_steps is not None and read_steps() >= max_steps:
                    with state_lock:
                        state["running"] = False
                    continue

                safe_step_once()
                with state_lock:
                    state["steps"] += 1
                    reached_limit = max_steps is not None and state["steps"] >= max_steps
                    if reached_limit:
                        state["running"] = False

                next_tick_time += tick_interval_seconds
                sleep_for = next_tick_time - time.perf_counter()
                if sleep_for > 0:
                    time.sleep(min(sleep_for, 0.02))
                else:
                    next_tick_time = time.perf_counter()

        def rerender(force_dashboard: bool = False):
            entities = safe_get_entities()
            self.render(canvas, entities, status_text=current_status())
            step_key = read_steps()
            agents = self._record_agent_history(entities, agent_history, step_key)
            with state_lock:
                state["render_count"] += 1
                render_count = state["render_count"]

            should_render_dashboard = force_dashboard or (
                render_count % self.DASHBOARD_RENDER_EVERY == 0
            )
            if state["dashboard_canvas"] is not None and should_render_dashboard:
                self.render_dashboard(state["dashboard_canvas"], agents, agent_history)

        def schedule_next():
            with state_lock:
                if state["after_id"] is None and not stop_event.is_set():
                    state["after_id"] = root.after(ui_interval_ms, tick)

        def tick():
            with state_lock:
                state["after_id"] = None
            rerender()
            schedule_next()

        def toggle_running(event=None):
            with state_lock:
                state["running"] = not state["running"]
            rerender(force_dashboard=True)

        def close_dashboard_window():
            if state["dashboard_window"] is None:
                return
            state["dashboard_window"].destroy()
            state["dashboard_window"] = None
            state["dashboard_canvas"] = None

        def close_window():
            stop_event.set()
            with state_lock:
                after_id = state["after_id"]
                state["after_id"] = None
            if after_id is not None:
                root.after_cancel(after_id)

            worker_thread = state["worker_thread"]
            if worker_thread is not None and worker_thread.is_alive():
                worker_thread.join(timeout=1.0)

            if state["dashboard_window"] is not None:
                state["dashboard_window"].destroy()
                state["dashboard_window"] = None
                state["dashboard_canvas"] = None
            root.destroy()

        worker_thread = threading.Thread(
            target=simulation_loop,
            name="simulation-loop",
            daemon=True,
        )
        state["worker_thread"] = worker_thread
        worker_thread.start()

        rerender(force_dashboard=True)
        self._bind_navigation(root, rerender)
        root.bind("<Escape>", lambda _: close_window())
        root.bind("<space>", toggle_running)
        root.protocol("WM_DELETE_WINDOW", close_window)

        dashboard_window.bind("<space>", toggle_running)
        dashboard_window.bind("<Escape>", lambda _: close_dashboard_window())
        dashboard_window.protocol("WM_DELETE_WINDOW", close_dashboard_window)

        schedule_next()
        root.mainloop()
