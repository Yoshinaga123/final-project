// /**
//  * 将棋盤のJavaScript機能
//  * 将棋盤の表示、駒の移動、棋譜管理などの機能を提供
//  */

// class ShogiBoard {
//     constructor() {
//         this.board = [];
//         this.currentPlayer = 'sente'; // 'sente' or 'gote'
//         this.selectedSquare = null;
//         this.kifu = [];
//         this.mochigoma = {
//             sente: {},
//             gote: {}
//         };
        
//         this.initializeBoard();
//         this.setupEventListeners();
//         this.updateDisplay();
//     }
    
//     initializeBoard() {
//         // 9x9の将棋盤を初期化
//         const boardElement = document.getElementById('shogi-board');
//         boardElement.innerHTML = '';
        
//         // 初期配置
//         const initialPieces = [
//             ['香', '桂', '銀', '金', '王', '金', '銀', '桂', '香'],
//             ['', '飛', '', '', '', '', '', '角', ''],
//             ['歩', '歩', '歩', '歩', '歩', '歩', '歩', '歩', '歩'],
//             ['', '', '', '', '', '', '', '', ''],
//             ['', '', '', '', '', '', '', '', ''],
//             ['', '', '', '', '', '', '', '', ''],
//             ['歩', '歩', '歩', '歩', '歩', '歩', '歩', '歩', '歩'],
//             ['', '角', '', '', '', '', '', '飛', ''],
//             ['香', '桂', '銀', '金', '王', '金', '銀', '桂', '香']
//         ];
        
//         for (let row = 0; row < 9; row++) {
//             this.board[row] = [];
//             for (let col = 0; col < 9; col++) {
//                 this.board[row][col] = {
//                     piece: initialPieces[row][col],
//                     player: row < 3 ? 'gote' : row > 5 ? 'sente' : null
//                 };
                
//                 const square = document.createElement('div');
//                 square.className = 'shogi-square';
//                 square.dataset.row = row;
//                 square.dataset.col = col;
                
//                 if (this.board[row][col].piece) {
//                     const pieceElement = document.createElement('div');
//                     pieceElement.className = `shogi-piece ${this.board[row][col].player}-piece`;
//                     pieceElement.textContent = this.board[row][col].piece;
//                     square.appendChild(pieceElement);
//                 }
                
//                 boardElement.appendChild(square);
//             }
//         }
//     }
    
//     setupEventListeners() {
//         // 盤面のクリックイベント
//         document.getElementById('shogi-board').addEventListener('click', (e) => {
//             if (e.target.classList.contains('shogi-square')) {
//                 this.handleSquareClick(e.target);
//             }
//         });
        
//         // ボタンのイベント
//         document.getElementById('resetBtn').addEventListener('click', () => this.resetBoard());
//         document.getElementById('saveBtn').addEventListener('click', () => this.showSaveModal());
//         document.getElementById('loadBtn').addEventListener('click', () => this.loadKifu());
        
//         // 保存モーダル
//         document.getElementById('confirmSave').addEventListener('click', () => this.saveKifu());
//     }
    
//     handleSquareClick(squareElement) {
//         const row = parseInt(squareElement.dataset.row);
//         const col = parseInt(squareElement.dataset.col);
        
//         if (this.selectedSquare) {
//             // 移動先を選択
//             if (this.isValidMove(this.selectedSquare, {row, col})) {
//                 this.makeMove(this.selectedSquare, {row, col});
//                 this.clearSelection();
//             } else {
//                 this.clearSelection();
//                 this.selectSquare(squareElement, row, col);
//             }
//         } else {
//             // 駒を選択
//             this.selectSquare(squareElement, row, col);
//         }
//     }
    
//     selectSquare(squareElement, row, col) {
//         const piece = this.board[row][col];
//         if (piece.piece && piece.player === this.currentPlayer) {
//             this.clearSelection();
//             squareElement.classList.add('selected');
//             this.selectedSquare = {row, col, element: squareElement};
//             this.highlightPossibleMoves(row, col);
//         }
//     }
    
//     clearSelection() {
//         document.querySelectorAll('.shogi-square').forEach(square => {
//             square.classList.remove('selected', 'possible-move');
//         });
//         this.selectedSquare = null;
//     }
    
//     highlightPossibleMoves(row, col) {
//         // 簡単な移動可能マスのハイライト（実装は簡略化）
//         for (let r = 0; r < 9; r++) {
//             for (let c = 0; c < 9; c++) {
//                 if (this.isValidMove({row, col}, {row: r, col: c})) {
//                     const square = document.querySelector(`[data-row="${r}"][data-col="${c}"]`);
//                     square.classList.add('possible-move');
//                 }
//             }
//         }
//     }
    
//     isValidMove(from, to) {
//         // 簡単な移動判定（実装は簡略化）
//         const piece = this.board[from.row][from.col];
//         if (!piece.piece) return false;
        
//         // 同じマスへの移動は不可
//         if (from.row === to.row && from.col === to.col) return false;
        
//         // 自分の駒があるマスへの移動は不可
//         const targetPiece = this.board[to.row][to.col];
//         if (targetPiece.piece && targetPiece.player === piece.player) return false;
        
//         // 基本的な移動ルール（簡略化）
//         return true;
//     }
    
//     makeMove(from, to) {
//         const piece = this.board[from.row][from.col];
//         const capturedPiece = this.board[to.row][to.col];
        
//         // 駒を移動
//         this.board[to.row][to.col] = {piece: piece.piece, player: piece.player};
//         this.board[from.row][from.col] = {piece: '', player: null};
        
//         // 取った駒があれば持ち駒に追加
//         if (capturedPiece.piece) {
//             this.addMochigoma(capturedPiece.piece, this.currentPlayer);
//         }
        
//         // 棋譜に記録
//         this.recordMove(from, to, piece.piece);
        
//         // 手番を変更
//         this.currentPlayer = this.currentPlayer === 'sente' ? 'gote' : 'sente';
        
//         this.updateDisplay();
//     }
    
//     addMochigoma(piece, player) {
//         if (this.mochigoma[player][piece]) {
//             this.mochigoma[player][piece]++;
//         } else {
//             this.mochigoma[player][piece] = 1;
//         }
//     }
    
//     recordMove(from, to, piece) {
//         const move = {
//             moveNumber: this.kifu.length + 1,
//             from: `${from.row + 1}${from.col + 1}`,
//             to: `${to.row + 1}${to.col + 1}`,
//             piece: piece,
//             player: this.currentPlayer
//         };
        
//         this.kifu.push(move);
//         this.updateKifuDisplay();
//     }
    
//     updateDisplay() {
//         // 盤面を更新
//         for (let row = 0; row < 9; row++) {
//             for (let col = 0; col < 9; col++) {
//                 const square = document.querySelector(`[data-row="${row}"][data-col="${col}"]`);
//                 square.innerHTML = '';
                
//                 const piece = this.board[row][col];
//                 if (piece.piece) {
//                     const pieceElement = document.createElement('div');
//                     pieceElement.className = `shogi-piece ${piece.player}-piece`;
//                     pieceElement.textContent = piece.piece;
//                     square.appendChild(pieceElement);
//                 }
//             }
//         }
        
//         // 手番表示を更新
//         const turnIndicator = document.getElementById('turn-indicator');
//         turnIndicator.textContent = this.currentPlayer === 'sente' ? '先手番' : '後手番';
//         turnIndicator.className = `badge ${this.currentPlayer === 'sente' ? 'bg-primary' : 'bg-danger'} fs-5`;
        
//         // 持ち駒を更新
//         this.updateMochigomaDisplay();
//     }
    
//     updateKifuDisplay() {
//         const kifuDisplay = document.getElementById('kifu-display');
//         kifuDisplay.innerHTML = '';
        
//         if (this.kifu.length === 0) {
//             kifuDisplay.innerHTML = '<p class="text-muted">手を打ってください</p>';
//             return;
//         }
        
//         this.kifu.forEach(move => {
//             const moveElement = document.createElement('div');
//             moveElement.className = 'kifu-move';
//             moveElement.innerHTML = `
//                 <span class="move-number">${move.moveNumber}.</span>
//                 <span class="move-text">${move.piece}${move.from}→${move.to}</span>
//             `;
//             kifuDisplay.appendChild(moveElement);
//         });
//     }
    
//     updateMochigomaDisplay() {
//         const senteMochigoma = document.getElementById('sente-mochigoma');
//         const goteMochigoma = document.getElementById('gote-mochigoma');
        
//         senteMochigoma.innerHTML = '';
//         goteMochigoma.innerHTML = '';
        
//         Object.entries(this.mochigoma.sente).forEach(([piece, count]) => {
//             for (let i = 0; i < count; i++) {
//                 const pieceElement = document.createElement('div');
//                 pieceElement.className = 'mochigoma-piece sente-piece';
//                 pieceElement.textContent = piece;
//                 senteMochigoma.appendChild(pieceElement);
//             }
//         });
        
//         Object.entries(this.mochigoma.gote).forEach(([piece, count]) => {
//             for (let i = 0; i < count; i++) {
//                 const pieceElement = document.createElement('div');
//                 pieceElement.className = 'mochigoma-piece gote-piece';
//                 pieceElement.textContent = piece;
//                 goteMochigoma.appendChild(pieceElement);
//             }
//         });
//     }
    
//     resetBoard() {
//         this.kifu = [];
//         this.mochigoma = {sente: {}, gote: {}};
//         this.currentPlayer = 'sente';
//         this.clearSelection();
//         this.initializeBoard();
//         this.updateDisplay();
//     }
    
//     showSaveModal() {
//         const modal = new bootstrap.Modal(document.getElementById('saveModal'));
//         modal.show();
//     }
    
//     saveKifu() {
//         const title = document.getElementById('kifuTitle').value || '無題の棋譜';
        
//         fetch('/shogi/api/save', {
//             method: 'POST',
//             headers: {
//                 'Content-Type': 'application/json',
//             },
//             body: JSON.stringify({
//                 title: title,
//                 timestamp: new Date().toISOString()
//             })
//         })
//         .then(response => response.json())
//         .then(data => {
//             if (data.success) {
//                 alert(data.message);
//                 const modal = bootstrap.Modal.getInstance(document.getElementById('saveModal'));
//                 modal.hide();
//             }
//         });
//     }
    
//     loadKifu() {
//         fetch('/shogi/api/kifu')
//         .then(response => response.json())
//         .then(data => {
//             if (data.success) {
//                 this.kifu = data.kifu;
//                 this.updateKifuDisplay();
//             }
//         });
//     }
// }

// // ページ読み込み時に将棋盤を初期化
// document.addEventListener('DOMContentLoaded', () => {
//     new ShogiBoard();
// });
