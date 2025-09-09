"""
データベースモデル定義

このモジュールには、アプリケーションで使用するSQLAlchemyモデルが定義されています。
各モデルはデータベーステーブルに対応し、データの構造と操作を定義します。
"""

from datetime import datetime
from flask_login import UserMixin, LoginManager
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# データベースオブジェクトの作成
# アプリケーションインスタンスに依存しない形で定義
db = SQLAlchemy()

# ログインマネージャーの作成
# アプリケーションインスタンスに依存しない形で定義
login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    """
    ユーザーIDからユーザーオブジェクトを取得する関数
    
    Flask-LoginがセッションからユーザーIDを取得した際に、
    この関数が呼び出されてユーザーオブジェクトを返します。
    
    Args:
        user_id (str): セッションに保存されたユーザーID
        
    Returns:
        User: ユーザーオブジェクト（見つからない場合はNone）
    """
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):#UserMixinを継承して、ユーザー情報を管理するためのモデルです。
    """
    ユーザーモデル
    
    システムのユーザー情報を管理するためのモデルです。
    認証、プロフィール管理、セッション管理に使用されます。
    """
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}

    # 基本フィールド
    id = db.Column(db.Integer, primary_key=True, comment='ユーザーID（主キー）')
    username = db.Column(db.String(64), index=True, unique=True, nullable=False, comment='ユーザー名（一意）')
    email = db.Column(db.String(120), index=True, unique=True, nullable=False, comment='メールアドレス（一意）')
    password_hash = db.Column(db.String(128), nullable=False, comment='パスワードハッシュ')
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='作成日時')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新日時')
    
    # ステータス管理
    is_active = db.Column(db.Boolean, default=True, comment='アカウント有効フラグ')
    is_admin = db.Column(db.Boolean, default=False, comment='管理者フラグ')
    
    # 追加のユーザー属性
    organization = db.Column(db.String(100), comment='所属')
    last_login = db.Column(db.DateTime, comment='最終ログイン日時')
    access_count = db.Column(db.Integer, default=0, comment='アクセス回数')
    status = db.Column(db.String(20), default='active', comment='ログイン状態')
    login_attempts = db.Column(db.Integer, default=0, comment='ログイン試行回数')
    role = db.Column(db.String(20), default='user', comment='権限/ロール')

    def set_password(self, password):
        """
        パスワードをハッシュ化して設定
        
        Args:
            password (str): 設定するパスワード（平文）
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """
        パスワードの検証
        
        Args:
            password (str): 検証するパスワード（平文）
            
        Returns:
            bool: パスワードが正しい場合True
        """
        return check_password_hash(self.password_hash, password)

    @property
    def password(self):
        """
        パスワードプロパティ（読み取り不可）
        
        Raises:
            AttributeError: パスワードの直接読み取りを防止
        """
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        """
        パスワードセッター（自動ハッシュ化）
        
        Args:
            password (str): 設定するパスワード（平文）
        """
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        """
        パスワードの検証（check_passwordのエイリアス）
        
        Args:
            password (str): 検証するパスワード（平文）
            
        Returns:
            bool: パスワードが正しい場合True
        """
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        """文字列表現"""
        return f'<User {self.username}>'


class Address(db.Model):
    """
    住所モデル
    
    ユーザーの住所情報を管理するためのモデルです。
    配送先、請求先などの住所データに使用されます。
    """
    __tablename__ = 'addresses'
    __table_args__ = {'extend_existing': True}
    # 基本フィールド
    id = db.Column(db.Integer, primary_key=True, comment='住所ID（主キー）')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='ユーザーID（外部キー）')
    
    # 住所情報
    name = db.Column(db.String(100), nullable=False, comment='宛先名')
    postal_code = db.Column(db.String(10), comment='郵便番号')
    prefecture = db.Column(db.String(20), comment='都道府県')
    city = db.Column(db.String(50), comment='市区町村')
    address_line1 = db.Column(db.String(100), comment='住所1（町名・番地）')
    address_line2 = db.Column(db.String(100), comment='住所2（建物名・部屋番号）')
    phone = db.Column(db.String(20), comment='電話番号')
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='作成日時')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新日時')
    
    # ステータス
    is_default = db.Column(db.Boolean, default=False, comment='デフォルト住所フラグ')
    is_active = db.Column(db.Boolean, default=True, comment='有効フラグ')

    # リレーションシップ
    user = db.relationship('User', backref=db.backref('addresses', lazy='dynamic'))

    def __repr__(self):
        """文字列表現"""
        return f'<Address {self.name} - {self.city}>'

    def debug_info(self):
        """
        住所インスタンスの詳細なデバッグ情報を返す
        
        Returns:
            str: デバッグ情報の文字列
        """
        info = {
            "id": self.id,
            "user_id": self.user_id,    
            "name": self.name,
            "postal_code": self.postal_code,
            "prefecture": self.prefecture,
            "city": self.city,
            "address_line1": self.address_line1,
            "address_line2": self.address_line2,
            "phone": self.phone,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_default": self.is_default,
            "is_active": self.is_active,
            "user_repr": repr(self.user) if self.user else None
        }
        # 見やすいように整形して返す
        return f"Address Debug Info: {info}"

    def print_debug(self):
        """
        デバッグ情報を標準出力に表示する
        """
        print(self.debug_info())


class UserImage(db.Model):
    """
    ユーザー画像モデル
    
    ログインしたユーザーがアップロードした画像のURL情報を管理するモデルです。
    usersテーブルとのリレーションを持ちます。
    """
    __tablename__ = 'user_images'
    __table_args__ = {'extend_existing': True}

    # 基本フィールド
    id = db.Column(db.Integer, primary_key=True, comment='画像ID（主キー）')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='ユーザーID（外部キー）')
    
    # 画像情報
    image_path = db.Column(db.String(255), nullable=False, comment='画像パス')
    filename = db.Column(db.String(255), nullable=False, comment='ファイル名')
    original_filename = db.Column(db.String(255), comment='元のファイル名')
    
    # タイムスタンプ
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='アップロード日時')
    
    # ステータス
    is_active = db.Column(db.Boolean, default=True, comment='有効フラグ')
    is_deleted = db.Column(db.Boolean, default=False, comment='論理削除フラグ')

    # リレーションシップ
    user = db.relationship('User', backref=db.backref('user_images', lazy='dynamic'))

    def __repr__(self):
        """文字列表現"""
        return f'<UserImage {self.image_path} by User {self.user_id}>'

    def to_dict(self):
        """
        辞書形式でデータを返す
        
        Returns:
            dict: 画像データの辞書
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'image_path': self.image_path,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'is_active': self.is_active,
            'is_deleted': self.is_deleted
        }



