"""
Shared multiprocessing context for the MP backend.

The backend uses `fork` (where available) so authored Flow instances cross
into worker processes without pickling. Requesting it through a dedicated
context — instead of `multiprocessing.set_start_method(..., force=True)` —
keeps importing retriever free of side effects on the host application's
global multiprocessing configuration.
"""

import multiprocessing
import sys

if sys.platform == 'win32':
    MP_CTX = multiprocessing.get_context('spawn')
else:
    MP_CTX = multiprocessing.get_context('fork')
