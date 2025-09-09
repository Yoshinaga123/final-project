# トラブルシューティング記録
作成日: 2025年9月8日
件名: 物体検知ギャラリー機能の500エラー解決

## 🚨 発生した問題

### 症状
- URL: `http://localhost:5000/detector/gallery`
- エラー: HTTP 500 Internal Server Error
- ユーザー報告: "ギャラリーページにアクセスすると500エラーが発生"

### エラーログ
```
Traceback (most recent call last):
  File "flask/app.py", line 917, in full_dispatch_request
    rv = self.dispatch_request()
  File "flask_debugtoolbar/__init__.py", line 222, in dispatch_request
    return view_func(**view_args)
  File "apps/detector/routes.py", line 37, in index
    return render_template('detector/index.html')
jinja2.exceptions.TemplateSyntaxError: Unexpected end of template. 
Jinja was looking for the following tags: 'endblock'.
```

---

## 🔍 調査プロセス

### Step 1: エラーログ分析
**発見**: Jinjaテンプレート構文エラーが最初の問題
- ファイル: `detector/index.html`
- 原因: ファイル末尾の不正な構文（余分な空行）

### Step 2: テンプレート修正
**対処**: detector/index.html の末尾修正
```diff
</div>
{% endblock %}
-

+{% endblock %}
```

### Step 3: 根本原因の特定
**発見**: ギャラリー機能で新たな500エラー
- 原因: UserImageテーブルが存在しない
- 状況: モデル定義は存在するが、マイグレーション未実行

### Step 4: データベース調査
**調査ツール**: 独自作成の `check_database.py`
**結果**: 
- 存在するテーブル: users, addresses
- 不存在: user_images テーブル
- マイグレーション履歴なし

---

## ✅ 解決手順

### 1. テンプレート構文エラー修正
```bash
# detector/index.html の末尾修正
```

### 2. エラーハンドリング追加
```python
# apps/detector/routes.py - gallery関数
try:
    images = UserImage.query.filter_by(is_deleted=False).all()
    count = len(images)
    return render_template('detector/gallery.html', images=images, count=count)
except Exception as e:
    return f"エラーが発生しました: {str(e)}", 500
```

### 3. マイグレーション実行
```bash
# UserImageテーブル作成
flask db migrate -m "Add UserImage table"
flask db upgrade
```

### 4. 動作確認
```bash
# データベース状況再確認
python check_database.py
```

---

## 🎯 解決結果

### Before (問題発生時)
- ❌ ギャラリーページアクセス → 500エラー
- ❌ UserImageテーブル未存在
- ❌ テンプレート構文エラー

### After (解決後)
- ✅ ギャラリーページ正常表示
- ✅ UserImageテーブル作成完了
- ✅ エラーハンドリング強化
- ✅ "0枚の画像が見つかりました"メッセージ表示

---

## 📚 学んだこと

### 1. モデル定義とマイグレーションの重要性
**教訓**: モデルを定義しただけではテーブルは作成されない
- SQLAlchemyモデル定義 ≠ 実際のデータベーステーブル
- マイグレーション実行が必須

### 2. エラーハンドリングの価値
**効果**: エラーの詳細が把握できるようになった
```python
# 追加したエラーハンドリング
try:
    # データベース操作
except Exception as e:
    return f"エラーが発生しました: {str(e)}", 500
```

### 3. 段階的デバッグの重要性
**プロセス**:
1. エラーログ確認
2. 表面的な問題修正（テンプレート）
3. 根本原因特定（データベース）
4. 根本解決（マイグレーション）

### 4. 調査ツールの作成
**価値**: `check_database.py` で状況を可視化
- テーブル一覧
- スキーマ情報
- 実際のデータ
- リレーションシップ確認

---

## 🛠️ 今後の改善案

### 1. 開発プロセス改善
- [ ] 新機能開発時のマイグレーション確認チェックリスト
- [ ] テスト環境でのデータベース状態確認
- [ ] CI/CDでのマイグレーション自動チェック

### 2. エラーハンドリング標準化
- [ ] 全ルートでの統一エラーハンドリング
- [ ] ユーザーフレンドリーなエラーメッセージ
- [ ] ログレベルの適切な設定

### 3. 監視・アラート
- [ ] データベース接続監視
- [ ] エラー率監視
- [ ] パフォーマンス監視

### 4. ドキュメント整備
- [ ] データベース設計書
- [ ] API仕様書
- [ ] トラブルシューティングガイド

---

## 🔧 使用したコマンド・ツール

### データベース調査
```bash
python check_database.py    # 独自作成の調査ツール
python check_models.py      # モデル定義確認ツール
```

### マイグレーション
```bash
flask db migrate -m "Add UserImage table"
flask db upgrade
```

### アプリケーション起動
```bash
python run.py
```

---

## 📊 影響範囲

### 修正されたファイル
1. `apps/detector/templates/detector/index.html` - テンプレート構文修正
2. `apps/detector/routes.py` - エラーハンドリング追加
3. `apps/detector/templates/detector/gallery.html` - テンプレート安全化
4. `migrations/versions/c1b0269f1c91_add_userimage_table.py` - 新規マイグレーション

### 新規作成されたテーブル
- `user_images` - 画像管理テーブル
- `alembic_version` - マイグレーション履歴テーブル

### 影響を受けた機能
- ✅ 物体検知ギャラリー機能 - 復旧
- ✅ 画像アップロード機能 - 準備完了
- ➡️ 将棋アプリ機能 - 影響なし

---

*このトラブルシューティング記録は、同様の問題が発生した際の参考資料として保管されます。*
*記録者: GitHub Copilot*
*最終更新: 2025年9月8日 16:50*
