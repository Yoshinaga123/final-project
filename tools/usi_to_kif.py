#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USI → KIF 変換ライブラリ（盤面トレース対応）
KifuForJS 連携用
"""
from __future__ import annotations
import datetime

try:
    import shogi
    HAS_SHOGI = True
except Exception:
    HAS_SHOGI = False


class USIToKIFConverter:
    KAN_FILE = {'9':'九','8':'八','7':'七','6':'六','5':'五','4':'四','3':'三','2':'二','1':'一'}
    KAN_RANK = {'a':'一','b':'二','c':'三','d':'四','e':'五','f':'六','g':'七','h':'八','i':'九'}

    PIECE_NAME = {
        # shogi.PAWN などの数値は実行時に埋める（HAS_SHOGI true の場合）
        'P': '歩', 'L': '香', 'N': '桂', 'S': '銀', 'G': '金', 'B': '角', 'R': '飛', 'K': '玉'
    }
    PROMOTED_NAME = {  # 角/飛は 馬/龍、その他は ～成 を使う
        'P': 'と', 'L': '成香', 'N': '成桂', 'S': '成銀', 'B': '馬', 'R': '龍'
    }

    def __init__(self, start_position: str = "startpos"):
        self.position = start_position  # "startpos" or "sfen ..."
        self.moves = []                 # [{'number':i,'usi':..., 'elapsed':ms?}, ...]
        self.prev_to_square = None      # 直前の移動先（「同」判定用）
        if HAS_SHOGI:
            self.board = shogi.Board() if start_position == "startpos" \
                else shogi.Board(sfen=start_position.replace("sfen ", ""))
            # shogi.* 定数に基づく名称テーブル（保険）
            self._pt_to_name = {
                shogi.PAWN:'歩', shogi.LANCE:'香', shogi.KNIGHT:'桂', shogi.SILVER:'銀',
                shogi.GOLD:'金', shogi.BISHOP:'角', shogi.ROOK:'飛', shogi.KING:'玉'
            }
        else:
            self.board = None
            self._pt_to_name = None  # フォールバック時は使わない

    # ---------- 公開API ----------
    def convert_game_to_kif(self, moves_list, game_info=None, per_move_ms=None) -> str:
        """
        moves_list: ["7g7f", "8c8d", ...]
        per_move_ms: [ms0, ms1, ...] 省略可
        """
        header = self._generate_kif_header(game_info)
        lines = [header]
        for i, usi_move in enumerate(moves_list, 1):
            if HAS_SHOGI and self.board is not None:
                try:
                    mv = shogi.Move.from_usi(usi_move)
                    if mv in self.board.legal_moves:
                        kif = self._usi_to_kif_with_board(usi_move)
                    else:
                        kif = f"[非合法手:{usi_move}]"
                except Exception as e:
                    kif = f"[変換エラー:{usi_move}]"
            else:
                kif = self._usi_to_kif_fallback(usi_move, i)  # 最低限の表記

            elapsed = self._fmt_time(per_move_ms[i-1]) if (per_move_ms and i-1 < len(per_move_ms)) else "00:00:00"
            lines.append(f"{i:4d} {kif:<15} ({elapsed})")

            # 合法手の場合のみ履歴に追加
            if not kif.startswith('['):
                self.moves.append({'number': i, 'usi': usi_move, 'japanese': kif})
        return "\n".join(lines)

    # ---------- 盤面トレース版 ----------
    def _usi_to_kif_with_board(self, usi_move: str) -> str:
        """合法手チェック済みの手をKIF形式に変換（上位でチェック済み前提）"""
        mv = shogi.Move.from_usi(usi_move)
        # 「同」判定
        head = self._head_same_or_sq(mv)

        # 駒打ちの判定（from_squareがNoneまたは81以上）
        is_drop = hasattr(mv, 'drop') and mv.drop or (mv.from_square is None or mv.from_square >= 81)
        
        if is_drop:
            # 駒打ち
            drop_piece = getattr(mv, 'drop_piece_type', None)
            if drop_piece is not None:
                name = self._pt_to_name[drop_piece]
            else:
                # USI文字列から駒種を推定
                if '*' in usi_move:
                    piece_char = usi_move.split('*')[0]
                    name = self.PIECE_NAME.get(piece_char, '駒')
                else:
                    name = '駒'
            self._push(mv)
            return f"{head}{name}打"

        # 駒移動
        piece_type = self.board.piece_type_at(mv.from_square)
        name = self._pt_to_name[piece_type]
        if hasattr(mv, 'promotion') and mv.promotion:
            # 角/飛は 馬/龍、それ以外は ～成
            if name in ('角', '飛'):
                name = self.PROMOTED_NAME['B' if name == '角' else 'R']
            else:
                name = f"{name}成"

        self._push(mv)
        return f"{head}{name}"

    def _head_same_or_sq(self, mv) -> str:
        if self.prev_to_square is not None and self.prev_to_square == mv.to_square:
            return "同　"
        # "7f" → "七六"
        sq = shogi.SQUARE_NAMES[mv.to_square]  # e.g., "7f"
        return f"{self.KAN_FILE[sq[0]]}{self.KAN_RANK[sq[1]]}"

    def _push(self, mv):
        self.prev_to_square = mv.to_square
        self.board.push(mv)

    # ---------- フォールバック（python-shogi未導入時の簡易表記） ----------
    def _usi_to_kif_fallback(self, usi_move: str, move_number: int) -> str:
        # 駒打ち
        if "*" in usi_move:
            piece_char, to = usi_move.split("*")
            return f"{self._sq_to_kan(to)}{self.PIECE_NAME.get(piece_char, '駒')}打"
        # 通常移動（駒種は推定のまま）
        frm, to = usi_move[:2], usi_move[2:4]
        promo = usi_move.endswith("+")
        name = self._guess_piece_from_move(usi_move, move_number)
        if promo and name in ('角','飛'):
            name = self.PROMOTED_NAME['B' if name == '角' else 'R']
        elif promo:
            name = f"{name}成"
        # 「同」判定（簡易：直前着手の to と比較）
        same = (len(self.moves) and self.moves[-1]['usi'][2:4] == to)
        head = "同　" if same else self._sq_to_kan(to)
        return f"{head}{name}"

    # ---------- 共通ユーティリティ ----------
    def _sq_to_kan(self, sq: str) -> str:
        # "7f" -> "七六"
        return f"{self.KAN_FILE.get(sq[0], sq[0])}{self.KAN_RANK.get(sq[1], sq[1])}"

    def _fmt_time(self, ms: int) -> str:
        if ms is None: return "00:00:00"
        s = max(0, int(round(ms/1000)))
        h, s = divmod(s, 3600)
        m, s = divmod(s, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _generate_kif_header(self, game_info=None) -> str:
        gi = game_info or {}
        date = gi.get('date') or datetime.date.today().strftime("%Y/%m/%d")
        handicap = gi.get('handicap', '平手')
        sente = gi.get('sente', '先手')
        gote = gi.get('gote', '後手')
        return "\n".join([
            "# KIF形式棋譜ファイル Generated by USI Bridge",
            f"開始日時：{date}",
            f"手合割：{handicap}",
            f"先手：{sente}",
            f"後手：{gote}",
            "手数----指手---------消費時間--",
        ])

    # 旧ロジックの簡易推定（保険）
    def _guess_piece_from_move(self, usi_move: str, move_number: int) -> str:
        if usi_move in ["7g7f","2g2f","8g8f","3g3f","1g1f","9g9f"]:
            return "歩"
        if usi_move in ["6i7h","4i5h","5i6h"]:
            return "玉"
        if usi_move.startswith(("8h","2h")):
            return "角" if ("7g" in usi_move or "3g" in usi_move) else "飛"
        return "駒"
    
    # ---------- 後方互換性メソッド ----------
    def usi_to_japanese_move(self, usi_move):
        """単一のUSI手をKIF形式に変換（後方互換性）"""
        try:
            if HAS_SHOGI and self.board is not None:
                return self._usi_to_kif_with_board(usi_move)
            else:
                return self._usi_to_kif_fallback(usi_move, 1)
        except Exception as e:
            return f"[変換エラー:{usi_move}]"


# ---- 簡易テスト ----
def test_converter():
    c = USIToKIFConverter()
    # 修正：合法手のみのテストデータ
    test_moves = ["7g7f","8c8d","2g2f","3c3d","7i7h","4a3b"]  # 期待: 七六歩 / 八四歩 / 二六歩 / 三四歩 / 七八玉 / 三二金
    kif = c.convert_game_to_kif(test_moves, {
        'sente': 'YaneuraOu NNUE',
        'gote': '人間',
        'date': '2025/09/11'
    })
    print("=== 生成されたKIF形式 ===")
    print(kif)
    return kif

if __name__ == "__main__":
    test_converter()
