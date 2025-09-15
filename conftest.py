import os, socket, contextlib, pytest


def _random_free_port():
    with contextlib.closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="function", autouse=True)
def auto_bridge_port(monkeypatch):
    """Auto-pick a free port unless CI pins one via env vars"""
    if not os.getenv("BRIDGE_PORT") and not os.getenv("USI_BRIDGE_PORT"):
        port = _random_free_port()
        monkeypatch.setenv("USI_BRIDGE_PORT", str(port))
        print(f"[conftest] Auto-assigned bridge port: {port}")
