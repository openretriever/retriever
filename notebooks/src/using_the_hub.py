# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Using the Hub
#
# The Hub loads a module export straight from its git repository at runtime.
# `hub.use("org/name:Export")` returns the actual object — a Flow class, a
# function, a type — with no PyPI wheel and no in-repo paths to reverse-engineer.
# This notebook resolves the **live** public module `openretriever/hello-world`,
# so every output below is captured from a real networked call. The only
# requirement beyond `retriever-core` is a network connection when you run it.

# %% [markdown]
# > **Running in Colab?** The next cell installs `retriever-core`. From a source
# > checkout (or once it's already installed) the install is skipped.

# %%
# Colab setup: install retriever-core only if it isn't importable yet.
try:
    import retriever  # noqa: F401
except ImportError:  # pragma: no cover
    import subprocess
    import sys

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "retriever-core"], check=True
    )

# %% [markdown]
# ## Load one export by its ref
#
# A ref is `{org}/{name}:{Export}`. Here `openretriever/hello-world` is the
# module and `HelloFlow` is one name from its export table. `hub.use` fetches the
# repo, imports it under a private namespace, and hands back the class itself —
# so you construct it and call `step()` exactly like a local Flow.

# %%
from retriever import hub

HelloFlow = hub.use("openretriever/hello-world:HelloFlow")

flow = HelloFlow()
print("returned:", HelloFlow.__name__)
print("step:", flow.step(None).text)

# %% [markdown]
# The object is real, not a proxy: `HelloFlow()` builds an instance and
# `step(None)` runs it in-process. Nothing here needed a backend or a clock.

# %% [markdown]
# ## An export can be any Python object
#
# The export table is not limited to Flows. A module can publish plain functions,
# types, or values under the same ref shape. `greet` is a function export — load
# it and call it directly.

# %%
greet = hub.use("openretriever/hello-world:greet")
print(greet("retriever"))

# %% [markdown]
# ## Load the whole module as a proxy
#
# Drop the `:attribute` and `hub.use` returns a `ModuleProxy` over the declared
# export table. `dir(proxy)` lists the exports and its repr names them, so the
# manifest — not the file tree — is the module's public surface.

# %%
mod = hub.use("openretriever/hello-world")
print("repr:", repr(mod))
print("exports:", dir(mod))
print("via proxy:", mod.HelloFlow().step(None).text)

# %% [markdown]
# A proxy exposes *only* declared exports. Reaching for a name that is not in the
# manifest raises `AttributeError` that lists what is actually available.

# %%
try:
    mod.SecretFlow
except AttributeError as exc:
    print("AttributeError:", exc)

# %% [markdown]
# ## The resolution chain, once
#
# Given a ref, the loader walks a fixed chain:
#
# 1. Parse `{org}/{name}[:attribute][@version]`.
# 2. Look up `{org}/{name}` in the Hub **index** to get the module's git repo URL.
# 3. Resolve the version to a commit — newest semver tag, or the tag you pinned.
# 4. Download that commit's tarball and cache it under `~/.retriever/hub/cache/`.
# 5. Read `[tool.retriever.module]` from the repo's `pyproject.toml` for the
#    export table, then check `min_retriever_version` and declared deps.
# 6. Import the package under a private, commit-scoped namespace and return the
#    requested export.
#
# The result is cached in-process, so a second `hub.use` of the same ref returns
# the *same* object without re-fetching.

# %%
first = hub.use("openretriever/hello-world:HelloFlow")
second = hub.use("openretriever/hello-world:HelloFlow")
print("same object cached in-process:", first is second)

from retriever.hub._ref import parse_ref

ref = parse_ref("openretriever/hello-world:HelloFlow")
print("parsed ->", f"org={ref.org} name={ref.name} attr={ref.attribute} version={ref.version}")
