#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USI Bridge Server - Quick Fix Version (migrated into final-project/tools)
"""

import asyncio
import json
import logging
import os
import re
import sys
import threading
import time
import subprocess
import websockets
import atexit
# websockets 15 では websockets.http.Response が期待される型
WEBSOCKETS_RESPONSE_AVAILABLE = False
Headers = None
Response = None
try:
    from websockets.http import Headers as _WSHeaders, Response as _WSResponse
    Headers, Response = _WSHeaders, _WSResponse
    WEBSOCKETS_RESPONSE_AVAILABLE = True
except Exception:
    # 古いバージョン向けフォールバック（tuple 返却許容）
    WEBSOCKETS_RESPONSE_AVAILABLE = False
from urllib.parse import parse_qs, urlparse
from pathlib import Path
from subprocess import Popen, PIPE, STDOUT

# optional: psutil for process tree kill on Windows
try:
    import psutil  # type: ignore
    PSUTIL = True
except Exception:
    PSUTIL = False

# python-shogi for legal move validation
try:
    import shogi
    SHOGI_AVAILABLE = True
except ImportError:
    SHOGI_AVAILABLE = False
    print("Warning: python-shogi not available.")

# USI→KIF 変換（人間可読なKIF生成）: クラス版（final-project/tools/usi_to_kif.py）優先、関数版(v2)フォールバック
KIF_CONVERTER_AVAILABLE = False
USI_KIF_CLASS = None
USI_KIF_FUNC = None
try:
    # まずは final-project ツールのパスを動的に追加してクラス版を試す
    try:
        repo_root = Path(__file__).resolve().parents[1]
        fp_tools = repo_root / 'tools'
        if fp_tools.exists():
            sys.path.insert(0, str(fp_tools))
    except Exception:
        pass
    try:
        from usi_to_kif import USIToKIFConverter as _USIToKIFConverter
        USI_KIF_CLASS = _USIToKIFConverter
        KIF_CONVERTER_AVAILABLE = True
    except Exception as e:
        # フォールバック: 同ディレクトリの関数版
        from usi_to_kif_v2 import usi_list_to_kif as _usi_list_to_kif
        USI_KIF_FUNC = _usi_list_to_kif
        KIF_CONVERTER_AVAILABLE = True
except Exception as e:
    print(f"Warning: KIF converter import failed: {e}")

# Configuration
DEFAULT_CONFIG = {
    "EvalDir": "C:\\shogi\\engines\\suisho\\eval",
    "FV_SCALE": 24,
    "Threads": 6,
    "USI_Hash": 1024,
    "Ponder": False,
    "MultiPV": 1,
    "USI_OwnBook": False,
    "BookFile": "no_book",
}

def apply_config_to_engine(proc_stdin, cfg: dict):
    """エンジン設定適用"""
    lines = [
        f"setoption name EvalDir value {cfg.get('EvalDir', DEFAULT_CONFIG['EvalDir'])}",
        f"setoption name FV_SCALE value {int(cfg.get('FV_SCALE', DEFAULT_CONFIG['FV_SCALE']))}",
        f"setoption name Threads value {int(cfg.get('Threads', DEFAULT_CONFIG['Threads']))}",
        f"setoption name USI_Hash value {int(cfg.get('USI_Hash', DEFAULT_CONFIG['USI_Hash']))}",
        f"setoption name USI_Ponder value {'true' if cfg.get('Ponder', DEFAULT_CONFIG['Ponder']) else 'false'}",
        f"setoption name MultiPV value {int(cfg.get('MultiPV', DEFAULT_CONFIG['MultiPV']))}",
        "isready"
    ]
    for l in lines:
        proc_stdin.write((l + "\n").encode("utf-8"))

async def apply_config_to_engine_async(proc_stdin, cfg: dict):
    """非同期版：エンジン設定適用"""
    lines = [
        f"setoption name EvalDir value {cfg.get('EvalDir', DEFAULT_CONFIG['EvalDir'])}",
        f"setoption name FV_SCALE value {int(cfg.get('FV_SCALE', DEFAULT_CONFIG['FV_SCALE']))}",
        f"setoption name Threads value {int(cfg.get('Threads', DEFAULT_CONFIG['Threads']))}",
        f"setoption name USI_Hash value {int(cfg.get('USI_Hash', DEFAULT_CONFIG['USI_Hash']))}",
        f"setoption name USI_Ponder value {'true' if cfg.get('Ponder', DEFAULT_CONFIG['Ponder']) else 'false'}",
        f"setoption name MultiPV value {int(cfg.get('MultiPV', DEFAULT_CONFIG['MultiPV']))}",
        f"setoption name USI_OwnBook value {'true' if cfg.get('USI_OwnBook', False) else 'false'}",
        f"setoption name BookFile value {cfg.get('BookFile', 'no_book')}",
        "isready"
    ]
    for l in lines:
        proc_stdin.write((l + "\n").encode("utf-8"))
        await proc_stdin.drain()

class GameState:
    def __init__(self):
        self.lock = threading.Lock()
        self.position = "startpos"   
        self.moves = []              
        self.current_player = "b"    
        self.move_times = []         
        
        # python-shogi Board for legal move checking
        if SHOGI_AVAILABLE:
            self.board = shogi.Board()
        else:
            self.board = None
            
    def is_legal_usi(self, usi_move):
        """USI形式の手が合法手かチェック"""
        if not SHOGI_AVAILABLE or not self.board:
            return True  # python-shogiが無い場合は常にTrue
            
        try:
            move = shogi.Move.from_usi(usi_move)
            return move in self.board.legal_moves
        except:
            return False
            
    def apply_move(self, usi_move):
        """手を適用"""
        if SHOGI_AVAILABLE and self.board:
            try:
                move = shogi.Move.from_usi(usi_move)
                self.board.push(move)
            except:
                pass
        
        self.moves.append(usi_move)
        self.current_player = "w" if self.current_player == "b" else "b"
        
    def reset_to_startpos(self):
        """開始局面にリセット"""
        self.position = "startpos"
        self.moves = []
        self.current_player = "b"
        self.move_times = []
        
        if SHOGI_AVAILABLE:
            self.board = shogi.Board()

class USIBridge:
    def __init__(self, engine_path):
        """USI ブリッジ初期化"""
        # 基本状態
        self.engine_path = engine_path
        self.engine_proc = None
        self._server = None  # websockets.serve() の戻り（クリーンアップ用）
        self.websocket_clients = set()
        self.controller = None
        self.state = "IDLE"
        self.command_queue = []
        self.timeout_task = None
        self.game_state = GameState()
        # 監視/再起動
        self.auto_restart = os.environ.get("USI_AUTO_RESTART", "1") not in ("0", "false", "False")
        self._engine_watch_task = None
        self._shutting_down = False
        self._resume_after_restart = False
        # ユーザー指定のオプション（setOption で与えられた差分）
        self.user_config = {}
        # 直近の致命的エラー内容
        self.last_error = None
        # GAME_OVER 通知は一度だけにするフラグ
        self.game_over_sent = False
        # ログ
        logging.basicConfig(level=logging.INFO, format='[usi-bridge] %(message)s')
        self.logger = logging.getLogger(__name__)
        # クライアントID管理と状態スナップショット用
        self._client_seq = 0
        self._client_ids = {}

        # atexit で最悪プロセスだけは握りつぶさない
        def _atexit_cleanup():
            try:
                if self.engine_proc:
                    try:
                        self.engine_proc.terminate()
                    except Exception:
                        pass
            except Exception:
                pass
        try:
            atexit.register(_atexit_cleanup)
        except Exception:
            pass

    async def start_timeout(self, expected_state, timeout_seconds):
        """タイムアウト監視開始"""
        if self.timeout_task:
            self.timeout_task.cancel()
        
        async def timeout_handler():
            await asyncio.sleep(timeout_seconds)
            self.logger.error(f"Timeout waiting for {expected_state}")
            await self.broadcast_error("ENGINE_TIMEOUT", f"Timeout waiting for {expected_state}")
        
        self.timeout_task = asyncio.create_task(timeout_handler())

    async def broadcast_status(self, phase):
        """状態を全クライアントに通知"""
        message = {"type": "status", "phase": phase}
        await self.broadcast_to_clients(message)

    async def broadcast_error(self, code, message):
        """エラーを全クライアントに通知"""
        error_msg = {"type": "error", "code": code, "message": message}
        await self.broadcast_to_clients(error_msg)

    async def broadcast_to_clients(self, message):
        """全クライアントにメッセージ送信"""
        if self.websocket_clients:
            await asyncio.gather(
                *[client.send(json.dumps(message)) for client in self.websocket_clients],
                return_exceptions=True
            )

    async def start_engine(self):
        """エンジン起動"""
        try:
            self.logger.info(f"Engine: {self.engine_path}")
            p = self.engine_path
            args = []
            if p.lower().endswith('.py'):
                # Pythonスクリプト → 現在のインタプリタで -u (行バッファ無効) 起動
                args = [sys.executable, '-u', p]
            elif os.name == 'nt' and p.lower().endswith(('.bat', '.cmd')):
                # バッチラッパー
                args = ['cmd.exe', '/c', p]
            else:
                args = [p]

            creationflags = 0
            if os.name == 'nt':
                # コンソールウィンドウを出さない（存在する場合）
                creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

            self.engine_proc = await asyncio.create_subprocess_exec(
                *args,
                stdin=PIPE, stdout=PIPE, stderr=STDOUT,
                creationflags=creationflags
            )
            
            self.state = "USI_SENT"
            await self.start_timeout("USIOK", 10.0)
            await self.send_to_engine_direct("usi")
            
            # エンジン出力監視開始
            asyncio.create_task(self.monitor_engine_output())
            # 予期せぬ終了を監視
            if self._engine_watch_task is None or self._engine_watch_task.done():
                self._engine_watch_task = asyncio.create_task(self._watch_engine_exit())
            
        except Exception as e:
            self.last_error = str(e)
            self.state = "ERROR"
            # WinError 193 ヒント付与
            hint = ""
            if isinstance(e, OSError) and getattr(e, 'winerror', None) == 193:
                hint = " (.py を直接渡した場合は .bat ラッパーか自動検出ロジックを利用してください)"
            self.logger.error(f"Engine start failed: {e}{hint}")
            await self.broadcast_error("ENGINE_START_FAILED", self.last_error)

    async def send_to_engine_direct(self, command):
        """エンジンに直接コマンド送信"""
        if self.engine_proc and self.engine_proc.stdin:
            self.logger.info(f"→ {command}")
            self.engine_proc.stdin.write(f"{command}\n".encode())
            await self.engine_proc.stdin.drain()

    async def send_to_engine(self, command):
        """エンジンにコマンド送信（状態チェック付き）"""
        if self.state in ("READYOK", "IN_GAME") or command in ("usi", "isready", "quit"):
            await self.send_to_engine_direct(command)
            
            if command == "isready":
                self.state = "ISREADY_SENT" 
                await self.start_timeout("READYOK", 5.0)

    async def monitor_engine_output(self):
        """エンジン出力監視"""
        try:
            while self.engine_proc and self.engine_proc.stdout:
                line = await self.engine_proc.stdout.readline()
                if not line:
                    break
                    
                line_str = line.decode('utf-8', errors='ignore').strip()
                if line_str:
                    self.logger.info(f"← {line_str}")
                    await self.process_engine_output(line_str)
                    
        except Exception as e:
            self.logger.error(f"Engine monitoring error: {e}")

    async def process_engine_output(self, line_str):
        """エンジン出力処理"""
        # エンジン生出力をクライアントに転送
        engine_msg = {"type": "engine", "output": line_str, "line": line_str}
        await self.broadcast_to_clients(engine_msg)

        # 特定行パース
        if line_str == "usiok":
            if self.timeout_task:
                self.timeout_task.cancel()
            self.state = "USIOK"
            await self.broadcast_status("USIOK")
            merged = {**DEFAULT_CONFIG, **self.user_config}
            await apply_config_to_engine_async(self.engine_proc.stdin, merged)

        elif line_str == "readyok":
            if self.timeout_task:
                self.timeout_task.cancel()
            self.state = "READYOK"
            await self.broadcast_status("READYOK")
            # 再起動後に対局継続中なら局面を再同期
            try:
                if self._resume_after_restart and self.game_state.moves:
                    pos_cmd = f"position startpos moves {' '.join(self.game_state.moves)}"
                    await self.send_to_engine_direct(pos_cmd)
            finally:
                self._resume_after_restart = False

        elif line_str.startswith("bestmove"):
            if self.state == "GAME_OVER":
                self.logger.info(f"Ignoring bestmove after game over: {line_str}")
                return
            move_match = re.search(r'bestmove\s+(\S+)', line_str)
            if move_match:
                move = move_match.group(1)
                try:
                    self.logger.info(f"bestmove {move}")
                except Exception:
                    pass
                if move not in ("resign", "win"):
                    self.game_state.apply_move(move)
                game_msg = {
                    "type": "game",
                    "event": "bestmove",
                    "lastMove": move,
                    "state": {
                        "moves": self.game_state.moves,
                        "currentPlayer": self.game_state.current_player
                    }
                }
                await self.broadcast_to_clients(game_msg)
                try:
                    if move not in ("resign","win") and self.is_checkmate():
                        await self.broadcast_to_clients({
                            "type":"game","event":"autoResign","by":"engine","reason":"checkmate",
                            "state":{"moves":self.game_state.moves,"currentPlayer":self.game_state.current_player}
                        })
                        try:
                            await self.send_to_engine_direct("stop")
                        except Exception:
                            pass
                        self.state = "GAME_OVER"
                        await self.broadcast_game_over(winner="engine", reason="checkmate", by="autoResign")
                except Exception as e:
                    self.logger.warning(f"Auto-resign bestmove check failed: {e}")

        elif line_str.startswith("info"):
            parsed_info = self.parse_info_line(line_str)
            if parsed_info:
                parsed_msg = {"type": "parsed", **parsed_info}
                await self.broadcast_to_clients(parsed_msg)

    def parse_info_line(self, line):
        """info行のパース"""
        info = {}
        tokens = line.split()
        i = 1
        while i < len(tokens):
            if tokens[i] == "depth" and i+1 < len(tokens):
                info["depth"] = int(tokens[i+1])
                i += 2
            elif tokens[i] == "nps" and i+1 < len(tokens):
                info["nps"] = int(tokens[i+1])
                i += 2
            elif tokens[i] == "score" and i+2 < len(tokens):
                info["scoreType"] = tokens[i+1]
                info["scoreValue"] = int(tokens[i+2])
                i += 3
            else:
                i += 1
        return info

    def is_checkmate(self) -> bool:
        """王手かつ逃げ場なし（詰み）を厳密判定。
        python-shogi が利用可能な場合のみ評価し、それ以外は False。
        """
        try:
            if not (SHOGI_AVAILABLE and self.game_state.board):
                return False
            board = self.game_state.board
            if not board.is_check():
                return False
            has_legal = any(True for _ in board.legal_moves)
            return not has_legal
        except Exception as e:
            self.logger.warning(f"checkmate detection failed: {e}")
            return False

    async def handle_websocket(self, websocket, path=None):
        """WebSocket接続処理（切断強制ロジックなし）"""
        self.websocket_clients.add(websocket)
        self._client_seq += 1
        cid = f"c{self._client_seq}"
        self._client_ids[websocket] = cid
        if not self.controller:
            self.controller = websocket
            self.logger.info(f"Controller assigned: {websocket.remote_address}")
        
        try:
            status_msg = {"type": "status", "phase": self.state}
            self.logger.info(f"Sending status: {status_msg}")
            await websocket.send(json.dumps(status_msg))
            if self.state == "ERROR" and self.last_error:
                await websocket.send(json.dumps({
                    "type": "error",
                    "code": "ENGINE_START_FAILED",
                    "message": self.last_error
                }))
            
            async for message in websocket:
                try:
                    self.logger.info(f"Received message: {message}")
                    data = json.loads(message)
                    if data.get("type") == "ping":
                        await websocket.send(json.dumps({"type":"pong","t":data.get("t")}))
                        continue
                    if data.get("type") == "hello":
                        client_id = data.get("clientId")
                        if client_id:
                            self._client_ids[websocket] = str(client_id)
                        await websocket.send(json.dumps({"type":"status","phase":"HELLO_OK"}))
                        continue
                    await self.process_websocket_message(websocket, data)
                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON decode error: {e}, message: {message}")
                    error_msg = {"type": "error", "code": "INVALID_JSON", "message": str(e)}
                    await websocket.send(json.dumps(error_msg))
                except Exception as e:
                    self.logger.error(f"Message processing error: {e}")
                    import traceback
                    traceback.print_exc()
                    error_msg = {"type": "error", "code": "PROCESSING_ERROR", "message": str(e)}
                    await websocket.send(json.dumps(error_msg))
                
        except Exception as e:
            self.logger.error(f"WebSocket error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.websocket_clients.discard(websocket)
            if self.controller == websocket:
                self.controller = None
            try:
                self._client_ids.pop(websocket, None)
            except Exception:
                pass

    async def process_websocket_message(self, websocket, data):
        """WebSocketメッセージ処理"""
        msg_type = data.get("type")
        controller_required = {"gameNew", "humanMove", "send", "setOption", "restart", "gameResign"}
        if msg_type in controller_required and websocket is not self.controller:
            err = {"type": "error", "code": "NOT_CONTROLLER", "message": "Only controller may send this message"}
            await websocket.send(json.dumps(err))
            return
        
        if msg_type == "getState":
            snap = self.snapshot_state()
            await websocket.send(json.dumps(snap))
            try:
                compat_state = {
                    "moves": snap.get("moves", []),
                    "current_player": snap.get("side_to_move", "b"),
                }
                await websocket.send(json.dumps({
                    "type": "game",
                    "event": "state",
                    "state": compat_state,
                }))
            except Exception:
                pass
            return

        if msg_type == "takeControl":
            self.controller = websocket
            await websocket.send(json.dumps({"type":"status","phase":"CONTROL_GRANTED"}))
            return

        if msg_type == "gameNew":
            self.game_state.reset_to_startpos()
            self.game_over_sent = False
            await self.send_to_engine_direct("usinewgame")
            await self.send_to_engine_direct("position startpos")
            self.state = "IN_GAME"
            try:
                def _norm_bool(v):
                    if isinstance(v, bool):
                        return v
                    if isinstance(v, str):
                        return v.strip().lower() in ("1", "true", "yes", "on")
                    if isinstance(v, (int, float)):
                        return v != 0
                    return False

                mt = data.get("movetime")
                if not isinstance(mt, int) or mt <= 0:
                    mt = data.get("movetime_ms")
                eng_starts_raw = data.get("engineStarts")
                send_go = False
                if isinstance(mt, int) and mt > 0:
                    if eng_starts_raw is None:
                        send_go = True
                    else:
                        send_go = _norm_bool(eng_starts_raw)
                if send_go:
                    await self.send_to_engine_direct(f"go movetime {mt}")
            except Exception:
                pass
            
            response = {"type": "game", "event": "new"}
            await websocket.send(json.dumps(response))
            
        elif msg_type == "humanMove":
            if self.state == "GAME_OVER":
                await websocket.send(json.dumps({"type":"error","code":"GAME_OVER","message":"Game already finished"}))
                return
            move = data.get("move")
            movetime_ms = data.get("movetime")
            if not isinstance(movetime_ms, int) or movetime_ms <= 0:
                movetime_ms = data.get("movetime_ms")
            # movetime_ms がまだない場合はデフォルト値を設定
            if not isinstance(movetime_ms, int) or movetime_ms <= 0:
                movetime_ms = 2000  # デフォルト2秒
            if not self.game_state.is_legal_usi(move):
                error_response = {"type": "error", "code": "ILLEGAL_MOVE", "message": f"Illegal move: {move}"}
                await websocket.send(json.dumps(error_response))
                return
                
            self.game_state.apply_move(move)
            position_cmd = f"position startpos moves {' '.join(self.game_state.moves)}"
            await self.send_to_engine_direct(position_cmd)
            
            response = {"type": "game", "event": "humanMove", "move": move, "lastMove": move,
                        "state": {"moves": self.game_state.moves, "currentPlayer": self.game_state.current_player}}
            await websocket.send(json.dumps(response))
            # movetime_ms は常に有効な値なので、必ず go コマンドを送信
            try:
                await self.send_to_engine_direct(f"go movetime {movetime_ms}")
                self.logger.info(f"Sent go movetime {movetime_ms} after humanMove {move}")
            except Exception as e:
                self.logger.error(f"Failed to send go command: {e}")
            try:
                if self.is_checkmate():
                    await self.broadcast_to_clients({
                        "type":"game","event":"autoResign","by":"human","reason":"checkmate",
                        "state":{"moves":self.game_state.moves,"currentPlayer":self.game_state.current_player}
                    })
                    try:
                        await self.send_to_engine_direct("stop")
                    except Exception:
                        pass
                    self.state = "GAME_OVER"
                    await self.broadcast_game_over(winner="human", reason="checkmate", by="autoResign")
            except Exception as e:
                self.logger.warning(f"Auto-resign humanMove check failed: {e}")
            
        elif msg_type == "send":
            if self.state == "GAME_OVER":
                await websocket.send(json.dumps({"type":"error","code":"GAME_OVER","message":"Game already finished"}))
                return
            command = data.get("line", "")
            if command:
                self.logger.info(f"Processing command: {command}")
                await self.send_to_engine_direct(command)
        
        elif msg_type == "setOption":
            name = data.get("name")
            value = data.get("value")
            if name is None:
                await websocket.send(json.dumps({"type":"error","code":"BAD_REQUEST","message":"name required"}))
                return
            norm_value = value
            if isinstance(value, str):
                if value.lower() == "true":
                    norm_value = True
                elif value.lower() == "false":
                    norm_value = False
            self.user_config[name] = norm_value
            await self.send_to_engine_direct(f"setoption name {name} value {value}")
            await websocket.send(json.dumps({"type":"option","event":"applied","name":name,"value":value}))

        elif msg_type == "restart":
            await websocket.send(json.dumps({"type":"status","phase":"RESTARTING"}))
            await self._restart_engine()
        
        elif msg_type == "gameResign":
            by = "human"
            winner = "engine"
            try:
                await self.send_to_engine_direct("stop")
            except Exception:
                pass
            resign_msg = {"type":"game","event":"resign","by":by,"result":f"{winner}-win"}
            await websocket.send(json.dumps(resign_msg))
            for c in list(self.websocket_clients):
                if c is not websocket:
                    try:
                        await c.send(json.dumps(resign_msg))
                    except Exception:
                        pass
            self.state = "GAME_OVER"
            await self.broadcast_game_over(winner=winner, reason="resign", by="manual")
            return
        
        elif msg_type == "generateKIF":
            kif_content = self.generate_kif(data.get("gameInfo", {}))
            response = {
                "type": "kifGenerated",
                "requestId": data.get("requestId"),
                "kifContent": kif_content
            }
            await websocket.send(json.dumps(response))


    async def broadcast_game_over(self, winner: str, reason: str, by: str = "autoResign"):
        """終局通知（1回だけ）。winner: "human" | "engine"。reason: "checkmate" 等。"""
        try:
            if self.game_over_sent:
                return
            self.game_over_sent = True
            at_ply = len(self.game_state.moves)
            payload = {
                "type": "game",
                "status": "GAME_OVER",
                "result": {
                    "winner": winner,
                    "reason": reason,
                    "by": by,
                    "atPly": at_ply
                }
            }
            await self.broadcast_to_clients(payload)
        except Exception as e:
            self.logger.warning(f"broadcast_game_over failed: {e}")

    def generate_kif(self, game_info):
        """KIF生成: 可能ならUSI→KIF変換を使って人間可読なKIFを返す。失敗時はUSI列挙にフォールバック。"""
        try:
            if KIF_CONVERTER_AVAILABLE:
                sente = game_info.get('black_player') or game_info.get('sente') or '先手'
                gote = game_info.get('white_player') or game_info.get('gote') or '後手'
                if USI_KIF_CLASS is not None:
                    try:
                        conv = USI_KIF_CLASS()
                        return conv.convert_game_to_kif(self.game_state.moves, {
                            'sente': sente,
                            'gote': gote,
                            'date': game_info.get('date') or time.strftime('%Y/%m/%d')
                        })
                    except Exception:
                        pass
                if USI_KIF_FUNC is not None:
                    return USI_KIF_FUNC(self.game_state.moves, sente, gote)
        except Exception as e:
            self.logger.warning(f"KIF convert failed, fallback to raw USI: {e}")

        lines = [
            "# KIF形式棋譜ファイル Generated by USI Bridge",
            f"開始日時：{game_info.get('date', '') or time.strftime('%Y/%m/%d')}",
            "手合割：平手",
            f"先手：{game_info.get('sente', '先手')}",
            f"後手：{game_info.get('gote', '後手')}",
            "手数----指手---------消費時間--",
        ]
        for i, move in enumerate(self.game_state.moves):
            lines.append(f"{i+1:4} {move:12} (00:00:00)")
        return "\n".join(lines)

    async def start_server(self, host="127.0.0.1", port=8787, auto_port=False, max_scan=20):
        """サーバー開始（WebSocket + 簡易HTTP /health）"""
        self.logger.info(f"Starting server on ws://{host}:{port} (auto_port={'on' if auto_port or port == 0 else 'off'})")

        async def process_request(path, request_headers):
            try:
                parsed = urlparse(path)
                WS_PATH = "/ws"
                token_env = os.getenv("USI_BRIDGE_TOKEN") or None

                def _mk_response(status: int, body_obj: dict, content_type: str = "application/json; charset=utf-8"):
                    payload = json.dumps(body_obj).encode("utf-8")
                    if WEBSOCKETS_RESPONSE_AVAILABLE and Response is not None and Headers is not None:
                        try:
                            return Response(
                                status=status,
                                headers=Headers([
                                    ("Content-Type", content_type),
                                    ("Cache-Control", "no-store"),
                                    ("Content-Length", str(len(payload))),
                                ]),
                                body=payload,
                            )
                        except Exception:
                            pass
                    headers = [("Content-Type", content_type), ("Cache-Control", "no-store"), ("Content-Length", str(len(payload)))]
                    return (status, headers, payload)

                if parsed.path == "/health":
                    qs = parse_qs(parsed.query or "")
                    req_tok = (qs.get("token") or [""])[0]
                    if token_env and req_tok != token_env:
                        return _mk_response(401, {"ok": False, "error": "invalid token"})

                    ok = self.state in ("USIOK", "READYOK", "IN_GAME")
                    return _mk_response(200, {"ok": ok, "status": self.state, "ws_path": WS_PATH})

                if parsed.path == WS_PATH:
                    return None

                return _mk_response(404, {"ok": False, "error": "not found"})
            except Exception:
                if WEBSOCKETS_RESPONSE_AVAILABLE and Response is not None and Headers is not None:
                    try:
                        return Response(status=500, headers=Headers([( "Content-Type", "text/plain" ), ( "Cache-Control", "no-store" ), ( "Content-Length", str(len(b"Internal Server Error")) )]), body=b"Internal Server Error")
                    except Exception:
                        pass
                return (500, [("Content-Type", "text/plain"), ("Cache-Control", "no-store"), ("Content-Length", str(len(b"Internal Server Error")))], b"Internal Server Error")

        attempt = 0
        base_port = port
        while True:
            try:
                server = await websockets.serve(
                    self.handle_websocket,
                    host, port,
                    max_size=4*1024*1024,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5,
                    max_queue=32,
                    process_request=(process_request if WEBSOCKETS_RESPONSE_AVAILABLE else None),
                )
                self._server = server
                break
            except OSError as e:
                self.logger.error(f"Failed to bind ws://{host}:{port}: {e}")
                msg = str(e).lower()
                in_use = (getattr(e, 'errno', None) in (98, 10048)) or ("in use" in msg) or ("already" in msg and "use" in msg)
                if (auto_port or base_port == 0) and in_use and attempt < max_scan:
                    if base_port != 0:
                        port += 1
                    attempt += 1
                    await asyncio.sleep(0.05)
                    continue
                raise

        actual_port = port
        try:
            if getattr(self._server, 'sockets', None):
                sock = self._server.sockets[0]
                actual_port = sock.getsockname()[1]
        except Exception:
            pass

        self.logger.info(f"WebSocket server listening on ws://{host}:{actual_port}")
        try:
            print(f"BRIDGE_PORT={actual_port}")
        except Exception:
            pass
        try:
            port_file = os.getenv("USI_PORT_FILE")
            port_dir = os.getenv("USI_PORT_DIR")
            if port_file:
                Path(port_file).parent.mkdir(parents=True, exist_ok=True)
                Path(port_file).write_text(str(actual_port), encoding="utf-8")
            elif port_dir:
                out = Path(port_dir) / "last_port.txt"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(str(actual_port), encoding="utf-8")
        except Exception:
            pass

        self.logger.info(
            "process_request configured: WS_PATH=/ws, token=%s, websockets.Response=%s"
            % ("SET" if (os.getenv("USI_BRIDGE_TOKEN") or None) else "NONE", WEBSOCKETS_RESPONSE_AVAILABLE)
        )
        self.logger.info("Ready for connections...")

        try:
            loop = asyncio.get_running_loop()
            if hasattr(loop, "add_signal_handler"):
                import signal
                def _reap_children():
                    try:
                        while True:
                            pid, _ = os.waitpid(-1, os.WNOHANG)
                            if pid == 0:
                                break
                    except ChildProcessError:
                        pass
                    except Exception:
                        pass
                try:
                    loop.add_signal_handler(signal.SIGCHLD, _reap_children)
                except Exception:
                    pass
        except Exception:
            pass

        await self.start_engine()

        try:
            await self._wait_server_closed()
        except KeyboardInterrupt:
            self.logger.info("Shutting down...")
        finally:
            self._shutting_down = True
            try:
                await self._graceful_shutdown()
            except Exception as e:
                self.logger.warning(f"graceful shutdown failed: {e}")

    async def _wait_server_closed(self):
        try:
            if self._server is not None:
                await self._server.wait_closed()
        except Exception:
            pass

    async def _kill_children_tree(self):
        if not PSUTIL:
            return
        try:
            p = psutil.Process()
            children = p.children(recursive=True)
            for c in children:
                try:
                    c.terminate()
                except Exception:
                    pass
            gone, alive = psutil.wait_procs(children, timeout=2)
            for a in alive:
                try:
                    a.kill()
                except Exception:
                    pass
        except Exception:
            pass

    async def _graceful_shutdown(self):
        try:
            if self.engine_proc:
                try:
                    self.engine_proc.terminate()
                except Exception:
                    pass
                try:
                    await asyncio.wait_for(self.engine_proc.wait(), timeout=3)
                except asyncio.TimeoutError:
                    try:
                        self.engine_proc.kill()
                    except Exception:
                        pass
                    try:
                        await self.engine_proc.wait()
                    except Exception:
                        pass
                self.engine_proc = None
        except Exception:
            pass
        try:
            if self._server is not None:
                self._server.close()
                try:
                    await self._server.wait_closed()
                except Exception:
                    pass
                self._server = None
        finally:
            try:
                await self._kill_children_tree()
            except Exception:
                pass

    def snapshot_state(self):
        try:
            controller_id = None
            if self.controller:
                controller_id = self._client_ids.get(self.controller)
            sfen = self.game_state.position if getattr(self.game_state, 'position', None) else 'startpos'
            moves = list(self.game_state.moves)
            side = self.game_state.current_player
            seq = len(moves)
            in_game = (self.state == 'IN_GAME')
            return {
                "type": "state",
                "in_game": in_game,
                "controller": controller_id,
                "sfen": sfen,
                "moves": moves,
                "side_to_move": side,
                "seq": seq,
            }
        except Exception as e:
            self.logger.warning(f"snapshot_state failed: {e}")
            return {
                "type": "state",
                "in_game": False,
                "controller": None,
                "sfen": "startpos",
                "moves": [],
                "side_to_move": "b",
                "seq": 0,
            }

    async def _restart_engine(self):
        try:
            if self.engine_proc:
                self.engine_proc.terminate()
                try:
                    await asyncio.wait_for(self.engine_proc.wait(), timeout=3)
                except asyncio.TimeoutError:
                    self.engine_proc.kill()
            self.state = "RESTARTING"
            await self.start_engine()
        except Exception as e:
            self.logger.error(f"Restart failed: {e}")
            await self.broadcast_error("RESTART_FAILED", str(e))

    async def _watch_engine_exit(self):
        try:
            if not self.engine_proc:
                return
            rc = await self.engine_proc.wait()
            self.logger.warning(f"Engine process exited with code {rc}")
            self.engine_proc = None
            if self._shutting_down:
                return
            if self.auto_restart:
                self._resume_after_restart = (self.state == "IN_GAME")
                await self.broadcast_status("ENGINE_DOWN")
                self.state = "RESTARTING"
                await self.broadcast_status("RESTARTING")
                await asyncio.sleep(1.0)
                try:
                    await self.start_engine()
                except Exception as e:
                    self.logger.error(f"Auto-restart failed: {e}")
                    await self.broadcast_error("AUTO_RESTART_FAILED", str(e))
            else:
                self.state = "ERROR"
                await self.broadcast_error("ENGINE_EXITED", f"code={rc}")
        except Exception as e:
            self.logger.error(f"Engine watch error: {e}")

def main():
    """CLI entrypoint
    Usage (backward compatible):
      python usi-bridge.py <engine_path> [port] [--token TOKEN] [--host HOST]
    """
    if len(sys.argv) < 2:
        print("Usage: python usi-bridge.py <engine_path> [port] [--token TOKEN] [--host HOST]")
        sys.exit(1)

    engine_path = sys.argv[1]
    port = 8787
    host = "127.0.0.1"
    token = None
    auto_port = False

    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if isinstance(arg, str) and arg.isdigit():
            try:
                port = int(arg)
                i += 1
                continue
            except Exception:
                pass
        if arg in ("--token", "-t"):
            if i + 1 < len(sys.argv):
                token = sys.argv[i + 1]
                i += 2
                continue
            else:
                print("ERROR: --token requires a value")
                sys.exit(2)
        if arg == "--host":
            if i + 1 < len(sys.argv):
                host = sys.argv[i + 1]
                i += 2
                continue
            else:
                print("ERROR: --host requires a value")
                sys.exit(2)
        if arg in ("--auto", "--auto-port", "-a"):
            auto_port = True
            i += 1
            continue
        i += 1

    if token:
        try:
            os.environ["USI_BRIDGE_TOKEN"] = token
        except Exception:
            pass

    bridge = USIBridge(engine_path)

    if not auto_port:
        env_auto = os.getenv("USI_AUTO_PORT")
        if env_auto and env_auto.lower() not in ("0", "false"):
            auto_port = True

    try:
        asyncio.run(bridge.start_server(host=host, port=port, auto_port=auto_port))
    except KeyboardInterrupt:
        print("\nShutdown requested")

if __name__ == "__main__":
    main()
