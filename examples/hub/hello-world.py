"""Retriever Hub hello-world example.

This demonstrates whole-module import through `hub.use("org/name")`.
The returned value is a `ModuleProxy` exposing the module's declared exports.

Set `RETRIEVER_HUB_HELLO_WORLD_MODULE` to a module available in your index
before running this example.

Run:
    RETRIEVER_HUB_HELLO_WORLD_MODULE=company-abc/hello-world     pixi run python examples/hub/hello-world.py
"""

from __future__ import annotations

import os

from retriever import hub

MODULE_REF = os.environ.get('RETRIEVER_HUB_HELLO_WORLD_MODULE', '').strip()
if not MODULE_REF:
    raise SystemExit(
        'Set RETRIEVER_HUB_HELLO_WORLD_MODULE=org/module before running this example.'
    )

hw = hub.use(MODULE_REF)
print(f'Module: {hw!r}')
print(f'Exports: {dir(hw)}')

g = hw.GreeterFlow(prefix='Hi')
inp = hw.GreeterInput(name='Nakiri Ayame')
out = g.step(inp)
print(f'Result: {out.greeting}')
