from flask import Blueprint

# Adminブループリントの作成
admin_bp = Blueprint('admin', __name__, 
                    template_folder='templates',
                    static_folder='static')

# ルートをインポート（循環インポートを避けるため）
from . import routes
