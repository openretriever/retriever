"""Retriever Hub hello-world example.

    pixi run python examples/hub/hello-world.py
"""

from retriever import hub

hw = hub.use("openretriever/hello-world")
print(f"Module: {hw!r}")
print(f"Exports: {dir(hw)}")

g = hw.GreeterFlow(prefix="Hi")
inp = hw.GreeterInput(name="Nakiri Ayame")
out = g.step(inp)
print(f"Result: {out.greeting}")
