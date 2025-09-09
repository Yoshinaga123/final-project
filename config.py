"""
アプリケーション設定

このモジュールには、アプリケーションの設定が定義されています。
環境に応じて異なる設定を適用できます。
"""

import os
from pathlib import Path

# ベースディレクトリの設定
basedir = Path(__file__).parent

class Config:
    """基本設定クラス"""
    
    # セキュリティ設定
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # データベース設定
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + str(basedir / 'local.sqlite')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_RECORD_QUERIES = True
    
    # 画像アップロード設定 - apps/imagesを指定（将来の商品販売サイト用）
    UPLOAD_FOLDER = str(basedir / 'apps' / 'images')
    
    # 画像検知専用アップロード設定
    DETECTOR_UPLOAD_FOLDER = str(basedir / 'apps' / 'detector' / 'images')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB制限
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'jfif'}
    
    # メール設定
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    MAIL_DEBUG = os.environ.get('MAIL_DEBUG', 'True').lower() == 'true'
    
    # その他の設定
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    DEBUG_TB_INTERCEPT_REDIRECTS = False

# BaseConfigクラス（エイリアス）
BaseConfig = Config

class LocalConfig(Config):
    """ローカル開発環境用設定"""
    DEBUG = True
    
    # その他のローカル設定
    SQLALCHEMY_ECHO = True
    TEMPLATES_AUTO_RELOAD = True

class DevelopmentConfig(Config):
    """開発環境用設定"""
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """本番環境用設定"""
    DEBUG = False
    SQLALCHEMY_ECHO = False

class TestingConfig(Config):
    """テスト環境用設定"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# 設定の辞書
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'local': LocalConfig,
    'default': DevelopmentConfig
}
