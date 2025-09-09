#!/usr/bin/env python3
"""
Flask-Migrateのマイグレーション状態とモデル定義を確認
"""

import os
import sys

# Flaskアプリケーションのパスを追加
sys.path.insert(0, r'c:\Users\yoshinaga_kosuke\flaskbook')

def check_migration_status():
    """マイグレーションの状態を確認"""
    try:
        from flask import Flask
        from apps.models.model import db, User, Address, UserImage
        from config import Config
        
        # Flaskアプリの作成
        app = Flask(__name__)
        app.config.from_object(Config)
        
        # データベース初期化
        db.init_app(app)
        
        with app.app_context():
            print("=" * 60)
            print("🔧 モデル定義の確認")
            print("=" * 60)
            
            # 定義されているモデル
            models = [User, Address, UserImage]
            for model in models:
                print(f"\n📋 モデル: {model.__name__}")
                print(f"テーブル名: {model.__tablename__}")
                
                # カラム情報
                print("カラム:")
                for column_name, column in model.__table__.columns.items():
                    nullable = "NULL" if column.nullable else "NOT NULL"
                    primary_key = "PK" if column.primary_key else ""
                    foreign_keys = ", ".join([str(fk.target_fullname) for fk in column.foreign_keys]) if column.foreign_keys else ""
                    fk_info = f" -> {foreign_keys}" if foreign_keys else ""
                    
                    print(f"  {column_name:20}: {column.type} {nullable} {primary_key}{fk_info}")
            
            print("\n" + "=" * 60)
            print("🗃️ 実際のテーブル存在確認")
            print("=" * 60)
            
            # データベース内の実際のテーブル確認
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            print(f"データベース内のテーブル: {existing_tables}")
            
            for model in models:
                table_name = model.__tablename__
                exists = table_name in existing_tables
                status = "✅ 存在" if exists else "❌ 未作成"
                print(f"{model.__name__:15}: {table_name:15} {status}")
                
                if not exists:
                    print(f"  ⚠️  {model.__name__}テーブルはまだ作成されていません")
            
            print("\n" + "=" * 60)
            print("📊 UserImageテーブルの詳細")
            print("=" * 60)
            
            if 'user_images' in existing_tables:
                # UserImageテーブルが存在する場合
                print("UserImageテーブルが存在します！")
                
                # 実際のデータを確認
                images = UserImage.query.all()
                print(f"UserImageレコード数: {len(images)}")
                
                for i, image in enumerate(images[:5], 1):
                    print(f"  画像 {i}: {image.filename} (ユーザーID: {image.user_id})")
            else:
                print("❌ UserImageテーブルは作成されていません")
                print("マイグレーションが必要です:")
                print("  1. flask db migrate -m 'Add UserImage table'")
                print("  2. flask db upgrade")
                
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_migration_status()
