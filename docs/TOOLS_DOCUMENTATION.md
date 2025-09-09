# 作成したツール・スクリプト一覧
作成日: 2025年9月8日
目的: データベース調査・管理用ツール

## 📋 作成したファイル一覧

### 1. check_database.py
**目的**: SQLiteデータベースの詳細調査
**機能**:
- テーブル一覧取得
- スキーマ情報表示（CREATE文、カラム情報）
- 実際のデータサンプル表示（最大5件）
- インデックス情報確認

**使用方法**:
```bash
python check_database.py
```

**出力例**:
```
📊 データベーススキーマ情報
🗂️ テーブル数: 4
📋 各テーブルの詳細スキーマ
💾 実際のデータサンプル
🔍 インデックス情報
```

### 2. check_models.py
**目的**: SQLAlchemyモデル定義と実テーブルの整合性確認
**機能**:
- モデル定義の詳細表示
- 実際のテーブル存在確認
- マイグレーション状態チェック
- UserImageテーブル特化チェック

**使用方法**:
```bash
python check_models.py
```

**重要な機能**:
- モデル定義 vs 実テーブルの乖離検出
- マイグレーション必要性の判定

### 3. relationship_example.py
**目的**: SQLAlchemyリレーションシップの使用例集
**機能**:
- リレーションシップ使用パターン
- テーブル結合の例
- lazyオプションの実践例

**内容**:
```python
def relationship_examples():
    """リレーションシップの使用例"""
    user = User.query.first()
    images = user.user_images.all()  # backref使用

def join_examples():
    """テーブル結合の例"""
    results = db.session.query(User, UserImage).join(UserImage).all()
```

### 4. DATABASE_REPORT.md
**目的**: データベース構造の包括的ドキュメント
**内容**:
- 全テーブルの詳細仕様
- リレーションシップ図解
- マイグレーション履歴
- 今後の拡張計画

### 5. TROUBLESHOOTING_20250908.md
**目的**: 500エラー解決プロセスの記録
**内容**:
- 問題発生から解決までの完全な記録
- 調査手順の詳細
- 学んだ教訓
- 今後の改善案

---

## 🛠️ ツールの特徴

### check_database.py の強み
1. **網羅性**: データベース全体を一度に把握
2. **視覚性**: 整理された見やすい出力
3. **実用性**: 実際のデータも確認可能
4. **汎用性**: 任意のSQLiteデータベースで使用可能

### check_models.py の価値
1. **整合性チェック**: モデル定義とテーブルの差分検出
2. **マイグレーション支援**: 何が未作成かを明確化
3. **開発支援**: Flask-SQLAlchemyの設定確認

### コード品質
- **エラーハンドリング**: try-catch で例外処理
- **可読性**: 適切なコメントと構造化
- **再利用性**: 関数分割で部分実行可能

---

## 🎯 実際の活用例

### 今回のトラブルシューティングでの使用
1. **check_database.py** → user_imagesテーブル未存在を発見
2. **check_models.py** → モデル定義との乖離を確認
3. **マイグレーション実行** → テーブル作成
4. **check_database.py** → 作成確認

### 今後の開発での活用
1. **新機能開発前**: 現在のDB状態確認
2. **マイグレーション後**: 適用結果確認
3. **デバッグ時**: データ状態の確認
4. **ドキュメント更新**: 最新状態の記録

---

## 📈 改善・拡張案

### check_database.py の拡張
- [ ] PostgreSQL対応
- [ ] テーブルサイズ情報
- [ ] 外部キー制約の詳細表示
- [ ] 出力フォーマット選択（JSON, CSV等）

### check_models.py の拡張
- [ ] 自動マイグレーション提案
- [ ] モデル変更の影響範囲分析
- [ ] テストデータ自動生成

### 新ツールのアイデア
- [ ] **backup_database.py**: 自動バックアップ
- [ ] **seed_data.py**: テストデータ投入
- [ ] **performance_check.py**: クエリパフォーマンス測定
- [ ] **schema_diff.py**: 環境間のスキーマ差分

---

## 🔧 使用方法・Tips

### 開発フロー組み込み
```bash
# 新機能開発開始時
python check_database.py > logs/db_state_before.txt

# モデル変更後
python check_models.py

# マイグレーション実行
flask db migrate -m "機能名"
flask db upgrade

# 結果確認
python check_database.py > logs/db_state_after.txt
```

### デバッグ時の活用
```bash
# エラー発生時
python check_models.py  # モデルとテーブルの整合性確認
python check_database.py  # 実データ確認
```

### 定期メンテナンス
```bash
# 週次または月次
python check_database.py > docs/weekly_db_report_$(date +%Y%m%d).txt
```

---

## 📝 保守・管理

### ファイル管理
- **場所**: プロジェクトルート
- **バックアップ**: Git管理
- **更新**: 機能追加時に随時アップデート

### 依存関係
- **必須**: sqlite3, SQLAlchemy, Flask
- **推奨**: プロジェクトの仮想環境内で実行

### ドキュメント連携
- DATABASE_REPORT.md: 定期更新
- TROUBLESHOOTING_*.md: 問題発生時に追記
- README_project.md: ツール使用方法を記載

---

*これらのツール群により、データベース管理とトラブルシューティングが大幅に効率化されました。*
*今後の開発・運用において継続的に活用・改善していきます。*

*作成者: GitHub Copilot*
*最終更新: 2025年9月8日 16:55*
