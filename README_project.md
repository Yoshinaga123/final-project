# Flaskbook - Flask アプリケーションプロジェクト

## プロジェクト概要

Flaskbookは、Blueprintを使用したモジュラー設計のFlaskアプリケーションです。認証、管理、CRUD機能を備えたWebアプリケーションとして構築されています。

## 技術スタック

### フレームワーク
- **Flask 3.1.2** - 軽量なWebフレームワーク
- **Blueprint** - モジュラー設計のための機能分割

### データベース
- **SQLAlchemy 2.0.43** - ORM（Object Relational Mapping）
- **Flask-SQLAlchemy 3.1.1** - Flask用SQLAlchemy拡張
- **Flask-Migrate 4.1.0** - データベースマイグレーション
- **SQLite** - 開発用データベース

### 認証・セキュリティ
- **Flask-Login 0.6.3** - ユーザーセッション管理
- **Flask-WTF 1.2.2** - フォーム処理とCSRF保護
- **Werkzeug** - パスワードハッシュ化

### フロントエンド・UI
- **Bootstrap 5.3.0** - レスポンシブUIフレームワーク
- **KifuForJS** - 将棋盤表示・操作ライブラリ
- **jQuery 3.6.0** - DOM操作・イベント処理

### 将棋機能
- **KIF形式サポート** - 日本将棋連盟標準棋譜形式
- **棋譜再生機能** - インタラクティブな盤面表示
- **棋譜管理機能** - アップロード・ダウンロード・一覧表示

### その他の機能
- **Flask-Mail 0.10.0** - メール送信機能
- **Flask-DebugToolbar 0.16.0** - デバッグツール
- **Bootstrap 5.3.0** - フロントエンドUI

## プロジェクト構造（最新）

```
final-project/
├── app.py                   # アプリケーションファクトリ
├── run.py                   # 起動スクリプト
├── config.py                # 設定
├── requirements.txt         # 依存関係
├── README_project.md        # このファイル
├── local.sqlite             # SQLite（開発用）
├── app.log / app.log.1 / app.log.5
├── error.log
├── yolov8n.pt               # YOLOv8 重み（大きいため提出時は除外推奨）
├── 詰将棋_*.kif             # 棋譜ファイル（KIF形式）
├── apps/
│   ├── __init__.py
│   ├── admin/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── templates/admin/
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── forms.py
│   │   ├── routes.py
│   │   ├── views.py
│   │   └── templates/auth/
│   ├── contact/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── templates/contact/
│   ├── crud/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── templates/crud/
│   ├── detector/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── images/
│   │   ├── static/
│   │   └── templates/detector/
│   ├── models/
│   │   ├── __init__.py
│   │   └── model.py
│   ├── shogi/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   ├── utils.py
│   │   └── templates/shogi/
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── kifu/
│   └── templates/
│       ├── base.html
│       ├── index.html
│       └── error_pages/
├── docs/
│   ├── API.md / ARCHITECTURE.md / DATABASE_REPORT.md / MIGRATION.md / OPERATIONS.md / TROUBLESHOOTING_*.md / RUNBOOKS/
├── logs/
│   └── app.log
├── migrations/
│   ├── alembic.ini / env.py / script.py.mako / README
│   └── versions/
│       └── fd160c6c9b0b_initial_migration.py
└── backup_20250906_154909/
    ├── app.py / config.py / run.py / requirements.txt
    └── contact/
```

## 現時点のファイル構成スナップショット (2025-09-09)

主要ディレクトリ/ファイルの抜粋です（実体ベース）。

```
final-project/
├─ app.py / run.py / config.py / requirements.txt / README_project.md
├─ app.log / app.log.1 / app.log.5 / error.log / local.sqlite / yolov8n.pt
├─ 詰将棋_NO_GUARD_OPENING_*.kif（2ファイル）
├─ backup_20250906_154909/
├─ docs/
├─ logs/
│  └─ app.log
├─ migrations/
│  ├─ alembic.ini / env.py / script.py.mako / README
│  └─ versions/
│     └─ fd160c6c9b0b_initial_migration.py
└─ apps/
    ├─ __init__.py
    ├─ admin/ auth/ contact/ crud/ detector/ models/ shogi/
    ├─ static/（css, js, kifu）
    └─ templates/（base.html, index.html, error_pages/）
```

補足:
- 画像の保存先は `apps/detector/images`（設定: `DETECTOR_UPLOAD_FOLDER`）。
- `apps/detector/static/detector/uploads` も存在しますが、現行実装では使用していません。
- 参考リポジトリ互換のため、一部エイリアスルートを用意しています（後述）。

## Detector モジュール報告 (2025-09-09)

機能サマリ（ユーザー単位の画像アップロード、表示、簡易検知、削除）。検知はダミー実装ですが、検出枠のキャンバス重畳描画に対応しました。

- 主要ルート
    - `GET /detector/` … トップ（機能案内＋最近の画像）
    - `GET|POST /detector/upload` … 画像アップロード（`file` もしくは `image` フィールド対応）
    - `GET /detector/detect/<image_id>` … 検知結果表示（検出枠キャンバス重畳、ON/OFFトグル付）
    - `GET /detector/gallery` … ギャラリー（ユーザー画像一覧）
    - `POST /detector/delete/<image_id>` … 画像削除（論理削除＋可能なら物理ファイル削除）
    - `GET /detector/uploads/<filename>` … アップロード画像の配信（所有者チェック）
    - 互換エイリアス: `GET /detector/image/<filename>`, `GET|POST /detector/upload_image`
    - API: `POST /detector/api/detect` … 簡易検知結果（JSON）

- テンプレート構成（`apps/detector/templates/detector/`）
    - `base.html` … detector用のベース（共通`base.html`に head/content/js ブロックを橋渡し）
    - `index.html` … 最近画像カード＋導線
    - `upload.html` … ドラッグ＆ドロップ/プレビュー対応
    - `detect.html` … 結果テーブル＋キャンバス重畳描画（レスポンシブ再描画、表示トグル）
    - `gallery.html` … 一覧（カード表示）

- 実装メモ
    - 保存名はタイムスタンプ＋UUIDの一意名（元ファイル名は別途保持）。
    - 画像配信は所有者チェック付きで `DETECTOR_UPLOAD_FOLDER` 直下のファイルのみ許可。
    - 削除は論理削除を基本とし、可能なら物理ファイルも削除（失敗時はワーニングログのみ）。
    - 参考リポジトリのテンプレート互換として、`/upload_image`・`/image/<filename>` を提供。
    - 検知は現状ダミー（ランダムBBox）。将来的にYOLO/OpenCV等と置換予定。

今後の改善候補（detector）
- 検知結果の永続化（履歴・バッジ表示、再描画用データ）
- ギャラリーのページング、メタ情報バッジ（検知件数・最終検知時刻など）
- 未使用テンプレートの整理（image_detail, my_images, results）
- WTForms化やAPI整備（ファイルバリデーション、サイズ上限など）

## 主要機能

### ✅ 将棋機能（メイン機能）
- **棋譜管理システム** - KIF形式ファイルの管理
- **棋譜表示・再生** - KifuForJSによるインタラクティブ盤面
- **棋譜一覧表示** - アップロード済み棋譜の一覧
- **棋譜ダウンロード** - ブラウザ経由でのファイルダウンロード
- **将棋盤表示** - リアルタイム盤面更新
- **手順再生** - 棋譜の手順を順次再生

### ✅ 認証システム
- **ログイン/ログアウト機能** - Flask-Loginを使用
- **ユーザー登録機能** - データベースベースの登録
- **パスワードハッシュ化** - Werkzeugによる安全なパスワード管理
- **CSRF保護** - Flask-WTFによるセキュリティ強化
- **レースコンディション対策** - アトミック操作による重複登録防止

### ✅ 管理機能
- **システム情報表示** - サーバー情報の確認
- **ユーザー管理** - ユーザー一覧表示
- **UI切り替え機能** - テーマ・言語・レイアウトの変更

### ✅ CRUD機能
- **商品管理** - 商品情報の表示・管理
- **アカウント管理** - ユーザーアカウント情報

### ✅ お問い合わせ機能
- **お問い合わせフォーム** - メール送信機能付き
- **バリデーション** - 入力値の検証
- **CSRF保護** - セキュリティ強化

### ✅ 画像・検出器機能
- **画像アップロード** - 静的ファイル管理
- **検出器機能** - 画像解析・処理機能

### ✅ ログ機能（強化済み）
- **詳細ログ記録** - DEBUGレベルでの詳細ログ
- **エラーログ分離** - `error.log`にERROR以上のログを記録
- **ログローテーション** - ファイルサイズ制限とバックアップ
- **コンソール出力** - 開発時のリアルタイムログ確認

## セットアップ手順

### 1. 環境準備
```bash
# 仮想環境の作成と有効化
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 2. 依存関係のインストール
```bash
pip install -r requirements.txt
```

### 3. データベースの初期化
```bash
# データベーステーブルの作成
python -c "from app import create_app; from apps.models import db; app = create_app(); app.app_context().push(); db.create_all()"

# デモユーザーの作成
python -c "from app import create_app; from apps.models import db, User; app = create_app(); app.app_context().push(); user = User(username='demo_user', email='demo@example.com'); user.set_password('demo_password'); db.session.add(user); db.session.commit(); print('デモユーザーを作成しました')"
```

### 4. アプリケーションの起動
```bash
python run.py
```

### 5. アクセス
- アプリケーション: http://127.0.0.1:5000
- 将棋機能: http://127.0.0.1:5000/shogi
- 管理画面: http://127.0.0.1:5000/admin
- ログイン: `demo_user` / `demo_password`

## 将棋機能の使い方

### 棋譜ファイルの配置
```bash
# kifファイルをstatic/kifuディレクトリに配置
cp your_game.kif apps/static/kifu/
```

### 棋譜の表示
1. ブラウザで `/shogi` にアクセス
2. 棋譜一覧から表示したい棋譜を選択
3. 棋譜表示画面で盤面を確認
4. 手順の進行・戻しが可能
5. ダウンロードボタンで棋譜ファイルをダウンロード

## 設計方針

### ✅ アプリケーションファクトリパターン
- **`app.py`**: アプリケーションファクトリ（メイン）
- **`apps/__init__.py`**: パッケージ初期化（簡素化）
- **`run.py`**: 起動専用ファイル（シンプルな起動スイッチ）
- **設定の分離**: `config.py`での環境別設定管理

### ✅ ブループリント設計
- **機能別モジュール化**: auth, admin, crud, contact, shogi, detector, images
- **テンプレートの分離**: 各ブループリント専用テンプレート
- **ルートの整理**: 機能ごとの明確な分離
- **静的ファイル管理**: 機能別のJavaScript・CSS配置

### ✅ フロントエンド設計
- **KifuForJS統合**: 将棋盤表示・操作の専用ライブラリ
- **Bootstrap5**: レスポンシブデザインの統一
- **jQuery**: DOM操作・イベント処理の統一
- **モジュラーJS**: 機能別JavaScriptファイルの分離

### ✅ データベース設計
- **モデル集約**: `apps/models/model.py`で全モデル管理
- **マイグレーション**: Flask-Migrateによるバージョン管理
- **セキュリティ**: パスワードハッシュ化、CSRF保護
- **レースコンディション対策**: アトミック操作による重複登録防止

### ✅ セキュリティ対策
- **CSRF保護**: 全フォームにCSRFトークン実装
- **パスワードハッシュ化**: Werkzeugによる安全な管理
- **セッション管理**: Flask-Loginによる適切な管理
- **データベース制約**: ユニーク制約による重複防止

### ✅ ログ設計（強化済み）
- **多層ログ**: アプリログ、エラーログ、コンソールログ
- **ログレベル**: DEBUG、INFO、WARNING、ERROR
- **ローテーション**: ファイルサイズ制限とバックアップ
- **詳細記録**: スタックトレース付きエラー情報

## 開発履歴

### 2025-09-08 将棋機能追加
- ✅ 将棋ブループリント実装（shogi）
- ✅ KifuForJSライブラリ統合
- ✅ 棋譜表示・再生機能実装
- ✅ 棋譜一覧・ダウンロード機能
- ✅ JavaScript エラー修正（downloadKifu関数）
- ✅ システム情報UI改善
- ✅ 静的ファイル管理最適化

### 2025-09-06 最新更新
- ✅ ログ設定の大幅強化（DEBUGレベル、エラーログ分離）
- ✅ 認証処理のログ機能追加
- ✅ エラーハンドラーの改善（スタックトレース記録）
- ✅ プロジェクト構造の最適化
- ✅ 不要ファイルのクリーンアップ
- ✅ レースコンディション対策の実装
- ✅ ブループリント設計の完成
- ✅ セキュリティ強化の完了

### 2025-09-06 修正完了
- ✅ 未定義変数エラーの修正（`send_email`関数）
- ✅ 重複ルート定義の削除
- ✅ URLエンドポイントエラーの修正
- ✅ CSRF保護の実装
- ✅ 依存関係のインストール
- ✅ ブループリント登録問題の解決
- ✅ ログイン機能の完全実装
- ✅ 新規登録機能の実装
- ✅ データベースベース認証システムの構築

## 今後の拡張予定

- ✅ 将棋機能（完成済み）
- [ ] 画像検出器機能の拡張
- [ ] 棋譜コメント機能
- [ ] ユーザー別棋譜管理
- [ ] API機能の追加
- [ ] テストカバレッジの向上
- [ ] 本番環境対応
- [ ] ログ監視機能の追加

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。