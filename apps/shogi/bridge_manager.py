"""
USIブリッジの簡易プロセスマネージャ

開発～小規模本番向け: Flask 起動時に未起動ならブリッジを起動し、
アプリ終了時に可能なら停止を試みます。
"""

import os
import time
import subprocess
from threading import Lock

import requests

_lock = Lock()
_proc = None


def _health_url(cfg) -> str:
    host = cfg.get('USI_BRIDGE_HOST', '127.0.0.1')
    port = int(cfg.get('USI_BRIDGE_PORT', 8787))
    token = cfg.get('USI_BRIDGE_TOKEN')
    qs = f"?token={token}" if token else ""
    return f"http://{host}:{port}/health{qs}"


def bridge_healthy(cfg, timeout=1.0) -> bool:
    """HTTP /health に依存せず、TCP LISTEN を確認して生存判定。
    websockets のバージョン違いで /health が提供されない環境でも安全。
    """
    try:
        import socket
        host = cfg.get('USI_BRIDGE_HOST', '127.0.0.1')
        port = int(cfg.get('USI_BRIDGE_PORT', 8787))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


def ensure_bridge_running(app):
    """App 起動時に呼ぶ。未起動なら scripts/run-bridge.ps1 を叩く。"""
    global _proc
    with _lock:
        if bridge_healthy(app.config):
            return "alive"

    # PowerShell スクリプトと引数
    ps1 = app.config.get('USI_BRIDGE_PS1') or os.path.join(app.root_path, 'scripts', 'run-bridge.ps1')
    ps1 = os.path.abspath(ps1)

    # エンジンパスが未設定の場合は既定の水匠パスにフォールバック（実際のインストール場所）
    engine = app.config.get('USI_ENGINE_PATH') or \
         r"C:\Users\yoshinaga_kosuke\Downloads\Suisho5-ZEN2.exe"
    port = str(app.config.get('USI_BRIDGE_PORT', 8787))
    token = app.config.get('USI_BRIDGE_TOKEN')
    pyexe = app.config.get('PYTHON_EXE', 'python')
    bridge_script = app.config.get('USI_BRIDGE_SCRIPT')  # 未指定なら ps1 既定を使用

    args = [
        'powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', ps1,
        '-Engine', engine,
        '-Port', port,
        '-PythonExe', pyexe,
        '-ReadyTimeoutSec', '10'
    ]
    if bridge_script:
        args += ['-BridgeScript', bridge_script]
    if token:
        args += ['-Token', token]

    try:
        _proc = subprocess.Popen(args, cwd=app.root_path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except Exception as e:
        app.logger.error(f"USI bridge spawn failed: {e}")
        return "spawn-error"

    # health OK まで一定時間待つ
    for _ in range(24):  # 最大約12秒
        if bridge_healthy(app.config):
            return "spawned"
        time.sleep(0.5)
    return "spawned-but-unhealthy"


def stop_bridge(app=None):
    """App 終了時。明示的な停止ができる場合のみ。"""
    global _proc
    with _lock:
        if _proc and _proc.poll() is None:
            try:
                _proc.terminate()
                try:
                    _proc.wait(timeout=3)
                except Exception:
                    _proc.kill()
            except Exception:
                pass
        _proc = None
