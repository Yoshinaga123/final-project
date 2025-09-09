# SQLAlchemyリレーションシップの使用例

from apps.models.model import User, UserImage, db
from datetime import datetime

def relationship_examples():
    """リレーションシップの使用例を示す関数"""
    
    # 1. ユーザーを取得
    user = User.query.first()
    if user:
        print(f"ユーザー: {user.username}")
        
        # 2. そのユーザーの画像一覧を取得（リレーションシップ経由）
        images = user.user_images.all()  # backrefで自動作成されたプロパティ
        print(f"画像数: {len(images)}")
        
        for image in images:
            print(f"  - {image.filename} (ID: {image.id})")
    
    # 3. 画像からユーザー情報へアクセス
    image = UserImage.query.first()
    if image:
        print(f"\n画像: {image.filename}")
        print(f"所有者: {image.user.username}")  # relationshipで定義したプロパティ
        print(f"所有者メール: {image.user.email}")

def join_examples():
    """テーブル結合の例"""
    
    # 1. 内部結合 (INNER JOIN)
    results = db.session.query(User, UserImage).join(UserImage).all()
    
    # 2. 左外部結合 (LEFT OUTER JOIN)
    results = db.session.query(User).outerjoin(UserImage).all()
    
    # 3. 条件付き結合
    active_users_with_images = (
        db.session.query(User)
        .join(UserImage)
        .filter(User.is_active == True)
        .filter(UserImage.is_deleted == False)
        .all()
    )

# 5. リレーションシップのlazyオプション
class UserWithDifferentLazy(db.Model):
    """異なるlazyオプションの例"""
    
    # lazy='select' (デフォルト): 個別にクエリ実行
    images_select = db.relationship('UserImage', lazy='select')
    
    # lazy='dynamic': クエリオブジェクトを返す（フィルタリング可能）
    images_dynamic = db.relationship('UserImage', lazy='dynamic')
    
    # lazy='joined': LEFT OUTER JOINで一度に取得
    images_joined = db.relationship('UserImage', lazy='joined')
    
    # lazy='subquery': サブクエリで取得
    images_subquery = db.relationship('UserImage', lazy='subquery')

# 使用例
def lazy_examples():
    user = User.query.first()
    
    # dynamic関係では追加フィルタリングが可能
    recent_images = user.user_images.filter(
        UserImage.uploaded_at > datetime(2025, 1, 1)
    ).all()
    
    active_images = user.user_images.filter(
        UserImage.is_active == True
    ).count()
