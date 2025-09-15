// Simple WebSocket Bridge for 水匠 (Suisho) Engine
// シンプルで確実に動作する実装

(function() {
    'use strict';
    
    // 二重初期化防止
    if (window.SimpleBridge) return;
    
    // 設定
    const CONFIG = {
        wsUrl: 'ws://127.0.0.1:8787/ws', // 固定ポート（8787）にのみ接続
        movetime: 2000, // 既定（後で ENGINE_CONFIG で上書き）
        reconnectDelay: 1000,
        maxReconnectAttempts: 10
    };
    
    // サーバ注入の設定（ENGINE_CONFIG）があれば反映
    try {
        if (window.ENGINE_CONFIG) {
            const inj = window.ENGINE_CONFIG;
            // ws_url は無視（ポート固定のため）
            if (typeof inj.movetime_ms === 'number' && inj.movetime_ms > 0) {
                CONFIG.movetime = inj.movetime_ms;
            }
        }
    } catch (e) {
        // noop（既定値を使用）
    }
    
    // 状態管理
    let ws = null;
    let connected = false;
    let reconnectAttempts = 0;
    let reconnectTimer = null;
    
    // フォールバックは使用せず、固定の CONFIG.wsUrl のみを使用（ユーザー要件）
    
    // イベントリスナー
    const listeners = {
        open: [],
        close: [],
        error: [],
        engineMove: [],
        humanMove: [],
        gameOver: [],
        message: []
    };
    
    // ログ出力
    function log(...args) {
        console.log('[SimpleBridge]', ...args);
    }
    
    // イベント登録
    function on(event, callback) {
        if (listeners[event]) {
            listeners[event].push(callback);
        }
    }
    
    // イベント発火
    function emit(event, data) {
        if (listeners[event]) {
            listeners[event].forEach(callback => {
                try {
                    callback(data);
                } catch (e) {
                    console.error('Event callback error:', e);
                }
            });
        }
    }
    
    // メッセージ送信
    function send(message) {
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            log('WebSocket not connected, cannot send:', message);
            return false;
        }
        
        try {
            const jsonMessage = typeof message === 'string' ? message : JSON.stringify(message);
            ws.send(jsonMessage);
            log('Sent:', jsonMessage);
            return true;
        } catch (e) {
            log('Send error:', e);
            return false;
        }
    }
    
    // WebSocket接続
    function connect() {
        if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) {
            log('Already connecting or connected');
            return;
        }
    const targetUrl = CONFIG.wsUrl;
    log('Connecting to:', targetUrl);
        
        try {
            ws = new WebSocket(targetUrl);
            
            ws.onopen = function() {
                log('Connected successfully');
                connected = true;
                reconnectAttempts = 0;
                emit('open');
                
                // 制御権を取得
                send({ type: 'takeControl' });
                
                // 状態を取得
                send({ type: 'getState' });
            };
            
            ws.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    handleMessage(data);
                } catch (e) {
                    log('Message parse error:', e);
                    emit('message', { type: 'raw', data: event.data });
                }
            };
            
            ws.onclose = function(event) {
                log('Connection closed:', event.code, event.reason);
                connected = false;
                emit('close', event);
                
                // 自動再接続
                if (reconnectAttempts < CONFIG.maxReconnectAttempts) {
                    reconnectAttempts++;
                    log(`Reconnecting in ${CONFIG.reconnectDelay}ms (attempt ${reconnectAttempts})`);
                    reconnectTimer = setTimeout(connect, CONFIG.reconnectDelay);
                }
            };
            
            ws.onerror = function(error) {
                log('WebSocket error:', error);
                emit('error', error);
            };
            
        } catch (e) {
            log('Connection error:', e);
            emit('error', e);
        }
    }
    
    // メッセージ処理
    function handleMessage(data) {
        log('Received:', data);
        
        const type = (data.type || '').toLowerCase();
        
        switch (type) {
            case 'game':
                handleGameMessage(data);
                break;
                
            case 'enginemove':
            case 'engine_move':
                emit('engineMove', data.move || data.lastMove);
                break;
                
            case 'state':
                emit('message', data);
                break;
                
            case 'error':
                log('Engine error:', data);
                emit('error', data);
                break;
                
            default:
                emit('message', data);
                break;
        }
    }
    
    // ゲームメッセージ処理
    function handleGameMessage(data) {
        const event = data.event || '';
        
        switch (event) {
            case 'bestmove':
                const move = data.lastMove || data.move;
                if (move && move !== 'resign' && move !== 'win') {
                    emit('engineMove', move);
                }
                break;
                
            case 'humanMove':
            case 'human':
            case 'move':
                emit('humanMove', data.lastMove || data.move);
                break;
                
            case 'new':
                log('New game started');
                emit('message', data);
                break;
                
            case 'gameOver':
                emit('gameOver', data.result || data);
                break;
                
            default:
                emit('message', data);
                break;
        }
    }
    
    // 接続切断
    function disconnect() {
        if (reconnectTimer) {
            clearTimeout(reconnectTimer);
            reconnectTimer = null;
        }
        
        reconnectAttempts = CONFIG.maxReconnectAttempts; // 再接続を停止
        
        if (ws) {
            ws.close();
            ws = null;
        }
        
        connected = false;
        log('Disconnected');
    }
    
    // 人間の手を送信
    function humanMove(move) {
        log('Human move:', move);
        
        if (!connected) {
            log('Not connected, attempting to connect...');
            connect();
            return false;
        }
        
        // 人間の手を送信
        const success = send({
            type: 'humanMove',
            move: move,
            movetime_ms: CONFIG.movetime
        });
        
        return success;
    }
    
    // 新しいゲーム開始
    function newGame() {
        log('Starting new game');
        
        if (!connected) {
            connect();
        }
        
        send({ type: 'takeControl' });
        send({
            type: 'gameNew',
            movetime: CONFIG.movetime,
            position: 'startpos',
            // 人間が先手番（sente）で開始するため、エンジンの自動着手を禁止
            engineStarts: false,
            gameId: 'game-' + Date.now()
        });
        send({ type: 'getState' });
    }
    
    // エンジン設定
    function setOption(name, value) {
        return send({
            type: 'setOption',
            name: name,
            value: value
        });
    }
    
    // 公開API
    const SimpleBridge = {
        // 接続関連
        connect: connect,
        disconnect: disconnect,
        isConnected: () => connected,
        
        // イベント
        on: on,
        
        // メッセージ送信
        send: send,
        
        // ゲーム操作
        humanMove: humanMove,
        newGame: newGame,
        setOption: setOption,
        
    // 設定（外部から wsUrl / movetime を上書き可能）
    config: CONFIG
    };
    
    // グローバルに登録
    window.SimpleBridge = SimpleBridge;
    
    // 旧API互換性のため
    window.Bridge = SimpleBridge;
    
    // 自動接続
    log('SimpleBridge initialized');
    
    // DOM読み込み完了後に自動接続
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', connect);
    } else {
        setTimeout(connect, 100);
    }
    
})();
