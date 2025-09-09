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
    app = Flask(__name__)
    
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
    
    # ユーザーローダー関数の設定
    @login_manager.user_loader
    def load_user(user_id):
        """セッションからユーザーを取得する関数"""
        from apps.models import User
        return User.query.get(int(user_id))
    
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
    
    # ルートをインポート（ブループリントのエンドポイントを登録するため）
    from apps.auth import routes as auth_routes  # noqa: F401
    from apps.admin import routes as admin_routes  # noqa: F401
    from apps.crud import routes as crud_routes  # noqa: F401
    from apps.contact import routes as contact_routes  # noqa: F401
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(crud_bp, url_prefix='/crud')
    app.register_blueprint(contact_bp, url_prefix='/contact')


def register_extensions(app):
    """拡張機能を初期化"""
    # デバッグツールバー
    toolbar = DebugToolbarExtension(app)
    
    # メール
    mail = Mail(app)
    app.mail = mail


def configure_logging(app):
    """ログ設定を構成"""
    if not app.debug and not app.testing:
        # 本番環境でのログ設定
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/app.log', maxBytes=10240, backupCount=10, encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('アプリケーション起動')


def register_routes(app):
    """ルートを登録"""
    
    @app.route("/")
    def index():
        """トップページ"""
        return render_template("index.html")


def register_error_handlers(app):
    """エラーハンドラーを登録"""
    
    @app.errorhandler(404)
    def error_404(error):
        return render_template('error_pages/404.html'), 404
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        try:
            app.logger.error(f'Unhandled Exception: {error}')
            return render_template('error_pages/500.html'), 500
        except:
            return f"<h1>Internal Server Error</h1><p>{error}</p>", 500


# 添付ファイルの読み込み
try:
    with open("requirements.txt", "rb") as f:
        attachment_data = f.read()
except FileNotFoundError:
    attachment_data = None
