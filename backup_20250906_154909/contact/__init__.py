"""
問い合わせ機能のブループリント

このモジュールには、お問い合わせ機能が実装されています。
"""

from flask import Blueprint

# 問い合わせ用ブループリントの作成
# url_prefix='/contact'により、すべてのルートが/contact/で始まる
# template_folder='templates'により、テンプレートディレクトリを指定
contact_bp = Blueprint('contact', __name__, url_prefix='/contact', template_folder='templates')

