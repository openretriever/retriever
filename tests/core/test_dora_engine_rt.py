from __future__ import annotations


def test_dora_engine_retries_up_when_fresh_runtime_requested(monkeypatch) -> None:
    from subprocess import CompletedProcess
    from types import SimpleNamespace

    from retriever.rt.backend.dora.engine import DoraEngine

    calls: list[tuple[str, ...]] = []
    up_attempts = {"count": 0}

    def fake_run(cmd, capture_output=True, text=True, timeout=None, cwd=None):
        cmd = tuple(cmd)
        calls.append(cmd)
        if cmd == ("dora", "up"):
            up_attempts["count"] += 1
            if up_attempts["count"] < 3:
                return CompletedProcess(cmd, 1, stdout="", stderr="not ready")
            return CompletedProcess(cmd, 0, stdout="ok", stderr="")
        if cmd == ("dora", "check"):
            return CompletedProcess(cmd, 0, stdout="ready", stderr="")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr("retriever.rt.backend.dora.engine.subprocess.run", fake_run)
    monkeypatch.setattr("retriever.rt.backend.dora.engine.time.sleep", lambda _s: None)

    engine = DoraEngine(SimpleNamespace(metadata=SimpleNamespace(name="demo")), config={"dora_fresh": True})
    monkeypatch.setattr(engine, "_destroy_dora_runtime", lambda: None)

    engine._start_dora_runtime(timeout=1.0)

    assert up_attempts["count"] == 3
    assert calls[:3] == [("dora", "up"), ("dora", "up"), ("dora", "up")]
    assert calls[-1] == ("dora", "check")
