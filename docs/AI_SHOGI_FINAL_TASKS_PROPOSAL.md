# 上申書：AI将棋機能—残タスク実行申請（技術詳細）

提出者：chatGPT  
宛先：事業開発部部門長chatGPT様  
件名：AI将棋（/engine/shogi 系）安定運用のための最終仕上げタスク実行申請

---

## 1. 目的

現状は「手動起動＋接続で対局可能」な水準です。本申請は、誰が・いつ使っても安定し、運用事故・説明コストを最小化するための仕上げタスクを実行する許可を求めるものです。技術的には、

1) WebSocketクライアントの単一路線化、  
2) 自動起動と健全性監視の実装強化、  
3) E2E 自動スモーク、  
4) 最低限の設定UI、  
5) トークン非開示化とログ・キャッシュのセキュア化徹底、  

の5本柱で構成します。

## 2. 現状（既に移行済みの要素）

- ルーティング：/engine/shogi 正規化、/engine/vs-engine リダイレクト、/engine/health プロキシ（OK/NG）。
- UI 注入：テンプレから ENGINE_CONFIG = { ws_url, movetime_ms } を注入済み。
- ポート検出：run-bridge.ps1 が last_port.txt に実ポートを書出し、Flask 側 routes.py が最優先で参照。
- WS 仕様：/ws 路線、?token= クエリ対応、タイプ互換（engineMove/engine_move）を吸収する準備。
- キャッシュ対策：Cache-Control: no-store を UI ルートへ付与、ログの token マスク済み。

## 3. 残タスク（実行申請）

### 3.1 WebSocket クライアントの単一路線化（bridge-adapter.js へ集約）

- 目的: 重複実装の解消、退行と保守コストの削減。
- 範囲: `apps/static/engine/bridge-adapter.js` を唯一の接続レイヤとして読み込み、テンプレ内のWS処理を Adapter 経由へ。
- API（固定化）: `Bridge.connect() / Bridge.disconnect() / Bridge.gameNew({movetime_ms}) / Bridge.humanMove(usi) / Bridge.send({type,line}) / Bridge.on(..)`
- 内部: ping/pong、指数バックオフ、二重接続ガード、送信キュー、type 正規化を実装。
- 受入基準: テンプレにWS直参照なし、切断→再接続で未送信キュー自動再送、二重送信なし。

### 3.2 自動起動（ヘルスNG時の /engine/start 連携）と健全性監視

- 目的: 「開いたが動かない」を根絶。未起動なら自動起動→接続まで自動化。
- 範囲: UI で `/engine/health` を確認し NG なら `/engine/start` をワンショット呼び出し→ ready 待ち→接続。サーバは `-Port 0` で起動し `last_port.txt` 更新を保証。
- セキュリティ: `/engine/start` は認可必須・レート制限、CSRF 対策。
- 受入基準: 未起動→ページ表示だけで自動起動・自動接続・初手応手まで成功。

### 3.3 E2E 自動スモーク（UI 実体験「初手→応手→KIF」）

- 目的: 実運用経路の回帰検知。
- 範囲: Playwright/Selenium で /engine/shogi を開き、接続→7g7f→bestmove→KIF 生成まで検証。Windows CI ランナーで実行、環境変数でスキップ可。
- 受入基準: 3項目が緑。失敗時は `/logs/usi-bridge/*.log` と console dump を添付。

### 3.4 最低限の設定UI（Threads / USI_Hash / movetime_ms）

- 目的: 性能・安定性の自己調整。
- 範囲: 簡易ドロワに 3 項目。`setoption` と `movetime_ms` を反映。localStorage 保存。
- 受入基準: 再対局で即反映。既定へ戻すリンクあり。

### 3.5 トークン非開示化・ログ/キャッシュのセキュリティ徹底

- 目的: 監査・外部公開に耐える露出最小化。
- 範囲: `/engine/health` から `ws_url`（token付）を削除し、`{ok,status,ws_path}` のみに。クライアントの `ws_url` はテンプレ注入のみ。全ルート no-store を確認。ログでは token マスク。
- 受入基準: クライアントログに token 表示なし。`/engine/health` 出力に token を含まない。

## 4. 技術的根拠（なぜ必要か）

- 単一路線化: 1箇所修正で全画面の挙動を統一。退行低減。
- 自動起動: 起動忘れ/ポート競合を恒久対策。UI からの一貫動作で説明不要化。
- E2E: WS 101〜双方向の実経路を毎回踏み、回帰を早期発見。
- 設定UI: 現場の自己解決を可能にし問合せ削減。
- 非開示化: token 露出の恒久対策。

## 5. 影響範囲と後方互換

- API/WS は後方互換（Adapter が互換吸収）。
- テンプレは接続呼び出し点の付け替えのみ。
- `/engine/health` の `ws_url` 削除は軽微で、テンプレ注入利用のためUI影響なし。

## 6. リスクと対策

- 集約での一時的な接続不具合 → フィーチャーフラグ `USE_BRIDGE_ADAPTER` でロールバック。
- `/engine/start` の濫用 → 認可必須・レート制限・監査ログ。
- CI の不安定 → スキップ環境変数/長めのタイムアウト/指数バックオフ。
- 設定の過大値 → サーバ側のバリデーション。

## 7. 実施手順（概略）

1) Adapter 統合ブランチ作成 → 差し替え → 手動スモーク  
2) `/engine/start` 実装・CSRF/RateLimit → ヘルスNGから自動起動の確認  
3) E2E（UI）を追加 → CI 組み込み（Windows）  
4) 設定UI 追加 → setoption / movetime_ms の反映確認  
5) `/engine/health` 非開示化 → grep による token 露出監査  
6) リリース：`USE_BRIDGE_ADAPTER` を ON、問題時 OFF

## 8. 受入判定（チェックリスト）

- [ ] ブリッジ未起動でも /engine/shogi が自動起動→自動接続する  
- [ ] 7g7f 入力で ENGINE 応手が返る（2 回連続で再現）  
- [ ] 切断→自動再接続→送信キュー再送が成立  
- [ ] `/engine/health` 出力に token が含まれない  
- [ ] `grep -R "token=" apps/static apps/shogi` でクライアント出力が無い  
- [ ] CI の E2E（UI）で 初手→応手→KIF が緑

---

承認欄：

- 承認者：____________________（部門長）  日付：__________
- 実施責任者：________________  日付：__________
