(function(){
  var CFG = window.ENGINE_CONFIG||{};
  var WS_URL = CFG.ws_url;
  window.FP_WS = function(){
    if (window.Bridge){
      window.Bridge.connect();
      var stub = { onmessage: null, readyState: 1,
        send: function(data){ try{ window.Bridge.send(JSON.parse(data)); }catch(e){} }
      };
      window.Bridge.on('event', function(m){ if(stub.onmessage) stub.onmessage({data: JSON.stringify(m)}); });
      window.Bridge.on('engineMove', function(mv){ if(stub.onmessage) stub.onmessage({data: JSON.stringify({type:'engineMove', move: mv})}); });
      window.Bridge.on('gameOver', function(r){ if(stub.onmessage) stub.onmessage({data: JSON.stringify({type:'game', status:'GAME_OVER', result:r})}); });
      return stub;
    }
    return new WebSocket(WS_URL);
  };
})();

/* --- extracted from shogi-ui-mvp.html --- */
let ws = null;
let gameState = null;
let selectedSquare = null;
let pendingMove = null;

// 初期盤面（平手）
const initialBoard = [
    ['l','n','s','g','k','g','s','n','l'],
    [null,'r',null,null,null,null,null,'b',null],
    ['p','p','p','p','p','p','p','p','p'],
    [null,null,null,null,null,null,null,null,null],
    [null,null,null,null,null,null,null,null,null],
    [null,null,null,null,null,null,null,null,null],
    ['P','P','P','P','P','P','P','P','P'],
    [null,'B',null,null,null,null,null,'R',null],
    ['L','N','S','G','K','G','S','N','L']
];

const pieceNames = {
    'P': '歩', 'L': '香', 'N': '桂', 'S': '銀', 'G': '金', 'B': '角', 'R': '飛', 'K': '玉',
    'p': '歩', 'l': '香', 'n': '桂', 's': '銀', 'g': '金', 'b': '角', 'r': '飛', 'k': '王',
    '+P': 'と', '+L': '杏', '+N': '圭', '+S': '全', '+B': '馬', '+R': '龍'
};

function connect() {
    try {
        log('WebSocket 接続開始');
        
        // 接続先URLを決定（ENGINE_CONFIG.ws_url があれば優先）。無ければ /ws に接続。
        (function(){
            const CFG = window.ENGINE_CONFIG || {};
            let url = CFG.ws_url;
            if (!url) {
                const params = new URLSearchParams(window.location.search);
                const token = params.get('token') || (CFG.token || null);
                url = 'ws://127.0.0.1:8787/ws' + (token ? ('?token=' + encodeURIComponent(token)) : '');
            }
            log('接続URL: ' + url);
            ws = new WebSocket(url);
        })();
        
        ws.onopen = function() {
            updateStatus('エンジンに接続しました', 'connected');
            log('✓ WebSocket接続成功');
            
            // 制御権を取得
            setTimeout(() => {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({type:'takeControl'}));
                    log('制御権を要求');
                }
            }, 100);
        };
        
        ws.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                log(`受信: ${data.type} - ${JSON.stringify(data)}`);
                
                if (data.type === 'game') {
                    if (data.event === 'bestmove') {
                        const move = data.lastMove || data.move;
                        if (move) {
                            log(`エンジン手: ${move}`);
                            updateStatus(`エンジンの手: ${move}`, 'info');
                        }
                    } else if (data.event === 'new') {
                        log('新しいゲーム開始');
                        updateStatus('新しいゲーム開始', 'info');
                    } else if (data.event === 'humanMove') {
                        const move = data.move || data.lastMove;
                        log(`人間の手確認: ${move}`);
                        updateStatus(`あなたの手: ${move}`, 'info');
                    }
                } else if (data.type === 'status') {
                    if (data.phase === 'CONTROL_GRANTED') {
                        log('制御権を取得しました');
                        updateStatus('制御権取得済み', 'connected');
                    }
                } else if (data.type === 'error') {
                    log(`エラー: ${data.message}`);
                    updateStatus(`エラー: ${data.message}`, 'error');
                }
            } catch (e) {
                log(`メッセージ解析エラー: ${e}`);
            }
        };
        
        ws.onclose = function(event) {
            updateStatus('切断されました', 'error');
            log(`✗ WebSocket切断 (code: ${event.code})`);
        };
        
        ws.onerror = function(error) {
            updateStatus('接続エラー', 'error');
            log(`✗ WebSocketエラー: ${error}`);
        };
    } catch (error) {
        updateStatus('接続失敗', 'error');
        log(`✗ 接続エラー: ${error}`);
    }
}

function disconnect() {
    if (ws) {
        ws = null;
    }
    updateStatus('未接続', 'info');
    log('切断しました');
}

function newGame() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        // 既存ブリッジに対応したメッセージ形式
        ws.send(JSON.stringify({type: 'gameNew'}));
        log('新規ゲーム開始');
        resetBoard();
    } else {
        log('エラー: 接続されていません');
        updateStatus('未接続', 'error');
    }
}

function resetBoard() {
    console.log('resetBoard called');
    gameState = JSON.parse(JSON.stringify(initialBoard));
    selectedSquare = null;
    pendingMove = null;
    console.log('gameState after reset:', gameState);
    initBoard();
}

function initBoard() {
    console.log('initBoard called');
    const board = document.getElementById('shogi-board');
    console.log('Board element found:', board);
    if (!board) {
        console.error('shogi-board element not found!');
        return;
    }
    
    board.innerHTML = '';
    console.log('Board cleared, gameState:', gameState);
    
    // 縦線
    for (let i = 0; i <= 9; i++) {
        const line = document.createElement('div');
        line.className = 'board-line';
        line.style.left = `${i * 45}px`;
        line.style.top = '0';
        line.style.width = '1px';
        line.style.height = '450px';
        board.appendChild(line);
    }
    
    // 横線
    for (let i = 0; i <= 9; i++) {
        const line = document.createElement('div');
        line.className = 'board-line';
        line.style.left = '0';
        line.style.top = `${i * 45}px`;
        line.style.width = '450px';
        line.style.height = '1px';
        board.appendChild(line);
    }
    
    // 駒配置
    let pieceCount = 0;
    for (let row = 0; row < 9; row++) {
        for (let col = 0; col < 9; col++) {
            const piece = gameState[row][col];
            if (piece) {
                console.log(`Placing piece at ${row},${col}: ${piece}`);
                createPiece(row, col, piece);
                pieceCount++;
            }
        }
    }
    console.log(`Total pieces placed: ${pieceCount}`);
    
    // クリックイベント
    board.addEventListener('click', onBoardClick);
}

function createPiece(row, col, piece) {
    const board = document.getElementById('shogi-board');
    const square = document.createElement('div');
    square.className = 'square';
    square.dataset.row = row;
    square.dataset.col = col;
    
    const x = col * 45 + 2;
    const y = row * 45 + 2;
    square.style.left = `${x}px`;
    square.style.top = `${y}px`;
    
    const pieceName = pieceNames[piece] || piece;
    square.textContent = pieceName;
    
    // 先手の駒は通常、後手の駒は反転
    if (piece === piece.toLowerCase()) {
        square.style.transform = 'rotate(180deg)';
    }
    
    board.appendChild(square);
}

function onBoardClick(event) {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    const col = Math.floor(x / 45);
    const row = Math.floor(y / 45);
    
    if (row < 0 || row >= 9 || col < 0 || col >= 9) return;
    
    if (selectedSquare === null) {
        // 駒を選択
        if (gameState[row][col]) {
            selectedSquare = { row, col };
            highlightSquare(row, col, true);
            log(`駒選択: ${row + 1}${col + 1}`);
        }
    } else {
        // 移動先を選択
        if (selectedSquare.row === row && selectedSquare.col === col) {
            // 同じマスをクリック = 選択解除
            highlightSquare(selectedSquare.row, selectedSquare.col, false);
            selectedSquare = null;
            log('選択解除');
        } else {
            // 移動
            makeMove(selectedSquare.row, selectedSquare.col, row, col);
        }
    }
}

function highlightSquare(row, col, highlight) {
    const squares = document.querySelectorAll('.square');
    squares.forEach(square => {
        if (parseInt(square.dataset.row) === row && parseInt(square.dataset.col) === col) {
            if (highlight) {
                square.classList.add('selected');
            } else {
                square.classList.remove('selected');
            }
        }
    });
}

function makeMove(fromRow, fromCol, toRow, toCol) {
    // USI フォーマットに変換（例: 7g7f）
    const fromUsi = String.fromCharCode('9'.charCodeAt(0) - fromCol) + String(fromRow + 1);
    const toUsi = String.fromCharCode('9'.charCodeAt(0) - toCol) + String(toRow + 1);
    const move = fromUsi + toUsi;
    
    if (ws && ws.readyState === WebSocket.OPEN) {
        // 人間の手を送信
        ws.send(JSON.stringify({
            type: 'humanMove',
            move: move
        }));
        log(`人間の手: ${move}`);
        
        // エンジンに思考開始を指示
        setTimeout(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'send',
                    line: 'go movetime 2000'
                }));
                log('エンジン思考開始');
                updateStatus('エンジン思考中...', 'info');
            }
        }, 100);
        
        // 盤面を更新
        gameState[toRow][toCol] = gameState[fromRow][fromCol];
        gameState[fromRow][fromCol] = null;
        
        // 選択解除
        highlightSquare(selectedSquare.row, selectedSquare.col, false);
        selectedSquare = null;
        
        // 盤面を再描画
        initBoard();
    } else {
        log('エラー: 接続されていません');
    }
}

function applyMove(moveStr) {
    // エンジンの手を盤面に反映
    const fromCol = 9 - parseInt(moveStr[0]);
    const fromRow = moveStr.charCodeAt(1) - 97;
    const toCol = 9 - parseInt(moveStr[2]);
    const toRow = moveStr.charCodeAt(3) - 97;
    
    gameState[toRow][toCol] = gameState[fromRow][fromCol];
    gameState[fromRow][fromCol] = null;
    
    initBoard();
}

function generateKIF() {
    log('KIF生成機能は未実装');
}

function clearLog() {
    const logElement = document.getElementById('log');
    if (logElement) {
        logElement.textContent = 'ログクリア...\n';
    }
}

function updateStatus(message, type) {
    const statusElement = document.getElementById('status');
    if (statusElement) {
        statusElement.textContent = message;
        statusElement.className = `status ${type}`;
    }
}

function log(message) {
    const logElement = document.getElementById('log');
    if (logElement) {
        const timestamp = new Date().toLocaleTimeString();
        logElement.textContent += `[${timestamp}] ${message}\n`;
        logElement.scrollTop = logElement.scrollHeight;
    }
    console.log(message);
}

// 初期化
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded fired');
    console.log('shogi-board element:', document.getElementById('shogi-board'));
    console.log('log element:', document.getElementById('log'));
    console.log('status element:', document.getElementById('status'));
    console.log('initialBoard:', initialBoard);
    
    // gameStateを確実に初期化
    gameState = JSON.parse(JSON.stringify(initialBoard));
    console.log('gameState initialized:', gameState);
    
    resetBoard();
    log('将棋UI初期化完了');
});
