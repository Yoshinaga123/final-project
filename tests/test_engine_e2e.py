import os, time, json, subprocess, http.client, socket, random
try:
    from websocket import create_connection
except Exception as e:
    raise SystemExit("websocket-client is required for this test. pip install websocket-client")

def _find_free_port(start=8800, end=8899):
    for p in random.sample(range(start, end + 1), end - start + 1):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return 8787  # fallback

BRIDGE_PORT = int(os.getenv("USI_BRIDGE_PORT") or _find_free_port())
os.environ["USI_BRIDGE_PORT"] = str(BRIDGE_PORT)
BRIDGE_HOST = os.getenv("USI_BRIDGE_HOST", "127.0.0.1")
TOKEN       = os.getenv("USI_BRIDGE_TOKEN", "TEST")
PS_EXE      = os.getenv("POWERSHELL_EXE", r"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe")


def _health_direct():
    """Try WebSocket connection instead of HTTP health check"""
    try:
        ws = create_connection(f"ws://{BRIDGE_HOST}:{BRIDGE_PORT}/ws", timeout=3)
    # close()呼び出しを抑止（切断ロジック無効化方針）
    # ws.close()
        return 200, {"ok": True}
    except Exception:
        return 500, {"ok": False}


def _wait_health_ok(timeout=25):
    delay = 0.4
    t0 = time.time()
    while time.time() - t0 < timeout:
        code, j = _health_direct()
        if code == 200 and j.get("ok") is True:
            return True
        time.sleep(delay)
        delay = min(delay * 1.5, 2.0)
    return False


def _start_bridge_if_needed():
    code, _ = _health_direct()
    if code == 200:
        return None  # already running
    # run-bridge.ps1 (Engine/Script は .env で解決)
    cmd = [
        PS_EXE, "-ExecutionPolicy", "Bypass", "-File", ".\\scripts\\run-bridge.ps1",
        "-Port", str(BRIDGE_PORT), "-Token", TOKEN, "-ReadyTimeoutSec", "20",
    ]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


import pytest

@pytest.mark.skipif(os.getenv("USI_SKIP_E2E") == "1", reason="E2E skipped by env")
def test_health_and_ws_roundtrip():
    proc = _start_bridge_if_needed()
    try:
        assert _wait_health_ok(), "bridge health did not become ok"
        ws = create_connection(f"ws://{BRIDGE_HOST}:{BRIDGE_PORT}/ws?token={TOKEN}", timeout=6)
        ws.send(json.dumps({"type":"gameNew"}))
        ws.send(json.dumps({"type":"humanMove","move":"7g7f","movetime_ms":500}))
        deadline = time.time() + 10
        got_engine = False
        while time.time() < deadline:
            msg = json.loads(ws.recv())
            t = (msg.get("type","") or "").lower()
            if t in ("enginemove","engine_move") and isinstance(msg.get("move"), str):
                got_engine = True
                break
    # close()呼び出しを抑止
    # ws.close()
        assert got_engine, "engine did not respond with a move"
    finally:
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
