"""
将棋機能ブループリント

将棋盤GUI、棋譜入力、棋譜管理、USIエンジン対戦などの機能を提供します。
"""

from flask import Blueprint

# 既存のBlueprint（互換性維持のため）
shogi_bp = Blueprint('shogi', __name__, template_folder='templates')

# USI Bridge統合用のBlueprint
bp = Blueprint('shogi_new', __name__, template_folder='templates')

# routes.pyでBlueprintを定義後にインポート
from . import routes  # noqa: E402,F401
