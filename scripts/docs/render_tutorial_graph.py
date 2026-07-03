"""Render tutorial pipeline visualizations used by the public docs."""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _render_perception(out: Path) -> Path:
    from examples.shared.perception_flows import build_tutorial_perception_pipeline

    path = build_tutorial_perception_pipeline(
        use_real_camera=False,
        show_window=False,
    ).visualize(str(out))
    return Path(path)


def _render_composable(out: Path) -> Path:
    mod = importlib.import_module("examples.tutorial.g_operations_interfaces.06_composable_pipelines")
    path = mod.build_outer_composable_counter().visualize(str(out))
    return Path(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "kind",
        choices=("perception", "composable"),
        help="Tutorial graph to render.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output HTML path. Defaults to artifacts/<kind>.html.",
    )
    args = parser.parse_args()

    out = args.out or Path("artifacts") / f"tutorial_{args.kind}.html"
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.kind == "perception":
        rendered = _render_perception(out)
    else:
        rendered = _render_composable(out)

    print(rendered)


if __name__ == "__main__":
    main()
