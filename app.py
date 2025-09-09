"""
Flaskアプリケーションファクトリ

このモジュールには、アプリケーションインスタンスを作成する
create_app関数が定義されています。
"""

import os
import logging
import sys
import platform
import time
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_debugtoolbar import DebugToolbarExtension
from flask_mail import Mail, Attachment, Message
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
from email_validator import validate_email, EmailNotValidError
from datetime import datetime

# 環境変数の読み込み
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# データベースとログインマネージャーのインポート
from apps.models import db, login_manager


def create_app(config_name=None):
    """
    アプリケーションファクトリ
    
    Args:
        config_name (str): 使用する設定名（development, production, testing）
    
    Returns:
        Flask: 設定済みのFlaskアプリケーションインスタンス
    """
    app = Flask(__name__, 
                template_folder='apps/templates',
                static_folder='apps/static',
                static_url_path='/static')
    
    # 設定の読み込み
    from config import config
    config_name = config_name or os.environ.get('FLASK_CONFIG') or 'default'
    app.config.from_object(config[config_name])
    
    # データベースの初期化
    db.init_app(app)
    
    # Flask-Migrateの初期化
    migrate = Migrate(app, db)
    
    # Flask-Loginの初期化
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'ログインが必要です。'
    login_manager.login_message_category = 'info'
    
    # CSRF保護の初期化
    csrf = CSRFProtect(app)
    
    # CSRF保護の除外設定
    csrf.exempt('debugtoolbar.template_preview')
    csrf.exempt('debugtoolbar.sql_select')
    csrf.exempt('debugtoolbar.sql_explain')
    
    # 静的ファイルを除外
    @app.before_request
    def exempt_static():
        if request.endpoint == 'static':
            return None
    
    # ユーザーローダー関数はmodel.pyで定義済み
    
    # ブループリントの登録
    register_blueprints(app)
    
    # 拡張機能の初期化
    register_extensions(app)
    
    # ログ設定
    configure_logging(app)
    
    # ルートの登録
    register_routes(app)
    
    # エラーハンドラーの登録
    register_error_handlers(app)
    
    return app


def register_blueprints(app):
    """ブループリントを登録"""
    from apps.auth import auth_bp
    from apps.admin import admin_bp
    from apps.crud import crud_bp
    from apps.contact import contact_bp
    from apps.shogi import shogi_bp
    from apps.detector import detector_bp
    
    # ルートをインポート（ブループリントのエンドポイントを登録するため）
    from apps.auth import routes as auth_routes  # noqa: F401
    from apps.admin import routes as admin_routes  # noqa: F401
    from apps.crud import routes as crud_routes  # noqa: F401
    from apps.contact import routes as contact_routes  # noqa: F401
    from apps.shogi import routes as shogi_routes  # noqa: F401
    from apps.detector import routes as detector_routes  # noqa: F401
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(crud_bp, url_prefix='/crud')
    app.register_blueprint(contact_bp, url_prefix='/contact')
    app.register_blueprint(shogi_bp, url_prefix='/shogi')
    app.register_blueprint(detector_bp, url_prefix='/detector')


def register_extensions(app):
    """拡張機能を初期化"""
    # デバッグツールバー（開発環境のみ）
    if app.debug:
        toolbar = DebugToolbarExtension(app)
        app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
    
    # メール
    mail = Mail(app)
    app.mail = mail


def configure_logging(app):
    """ログ設定を構成"""
    # ログディレクトリを作成
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # アプリケーションログ（INFO以上）- ルートディレクトリ
    app_file_handler = RotatingFileHandler(
        'app.log', maxBytes=102400, backupCount=5, encoding='utf-8'
    )
    app_file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    app_file_handler.setLevel(logging.INFO)
    app.logger.addHandler(app_file_handler)
    
    # アプリケーションログ（INFO以上）- logsディレクトリ（バックアップ用）
    logs_file_handler = RotatingFileHandler(
        'logs/app.log', maxBytes=102400, backupCount=5, encoding='utf-8'
    )
    logs_file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    logs_file_handler.setLevel(logging.INFO)
    app.logger.addHandler(logs_file_handler)
    
    # エラーログ（ERROR以上）
    error_file_handler = RotatingFileHandler(
        'error.log', maxBytes=102400, backupCount=5, encoding='utf-8'
    )
    error_file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    error_file_handler.setLevel(logging.ERROR)
    app.logger.addHandler(error_file_handler)
    
    # ログレベルをDEBUGに設定（より詳細なログを記録）
    app.logger.setLevel(logging.DEBUG)
    
    # コンソールにもログを出力
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s'
    ))
    app.logger.addHandler(console_handler)
    
    # アプリケーション起動ログ
    app.logger.info('アプリケーション起動')
    app.logger.info('ログ設定完了 - app.log と error.log に記録されます')


def register_routes(app):
    """ルートを登録"""
    
    @app.route("/")
    def index():
        """ルートアクセス処理"""
        from flask_login import current_user
        from flask_login import current_user
        
        # 未認証ユーザーはログイン画面へ
        if not current_user.is_authenticated:
            app.logger.info('未認証ユーザー - ログイン画面へリダイレクト')
            return redirect(url_for('auth.login'))
        
        # 認証済みユーザーはダッシュボードを表示
        app.logger.info(f'認証済みユーザー {current_user.username} - ダッシュボード表示')
        return render_template("index.html")

    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        """アップロードされた画像を配信（検知用）"""
        from flask import send_from_directory
        return send_from_directory(app.config['DETECTOR_UPLOAD_FOLDER'], filename)
    
    @app.route('/images/<filename>')
    def images_file(filename):
        """画像ファイルを配信（UPLOAD_FOLDERから）"""
        from flask import send_from_directory
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


def register_error_handlers(app):
    """エラーハンドラーを登録"""
    
    @app.errorhandler(404)
    def error_404(error):
        # 静的ファイルやデバッグツールバーの404はログレベルを下げる
        if request.endpoint and ('static' in request.endpoint or 'debugtoolbar' in request.endpoint):
            app.logger.debug(f'404 Error (static/debug): {error}')
        else:
            app.logger.warning(f'404 Error: {error}')
        return render_template('error_pages/404.html'), 404
    
    @app.errorhandler(403)
    def error_403(error):
        app.logger.warning(f'403 Error: {error}')
        return render_template('error_pages/403.html'), 403
    
    @app.errorhandler(500)
    def error_500(error):
        app.logger.error(f'500 Error: {error}')
        return render_template('error_pages/500.html'), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        import traceback
        app.logger.error(f'Unhandled Exception: {error}')
        app.logger.error(f'Traceback: {traceback.format_exc()}')
        try:
            return render_template('error_pages/500.html'), 500
        except:
            return f"<h1>Internal Server Error</h1><p>{error}</p>", 500


# 添付ファイルの読み込み
try:
    with open("requirements.txt", "rb") as f:
        attachment_data = f.read()
except FileNotFoundError:
    attachment_data = None



