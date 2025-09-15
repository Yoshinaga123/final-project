"""候補手機能（サーバサイド）

USIエンジン（ローカル実行）で MultiPV から候補手を収集し、
利用不可のときは安全なフォールバック候補を返します。

返却フォーマット（各候補）:
- move: str        USI文字列（例: "7g7f", "P*7f", "2b3c+"）
- notation: str    簡易KIF風（例: "▲７六歩"）
- eval: int        評価値（cpを正、後手良しは負）/ 詰みは ±30000 近辺
- eval_type: str   "cp" | "mate" | "unknown"
- rank: int        1..N（MultiPVの順）
- source: str      "engine" | "predefined" | "fallback" | "emergency"
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable
import os
import re
try:
    import shogi  # type: ignore
except Exception:
    shogi = None  # フォールバックで簡易表記を使用

KANJI_NUMS = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九']
PIECE_KANJI = {
    'P': '歩', 'L': '香', 'N': '桂', 'S': '銀', 'G': '金', 'B': '角', 'R': '飛', 'K': '玉'
}

# python-shogi の piece_type から漢字へ（利用可能なら）
PIECE_TYPE_TO_KANJI = {}
PROMOTED_KANJI_BY_BASE = {}
if shogi is not None:
    try:
        # 基本駒
        PIECE_TYPE_TO_KANJI[getattr(shogi, 'PAWN', 1)] = '歩'
        PIECE_TYPE_TO_KANJI[getattr(shogi, 'LANCE', 2)] = '香'
        PIECE_TYPE_TO_KANJI[getattr(shogi, 'KNIGHT', 3)] = '桂'
        PIECE_TYPE_TO_KANJI[getattr(shogi, 'SILVER', 4)] = '銀'
        PIECE_TYPE_TO_KANJI[getattr(shogi, 'GOLD', 5)] = '金'
        PIECE_TYPE_TO_KANJI[getattr(shogi, 'BISHOP', 6)] = '角'
        PIECE_TYPE_TO_KANJI[getattr(shogi, 'ROOK', 7)] = '飛'
        PIECE_TYPE_TO_KANJI[getattr(shogi, 'KING', 8)] = '玉'
        # 成り駒表記（元の駒種ベース）
        PROMOTED_KANJI_BY_BASE[getattr(shogi, 'PAWN', 1)] = 'と'
        PROMOTED_KANJI_BY_BASE[getattr(shogi, 'LANCE', 2)] = '成香'
        PROMOTED_KANJI_BY_BASE[getattr(shogi, 'KNIGHT', 3)] = '成桂'
        PROMOTED_KANJI_BY_BASE[getattr(shogi, 'SILVER', 4)] = '成銀'
        PROMOTED_KANJI_BY_BASE[getattr(shogi, 'BISHOP', 6)] = '馬'
        PROMOTED_KANJI_BY_BASE[getattr(shogi, 'ROOK', 7)] = '竜'
    except Exception:
        PIECE_TYPE_TO_KANJI = {}
        PROMOTED_KANJI_BY_BASE = {}


def _rank_letter_to_kanji(rank_letter: str) -> str:
    # 'a'..'i' -> 一..九
    if 'a' <= rank_letter <= 'i':
        return KANJI_NUMS[ord(rank_letter) - 96]
    return rank_letter


def _format_square_kanji(file_digit: int, rank_letter: str) -> str:
    file_k = KANJI_NUMS[file_digit] if 0 < file_digit <= 9 else str(file_digit)
    rank_k = _rank_letter_to_kanji(rank_letter)
    return f"{file_k}{rank_k}"


def build_board_from_moves(moves: List[str]):
    """startpos + moves から盤面を構築（python-shogi 利用）。失敗時は None。
    """
    if shogi is None:
        return None
    try:
        board = shogi.Board()
        for mv in moves or []:
            try:
                board.push_usi(mv)
            except Exception:
                # 不正な手は無視して継続
                pass
        return board
    except Exception:
        return None


def usi_to_kif_with_board(usi_move: str, current_player: str, board) -> str:
    """現在の盤面 board を用いて USI を KIF 風に整形。打/成を表現。"""
    prefix = '▲' if current_player == 'b' else '△'
    if not usi_move:
        return prefix + '？'
    try:
        # 打ち手: e.g., P*7f
        if '*' in usi_move:
            pt_letter, rest = usi_move.split('*', 1)
            to_file = int(rest[0])
            to_rank = rest[1]
            piece_k = PIECE_KANJI.get(pt_letter.upper(), '？')
            return f"{prefix}{_format_square_kanji(to_file, to_rank)}{piece_k}打"

        # 通常手: 7g7f or 2b3c+
        promote = usi_move.endswith('+')
        core = usi_move[:-1] if promote else usi_move
        if len(core) < 4:
            return prefix + usi_move
        from_sq = core[0:2]
        to_file = int(core[2])
        to_rank = core[3]

        piece_k = '？'
        if board is not None and shogi is not None:
            try:
                mv = shogi.Move.from_usi(core)
                # まず piece_type_at で基本駒種を取得
                pt = None
                try:
                    pt = board.piece_type_at(mv.from_square)
                except Exception:
                    pt = None

                if pt in PIECE_TYPE_TO_KANJI:
                    piece_k = PIECE_TYPE_TO_KANJI[pt]
                    # 可能なら成り状態を確認
                    try:
                        p = board.piece_at(mv.from_square)
                    except Exception:
                        p = None
                    if p is not None and getattr(p, 'promoted', False):
                        piece_k = PROMOTED_KANJI_BY_BASE.get(pt, piece_k)
                else:
                    # 最後の手段: 実際の駒オブジェクトから記号を得る
                    try:
                        p = board.piece_at(mv.from_square)
                    except Exception:
                        p = None
                    if p is not None:
                        sym = getattr(p, 'symbol', None)
                        if callable(sym):
                            try:
                                piece_k = PIECE_KANJI.get(sym().upper().lstrip('+'), '？')
                                if getattr(p, 'promoted', False):
                                    # 記号ベースでの成り調整
                                    pt2 = getattr(p, 'piece_type', None)
                                    if pt2 in PROMOTED_KANJI_BY_BASE:
                                        piece_k = PROMOTED_KANJI_BY_BASE.get(pt2, piece_k)
                            except Exception:
                                pass
            except Exception:
                pass
        # board が無ければ（または失敗時）は駒種不明「？」
        kif = f"{prefix}{_format_square_kanji(to_file, to_rank)}{piece_k}"
        if promote:
            kif += '成'
        return kif
    except Exception:
        return prefix + usi_move


def usi_to_notation_simple(usi_move: str, current_player: str) -> str:
    """フォールバック: board 無しで最小限整形（駒種は不明時『？』）。"""
    prefix = '▲' if current_player == 'b' else '△'
    if not usi_move:
        return prefix + '？'
    try:
        if '*' in usi_move:
            pt, rest = usi_move.split('*', 1)
            to_file = int(rest[0])
            to_rank = rest[1]
            piece_k = PIECE_KANJI.get(pt.upper(), '？')
            return f"{prefix}{_format_square_kanji(to_file, to_rank)}{piece_k}打"
        promote = usi_move.endswith('+')
        core = usi_move[:-1] if promote else usi_move
        if len(core) < 4:
            return prefix + usi_move
        to_file = int(core[2])
        to_rank = core[3]
        kif = f"{prefix}{_format_square_kanji(to_file, to_rank)}？"
        if promote:
            kif += '成'
        return kif
    except Exception:
        return prefix + usi_move


def _load_engine_adapter(root_path: str):
    from importlib.machinery import SourceFileLoader
    adapter_path = os.path.join(root_path, 'tools', 'engine_adapter.py')
    mod = SourceFileLoader('engine_adapter', adapter_path).load_module()
    return mod.EngineAdapter


def collect_candidates_via_engine(
    *,
    engine_path: str,
    root_path: str,
    moves: List[str],
    current_player: str,
    limit: int = 4,
    movetime_ms: int = 1000,
    logger: Optional[Any] = None,
) -> Optional[List[Dict[str, Any]]]:
    """ローカルUSIエンジンを直接起動して MultiPV 候補を収集。
    失敗時は None。
    """
    log = (logger.info if logger else (lambda *_: None))
    warn = (logger.warning if logger else (lambda *_: None))

    try:
        EngineAdapter = _load_engine_adapter(root_path)
    except Exception as e:
        warn(f"EngineAdapter load failed: {e}")
        return None

    import threading
    candidates_by_idx: Dict[int, Dict[str, Any]] = {}
    eval_type_by_idx: Dict[int, str] = {}
    best_event = threading.Event()

    # 盤面を一度だけ構築（候補手の表記に使用）
    board_for_notation = build_board_from_moves(moves)

    def on_info(d: Dict[str, Any]):
        try:
            raw = d.get('raw', '') or ''
            m = re.search(r'\bmultipv (\d+)', raw)
            idx = int(m.group(1)) if m else 1
            pv = d.get('pv') or []
            if not pv:
                return
            first = pv[0]
            score_cp = d.get('score_cp')
            mate = d.get('mate')

            eval_val: int
            eval_type = 'unknown'
            if score_cp is not None:
                eval_val = score_cp
                eval_type = 'cp'
            elif mate is not None:
                eval_val = 30000 if mate > 0 else -30000
                eval_type = 'mate'
            else:
                eval_val = 0

            # 表記は可能なら盤面を使って駒種を特定
            if board_for_notation is not None:
                notation = usi_to_kif_with_board(first, current_player, board_for_notation)
            else:
                notation = usi_to_notation_simple(first, current_player)

            candidates_by_idx[idx] = {
                'move': first,
                'notation': notation,
                'eval': eval_val,
                'rank': idx,
                'source': 'engine',
            }
            eval_type_by_idx[idx] = eval_type
        except Exception:
            pass

    def on_best(_):
        best_event.set()

    adapter = EngineAdapter(
        engine_path,
        options={"Threads": 2, "USI_Hash": 256, "MultiPV": max(1, int(limit)), "USI_Ponder": "false"},
        on_info=on_info,
        on_best=on_best,
    )

    try:
        adapter.start()
        if moves:
            adapter.position('startpos', moves)
        else:
            adapter.position('startpos')
        adapter.go(movetime_ms=movetime_ms)
        best_event.wait(timeout=(movetime_ms / 1000.0) + 1.5)
    except Exception as e:
        warn(f"Engine think error: {e}")
    finally:
        try:
            adapter.stop()
        except Exception:
            pass
        try:
            adapter.quit()
        except Exception:
            pass

    if not candidates_by_idx:
        return None

    out: List[Dict[str, Any]] = []
    for i in sorted(candidates_by_idx.keys()):
        if i > limit:
            continue
        c = dict(candidates_by_idx[i])
        et = eval_type_by_idx.get(i)
        if et:
            c['eval_type'] = et
        # 互換フィールド: 'usi' を 'move' の別名として付与
        if 'move' in c and 'usi' not in c:
            c['usi'] = c['move']
        out.append(c)
    return out


def predefined_candidates(move_count: int, current_player: str) -> List[Dict[str, Any]]:
    """定義済み候補（簡易ブック）。"""
    if move_count == 0:
        return (
            [
                {'move': '7g7f', 'notation': '▲７六歩', 'eval': 32, 'rank': 1},
                {'move': '2g2f', 'notation': '▲２六歩', 'eval': 28, 'rank': 2},
                {'move': '6g6f', 'notation': '▲６六歩', 'eval': 15, 'rank': 3},
                {'move': '5g5f', 'notation': '▲５六歩', 'eval': 8, 'rank': 4},
            ]
            if current_player == 'b'
            else [
                {'move': '3c3d', 'notation': '△３四歩', 'eval': -30, 'rank': 1},
                {'move': '8c8d', 'notation': '△８四歩', 'eval': -25, 'rank': 2},
                {'move': '4c4d', 'notation': '△４四歩', 'eval': -18, 'rank': 3},
                {'move': '5c5d', 'notation': '△５四歩', 'eval': -12, 'rank': 4},
            ]
        )
    if move_count <= 10:
        return (
            [
                {'move': '7i6h', 'notation': '▲６八銀', 'eval': 45, 'rank': 1},
                {'move': '5i4h', 'notation': '▲４八金', 'eval': 38, 'rank': 2},
                {'move': '2h7h', 'notation': '▲７八飛', 'eval': 32, 'rank': 3},
                {'move': '6i7i', 'notation': '▲７九角', 'eval': 25, 'rank': 4},
            ]
            if current_player == 'b'
            else [
                {'move': '3a3b', 'notation': '△３二銀', 'eval': -42, 'rank': 1},
                {'move': '5a4b', 'notation': '△４二金', 'eval': -38, 'rank': 2},
                {'move': '8b3b', 'notation': '△３二飛', 'eval': -35, 'rank': 3},
                {'move': '4a3b', 'notation': '△３二角', 'eval': -28, 'rank': 4},
            ]
        )
    if move_count <= 30:
        return (
            [
                {'move': '6h7g', 'notation': '▲７七銀', 'eval': 58, 'rank': 1},
                {'move': '4h3h', 'notation': '▲３八金', 'eval': 52, 'rank': 2},
                {'move': '7h4h', 'notation': '▲４八飛', 'eval': 48, 'rank': 3},
                {'move': '3g3f', 'notation': '▲３六歩', 'eval': 35, 'rank': 4},
            ]
            if current_player == 'b'
            else [
                {'move': '3b4c', 'notation': '△４三銀', 'eval': -55, 'rank': 1},
                {'move': '4b3c', 'notation': '△３三金', 'eval': -48, 'rank': 2},
                {'move': '3b6b', 'notation': '△６二飛', 'eval': -45, 'rank': 3},
                {'move': '7c7d', 'notation': '△７四歩', 'eval': -38, 'rank': 4},
            ]
        )
    # 31手以降
    return (
        [
            {'move': '4h2h', 'notation': '▲２八飛', 'eval': 72, 'rank': 1},
            {'move': '7g8f', 'notation': '▲８六銀', 'eval': 65, 'rank': 2},
            {'move': '3h4g', 'notation': '▲４七金', 'eval': 58, 'rank': 3},
            {'move': '1i1h', 'notation': '▲１八香', 'eval': 42, 'rank': 4},
        ]
        if current_player == 'b'
        else [
            {'move': '6b8b', 'notation': '△８二飛', 'eval': -68, 'rank': 1},
            {'move': '4c3d', 'notation': '△３四銀', 'eval': -62, 'rank': 2},
            {'move': '3c2d', 'notation': '△２四金', 'eval': -55, 'rank': 3},
            {'move': '9a9b', 'notation': '△９二香', 'eval': -48, 'rank': 4},
        ]
    )


def fallback_candidates(current_player: str) -> List[Dict[str, Any]]:
    if current_player == 'b':
        return [
            {'move': '7g7f', 'notation': '▲７六歩', 'eval': 20, 'rank': 1, 'source': 'fallback'},
            {'move': '2g2f', 'notation': '▲２六歩', 'eval': 15, 'rank': 2, 'source': 'fallback'},
            {'move': '6g6f', 'notation': '▲６六歩', 'eval': 10, 'rank': 3, 'source': 'fallback'},
            {'move': '5g5f', 'notation': '▲５六歩', 'eval': 5, 'rank': 4, 'source': 'fallback'},
        ]
    return [
        {'move': '3c3d', 'notation': '△３四歩', 'eval': -20, 'rank': 1, 'source': 'fallback'},
        {'move': '8c8d', 'notation': '△８四歩', 'eval': -15, 'rank': 2, 'source': 'fallback'},
        {'move': '4c4d', 'notation': '△４四歩', 'eval': -10, 'rank': 3, 'source': 'fallback'},
        {'move': '5c5d', 'notation': '△５四歩', 'eval': -5, 'rank': 4, 'source': 'fallback'},
    ]


def emergency_candidates(current_player: str) -> List[Dict[str, Any]]:
    return (
        [
            {'move': '7g7f', 'notation': '▲７六歩', 'eval': 0, 'rank': 1, 'source': 'emergency'},
            {'move': '2g2f', 'notation': '▲２六歩', 'eval': 0, 'rank': 2, 'source': 'emergency'},
        ]
        if current_player == 'b'
        else [
            {'move': '3c3d', 'notation': '△３四歩', 'eval': 0, 'rank': 1, 'source': 'emergency'},
            {'move': '8c8d', 'notation': '△８四歩', 'eval': 0, 'rank': 2, 'source': 'emergency'},
        ]
    )


def generate_candidates(
    *,
    moves: List[str],
    current_player: str,
    limit: int = 4,
    movetime_ms: int = 1000,
    logger: Optional[Any] = None,
    config: Optional[Dict[str, Any]] = None,
    root_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """候補手の総合生成器。
    - USIエンジン（ローカル）優先
    - 利用不可なら定義済み
    - さらに失敗時はフォールバック/エマージェンシー
    """
    log = (logger.info if logger else (lambda *_: None))
    warn = (logger.warning if logger else (lambda *_: None))

    if not isinstance(moves, list):
        moves = []
    if current_player not in ('b', 'w'):
        current_player = 'b'

    cfg = config or {}
    engine_path = (cfg.get('USI_ENGINE_PATH', '') or '').strip()
    base_path = root_path or cfg.get('ROOT_PATH') or os.getcwd()
    mt = int(cfg.get('CANDIDATE_MOVETIME_MS', movetime_ms))
    top_n = max(1, int(cfg.get('CANDIDATE_LIMIT', limit)))

    # 盤面（表記生成用）を最初に構築
    board = build_board_from_moves(moves)

    # 1) エンジン（MultiPV）
    if engine_path and os.path.exists(engine_path):
        try:
            got = collect_candidates_via_engine(
                engine_path=engine_path,
                root_path=base_path,
                moves=moves,
                current_player=current_player,
                limit=top_n,
                movetime_ms=mt,
                logger=logger,
            )
            if got:
                # 念のため最終整形（将来の変更に備え統一）
                try:
                    for c in got:
                        mv = c.get('move') or c.get('usi') or c.get('USI')
                        if not mv:
                            continue
                        c['notation'] = (
                            usi_to_kif_with_board(mv, current_player, board)
                            if board is not None else
                            usi_to_notation_simple(mv, current_player)
                        )
                except Exception:
                    pass
                return got
        except Exception as e:
            warn(f"engine candidates failed: {e}")
    else:
        warn("USI engine path not configured or not found. Set USI_ENGINE_PATH.")

    # 2) 定義済み（簡易ブック）
    try:
        book = predefined_candidates(len(moves), current_player)
        if book:
            for i, c in enumerate(book, 1):
                c.setdefault('source', 'predefined')
                c['rank'] = i
            # 表記を統一して上書き
            try:
                for c in book:
                    mv = c.get('move')
                    if not mv:
                        continue
                    c.setdefault('usi', mv)
                    c['notation'] = (
                        usi_to_kif_with_board(mv, current_player, board)
                        if board is not None else
                        usi_to_notation_simple(mv, current_player)
                    )
            except Exception:
                pass
            return book[:top_n]
    except Exception:
        pass

    # 3) フォールバック
    fb = fallback_candidates(current_player)
    if fb:
        try:
            for c in fb:
                mv = c.get('move')
                if not mv:
                    continue
                c.setdefault('usi', mv)
                c['notation'] = (
                    usi_to_kif_with_board(mv, current_player, board)
                    if board is not None else
                    usi_to_notation_simple(mv, current_player)
                )
        except Exception:
            pass
        return fb[:top_n]

    # 4) エマージェンシー
    em = emergency_candidates(current_player)
    try:
        for c in em:
            mv = c.get('move')
            if not mv:
                continue
            c.setdefault('usi', mv)
            c['notation'] = (
                usi_to_kif_with_board(mv, current_player, board)
                if board is not None else
                usi_to_notation_simple(mv, current_player)
            )
    except Exception:
        pass
    return em
