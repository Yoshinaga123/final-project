# データベース構造・状況レポート
作成日: 2025年9月8日
プロジェクト: Flask Book アプリケーション

## 📊 データベース全体概要

### 使用技術
- データベース: SQLite
- ORM: SQLAlchemy
- マイグレーション: Flask-Migrate (Alembic)
- データベースファイル: `local.sqlite`

### テーブル一覧 (4テーブル)
1. users - ユーザー管理
2. addresses - 住所管理  
3. user_images - 画像管理 (新規追加)
4. alembic_version - マイグレーション履歴

---

## 🗂️ 各テーブル詳細

### 1. users テーブル
**役割**: システムのユーザー情報管理、認証・認可
**レコード数**: 2件

#### スキーマ (14カラム)
```sql
CREATE TABLE users (
    id INTEGER NOT NULL PRIMARY KEY,
    username VARCHAR(64) NOT NULL,
    email VARCHAR(120) NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    created_at DATETIME,
    updated_at DATETIME,
    is_active BOOLEAN,
    is_admin BOOLEAN,
    organization VARCHAR(100),
    last_login DATETIME,
    access_count INTEGER,
    status VARCHAR(20),
    login_attempts INTEGER,
    role VARCHAR(20)
)
```

#### インデックス
- ix_users_username: UNIQUE INDEX (username)
- ix_users_email: UNIQUE INDEX (email)

#### 実際のデータ
```
ID: 1, ユーザー名: demo_user, メール: demo@example.com, 権限: user
ID: 3, ユーザー名: admin, メール: admin@example.com, 権限: admin
```

### 2. addresses テーブル
**役割**: ユーザーの住所情報管理
**レコード数**: 0件

#### スキーマ (13カラム)
```sql
CREATE TABLE addresses (
    id INTEGER NOT NULL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    postal_code VARCHAR(10),
    prefecture VARCHAR(20),
    city VARCHAR(50),
    address_line1 VARCHAR(100),
    address_line2 VARCHAR(100),
    phone VARCHAR(20),
    created_at DATETIME,
    updated_at DATETIME,
    is_default BOOLEAN,
    is_active BOOLEAN,
    FOREIGN KEY(user_id) REFERENCES users (id)
)
```

#### リレーションシップ
- User (1) ←→ Address (多): 1人のユーザーが複数の住所を持てる

### 3. user_images テーブル ⭐ 新規作成
**役割**: 物体検知システムでアップロードされた画像管理
**レコード数**: 0件

#### スキーマ (8カラム)
```sql
CREATE TABLE user_images (
    id INTEGER NOT NULL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    image_path VARCHAR(255) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    uploaded_at DATETIME,
    is_active BOOLEAN,
    is_deleted BOOLEAN,
    FOREIGN KEY(user_id) REFERENCES users (id)
)
```

#### リレーションシップ
- User (1) ←→ UserImage (多): 1人のユーザーが複数の画像をアップロード可能
- SQLAlchemyコード: `user.user_images.all()` で関連画像取得

### 4. alembic_version テーブル
**役割**: Flask-Migrateのマイグレーション履歴管理
**レコード数**: 1件

#### スキーマ (1カラム)
```sql
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
)
```

#### 現在のバージョン
- c1b0269f1c91: "Add UserImage table" マイグレーション

---

## 🔗 SQLAlchemyリレーションシップ詳細

### リレーションシップの種類と実装

#### 1. User ↔ Address (1対多)
```python
class User(db.Model):
    # リレーションシップは自動で addresses プロパティを作成

class Address(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', backref=db.backref('addresses', lazy='dynamic'))
```

**使用例**:
```python
user = User.query.first()
addresses = user.addresses.all()  # そのユーザーの全住所
```

#### 2. User ↔ UserImage (1対多)
```python
class UserImage(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', backref=db.backref('user_images', lazy='dynamic'))
```

**使用例**:
```python
user = User.query.first()
images = user.user_images.filter(UserImage.is_active == True).all()
image = UserImage.query.first()
owner = image.user  # 画像の所有者を取得
```

### lazy オプションの効果
- `lazy='dynamic'`: クエリオブジェクトを返すため、追加フィルタリングが可能
- 例: `user.user_images.filter(UserImage.uploaded_at > datetime(2025, 1, 1))`

---

## 🛠️ 実行したマイグレーション

### マイグレーション履歴
1. **初期状態**: users, addresses テーブルが存在
2. **2025-09-08**: UserImage テーブル追加
   - コマンド: `flask db migrate -m "Add UserImage table"`
   - 適用: `flask db upgrade`
   - バージョン: c1b0269f1c91

### 解決した問題
- **問題**: 物体検知ギャラリーページで500エラー
- **原因**: UserImageモデルは定義されているが、実際のテーブルが未作成
- **解決**: マイグレーション実行でテーブル作成
- **結果**: ギャラリーページが正常動作（"0枚の画像が見つかりました"表示）

---

## 🎯 アプリケーション機能との関連

### 物体検知システム
- **URL**: `/detector/`
- **機能**: 画像アップロード → AI物体検知 → 結果表示
- **データベース利用**:
  - アップロード時: user_images テーブルに画像情報保存
  - ギャラリー: user_images テーブルから画像一覧取得
  - ユーザー認証: users テーブルでログインユーザー管理

### 将棋アプリケーション
- **既存機能**: 棋譜管理、将棋盤表示
- **データベース利用**: 主にusersテーブルでユーザー管理

### 認証システム
- **機能**: ログイン、ユーザー登録、権限管理
- **データベース利用**: users テーブル
- **実装**: Flask-Login + Werkzeug パスワードハッシュ

---

## 📈 今後の拡張可能性

### 物体検知システムの改善
1. **検知結果テーブル**: 検知された物体情報を保存
2. **画像カテゴリテーブル**: 画像の分類管理
3. **検知履歴テーブル**: AI処理の履歴・統計

### パフォーマンス最適化
1. **画像パスインデックス**: image_path カラムにインデックス追加
2. **ユーザー画像インデックス**: (user_id, uploaded_at) 複合インデックス
3. **論理削除最適化**: is_deleted フィールドでの効率的なクエリ

### セキュリティ強化
1. **ファイルアップロード制限**: 拡張子・サイズ制限
2. **アクセス制御**: 画像の所有者チェック
3. **監査ログ**: ユーザーアクション履歴

---

## 🔧 運用・保守情報

### バックアップ
- データベースファイル: `local.sqlite`
- バックアップ方法: ファイルコピー
- 自動バックアップ: 未実装（今後の課題）

### ログ管理
- アプリケーションログ: `app.log`
- エラーログ: `error.log`
- SQLクエリログ: DEBUG モードで確認可能

### 開発ツール
- データベース確認スクリプト: `check_database.py`
- モデル確認スクリプト: `check_models.py`
- リレーションシップ例: `relationship_example.py`

---

## 📝 メモ・注意事項

### 重要な発見
1. **モデル定義と実テーブルの乖離**: 
   - UserImageモデルは存在していたが、マイグレーション未実行で実テーブルなし
   - これが500エラーの根本原因

2. **lazy='dynamic' の利点**:
   - クエリオブジェクトを返すため、柔軟なフィルタリングが可能
   - メモリ効率も良い

3. **インデックス設計**:
   - username, email に自動でUNIQUEインデックス
   - 外部キーにはインデックス追加を検討

### 今後の課題
1. テストデータの追加
2. パフォーマンステスト
3. 本番環境での PostgreSQL 移行検討

---

*このレポートは実際のデータベース調査結果を基に作成されました。*
*最終更新: 2025年9月8日 16:45*
