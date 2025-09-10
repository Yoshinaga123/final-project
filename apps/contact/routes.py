"""
問い合わせ機能のルート

このモジュールには、お問い合わせ機能のルートが定義されています。
"""

import os
import sys
import platform
import time
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, current_app
from flask_mail import Attachment
from email_validator import validate_email, EmailNotValidError
from . import contact_bp

@contact_bp.route('/', methods=['GET', 'POST'])
def contact():
    """お問い合わせページ"""
    if request.method == 'POST':
        try:
            # 問い合わせ処理
            name = request.form.get('name')
            email = request.form.get('email')
            message = request.form.get('message')
            
            # デバッグ用: 受信したデータをコンソールに出力
            print(f"受信データ - name: '{name}', email: '{email}', message: '{message}'")
            
            # バリデーション
            if not name or not email or not message:
                flash('すべての項目を入力してください', 'warning')
                return redirect(url_for('contact.contact'))
            
            # メールアドレス検証
            try:
                validate_email(email)
            except EmailNotValidError:
                flash('無効なメールアドレスです', 'danger')
                return redirect(url_for('contact.contact'))
            
            # メール送信
            send_email(
                current_app,
                template="contact/contact_mail",
                subject="お問い合わせありがとうございました。",
                recipients=[email],
                username=name,
                message=message,
                cc=[os.environ.get('CC_EMAIL')],
                bcc=[os.environ.get('BCC_EMAIL')],
                reply_to=os.environ.get('REPLY_TO_EMAIL'),
                attachments=[
                    Attachment(
                        filename="requirements.txt",
                        content_type="text/plain",
                        data=attachment_data
                    )
                ] if attachment_data else None,
                charset="utf-8",
                extra_headers={"X-Custom": "requirements.txt"},
                email=email,
                submission_date=datetime.now()
            )
            
            return redirect(url_for('contact.contact_complete'))
            
        except Exception as e:
            flash(f'送信エラー: {str(e)}', 'error')
            print(f"Contact error: {e}")  # デバッグ用
    
    return render_template('contact/contact.html')

@contact_bp.route('/complete')
def contact_complete():
    """お問い合わせ完了ページ"""
    context = {
        'config': current_app.config,
        'app': current_app,
        'python_version': sys.version,
        'platform': platform.platform(),
        'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'timezone': time.tzname[0]
    }
    
    return render_template('contact/contact_complete.html', **context)


def send_email(app, template, subject, recipients, **kwargs):
    """メールを送信するためのヘルパー関数"""
    from flask_mail import Message
    
    # Messageオブジェクトを作成する際に、attachmentsのリストをそのまま渡す
    msg = Message(
        subject=subject,
        recipients=recipients,
        cc=kwargs.get("cc"),
        bcc=kwargs.get("bcc"),
        attachments=kwargs.get("attachments"),
        reply_to=kwargs.get("reply_to"),
        charset=kwargs.get("charset"),
        extra_headers=kwargs.get("extra_headers") 
    )

    # メール本文をテンプレートから生成
    msg.body = render_template(f"{template}.txt", **kwargs)
    msg.html = render_template(f"{template}.html", **kwargs)

    # メールを送信
    app.mail.send(msg)

# 互換性のためのエイリアス: index -> contact, contact.index で参照できるように
@contact_bp.route('/index')
def index():  # pragma: no cover - 単純委譲
    return contact()


# 添付ファイルの読み込み
try:
    with open("requirements.txt", "rb") as f:
        attachment_data = f.read()
except FileNotFoundError:
    attachment_data = None
