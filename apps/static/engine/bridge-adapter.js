// Robust WS Bridge Adapter (minimal drop-in)
// - single-flight connect guard
// - exponential backoff with jitter (250ms -> 5s)
// - app-level ping/pong + stale detection
// - send queue
// - auto resume by getState
// - engineMove / engine_move 互換
// 既存 UI からは window.Bridge を呼ぶだけで良い。

(function () {
  if (window.ENGINE_WS_BOUND) return; // 二重バインド防止
  window.ENGINE_WS_BOUND = true;

  const CFG = (window.ENGINE_CONFIG || {});
  const BASE_WS_URL = CFG.ws_url || null; // サーバが注入（推奨）
  const MOVETIME_MS = Number(CFG.movetime_ms || window.MOVETIME_MS || 2000);
  const DUMP = (localStorage.getItem("shogi.dump") === "1");
  const AUTOCONN = (window.BRIDGE_AUTOCONNECT !== false);
  // アプリ層 ping/pong はサーバのプロトコル ping と競合しうるため、デフォルト無効
  // 有効化したい場合のみ window.BRIDGE_APP_PING = true を設定
  const APP_PING = (window.BRIDGE_APP_PING === true);
  const APP_PING_INTERVAL = Number(window.BRIDGE_APP_PING_INTERVAL || 45000);
  const APP_PONG_TIMEOUT = Number(window.BRIDGE_APP_PONG_TIMEOUT || 30000);

  const EVT = new Map(); // event -> Set<fn>
  const on = (e, f) => { if (!EVT.has(e)) EVT.set(e, new Set()); EVT.get(e).add(f); return () => off(e, f); };
  const off = (e, f) => { const s = EVT.get(e); if (s) s.delete(f); };
  const emit = (e, payload) => { const s = EVT.get(e); if (s) for (const f of s) try { f(payload) } catch(_){} };

  let ws = null;
  let wsUrl = BASE_WS_URL;         // 現在の接続先（?token 含む）
  let connecting = false;
  let closedByUser = false;
  let backoffMs = 250;             // 指数バックオフ 250ms〜5000ms
  let pingTimer = null;
  let pongTimer = null;
  let lastPongAt = 0;
  let sendQueue = [];              // 未接続時の送信バッファ
  let clientId = `fp-${Math.random().toString(36).slice(2)}`;
  let connected = false;
  let inGame = false;              // 対局中フラグ（state/new から同期）
  // humanMove 後の go movetime 送信制御（エコー遅延/欠落フォールバック）
  let goArmed = false;
  let goSent = false;
  let goTimer = null;
  // bestmove の連続重複を抑止（UI 二重ログ防止）
  let lastEngineMove = null;

  function log() { if (DUMP) console.log("[Bridge]", ...arguments); }

  // ws_url が未注入でも復旧できるよう デフォルトを設定
  async function resolveWsUrl() {
    if (wsUrl) return wsUrl;
    try {
      // ENGINE_CONFIG から token を取得
      const tok = (typeof CFG.token === "string" ? CFG.token : null);
      
  // デフォルト接続先を設定（固定ポリシーに合わせ 8787 に統一）
  wsUrl = `ws://${(location && location.hostname) ? location.hostname : "127.0.0.1"}:8787/ws${tok ? `?token=${encodeURIComponent(tok)}` : ""}`;
      log("using default ws_url:", wsUrl);
      return wsUrl;
    } catch (e) {
      log("resolveWsUrl failed:", e);
  // 最後の保険：既知デフォルト（固定ポリシーに合わせ 8787 に統一）
  wsUrl = `ws://${(location && location.hostname) ? location.hostname : "127.0.0.1"}:8787/ws`;
      return wsUrl;
    }
  }

  function startPing() {
    if (!APP_PING) return; // 既定では無効
    stopPing();
    pingTimer = setInterval(() => {
      safeSend({ type: "ping", t: Date.now() });
      // pong 未着はログのみ（サーバ側のプロトコル ping に任せる）
      clearTimeout(pongTimer);
      pongTimer = setTimeout(() => {
        if (!connected) return;
        log("pong timeout (app-level) — ignore; server ping handles liveness");
        emit("stale", { since: Date.now() - lastPongAt });
      }, APP_PONG_TIMEOUT);
    }, APP_PING_INTERVAL);
  }
  function stopPing() {
    if (pingTimer) { clearInterval(pingTimer); pingTimer = null; }
    if (pongTimer) { clearTimeout(pongTimer); pongTimer = null; }
  }

  function flushQueue() {
    if (!connected) return;
    const q = sendQueue.slice(); sendQueue.length = 0;
    for (const msg of q) {
      try { ws.send(JSON.stringify(msg)); } catch(e){ log("flush failed:", e); }
    }
  }

  function scheduleReconnect() {
    if (closedByUser) return;
    const jitter = Math.random() * 0.25 + 0.875; // 微揺らぎ
    const wait = Math.min(backoffMs, 5000) * jitter;
    log(`reconnect in ${Math.round(wait)}ms`);
    setTimeout(() => connect(), wait);
    backoffMs = Math.min(backoffMs * 2, 5000);
  }

  async function connect() {
    if (connecting || connected || closedByUser) return;
    connecting = true;
    try {
      await resolveWsUrl();
      if (!wsUrl) {
        throw new Error("WebSocket URL not resolved");
      }
      log("connecting to", wsUrl);

      ws.onopen = () => {
        connecting = false;
        connected = true;
        backoffMs = 250;
        emit("open");
        log("OPEN");
        // 初回ハンドシェイク（任意）
        safeSend({ type: "hello", clientId });
        // 参照実装に合わせ、まず制御権を確保 → 状態復元
        safeSend({ type: "takeControl" });
        safeSend({ type: "getState" });
        startPing(); // デフォルトでは動かない（APP_PING=false）
        flushQueue();
      };

      ws.onmessage = (ev) => {
        let data = null;
        try { data = JSON.parse(ev.data); } catch(_) { data = { type: "raw", data: ev.data }; }
        if (!data || typeof data !== "object") return;

        // 正規化：type 小文字化 + 互換吸収
        const tRaw = String(data.type || "").toLowerCase();
        if (tRaw === "pong") { lastPongAt = Date.now(); return; }

        // NOT_CONTROLLER を踏んだら即座に制御権を再取得
        if (tRaw === "error" && data.code === "NOT_CONTROLLER") {
          safeSend({ type: "takeControl" });
          // 状態を明示取得して UI の flushQueuedMove を促す
          safeSend({ type: "getState" });
          emit("error", data);
          return;
        }

        // 対局開始通知で inGame を true に（UI にも 'game' を通知）
        if (tRaw === "game" && data.event === "new") {
          inGame = true;
          lastEngineMove = null;
          emit("game", data);
          return;
        }

        // 旧イベント互換（engine_move）
        if (tRaw === "enginemove" || tRaw === "engine_move") {
          emit("engineMove", data.move || data.lastMove || data);
          return;
        }
        // GAME_OVER バリエーション
        if (tRaw === "game" && ((data.status||"").toUpperCase() === "GAME_OVER" || data.event === "gameOver")) {
          emit("gameOver", data.result || data);
          return;
        }
        // bestmove → engineMove 合流（go武装解除）
        if (tRaw === "game" && data.event === "bestmove") {
          goArmed = false; if (goTimer) { clearTimeout(goTimer); goTimer = null; }
          goSent = false;
          let mv = data.lastMove || data.move;
          // bestmove正規化：空文字・resign・win除去、ponder分離
          if (typeof mv === "string" && mv.trim()) {
            mv = mv.trim().split(/\s+/)[0]; // "7g7f ponder 8c8d" → "7g7f"
            if (mv === "resign" || mv === "win") mv = null;
          } else {
            mv = null;
          }
          if (!mv) return; // 有効な手がない場合は何もしない
          if (mv === lastEngineMove) return; // 直近と同一なら無視
          lastEngineMove = mv;
          // デバッグ: ブリッジからフロントへの送信ログ
          log("emit engineMove:", mv);
          emit("engineMove", mv);
          return;
        }
  // 人間手エコー：event 名の揺れ（humanMove/human/move）に対応
        if (tRaw === "game" && (data.event === "humanMove" || data.event === "human" || data.event === "move")) {
          emit("humanMove", data.lastMove || data.move);
          if (!goSent) {
            safeSend({ type: "send", line: `go movetime ${MOVETIME_MS}` });
            goSent = true;
          }
          goArmed = false; if (goTimer) { clearTimeout(goTimer); goTimer = null; }
          return;
        }
        // 状態スナップショット（inGame 同期）
        if (tRaw === "state" || (tRaw === "game" && data.event === "state")) {
          const st = data.state || data;
          if (st) {
            if (typeof st.in_game === "boolean") inGame = !!st.in_game;
            else if (Array.isArray(st.moves) && st.moves.length > 0) inGame = true;
          }
          // 状態同期時もデデュープ基準をリセット
          lastEngineMove = null;
          emit("state", st);
          return;
        }
        // ゲーム終了で inGame=false
        if (tRaw === "game" && (String(data.status||"").toUpperCase() === "GAME_OVER")) {
          inGame = false;
          goArmed = false; goSent = false; if (goTimer) { clearTimeout(goTimer); goTimer = null; }
          emit("gameOver", data.result || data);
          return;
        }
        // 解析行などはそのまま
        emit(tRaw || "message", data);
      };

      ws.onerror = (e) => {
        emit("error", e);
        const msg = (e && e.message) ? e.message : e;
        log("ONERROR", msg);
      };

      ws.onclose = (e) => {
        connecting = false;
        if (!connected && backoffMs === 250) {
          // 早期 Close は握手失敗のことが多い → health で ws_url 再解決
          wsUrl = null;
        }
        connected = false;
        stopPing();
  emit("close", e);
  const code = (e && typeof e.code !== 'undefined') ? e.code : '';
  const reason = (e && typeof e.reason !== 'undefined') ? e.reason : '';
  log("CLOSE", code, reason);
        scheduleReconnect();
      };
    } catch (e) {
      connecting = false;
      connected = false;
      emit("error", e);
      log("connect failed:", e);
      scheduleReconnect();
    }
  }

  function safeSend(msgObj) {
    if (!ws || ws.readyState !== 1) { // OPEN=1
      sendQueue.push(msgObj);
      return;
    }
    try { ws.send(JSON.stringify(msgObj)); }
    catch (e) { sendQueue.push(msgObj); log("send enqueue (err):", e); }
  }

  // --- 公開 API ---
  const Bridge = {
    connect,                               // 明示接続
    disconnect: () => { closedByUser = true; try { ws && ws.close(4001, "user-close"); } catch(_) {} },
    isConnected: () => connected,
    wsUrl:       () => wsUrl,
    ws:          () => ws,
    on, off,

    // 旧UI互換：send/ humanMove/ gameNew など
    send: (obj) => safeSend(obj),
    humanMove: (usiMove) => {
      // ① 未接続なら即座に接続開始（送信はキューに積まれる）
      if (!ws || ws.readyState !== 1) { try { connect(); } catch(_) {} }
      if (!inGame) { safeSend({ type: "gameNew", movetime: MOVETIME_MS, position: "startpos" }); }
      // go 送信のフォールバックを無効化（サーバ側で自動送信）
      // goArmed = true; goSent = false; if (goTimer) { clearTimeout(goTimer); goTimer = null; }
      // goTimer = setTimeout(() => {
      //   if (goArmed && !goSent) {
      //     // connected でなくても safeSend がキューし、接続後に送信される
      //     safeSend({ type: "send", line: `go movetime ${MOVETIME_MS}` });
      //     goSent = true;
      //   }
      // }, 400); // エコーが遅い環境向けの微待ち
      // サーバ側の便利用処理: movetime_ms があると自動で go を送る
      safeSend({ type: "humanMove", move: usiMove, movetime_ms: MOVETIME_MS });
    },
    gameNew: () => {
      // 参照実装に合わせる: 制御権を明示取得し、startpos を指定
      safeSend({ type: "takeControl" });
      safeSend({ type: "gameNew", movetime: MOVETIME_MS, position: "startpos", gameId: `auto-${Date.now()}` });
      // 念のための状態取得（UI 初期化）
      safeSend({ type: "getState" });
    },
    setOption: (name, value) => safeSend({ type: "setOption", name, value }),
    restart: () => safeSend({ type: "restart" }),
    getState: () => safeSend({ type: "getState" }),

    // 便利用：bestmoveを engineMove に束ね済み（on('engineMove', fn) を使う）
  };

  // 自動接続（テンプレ側から window.BRIDGE_AUTOCONNECT=false で無効化可）
  if (AUTOCONN) {
    if (document.readyState === "complete" || document.readyState === "interactive") {
      setTimeout(connect, 0);
    } else {
      document.addEventListener("DOMContentLoaded", () => connect(), { once: true });
    }
  }

  window.Bridge = Bridge;
})();
