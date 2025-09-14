// KifuForJS連携サンプル（最小実装）
// tools/kifu-integration.js

/**
 * bestmove受信時にKifuForJSの盤面を更新するサンプル
 */
class KifuIntegration {
    constructor() {
        this.position = "startpos";
        this.moves = [];
        this.ws = null;
    }

    // WebSocket接続
    connectToEngine() {
        // 共有Bridgeアダプタがあればそれを利用（UI側で自動接続される想定）
        if (window.Bridge && typeof window.Bridge.on === 'function') {
            window.Bridge.on('engine', (msg) => this.handleEngineMessage(msg));
            window.Bridge.on('parsed', (msg) => this.handleEngineMessage(msg));
            // エンジン応答（bestmove）
            window.Bridge.on('engineMove', (mv) => this.applyMoveToBoard(mv));
            // 人間の手エコーも取り込み、KIFU側の手順に反映
            window.Bridge.on('humanMove', (mv) => this.applyMoveToBoard(mv));
            // 状態同期で既存の手順があれば初期化
            window.Bridge.on('state', (st) => {
                const moves = st && Array.isArray(st.moves) ? st.moves.slice() : [];
                this.moves = moves;
                this.position = 'startpos';
                try { if (typeof log === 'function') log(`KIFU state sync: ${this.moves.length}手`); } catch(_) {}
            });
            return;
        }
        // 直接WS接続
        const cfg = (window.ENGINE_CONFIG||{});
        const url = cfg.ws_url || 'ws://127.0.0.1:8787/ws';
        this.ws = new WebSocket(url);
        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleEngineMessage(data);
            } catch (e) {
                console.log('Raw message:', event.data);
            }
        };
    }

    // エンジンメッセージ処理
    handleEngineMessage(data) {
        if (data.type === 'engine') {
            // bestmove受信時の処理
            if (data.line.startsWith('bestmove ')) {
                const move = data.line.split(' ')[1];
                if (move && move !== 'resign') {
                    this.applyMoveToBoard(move);
                }
            }
        } else if (data.type === 'parsed') {
            // pv（主変化）のハイライト表示
            if (data.pv && data.pv.length > 0) {
                this.highlightPvMoves(data.pv);
            }
        }
    }

    // 指し手を盤面に適用
    applyMoveToBoard(move) {
    // 同一手の連続適用を抑止（engineMove と engine 生ログの二重通知対策）
    if (!move) return;
    if (this.moves.length > 0 && this.moves[this.moves.length - 1] === move) { return; }
    try { if (typeof log === 'function') log(`move: ${move}`); } catch(_) {}
        
        // 指し手リストに追加
        this.moves.push(move);
        
        // KifuForJSに適用するposition文字列を構築
        const positionCommand = this.buildPositionCommand();
    try { if (typeof log === 'function') log(`position: ${positionCommand}`); } catch(_) {}
        
        // KifuForJSのAPIを呼び出し（実際の実装では適切なAPIを使用）
        if (typeof window !== 'undefined' && window.kifuForJS) {
            this.updateKifuForJS(positionCommand, move);
        }
    }

    // position startpos moves ... の構築
    buildPositionCommand() {
        if (this.moves.length === 0) {
            return "position startpos";
        }
        return `position startpos moves ${this.moves.join(' ')}`;
    }

    // KifuForJS更新（サンプル実装）
    updateKifuForJS(positionCommand, lastMove) {
        // KifuForJSの実際のAPIに合わせて実装
        // 例: window.kifuForJS.setPosition(positionCommand);
        
    try { if (typeof log === 'function') log('KifuForJS更新'); } catch(_) {}
    console.log('KifuForJS Update:', {
            position: positionCommand,
            lastMove: lastMove,
            moveCount: this.moves.length
        });
    }

    // 主変化のハイライト表示
    highlightPvMoves(pvMoves) {
        console.log('PV Highlight:', pvMoves.slice(0, 3).join(' '));
        
        // 候補手のハイライト表示（実装例）
        if (typeof window !== 'undefined' && window.kifuForJS) {
            // window.kifuForJS.highlightMoves(pvMoves.slice(0, 3));
        }
    }

    // エンジンに指し手を送信
    sendMove(position = "startpos", moves = []) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const positionCmd = moves.length > 0 
                ? `position ${position} moves ${moves.join(' ')}`
                : `position ${position}`;
            
            this.ws.send(JSON.stringify({
                type: 'send',
                lines: [
                    positionCmd,
                    'go movetime 2000'
                ]
            }));
        }
    }

    // 新しいゲーム開始
    startNewGame() {
        this.position = "startpos";
        this.moves = [];
        
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'send',
                line: 'usinewgame'
            }));
        }
    }
}

// 使用例
const kifuIntegration = new KifuIntegration();

// DOM読み込み後に接続
if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
        kifuIntegration.connectToEngine();
        
        // 例: 2秒後に初期局面で思考開始
        setTimeout(() => {
            kifuIntegration.sendMove();
        }, 2000);
    });
}

// Node.js環境でのエクスポート
if (typeof module !== 'undefined' && module.exports) {
    module.exports = KifuIntegration;
}

// ブラウザ環境でのグローバル
if (typeof window !== 'undefined') {
    window.KifuIntegration = KifuIntegration;
}
