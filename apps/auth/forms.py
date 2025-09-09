from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, EmailField
from wtforms.validators import DataRequired, Email, EqualTo, Length

class LoginForm(FlaskForm):
    username = StringField(
        'ユーザー名',
        validators=[
            DataRequired("ユーザー名は必須です。"),
            Length(max=30, message="ユーザー名は30文字以内で入力してください。")
        ],
        render_kw={"placeholder": "ユーザー名を入力してください"}
    )
    password = PasswordField(
        'パスワード',
        validators=[
            DataRequired("パスワードは必須です。"),
            Length(min=1, message="パスワードを入力してください。")
        ],
        render_kw={"placeholder": "パスワードを入力してください"}
    )
    submit = SubmitField('ログイン')

class signupForm(FlaskForm):
    username = StringField(
        'ユーザー名',
         validators=[
            DataRequired("ユーザー名は必須です。"),
            Length(max=30, message="ユーザー名は30文字以内で入力してください。")
            ],
        )
    email = EmailField(
        'メールアドレス',
         validators=[
            DataRequired("メールアドレスは必須です。"),
            Email(message="メールアドレスが不正です。")
            ],
        )
    password = PasswordField(
        'パスワード',
        validators=[DataRequired("パスワードは必須です。"), Length(min=8, message="パスワードは8文字以上で入力してください。")])
    submit = SubmitField('登録')