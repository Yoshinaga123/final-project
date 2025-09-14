/**
 * KifuForJS連携モジュール
 * USI Bridge → KIF変換 → KifuForJS表示
 */

class KifuJSBridge {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.kifuInstance = null;
        this.currentMoves = [];
    }

    // WebSocketからの対局データを受信
    onGameEvent(gameData) {
        if (gameData.type === 'game') {
            this.updateKifuDisplay(gameData.state);
        }
    }

    // USI棋譜をKIF形式に変換してKifuForJSに送信
    async updateKifuDisplay(gameState) {
        try {
            // サーバーサイドでUSI→KIF変換を依頼
            const kifData = await this.convertUSIToKIF(gameState.moves);
            
            // KifuForJSに読み込み
            this.loadKifuData(kifData);
            
            // 最新手に移動
            if (this.kifuInstance) {
                this.kifuInstance.goto(gameState.moves.length);
            }
            
        } catch (error) {
            console.error('KifuJS更新エラー:', error);
        }
    }

    // USI→KIF変換 (WebSocket経由)
    async convertUSIToKIF(usiMoves) {
        return new Promise((resolve, reject) => {
            // WebSocketでサーバーに変換要求
            if (ws && ws.readyState === WebSocket.OPEN) {
                const requestId = 'kif_' + Date.now();
                
                // レスポンス待機
                const messageHandler = (event) => {
                    const data = JSON.parse(event.data);
                    if (data.type === 'kifGenerated' && data.requestId === requestId) {
                        ws.removeEventListener('message', messageHandler);
                        resolve(data.kifContent);
                    }
                };
                
                ws.addEventListener('message', messageHandler);
                
                // 変換要求送信
                ws.send(JSON.stringify({
                    type: 'generateKIF',
                    requestId: requestId,
                    moves: usiMoves,
                    gameInfo: {
                        sente: '水匠',
                        gote: '人間',
                        date: new Date().toLocaleDateString('ja-JP')
                    }
                }));
                
                // タイムアウト設定
                setTimeout(() => {
                    ws.removeEventListener('message', messageHandler);
                    reject(new Error('KIF変換タイムアウト'));
                }, 5000);
            } else {
                reject(new Error('WebSocket未接続'));
            }
        });
    }

    // KifuForJSにKIFデータをロード
    loadKifuData(kifContent) {
        try {
            // KifuForJSインスタンス作成/更新
            if (this.kifuInstance) {
                this.kifuInstance.destroy();
            }
            
            this.kifuInstance = new Kifu(this.container, {
                kifu: kifContent,
                format: 'kif',
                showComments: false,
                showBoardNumber: true,
                enableEdit: false
            });
            
            console.log('KifuForJS更新完了');
            
        } catch (error) {
            console.error('KifuForJS読み込みエラー:', error);
        }
    }

    // 手動で特定の手数に移動
    gotoMove(moveNumber) {
        if (this.kifuInstance) {
            this.kifuInstance.goto(moveNumber);
        }
    }

    // 盤面をリセット
    reset() {
        if (this.kifuInstance) {
            this.kifuInstance.goto(0);
        }
    }
}

// 使用例
/*
const kifuBridge = new KifuJSBridge('kifu-container');

// WebSocketメッセージハンドラーに統合
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'game') {
        kifuBridge.onGameEvent(data);
    }
    
    // 既存の処理...
};
*/
