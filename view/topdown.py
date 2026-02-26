import tkinter as tk
from model.test import Agent, InteractiveEntity, Entity


class TopDownVisualizer:
    """
    簡易的上帝視角視覺化器（tkinter）。

    用法:
        viz = TopDownVisualizer(width=800, height=600)
        viz.show(entities)
    """

    COLOR_MAP = {
        'Agent': '#E53935',  # 紅色
        'InteractiveEntity': '#1E88E5',  # 藍色
        'Entity': '#9E9E9E',  # 灰色
    }

    def __init__(self, width=800, height=600, margin=0.1):
        self.width = width
        self.height = height
        self.margin = margin
        self.scale = None
        self.offset_x = 0
        self.offset_y = 0

    def entity_color(self, entity):
        name = entity.__class__.__name__
        return self.COLOR_MAP.get(name, '#777777')

    def compute_bounds(self, entities):
        if not entities:
            return (0, 10, 0, 10)
        xs = [e.x for e in entities]
        ys = [e.y for e in entities]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        # If all entities have same coord, expand bounds slightly
        if min_x == max_x:
            min_x -= 1
            max_x += 1
        if min_y == max_y:
            min_y -= 1
            max_y += 1
        # add margin
        dx = max_x - min_x
        dy = max_y - min_y
        min_x -= dx * self.margin
        max_x += dx * self.margin
        min_y -= dy * self.margin
        max_y += dy * self.margin
        return (min_x, max_x, min_y, max_y)

    def world_to_screen(self, x, y, bounds):
        min_x, max_x, min_y, max_y = bounds
        world_w = max_x - min_x
        world_h = max_y - min_y
        # compute scale to fit world into canvas
        scale_x = (self.width - 20) / world_w
        scale_y = (self.height - 20) / world_h
        scale = min(scale_x, scale_y)
        self.scale = scale
        # compute offsets to center
        px = (x - min_x) * scale + 10
        # flip y: world y up -> screen y down
        py = self.height - (y - min_y) * scale - 10
        return (px, py)

    def draw_legend(self, canvas):
        padding = 8
        x = self.width - 150
        y = 10
        canvas.create_rectangle(x - 6, y - 6, self.width - 6, y + 110, fill='#FFFFFF', outline='#000000')
        oy = y
        for cls_name, color in self.COLOR_MAP.items():
            canvas.create_rectangle(x, oy, x + 16, oy + 16, fill=color, outline='#222222')
            canvas.create_text(x + 24, oy + 8, text=cls_name, anchor='w', fill='#000000', font=('Arial', 10))
            oy += 22

    def render(self, canvas, entities):
        canvas.delete('all')
        bounds = self.compute_bounds(entities)
        # draw grid lines (optional)
        min_x, max_x, min_y, max_y = bounds
        # draw entities
        for e in entities:
            x, y = e.x, e.y
            sx, sy = self.world_to_screen(x, y, bounds)
            size = max(6, min(20, int(self.scale * 0.5)))
            color = self.entity_color(e)
            canvas.create_rectangle(sx - size / 2, sy - size / 2, sx + size / 2, sy + size / 2,
                                    fill=color, outline='#222222')
            # optional: draw id or name
            canvas.create_text(sx, sy - size, text=str(getattr(e, 'name', getattr(e, 'entity_id', ''))),
                               anchor='s', fill='#111111', font=('Arial', 8))
        # legend
        self.draw_legend(canvas)

    def show(self, entities):
        root = tk.Tk()
        root.title('Top-down Visualizer')
        canvas = tk.Canvas(root, width=self.width, height=self.height, bg='#F0F0F0')
        canvas.pack()

        def _render():
            self.render(canvas, entities)
            # no auto-refresh by default

        _render()

        # key bindings for zoom
        def zoom_in(event=None):
            # increase margins slightly to zoom out effect by changing margin
            self.margin = max(0.0, self.margin - 0.02)
            _render()

        def zoom_out(event=None):
            self.margin = min(0.5, self.margin + 0.02)
            _render()

        root.bind('+', zoom_in)
        root.bind('-', zoom_out)
        root.bind('<Escape>', lambda e: root.destroy())

        root.mainloop()

