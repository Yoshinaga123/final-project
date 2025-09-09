#!/usr/bin/env python3
"""
WTFormsが生成するHTMLを確認するスクリプト
"""

import sys
sys.path.insert(0, r'c:\Users\yoshinaga_kosuke\flaskbook')

def check_form_rendering():
    """フォームのレンダリング結果を確認"""
    try:
        from flask import Flask
        from config import Config
        from apps.auth.forms import LoginForm
        
        # Flaskアプリの作成
        app = Flask(__name__)
        app.config.from_object(Config)
        
        with app.app_context():
            with app.test_request_context():  # リクエストコンテキストを追加
                form = LoginForm()
                
                print("=" * 60)
                print("🔍 WTForms LoginForm のHTML出力確認")
                print("=" * 60)
                
                print("\n📋 Username フィールド:")
                print("Label:", form.username.label())
                print("Field:", form.username())
                print("Field with class:", form.username(class_="form-control"))
                
                print("\n📋 Password フィールド:")
                print("Label:", form.password.label())
                print("Field:", form.password())
                print("Field with class:", form.password(class_="form-control"))
                
                print("\n📋 Submit ボタン:")
                print("Submit:", form.submit())
                print("Submit with class:", form.submit(class_="btn btn-primary"))
                
                # フィールドの属性確認
                print("\n" + "=" * 60)
                print("🔧 フィールド属性の詳細")
                print("=" * 60)
                
                print("\n📋 Username フィールド属性:")
                print(f"Type: {form.username.type}")
                print(f"Validators: {[str(v) for v in form.username.validators]}")
                print(f"Flags: {form.username.flags}")
                print(f"Render kwargs: {form.username.render_kw}")
                
                print("\n📋 Password フィールド属性:")
                print(f"Type: {form.password.type}")
                print(f"Validators: {[str(v) for v in form.password.validators]}")
                print(f"Flags: {form.password.flags}")
                print(f"Render kwargs: {form.password.render_kw}")
                
                # クライアントサイドバリデーション確認
                print("\n" + "=" * 60)
                print("🌐 クライアントサイドバリデーション確認")
                print("=" * 60)
                
                # DataRequired バリデーターがある場合、WTFormsは自動的に required 属性を追加
                print("\n📋 HTML5 バリデーション属性:")
                username_html = str(form.username(class_="form-control"))
                password_html = str(form.password(class_="form-control"))
                
                print(f"Username HTML: {username_html}")
                print(f"Password HTML: {password_html}")
                
                print(f"\nUsername に 'required' が含まれている: {'required' in username_html}")
                print(f"Password に 'required' が含まれている: {'required' in password_html}")
                
                # バリデーション動作テスト
                print("\n" + "=" * 60)
                print("🧪 バリデーション動作テスト")
                print("=" * 60)
                
                # 空データでバリデーション
                form.username.data = ""
                form.password.data = ""
                
                validation_result = form.validate()
                print(f"\n空データのバリデーション結果: {validation_result}")
                
                if not validation_result:
                    print("エラー内容:")
                    for field_name, errors in form.errors.items():
                        print(f"  {field_name}: {errors}")
                
                # 有効なデータでバリデーション
                form.username.data = "testuser"
                form.password.data = "testpass"
                
                validation_result = form.validate()
                print(f"\n有効データのバリデーション結果: {validation_result}")
                
                if not validation_result:
                    print("エラー内容:")
                    for field_name, errors in form.errors.items():
                        print(f"  {field_name}: {errors}")
            
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_form_rendering()
