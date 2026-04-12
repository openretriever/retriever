"""Compatibility shim — retriever.data_spec has moved to retriever.types.data."""
from retriever.types.data import *  # noqa: F401, F403
from retriever.types.data import __all__
