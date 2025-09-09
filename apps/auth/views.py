"""
認証関連のビュー関数

このモジュールには、ユーザー登録（サインアップ）機能が実装されています。
Flask-WTFを使用したフォームバリデーションと、SQLAlchemyを使用したデータベース操作を行います。
"""

# 必要なモジュールのインポート
from apps.auth.forms import signupForm  # サインアップフォームクラス
from apps.models import User  # ユーザーモデル
from apps.models import db  # データベースオブジェクト
from flask import render_template, request, redirect, url_for, flash
from . import auth_bp
from flask_login import logout_user, login_required,login_user

# ブループリントは__init__.pyで定義済み

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    ユーザー登録（サインアップ）機能
    
    GET: サインアップフォームを表示
    POST: フォームデータを受け取り、ユーザーを登録
    
    Returns:
        render_template: サインアップページの表示
        redirect: 登録成功時のログインページへのリダイレクト
    """
    # サインアップフォームのインスタンスを作成
    form = signupForm()
    
    # フォームが送信され、バリデーションが成功した場合
    # validate_on_submit()は以下を自動実行：
    # 1. POSTリクエストかチェック
    # 2. CSRFトークンの検証
    # 3. 各フィールドのバリデーション（DataRequired, Email, Length等）
    if form.validate_on_submit():
        # メールアドレスの重複チェック
        # データベースから同じメールアドレスを持つユーザーを検索
        if User.query.filter_by(email=form.email.data).first():
            # 重複している場合、エラーメッセージを表示してフォームを再表示
            flash('このメールアドレスは既に登録されています。', 'danger')
            return render_template('auth/signup.html', form=form)

        # この時点で、必須項目・メール形式・メールの重複がないことが
        # 全て保証されている状態になる
        
        # あとは安心してユーザー登録処理を進めるだけ
        try:
            # 新しいユーザーインスタンスを作成
            # form.field.dataでフォームから値を取得
            user = User(
                username=form.username.data,  # ユーザー名
                email=form.email.data        # メールアドレス
            )
            # パスワードをハッシュ化して設定
            # set_password()メソッドで自動的にハッシュ化される
            user.set_password(form.password.data)
            
            # データベースにユーザーを追加
            db.session.add(user)  # セッションに追加（まだDBには保存されない）
            db.session.commit()   # データベースに実際に保存
            
            # 成功メッセージを表示
            flash('ユーザー登録が完了しました。ログインしてください。', 'success')
            
            # ログインページにリダイレクト
            # url_for('auth.login')で/auth/loginのURLを生成
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            # データベースエラーが発生した場合の処理
            db.session.rollback()  # 変更を元に戻す
            flash('登録中にエラーが発生しました。', 'danger')
            return render_template('auth/signup.html', form=form)

    # GETリクエストまたはバリデーションエラーの場合
    # フォームをテンプレートに渡して表示
    # form=formにより、エラー時に入力値が保持される
    return render_template('auth/signup.html', form=form)

