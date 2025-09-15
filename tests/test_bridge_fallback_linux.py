import os, time, json, http.client, subprocess, platform

import pytest


def _health(host: str, port: int, token: str | None = None) -> bool:
    try:
        conn = http.client.HTTPConnection(host, port, timeout=2)
        path = "/health"
        if token:
            path += f"?token={token}"
        conn.request("GET", path)
        resp = conn.getresponse()
        if resp.status != 200:
            return False
        body = resp.read()
        data = json.loads(body.decode("utf-8")) if body else {}
        return data.get("ok", True) is True
    except Exception:
        return False


@pytest.mark.skipif(platform.system() == "Windows", reason="Linux-only fallback test")
def test_bridge_starts_with_fallback_when_no_engine(tmp_path):
    env = os.environ.copy()
    env.pop("USI_ENGINE_PATH", None)  # ensure env not set
    env["USI_BRIDGE_PORT"] = "8877"  # custom to avoid collisions
    env["USI_BRIDGE_TOKEN"] = "TEST"
    env["APP_ENV"] = "development"  # allow fallback

    # start bridge script (bash)
    proc = subprocess.Popen(["bash", "./scripts/run-bridge.sh"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    try:
        # wait until health OK
        ok = False
        deadline = time.time() + 20
        while time.time() < deadline:
            if _health("127.0.0.1", 8877, "TEST"):
                ok = True
                break
            time.sleep(0.5)
        assert ok, "fallback mock did not become healthy on Linux"
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except Exception:
                proc.kill()
