from __future__ import annotations

from pathlib import Path
import sys


if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from model.config import LoggingConfig, SimulationConfig
from model.test import build_demo_simulation, simulation_to_entities
from view.topdown import TopDownVisualizer

TARGET_FPS = 5
FRAME_INTERVAL_MS = 1000 // TARGET_FPS


def main() -> None:
    config = SimulationConfig(logging=LoggingConfig(print_to_stdout=False))
    simulation = build_demo_simulation(config)
    visualizer = TopDownVisualizer(width=900, height=700)

    def get_entities():
        return simulation_to_entities(simulation)

    def step_once():
        simulation.step()

    def status_text(is_running: bool) -> str:
        minute_of_day = simulation.world.minute_of_day
        hour = minute_of_day // 60
        minute = minute_of_day % 60
        state_label = "播放中" if is_running else "已暫停"
        return (
            f"步次: {simulation.world.tick_count:03d}  "
            f"時間: {hour:02d}:{minute:02d}  "
            f"狀態: {state_label}  "
            "操作: 空白鍵播放/暫停, +/- 縮放, Esc 關閉主視窗。"
            "另有代理人需求即時線圖視窗會同步更新。"
        )

    visualizer.show_live(
        get_entities=get_entities,
        step_once=step_once,
        status_provider=status_text,
        interval_ms=FRAME_INTERVAL_MS,
    )


if __name__ == "__main__":
    main()
