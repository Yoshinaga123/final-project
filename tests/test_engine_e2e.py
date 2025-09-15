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
    except Exception as e:
        print(f"[DEBUG] Health check failed: {e}")
        return 500, {"ok": False, "error": str(e)}


def _wait_health_ok(timeout=25):
    delay = 0.4
    t0 = time.time()
    attempts = 0
    while time.time() - t0 < timeout:
        attempts += 1
        code, j = _health_direct()
        print(f"[DEBUG] Health check attempt {attempts}: code={code}, response={j}")
        if code == 200 and j.get("ok") is True:
            print(f"[DEBUG] Bridge health OK after {attempts} attempts in {time.time() - t0:.1f}s")
            return True
        time.sleep(delay)
        delay = min(delay * 1.5, 2.0)
    print(f"[DEBUG] Bridge health failed after {attempts} attempts in {timeout}s")
    return False


def _start_bridge_if_needed():
    code, j = _health_direct()
    print(f"[DEBUG] Initial health check: code={code}, response={j}")
    if code == 200:
        print("[DEBUG] Bridge already running")
        return None  # already running
    # run-bridge.ps1 (Engine/Script は .env で解決)
    cmd = [
        PS_EXE, "-ExecutionPolicy", "Bypass", "-File", ".\\scripts\\run-bridge.ps1",
        "-Port", str(BRIDGE_PORT), "-Token", TOKEN, "-ReadyTimeoutSec", "20",
    ]
    print(f"[DEBUG] Starting bridge with command: {' '.join(cmd)}")
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        print(f"[DEBUG] Bridge process started with PID: {proc.pid}")
        # Give it more time to start and capture output
        time.sleep(5)
        if proc.poll() is not None:
            stdout, _ = proc.communicate()
            print(f"[DEBUG] Bridge process exited early with code {proc.returncode}")
            print(f"[DEBUG] Bridge output: {stdout}")
            return None
        else:
            print("[DEBUG] Bridge process still running after 5s, checking health")
            return proc
    except Exception as e:
        print(f"[DEBUG] Failed to start bridge: {e}")
        return None


import pytest

@pytest.mark.skipif(os.getenv("USI_SKIP_E2E") == "1", reason="E2E skipped by env")
def test_health_and_ws_roundtrip():
    print(f"[DEBUG] Starting E2E test - Host: {BRIDGE_HOST}, Port: {BRIDGE_PORT}, Token: {TOKEN}")
    print(f"[DEBUG] PowerShell executable: {PS_EXE}")
    
    proc = _start_bridge_if_needed()
    try:
        health_ok = _wait_health_ok()
        if not health_ok:
            # Try to get more info about the bridge process
            if proc and proc.poll() is None:
                print("[DEBUG] Bridge process is still running but health check failed")
                try:
                    # Try to get partial output without terminating
                    print("[DEBUG] Attempting to get bridge process output...")
                    proc.terminate()
                    stdout, _ = proc.communicate(timeout=10)
                    print(f"[DEBUG] Bridge process output: {stdout}")
                except subprocess.TimeoutExpired:
                    print("[DEBUG] Bridge process didn't terminate, forcing kill")
                    proc.kill()
                    stdout, _ = proc.communicate()
                    print(f"[DEBUG] Bridge process output after kill: {stdout}")
                except Exception as e:
                    print(f"[DEBUG] Error getting bridge output: {e}")
            elif proc and proc.poll() is not None:
                print(f"[DEBUG] Bridge process exited with code: {proc.returncode}")
                try:
                    stdout, _ = proc.communicate()
                    print(f"[DEBUG] Final bridge output: {stdout}")
                except:
                    print("[DEBUG] Could not get bridge output")
            else:
                print("[DEBUG] No bridge process was started")
        
        assert health_ok, "bridge health did not become ok"
        
        print(f"[DEBUG] Connecting to WebSocket at ws://{BRIDGE_HOST}:{BRIDGE_PORT}/ws?token={TOKEN}")
        ws = create_connection(f"ws://{BRIDGE_HOST}:{BRIDGE_PORT}/ws?token={TOKEN}", timeout=6)
        
        print("[DEBUG] Sending gameNew message")
        ws.send(json.dumps({"type":"gameNew"}))
        
        print("[DEBUG] Sending humanMove message")
        ws.send(json.dumps({"type":"humanMove","move":"7g7f","movetime_ms":500}))
        
        deadline = time.time() + 10
        got_engine = False
        while time.time() < deadline:
            msg = json.loads(ws.recv())
            print(f"[DEBUG] Received message: {msg}")
            t = (msg.get("type","") or "").lower()
            if t in ("enginemove","engine_move") and isinstance(msg.get("move"), str):
                print(f"[DEBUG] Got engine move: {msg.get('move')}")
                got_engine = True
                break
    # close()呼び出しを抑止
    # ws.close()
        assert got_engine, "engine did not respond with a move"
        print("[DEBUG] E2E test completed successfully")
    except Exception as e:
        print(f"[DEBUG] E2E test failed with exception: {e}")
        raise
    finally:
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
