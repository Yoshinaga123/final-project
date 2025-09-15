import os, platform, subprocess, time, json, sys
import pytest
import urllib.request

pytestmark = pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only")


def get_health(port=8787, timeout=0.5):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except Exception:
        return 500, {"ok": False}


def test_bridge_starts_with_fallback_when_no_engine(tmp_path):
    # Ensure no engine is provided
    os.environ.pop("USI_ENGINE_PATH", None)
    os.environ["APP_ENV"] = "development"
    os.environ["USI_BRIDGE_PORT"] = "8879"

    # Start bridge; rely on PowerShell script’s fallback to mock .bat
    ps = os.environ.get("PS_EXE", r"C:\Program Files\PowerShell\7\pwsh.exe")
    if not os.path.exists(ps):
        ps = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"

    proc = subprocess.Popen(
        [ps, "-ExecutionPolicy", "Bypass", "-File", r".\scripts\run-bridge.ps1"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    try:
        ok = False
        for _ in range(40):  # ~10s
            time.sleep(0.25)
            code, body = get_health(port=8879)
            if body.get("ok"):
                ok = True
                break
        # Dump some logs to help triage if it fails
        if not ok and proc.stdout:
            try:
                print(proc.stdout.read())
            except Exception:
                pass
        assert ok, "fallback mock did not become healthy"
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
