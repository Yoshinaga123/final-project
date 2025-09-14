import subprocess, threading, queue, time, re
from typing import Callable, Optional, Dict, Any
from pathlib import Path

BEST_RE = re.compile(r'^bestmove (\S+)(?: ponder (\S+))?$')

# 初期実装用デフォルトオプション
DEFAULT_ENGINE_OPTIONS = {
    "Threads": 2,
    "USI_Hash": 256,  # Hash オプションの標準名
    "MultiPV": 1,
    "USI_Ponder": "false",  # USI_Ponder の標準名（Ponderも fallback対応）
}

class EngineAdapter:
    """Minimal USI engine adapter.

    Responsibilities:
      * Spawn engine process
      * USI handshake (usi -> usiok, isready -> readyok, usinewgame)
      * Send position / go commands
      * Parse info / bestmove lines and dispatch via callbacks
    """
    def __init__(self, path: str, options: Optional[Dict[str, Any]] = None,
                 on_info: Optional[Callable[[Dict[str, Any]], None]] = None,
                 on_best: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.path = path
        self.options = options or {}
        self.on_info = on_info or (lambda *_: None)
        self.on_best = on_best or (lambda *_: None)
        self.proc = None
        self._q: "queue.Queue[str]" = queue.Queue()
        self._lock = threading.Lock()
        self._alive = False

    def start(self):
        # Windows固有ケア: CREATE_NO_WINDOW + text正規化
        import platform
        creation_flags = 0
        if platform.system() == "Windows":
            creation_flags = subprocess.CREATE_NO_WINDOW
        
        # pathlib.Pathでパス正規化（スペース・全角文字混入対応）
        engine_path = Path(self.path).resolve()
        
        self.proc = subprocess.Popen(
            [str(engine_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            creationflags=creation_flags
        )
        self._alive = True
        threading.Thread(target=self._reader_loop, daemon=True).start()

        # USI初期化
        self._send('usi')
        self._wait_for('usiok')
        
        # 一括setoptionで統一反映（先輩エンジニア推奨）
        self._apply_engine_options()
        
        self._send('isready')
        self._wait_for('readyok')
        self._send('usinewgame')

    def _apply_engine_options(self):
        """USIオプションの統一反映（名前の揺れ対応含む）"""
        for key, value in self.options.items():
            # USI_Ponder/Ponder の名前揺れ対応
            if key == "Ponder" and "USI_Ponder" not in self.options:
                # USI_Ponder を優先、なければ Ponder で試行
                self._send(f'setoption name USI_Ponder value {value}')
                self._send(f'setoption name Ponder value {value}')
            elif key == "Hash" and "USI_Hash" not in self.options:
                # USI_Hash を優先、なければ Hash で試行
                self._send(f'setoption name USI_Hash value {value}')
                self._send(f'setoption name Hash value {value}')
            else:
                self._send(f'setoption name {key} value {value}')
        
        # NNUE用のEvalDir設定（環境変数があれば自動設定）
        import os
        eval_dir = os.environ.get('EVAL_DIR')
        if eval_dir and Path(eval_dir).exists():
            self._send(f'setoption name EvalDir value {eval_dir}')

    def position(self, sfen_or_startpos: str = 'startpos', moves=None):
        if moves:
            self._send(f'position {sfen_or_startpos} moves {" ".join(moves)}')
        else:
            self._send(f'position {sfen_or_startpos}')

    def go(self, movetime_ms: int = 1000, btime=None, wtime=None, byoyomi=None):
        if btime is not None and wtime is not None:
            self._send(f'go btime {btime} wtime {wtime} byoyomi {byoyomi or 0}')
        else:
            self._send(f'go movetime {movetime_ms}')

    def stop(self):
        self._send('stop')

    def quit(self):
        """安全終了: quit応答待ち → terminate の二段構え"""
        try:
            if self.proc and self.proc.poll() is None:  # プロセスが生きている場合のみ
                self._send('quit')
                # quit応答を少し待つ（タイムアウト付き）
                try:
                    self.proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # quit応答がない場合は強制終了
                    self.proc.terminate()
                    try:
                        self.proc.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        # それでも終了しない場合は kill
                        self.proc.kill()
        except Exception:
            # エラーが発生しても確実にクリーンアップ
            if self.proc:
                try:
                    self.proc.terminate()
                except:
                    pass
        finally:
            self._alive = False
            self.proc = None

    def _send(self, line: str):
        with self._lock:
            if self.proc and self.proc.stdin:
                self.proc.stdin.write(line + '\n')
                self.proc.stdin.flush()

    def _reader_loop(self):
        assert self.proc and self.proc.stdout
        for raw in self.proc.stdout:
            if not self._alive:
                break
            line = raw.strip()
            if not line:
                continue
            if line.startswith('info '):
                self.on_info(self._parse_info(line))
            elif line.startswith('bestmove'):
                m = BEST_RE.match(line)
                if m:
                    self.on_best({'move': m.group(1), 'ponder': m.group(2)})
            if line in ('usiok', 'readyok'):
                self._q.put(line)

    def _wait_for(self, token: str, timeout=5.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                got = self._q.get(timeout=0.1)
                if got == token:
                    return True
            except queue.Empty:
                pass
        raise TimeoutError(f'timeout waiting for {token}')

    def _parse_info(self, line: str):
        def pick_int(key):
            m = re.search(rf'\b{key} (\d+)', line)
            return int(m.group(1)) if m else None
        depth = pick_int('depth')
        nps = pick_int('nps')
        score_cp, mate = None, None
        m = re.search(r'score (cp|mate) (-?\d+)', line)
        if m:
            if m.group(1) == 'cp':
                score_cp = int(m.group(2))
            else:
                mate = int(m.group(2))
        pv = None
        m = re.search(r'\bpv (.+)$', line)
        if m:
            pv = m.group(1).split()
        return {'raw': line, 'depth': depth, 'nps': nps, 'score_cp': score_cp, 'mate': mate, 'pv': pv}
