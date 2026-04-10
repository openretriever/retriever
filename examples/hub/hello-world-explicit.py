"""Retriever Hub explicit export example.

Set `RETRIEVER_HUB_HELLO_WORLD_MODULE` to a published Hub module ref that exports
`GreeterFlow`, `GreeterInput`, and `GreeterOutput`.

Run:
    RETRIEVER_HUB_HELLO_WORLD_MODULE=your-org/hello-world pixi run python examples/hub/hello-world-explicit.py
"""

import os

from retriever import hub

module_ref = os.environ.get("RETRIEVER_HUB_HELLO_WORLD_MODULE", "").strip()
if not module_ref:
    raise SystemExit(
        "Set RETRIEVER_HUB_HELLO_WORLD_MODULE to a published Hub module ref, "
        "for example 'your-org/hello-world'."
    )

GreeterFlow = hub.use(f"{module_ref}:GreeterFlow")
GreeterInput = hub.use(f"{module_ref}:GreeterInput")
GreeterOutput = hub.use(f"{module_ref}:GreeterOutput")

greeter = GreeterFlow(prefix="Hi")
inp = GreeterInput(name="Retriever")
out = greeter.step(inp)

assert isinstance(out, GreeterOutput)
print(f"Result: {out.greeting}")
