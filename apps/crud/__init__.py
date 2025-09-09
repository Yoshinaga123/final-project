from flask import Blueprint

# CRUDブループリントの作成
crud_bp = Blueprint('crud', __name__, 
                   template_folder='templates',
                   static_folder='static')

# ルートをインポート（循環インポートを避けるため）
from . import routes
