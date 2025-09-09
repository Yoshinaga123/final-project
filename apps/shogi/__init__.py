"""
将棋機能ブループリント

将棋盤GUI、棋譜入力、棋譜管理などの機能を提供します。
"""

from flask import Blueprint

shogi_bp = Blueprint('shogi', __name__, url_prefix='/shogi', template_folder='templates')

from . import routes
