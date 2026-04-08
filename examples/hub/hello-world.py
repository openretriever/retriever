"""Retriever Hub hello-world example.

This demonstrates whole-module import through `hub.use("org/name")`.
The returned value is a `ModuleProxy` exposing the module's declared exports.

Run:
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
