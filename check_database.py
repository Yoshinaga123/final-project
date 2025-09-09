#!/usr/bin/env python3
"""
データベーススキーマと実際のデータを確認するスクリプト
"""

import sqlite3
import os
from datetime import datetime

def check_database():
    """データベースの内容を確認する"""
    db_path = r"c:\Users\yoshinaga_kosuke\flaskbook\local.sqlite"
    
    if not os.path.exists(db_path):
        print(f"データベースファイルが見つかりません: {db_path}")
        return
    
    try:
        # データベースに接続
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("=" * 60)
        print("📊 データベーススキーマ情報")
        print("=" * 60)
        
        # 1. テーブル一覧を取得
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"\n🗂️  テーブル数: {len(tables)}")
        for table in tables:
            print(f"   - {table[0]}")
        
        print("\n" + "=" * 60)
        print("📋 各テーブルの詳細スキーマ")
        print("=" * 60)
        
        # 2. 各テーブルのスキーマを表示
        for table in tables:
            table_name = table[0]
            print(f"\n🔷 テーブル: {table_name}")
            print("-" * 40)
            
            # テーブル作成SQL
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?;", (table_name,))
            create_sql = cursor.fetchone()
            if create_sql:
                print("CREATE文:")
                print(create_sql[0])
            
            # カラム情報
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            print(f"\nカラム情報 ({len(columns)}個):")
            for col in columns:
                print(f"  {col[1]:20} {col[2]:15} {'NOT NULL' if col[3] else 'NULL':8} {'PK' if col[5] else '':3}")
        
        print("\n" + "=" * 60)
        print("💾 実際のデータサンプル")
        print("=" * 60)
        
        # 3. 各テーブルの実際のデータを表示
        for table in tables:
            table_name = table[0]
            print(f"\n📄 テーブル: {table_name}")
            print("-" * 40)
            
            # レコード数
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"レコード数: {count}")
            
            if count > 0:
                # 最初の5件を表示
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")
                rows = cursor.fetchall()
                
                # カラム名を取得
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = [col[1] for col in cursor.fetchall()]
                
                print("サンプルデータ (最大5件):")
                for i, row in enumerate(rows, 1):
                    print(f"  レコード {i}:")
                    for col_name, value in zip(columns, row):
                        print(f"    {col_name:20}: {value}")
                    print()
            else:
                print("データが存在しません")
        
        print("\n" + "=" * 60)
        print("🔍 インデックス情報")
        print("=" * 60)
        
        # 4. インデックス情報
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL;")
        indexes = cursor.fetchall()
        
        if indexes:
            for index in indexes:
                print(f"インデックス: {index[0]}")
                print(f"SQL: {index[1]}")
                print()
        else:
            print("カスタムインデックスは存在しません")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"データベースエラー: {e}")
    except Exception as e:
        print(f"予期しないエラー: {e}")

if __name__ == "__main__":
    check_database()
