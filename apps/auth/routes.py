from flask import render_template, request, redirect, url_for, flash, session, current_app
from . import auth_bp

# Blueprint は /auth にマウントされるため、ここでは '/login' とする（最終URLは /auth/login）
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """ログインページ"""
    from .forms import LoginForm
    form = LoginForm()
    
    if form.validate_on_submit():
        try:
            # ログイン処理
            username = form.username.data
            password = form.password.data
            
            current_app.logger.info(f"Login attempt - Username: {username}")
            
            # データベースからユーザーを検索
            from apps.models import User
            user = User.query.filter_by(username=username).first()
            
            current_app.logger.debug(f"User found: {user is not None}")
            
            if user:
                current_app.logger.debug(f"Password check result: {user.check_password(password)}")
            
            # ユーザーが存在し、パスワードが正しい場合
            if user and user.check_password(password):
                from flask_login import login_user
                login_user(user)
                flash('ログインしました！', 'success')
                # ログイン成功後はホームページへリダイレクト
                return redirect(url_for('index'))
            else:
                flash('ユーザー名またはパスワードが間違っています', 'error')
                # PRGパターン: ログイン失敗時はリダイレクトしてGETリクエストにする
                return redirect(url_for('auth.login', error=1))
        except Exception as e:
            current_app.logger.error(f"Login error: {e}")
            flash(f'ログインエラー: {str(e)}', 'error')
            # PRGパターン: エラー時もリダイレクト
            return redirect(url_for('auth.login', error=1))
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """ユーザー登録ページ"""
    if request.method == 'POST':
        try:
            # 登録処理
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            
            current_app.logger.info(f"Registration attempt - Username: {username}, Email: {email}")
            
            # バリデーション
            if not username or not email or not password:
                flash('すべての項目を入力してください', 'error')
                return render_template('auth/signup.html')
            
            # データベースからユーザーを検索
            from apps.models import User, db
            
            # 【レースコンディション対策】事前チェックを削除し、データベース制約に依存
            # 理由: チェックと保存の間に時間差があると、同時リクエストで重複登録が発生する可能性がある
            # 改善前: User.query.filter_by(email=email).first() で事前チェック → 時間差 → db.session.commit()
            # 改善後: 直接データベースに保存し、制約違反を例外でキャッチ
            
            # 新しいユーザーを作成
            user = User(username=username, email=email)
            user.set_password(password)
            
            # 【アトミック操作】データベースに保存（トランザクション内でチェック）
            # チェックと保存が1つのトランザクション内で実行されるため、レースコンディションを回避
            try:
                db.session.add(user)
                db.session.commit()  # ここでユニーク制約がチェックされる
            except Exception as e:
                # 【例外処理による重複検出】データベース制約違反（ユニーク制約など）をチェック
                current_app.logger.error(f"Database error during registration: {e}")
                db.session.rollback()  # エラー時は変更を元に戻す
                
                # 【データベース別エラー検出】SQLiteのUNIQUE制約エラーを検出
                # SQLite: 'UNIQUE constraint failed'
                # PostgreSQL: 'duplicate key value violates unique constraint'
                # MySQL: 'Duplicate entry'
                if any(keyword in str(e) for keyword in [
                    'UNIQUE constraint failed',  # SQLite
                    'duplicate key',             # PostgreSQL
                    'Duplicate entry'            # MySQL
                ]):
                    # 【正確なエラーメッセージ】どのフィールドが重複しているかを特定
                    if User.query.filter_by(username=username).first():
                        flash('このユーザー名は既に使用されています', 'error')
                    elif User.query.filter_by(email=email).first():
                        flash('このメールアドレスは既に使用されています', 'error')
                    else:
                        flash('登録に失敗しました。入力内容を確認してください。', 'error')
                    return render_template('auth/signup.html')
                else:
                    # その他のデータベースエラー（接続エラーなど）は再発生させる
                    raise e
            
            flash('ユーザー登録が完了しました！', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            current_app.logger.error(f"Registration error: {e}")
            flash(f'登録エラー: {str(e)}', 'error')
            db.session.rollback()
    
    return render_template('auth/signup.html')

@auth_bp.route('/logout')
def logout():
    """ログアウト"""
    from flask_login import logout_user
    current_app.logger.info("User logout")
    logout_user()
    flash('ログアウトしました', 'info')
    return redirect(url_for('auth.login'))
