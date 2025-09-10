"""
データベーステーブル構造確認スクリプト
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from apps.models import db, User

# アプリケーションコンテキストを作成
app = create_app()

with app.app_context():
    print("Users table columns:")
    for column in User.__table__.columns:
        print(f"  {column.name}: {column.type}")
    
    print(f"\nTotal columns: {len(User.__table__.columns)}")
