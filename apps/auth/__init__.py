from flask import Blueprint

# 認証ブループリントを作成
auth_bp = Blueprint('auth', __name__, 
                   template_folder='templates',
                   static_folder='static')

# ルートをインポート（循環インポートを避けるため）
from . import routes  # noqa: F401
