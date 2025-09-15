# Shogi UI（案A: サイドカー運用）

## 起動手順
1. ブリッジを起動:
   ```powershell
   scripts\run-bridge.ps1 -Engine "C:\\shogi\\engines\\suisho*.exe" -Port 8787
   ```
   - ログ: `logs/usi-bridge/bridge-YYYYMMDD-HHMMSS.log`
   - ヘルス: ログに `usi` → `usiok` → `readyok`

2. Flask を起動し、正規URL `/engine/shogi` へアクセス。（互換: `/shogi/vs-engine` → リダイレクト）

## 設定（.env 推奨）
MOVETIME_MS=2000  # 既定値は 2000ms（旧 USI_MOVETIME_MS は後方互換で読み取りのみ）
# USI_BRIDGE_TOKEN=xxxx   # optional
```

## ゼロセットアップ（公式配布からの自動導入）

ライセンスに同意済みであれば、次の手順で水匠（またはやねうら王相当）を自動ダウンロード・検証・展開して `engines/` に配置できます。

1) マニフェスト JSON を作成（URL と SHA256 を記載）
   - 雛形: `tools/suisho_manifest.sample.json`
   - 例: `tools/suisho_manifest.json` を作成し、`archiveUrl` と `archiveSha256` を実ファイルに合わせて書き換え

2) セットアップスクリプトの実行（PowerShell）
   ```powershell
   # PowerShell を管理者で開くことを推奨（7zip の PATH など環境依存のため）
   cd .\final-project
   scripts\setup-suisho.ps1 -Manifest tools/suisho_manifest.json -InstallDir engines/suisho
   ```

   - ZIP の場合は OS 標準で展開します
   - 7z の場合は `7z` コマンドが必要です（PATH 上に 7z.exe を追加）
   - ダウンロード完了後に SHA256 を検証し、不一致なら中断します
   - 展開後に最適な exe を自動検出し、`.env` の `USI_ENGINE_PATH` を上書きします（`-NoEnv` で抑止可）

3) ブリッジ起動（通常どおり）
   ```powershell
   scripts\run-bridge.ps1 -Port 8787
   ```

トラブルシュート:
- "7z not found" → 7-Zip をインストールし、`7z` が PATH から呼べるようにしてください
- "SHA256 mismatch" → URL・ファイルの改版や入力ミスを確認してください
- "No engine .exe found" → マニフェストの `innerPathHints` を実アーカイブの構成に合わせて調整

## 受け入れ基準（DoD）
- `/shogi/vs-engine` でUI表示、WS疎通
- 終局時に1回だけ `GAME_OVER` を受信し、以後入力拒否（UIロック）
- 再戦で復帰
- run-bridge.ps1 がポート衝突や起動失敗をわかりやすく通知

## 既知の復旧手順
- PORT_IN_USE: 8787を使用しているプロセスを停止 or `-Port`を変更
- ENGINE_START_FAILED: `-Engine` のパス/グロブを確認
## サービス化（任意: NSSM）
```powershell
nssm install usi-bridge "powershell.exe" "-ExecutionPolicy Bypass -File scripts\run-bridge.ps1 -Engine 'C:\\shogi\\engines\\suisho.exe' -Port 8787"
nssm set usi-bridge AppDirectory "<final-project root>"
nssm set usi-bridge AppStdout logs\usi-bridge\service.log
nssm set usi-bridge AppStderr logs\usi-bridge\service.err.log
```

---

セットアップ

## Engine VS Human UI

 - 正規URL: `/engine/shogi`
 - `ws_url` と `movetime_ms` をテンプレへ注入（Jinja）
 - UIは最小DOMでプレイ可能。既存UIへ置換する場合は以下の方針。

### 既存UIの丸ごと流用（最小差分）

1) サブモジュール: `vendor/shogi-engine-prototype`
2) 静的資産: `vendor/.../ui/*` を `apps/static/engine/` にコピー（または参照）
3) 設定注入: テンプレ内の `#shogi-config` JSON から `window.ENGINE_CONFIG` を組み立て
4) WSアダプタ: `apps/static/engine/bridge-adapter.js` を読み込み、既存UIの送受信を `window.Bridge` に委譲
5) 互換: `engineMove/engine_move` はアダプタで吸収、トークン付与・自動 `gameNew` はアダプタ側で対応
   - USI_BRIDGE_HOST / PORT / TOKEN / MOVETIME_MS / USI_AUTOSTART
   - USI_ENGINE_PATH / PYTHON_EXE / USI_BRIDGE_SCRIPT / USI_BRIDGE_PS1

起動
1. `python run.py`
2. 自動起動が有効ならブリッジ状態を確認し、未起動の場合は `scripts/run-bridge.ps1` を実行
3. ブラウザで `/engine/shogi`（または `/shogi/vs-engine`）へ

ヘルスチェック
- `/engine/health` で状態確認（ok=false の場合はログを確認）
- `scripts/run-bridge.ps1` のログは `logs/usi-bridge` 配下

トラブルシュート
- venv 取り違え: 依存未検出が多発。必ず同一 venv で起動
- TOKEN はログに出さない運用

