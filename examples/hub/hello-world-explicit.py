"""Retriever Hub explicit export example.

    pixi run python examples/hub/hello-world-explicit.py
"""

from retriever import hub

GreeterFlow = hub.use("openretriever/hello-world:GreeterFlow")
GreeterInput = hub.use("openretriever/hello-world:GreeterInput")
GreeterOutput = hub.use("openretriever/hello-world:GreeterOutput")

greeter = GreeterFlow(prefix="Hi")
inp = GreeterInput(name="Retriever")
out = greeter.run(inp)

assert isinstance(out, GreeterOutput)
print(f"Result: {out.greeting}")
