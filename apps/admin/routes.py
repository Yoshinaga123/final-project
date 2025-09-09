from flask import render_template, request, session, current_app, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from functools import wraps
import platform
import sys
import datetime
import os
import psutil
from . import admin_bp
from apps.models import db, User
from email_validator import validate_email, EmailNotValidError


@admin_bp.errorhandler(403)
def forbidden(error):
    """403エラーハンドラー"""
    return render_template('error_pages/403.html'), 403


def admin_required(f):
    """管理者権限が必要なデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('ログインが必要です', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_admin:
            flash('管理者権限が必要です', 'danger')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def validate_user_input(username, email, password=None, password_confirm=None):
    """ユーザー入力のバリデーション"""
    errors = []
    
    # ユーザー名の検証
    if not username or len(username.strip()) < 3:
        errors.append('ユーザー名は3文字以上で入力してください')
    elif len(username) > 64:
        errors.append('ユーザー名は64文字以内で入力してください')
    
    # メールアドレスの検証
    if not email or len(email.strip()) == 0:
        errors.append('メールアドレスを入力してください')
    else:
        try:
            validate_email(email)
        except EmailNotValidError:
            errors.append('有効なメールアドレスを入力してください')
    
    # パスワードの検証（パスワードが提供された場合）
    if password is not None:
        if not password or len(password) < 6:
            errors.append('パスワードは6文字以上で入力してください')
        elif password_confirm and password != password_confirm:
            errors.append('パスワードが一致しません')
    
    return errors


@admin_bp.route('/sys')
@login_required
@admin_required
def sys_info():
    """システム情報を表示するページ"""
    try:
        # セッションからシステム情報を取得（デコレータから来た場合）
        system_info = session.get('system_info', {})
        
        # Python情報
        python_version = sys.version
        platform_info = platform.platform()
        architecture = platform.architecture()[0]
        implementation = platform.python_implementation()
        byte_order = sys.byteorder
        executable = sys.executable
        prefix = sys.prefix
        base_prefix = sys.base_prefix
        max_size = sys.maxsize
        max_unicode = sys.maxunicode
        
        # 時刻情報
        current_time = datetime.datetime.now()
        timezone = str(current_time.astimezone().tzinfo)
        utc_time = datetime.datetime.utcnow()
        timestamp = current_time.timestamp()
        iso_time = current_time.isoformat()
        date_only = current_time.date()
        time_only = current_time.time()
        
        # システム情報
        cpu_count = psutil.cpu_count()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # ネットワーク情報
        try:
            import socket
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            network_info = {
                'hostname': hostname,
                'ip': ip,
                'mac': 'N/A',
                'interfaces': 'N/A'
            }
        except:
            network_info = None
        
        # データベース情報
        try:
            db_info = {
                'type': 'SQLite',
                'name': 'local.sqlite',
                'host': 'localhost',
                'port': 'N/A',
                'user': 'N/A',
                'status': 'Connected'
            }
        except:
            db_info = None
        
        # インストール済みパッケージ情報
        try:
            import pkg_resources
            installed_packages = [
                {'name': pkg.project_name, 'version': pkg.version}
                for pkg in pkg_resources.working_set
            ]
        except:
            installed_packages = None
        
        return render_template('admin/sys.html',
                             app=current_app,
                             system_info=system_info,
                             python_version=python_version,
                             platform=platform_info,
                             architecture=architecture,
                             implementation=implementation,
                             byte_order=byte_order,
                             executable=executable,
                             prefix=prefix,
                             base_prefix=base_prefix,
                             max_size=max_size,
                             max_unicode=max_unicode,
                             current_time=current_time,
                             timezone=timezone,
                             utc_time=utc_time,
                             timestamp=timestamp,
                             iso_time=iso_time,
                             date_only=date_only,
                             time_only=time_only,
                             cpu_count=cpu_count,
                             memory=memory,
                             disk=disk,
                             network_info=network_info,
                             db_info=db_info,
                             installed_packages=installed_packages)
    
    except Exception as e:
        current_app.logger.error(f"システム情報の取得中にエラーが発生しました: {str(e)}")
        flash('システム情報の取得中にエラーが発生しました', 'danger')
        return redirect(url_for('admin.admin_users'))


@admin_bp.route('/admin_users', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_users():
    """ユーザー管理ページ"""
    try:
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'add':
                # 新規ユーザー追加
                username = request.form.get('username', '').strip()
                email = request.form.get('email', '').strip()
                password = request.form.get('password', '')
                password_confirm = request.form.get('password_confirm', '')
                organization = request.form.get('organization', '').strip()
                role = request.form.get('role', 'user')
                
                # 入力値の検証
                errors = validate_user_input(username, email, password, password_confirm)
                
                if errors:
                    for error in errors:
                        flash(error, 'danger')
                else:
                    # 重複チェック
                    if User.query.filter_by(username=username).first():
                        flash('このユーザー名は既に使用されています', 'danger')
                    elif User.query.filter_by(email=email).first():
                        flash('このメールアドレスは既に使用されています', 'danger')
                    else:
                        try:
                            # 新規ユーザー作成
                            new_user = User(
                                username=username,
                                email=email,
                                organization=organization,
                                role=role,
                                is_active=True
                            )
                            new_user.set_password(password)
                            
                            db.session.add(new_user)
                            db.session.commit()
                            
                            flash(f'ユーザー {username} を正常に追加しました', 'success')
                            return redirect(url_for('admin.admin_users'))
                        except Exception as e:
                            db.session.rollback()
                            current_app.logger.error(f"ユーザー追加エラー: {str(e)}")
                            flash('ユーザーの追加中にエラーが発生しました', 'danger')
            
            elif action == 'edit':
                # ユーザー編集
                try:
                    user_id = int(request.form.get('user_id', 0))
                except (ValueError, TypeError):
                    flash('無効なユーザーIDです', 'danger')
                    return redirect(url_for('admin.admin_users'))
                
                user = User.query.get(user_id)
                if not user:
                    flash('指定されたユーザーが見つかりません', 'danger')
                    return redirect(url_for('admin.admin_users'))
                
                username = request.form.get('username', '').strip()
                email = request.form.get('email', '').strip()
                password = request.form.get('password', '')
                password_confirm = request.form.get('password_confirm', '')
                organization = request.form.get('organization', '').strip()
                role = request.form.get('role', 'user')
                is_active = request.form.get('is_active') == 'on'
                
                # 入力値の検証（パスワードが空の場合は検証しない）
                password_to_validate = password if password else None
                errors = validate_user_input(username, email, password_to_validate, password_confirm)
                
                if errors:
                    for error in errors:
                        flash(error, 'danger')
                else:
                    # 重複チェック（自分以外）
                    existing_user = User.query.filter(
                        (User.username == username) & (User.id != user_id)
                    ).first()
                    if existing_user:
                        flash('このユーザー名は既に使用されています', 'danger')
                    else:
                        existing_email = User.query.filter(
                            (User.email == email) & (User.id != user_id)
                        ).first()
                        if existing_email:
                            flash('このメールアドレスは既に使用されています', 'danger')
                        else:
                            try:
                                # ユーザー情報更新
                                user.username = username
                                user.email = email
                                user.organization = organization
                                user.role = role
                                user.is_active = is_active
                                
                                # パスワードが入力された場合のみ更新
                                if password:
                                    user.set_password(password)
                                
                                user.updated_at = datetime.datetime.utcnow()
                                
                                db.session.commit()
                                
                                flash(f'ユーザー {username} を正常に更新しました', 'success')
                                return redirect(url_for('admin.admin_users'))
                            except Exception as e:
                                db.session.rollback()
                                current_app.logger.error(f"ユーザー更新エラー: {str(e)}")
                                flash('ユーザーの更新中にエラーが発生しました', 'danger')
            
            elif action == 'delete':
                # ユーザー削除
                try:
                    user_id = int(request.form.get('user_id', 0))
                except (ValueError, TypeError):
                    flash('無効なユーザーIDです', 'danger')
                    return redirect(url_for('admin.admin_users'))
                
                user = User.query.get(user_id)
                if not user:
                    flash('指定されたユーザーが見つかりません', 'danger')
                elif user.id == current_user.id:
                    flash('自分自身を削除することはできません', 'danger')
                else:
                    try:
                        db.session.delete(user)
                        db.session.commit()
                        flash(f'ユーザー {user.username} を正常に削除しました', 'success')
                        return redirect(url_for('admin.admin_users'))
                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.error(f"ユーザー削除エラー: {str(e)}")
                        flash('ユーザーの削除中にエラーが発生しました', 'danger')
        
        # ユーザー一覧を取得
        users = User.query.order_by(User.created_at.desc()).all()
        return render_template('admin/admin_users.html', users=users)
        
    except Exception as e:
        current_app.logger.error(f"ユーザー管理ページエラー: {str(e)}")
        flash('ページの読み込み中にエラーが発生しました', 'danger')
        return render_template('admin/admin_users.html', users=[])
