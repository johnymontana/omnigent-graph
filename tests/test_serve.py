from types import SimpleNamespace

import pytest

from omnigent_neo4j_memory import serve


def _args(**over):
    base = dict(host="0.0.0.0", port="8000", transport="sse", profile="extended", extra=[])
    base.update(over)
    return SimpleNamespace(**base)


def test_backend_is_nams_when_key_present(monkeypatch):
    monkeypatch.setenv("MEMORY_API_KEY", "nams_test")
    assert serve.resolve_backend() == "nams"


def test_backend_is_local_without_key(monkeypatch):
    monkeypatch.delenv("MEMORY_API_KEY", raising=False)
    assert serve.resolve_backend() == "local"


def test_nams_command_has_no_password(monkeypatch):
    monkeypatch.setenv("MEMORY_API_KEY", "nams_test")
    cmd = serve.build_serve_command(_args())
    assert "--password" not in cmd
    assert "mcp" in cmd and "serve" in cmd
    assert "--transport" in cmd and "sse" in cmd


def test_local_command_requires_password(monkeypatch):
    monkeypatch.delenv("MEMORY_API_KEY", raising=False)
    monkeypatch.delenv("NAM_NEO4J__PASSWORD", raising=False)
    with pytest.raises(SystemExit):
        serve.build_serve_command(_args(), strict=True)


def test_local_command_includes_password(monkeypatch):
    monkeypatch.delenv("MEMORY_API_KEY", raising=False)
    monkeypatch.setenv("NAM_NEO4J__PASSWORD", "secret")
    cmd = serve.build_serve_command(_args())
    assert "--password" in cmd and "secret" in cmd
    # …but the redacted form must not leak it.
    assert "secret" not in serve._redact(cmd)


def test_host_omitted_when_empty(monkeypatch):
    monkeypatch.setenv("MEMORY_API_KEY", "nams_test")
    cmd = serve.build_serve_command(_args(host=""))
    assert "--host" not in cmd


def test_print_cmd_tolerates_missing_password(monkeypatch):
    # The CI smoke runs `serve --print-cmd` with no creds; it must not raise.
    monkeypatch.delenv("MEMORY_API_KEY", raising=False)
    monkeypatch.delenv("NAM_NEO4J__PASSWORD", raising=False)
    assert serve.main(["serve", "--print-cmd"]) == 0
