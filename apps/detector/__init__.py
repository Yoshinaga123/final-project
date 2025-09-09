"""
物体検知機能のブループリント初期化
"""

from flask import Blueprint
from zoneinfo import ZoneInfo
from datetime import datetime

# 物体検知ブループリントの作成
detector_bp = Blueprint(
    'detector',
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/detector'
)

# Jinjaフィルタ: JST表示用
@detector_bp.app_template_filter('jst')
def jst(dt: datetime, fmt: str = '%Y/%m/%d %H:%M') -> str:
    """UTC想定の日時を日本時間(Asia/Tokyo)でフォーマットする。
    未設定や不正値は空文字を返す。
    """
    if not dt:
        return ''
    try:
        # タイムゾーン未設定はUTCとみなす
        if getattr(dt, 'tzinfo', None) is None:
            dt = dt.replace(tzinfo=ZoneInfo('UTC'))
        return dt.astimezone(ZoneInfo('Asia/Tokyo')).strftime(fmt)
    except Exception:
        try:
            return dt.strftime(fmt)
        except Exception:
            return str(dt)

# ルートのインポート
from . import routes
