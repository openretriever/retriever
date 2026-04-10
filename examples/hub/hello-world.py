"""Retriever Hub hello-world example.

Set `RETRIEVER_HUB_HELLO_WORLD_MODULE` to a published Hub module ref that exports
`GreeterFlow` and `GreeterInput`.

Run:
    RETRIEVER_HUB_HELLO_WORLD_MODULE=your-org/hello-world pixi run python examples/hub/hello-world.py
"""

import os

from retriever import hub

module_ref = os.environ.get("RETRIEVER_HUB_HELLO_WORLD_MODULE", "").strip()
if not module_ref:
    raise SystemExit(
        "Set RETRIEVER_HUB_HELLO_WORLD_MODULE to a published Hub module ref, "
        "for example 'your-org/hello-world'."
    )

hw = hub.use(module_ref)
print(f"Module: {hw!r}")
print(f"Exports: {dir(hw)}")

g = hw.GreeterFlow(prefix="Hi")
inp = hw.GreeterInput(name="Nakiri Ayame")
out = g.step(inp)
print(f"Result: {out.greeting}")
