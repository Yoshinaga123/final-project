from flask import render_template, abort, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from flask_wtf.csrf import validate_csrf
from wtforms import ValidationError
from . import crud_bp
from apps.models import db, User

# 互換性: indexリンク解決用のエイリアス (テンプレートで crud.index を参照しているため)
@crud_bp.route('/')
def index():  # pragma: no cover - 単純フォワード
    return redirect(url_for('crud.account'))

@crud_bp.route('/product/<int:product_id>', methods=['GET', 'POST'])
def product(product_id):
    # 1. 商品情報のリスト
    products_list = [
        # PC商品
        [1, "Mac", "Core i5", "¥100000", "Macの説明", 10],
        [2, "MacBook Pro", "Core M4", "¥100000", "MacBook Proの説明", 10],
        # 将棋商品
        [3, "本格将棋盤", "本榧材", "¥50000", "本格的な将棋盤。本榧材を使用した高級品です。", 5],
        [4, "高級駒セット", "本格駒", "¥15000", "本格的な将棋駒セット。職人による手作り駒です。", 8],
    ]
    
    # 2. 指定されたIDの商品を検索
    selected_product = None
    for product in products_list:
        if product[0] == product_id:  # 整数同士で比較
            selected_product = product
            break
    
    # 3. 商品が見つからない場合は404エラー
    if selected_product is None:
        abort(404)
    
    # 4. 見つかった商品のリストをテンプレートに渡す
    return render_template("crud/product.html", product=selected_product)

@crud_bp.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    """アカウント設定ページ"""
    try:
        # ログイン確認ログ
        current_app.logger.info(f"Account page accessed by user: {current_user.username}")
        
        if request.method == 'POST':
            # CSRFトークンの検証
            try:
                validate_csrf(request.form.get('csrf_token'))
            except ValidationError:
                current_app.logger.warning(f"CSRF validation failed for user: {current_user.username}")
                flash('セキュリティエラーが発生しました。再度お試しください。', 'danger')
                return redirect(url_for('crud.account'))
            
            action = request.form.get('action')
            current_app.logger.info(f"Account action requested: {action} by user: {current_user.username}")
            
            if action == 'update':
                # アカウント更新処理
                try:
                    # フォームデータを取得
                    new_username = request.form.get('username', '').strip()
                    new_email = request.form.get('email', '').strip()
                    new_password = request.form.get('password', '')
                    password_confirm = request.form.get('password_confirm', '')
                    
                    current_app.logger.info(f"Update attempt - Username: {new_username}, Email: {new_email}")
                    
                    # 基本的なバリデーション
                    if not new_username or not new_email:
                        flash('ユーザー名とメールアドレスは必須です', 'danger')
                        return redirect(url_for('crud.account'))
                    
                    # パスワードが入力された場合の確認
                    if new_password and new_password != password_confirm:
                        flash('パスワードが一致しません', 'danger')
                        return redirect(url_for('crud.account'))
                    
                    # ユーザー名の重複チェック（自分以外）
                    existing_user = User.query.filter(
                        (User.username == new_username) & (User.id != current_user.id)
                    ).first()
                    if existing_user:
                        flash('このユーザー名は既に使用されています', 'danger')
                        return redirect(url_for('crud.account'))
                    
                    # メールアドレスの重複チェック（自分以外）
                    existing_email = User.query.filter(
                        (User.email == new_email) & (User.id != current_user.id)
                    ).first()
                    if existing_email:
                        flash('このメールアドレスは既に使用されています', 'danger')
                        return redirect(url_for('crud.account'))
                    
                    # データベース更新
                    current_user.username = new_username
                    current_user.email = new_email
                    
                    # パスワードが入力された場合のみ更新
                    if new_password:
                        current_user.set_password(new_password)
                        current_app.logger.info(f"Password updated for user: {current_user.username}")
                    
                    db.session.commit()
                    current_app.logger.info(f"Account updated successfully for user: {current_user.username}")
                    flash('アカウント情報を更新しました', 'success')
                    return redirect(url_for('crud.account'))
                    
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Account update error: {e}")
                    flash('アカウントの更新中にエラーが発生しました', 'danger')
                    return redirect(url_for('crud.account'))
            
            elif action == 'delete':
                # アカウント削除処理
                try:
                    current_app.logger.warning(f"Account deletion requested by user: {current_user.username}")
                    
                    # 現在のユーザー情報を保存（ログ用）
                    username = current_user.username
                    user_id = current_user.id
                    
                    # ユーザーをデータベースから削除
                    db.session.delete(current_user)
                    db.session.commit()
                    
                    current_app.logger.warning(f"Account deleted successfully - User ID: {user_id}, Username: {username}")
                    flash('アカウントを削除しました。ご利用ありがとうございました。', 'success')
                    
                    # ログアウトしてトップページにリダイレクト
                    from flask_login import logout_user
                    logout_user()
                    return redirect(url_for('index'))
                    
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Account deletion error: {e}")
                    flash('アカウントの削除中にエラーが発生しました', 'danger')
                    return redirect(url_for('crud.account'))
        
        # 現在のユーザー情報をテンプレートに渡す
        return render_template("crud/account.html", user=current_user)
        
    except Exception as e:
        current_app.logger.error(f"Account page error: {e}")
        flash('アカウントページの読み込み中にエラーが発生しました', 'danger')
        return redirect(url_for('index'))
