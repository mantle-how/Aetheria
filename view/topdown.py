from __future__ import annotations

from collections.abc import Callable
import tkinter as tk


class TopDownVisualizer:
    """
    使用 tkinter 顯示模擬世界的俯視圖。

    範例:
        viz = TopDownVisualizer(width=800, height=600)
        viz.show(entities)
    """

    FONT_FAMILY = "Microsoft JhengHei UI"
    COLOR_MAP = {
        "Agent": "#E53935",
        "InteractiveEntity": "#1E88E5",
        "Entity": "#9E9E9E",
    }
    LEGEND_LABELS = {
        "Agent": "代理人",
        "InteractiveEntity": "互動地標",
        "Entity": "一般物件",
    }

    def __init__(self, width: int = 800, height: int = 600, margin: float = 0.1):
        self.width = width
        self.height = height
        self.margin = margin
        self.scale: float | None = None

    def entity_color(self, entity) -> str:
        class_name = entity.__class__.__name__
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

        padding = 10
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
            10 + padding,
            top + 11,
            text=status_text,
            anchor="w",
            fill="#111111",
            font=(self.FONT_FAMILY, 10),
        )

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
                screen_x,
                screen_y - size,
                text=str(getattr(entity, "name", getattr(entity, "entity_id", ""))),
                anchor="s",
                fill="#111111",
                font=(self.FONT_FAMILY, 8),
            )

        self.draw_legend(canvas)
        self.draw_status(canvas, status_text)

    def _bind_navigation(self, root: tk.Tk, rerender: Callable[[], None]) -> None:
        def zoom_in(event=None):
            self.margin = max(0.0, self.margin - 0.02)
            rerender()

        def zoom_out(event=None):
            self.margin = min(0.5, self.margin + 0.02)
            rerender()

        root.bind("+", zoom_in)
        root.bind("-", zoom_out)
        root.bind("<Escape>", lambda _: root.destroy())

    def show(self, entities, title: str = "模擬世界俯視圖", status_text: str = "") -> None:
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
        title: str = "模擬世界逐步播放",
    ) -> None:
        root = tk.Tk()
        root.title(title)
        canvas = tk.Canvas(root, width=self.width, height=self.height, bg="#F0F0F0")
        canvas.pack()

        state = {
            "running": True,
            "steps": 0,
            "after_id": None,
        }

        def current_status() -> str:
            if status_provider is None:
                return ""
            return status_provider(state["running"])

        def rerender():
            self.render(canvas, get_entities(), status_text=current_status())

        def schedule_next():
            if state["running"] and state["after_id"] is None:
                state["after_id"] = root.after(interval_ms, tick)

        def tick():
            state["after_id"] = None
            if not state["running"]:
                return

            if max_steps is not None and state["steps"] >= max_steps:
                state["running"] = False
                rerender()
                return

            step_once()
            state["steps"] += 1
            rerender()
            schedule_next()

        def toggle_running(event=None):
            if state["running"]:
                state["running"] = False
                if state["after_id"] is not None:
                    root.after_cancel(state["after_id"])
                    state["after_id"] = None
            else:
                state["running"] = True
                schedule_next()
            rerender()

        def close_window():
            if state["after_id"] is not None:
                root.after_cancel(state["after_id"])
                state["after_id"] = None
            root.destroy()

        rerender()
        self._bind_navigation(root, rerender)
        root.bind("<space>", toggle_running)
        root.protocol("WM_DELETE_WINDOW", close_window)
        schedule_next()
        root.mainloop()
