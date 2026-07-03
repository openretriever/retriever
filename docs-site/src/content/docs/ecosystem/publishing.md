---
title: Publishing
---

# Publishing

Publish Hub modules only after the boundary is stable.

Checklist:

- imports are lightweight and safe at module import time
- heavy resources are loaded lazily inside runtime-local hooks
- public payload types are documented
- exported Flow classes and factories have stable names
- examples show the smallest runnable usage
- version metadata explains compatibility

The goal is reuse without forcing downstream projects to copy private application code.
