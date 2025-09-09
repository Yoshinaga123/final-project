// /**
//  * 棋譜入力のJavaScript機能
//  * 棋譜の手動入力、編集、保存などの機能を提供
//  */

// class KifuInput {
//     constructor() {
//         this.kifu = [];
//         this.currentMove = null;
//         this.setupEventListeners();
//         this.initializeSquareOptions();
//     }
    
//     setupEventListeners() {
//         // フォーム送信
//         document.getElementById('kifuForm').addEventListener('submit', (e) => {
//             e.preventDefault();
//             this.addMove();
//         });
        
//         // ボタンイベント
//         document.getElementById('addMoveBtn').addEventListener('click', () => this.addMove());
//         document.getElementById('editMoveBtn').addEventListener('click', () => this.editMove());
//         document.getElementById('deleteMoveBtn').addEventListener('click', () => this.deleteMove());
//         document.getElementById('clearForm').addEventListener('click', () => this.clearForm());
        
//         // 操作ボタン
//         document.getElementById('saveKifuBtn').addEventListener('click', () => this.showSaveModal());
//         document.getElementById('loadKifuBtn').addEventListener('click', () => this.loadKifu());
//         document.getElementById('exportKifuBtn').addEventListener('click', () => this.exportKifu());
//         document.getElementById('clearKifuBtn').addEventListener('click', () => this.clearKifu());
        
//         // 保存モーダル
//         document.getElementById('confirmSaveKifu').addEventListener('click', () => this.saveKifu());
        
//         // 棋譜リストのクリック
//         document.getElementById('kifuList').addEventListener('click', (e) => {
//             if (e.target.classList.contains('kifu-item')) {
//                 this.selectMove(e.target);
//             }
//         });
//     }
    
//     initializeSquareOptions() {
//         const fromSquare = document.getElementById('fromSquare');
//         const toSquare = document.getElementById('toSquare');
        
//         // 9x9のマス目オプションを生成
//         const squares = [];
//         for (let row = 1; row <= 9; row++) {
//             for (let col = 1; col <= 9; col++) {
//                 const value = `${row}${col}`;
//                 const label = `${row}${String.fromCharCode(0x4e00 + col - 1)}`;
//                 squares.push({value, label});
//             }
//         }
        
//         squares.forEach(square => {
//             const option1 = document.createElement('option');
//             option1.value = square.value;
//             option1.textContent = square.label;
//             fromSquare.appendChild(option1);
            
//             const option2 = document.createElement('option');
//             option2.value = square.value;
//             option2.textContent = square.label;
//             toSquare.appendChild(option2);
//         });
//     }
    
//     addMove() {
//         const moveData = this.getFormData();
        
//         if (!this.validateMove(moveData)) {
//             return;
//         }
        
//         const move = {
//             moveNumber: moveData.moveNumber,
//             from: moveData.fromSquare,
//             to: moveData.toSquare,
//             piece: moveData.piece,
//             promotion: moveData.promotion,
//             drop: moveData.drop,
//             timestamp: new Date().toISOString()
//         };
        
//         this.kifu.push(move);
//         this.updateKifuList();
//         this.clearForm();
//         this.updateMoveNumber();
//     }
    
//     getFormData() {
//         return {
//             moveNumber: parseInt(document.getElementById('moveNumber').value),
//             fromSquare: document.getElementById('fromSquare').value,
//             toSquare: document.getElementById('toSquare').value,
//             piece: document.getElementById('piece').value,
//             promotion: document.getElementById('promotion').checked,
//             drop: document.getElementById('drop').checked
//         };
//     }
    
//     validateMove(moveData) {
//         if (!moveData.fromSquare && !moveData.drop) {
//             alert('移動元を選択してください（打ちの場合はチェックを入れてください）');
//             return false;
//         }
        
//         if (!moveData.toSquare) {
//             alert('移動先を選択してください');
//             return false;
//         }
        
//         if (!moveData.piece) {
//             alert('駒を選択してください');
//             return false;
//         }
        
//         if (moveData.fromSquare === moveData.toSquare) {
//             alert('移動元と移動先が同じです');
//             return false;
//         }
        
//         return true;
//     }
    
//     editMove() {
//         if (!this.currentMove) {
//             alert('編集する手を選択してください');
//             return;
//         }
        
//         const moveData = this.getFormData();
//         if (!this.validateMove(moveData)) {
//             return;
//         }
        
//         const moveIndex = this.kifu.findIndex(move => move === this.currentMove);
//         if (moveIndex !== -1) {
//             this.kifu[moveIndex] = {
//                 moveNumber: moveData.moveNumber,
//                 from: moveData.fromSquare,
//                 to: moveData.toSquare,
//                 piece: moveData.piece,
//                 promotion: moveData.promotion,
//                 drop: moveData.drop,
//                 timestamp: new Date().toISOString()
//             };
            
//             this.updateKifuList();
//             this.clearForm();
//         }
//     }
    
//     deleteMove() {
//         if (!this.currentMove) {
//             alert('削除する手を選択してください');
//             return;
//         }
        
//         if (confirm('この手を削除しますか？')) {
//             const moveIndex = this.kifu.findIndex(move => move === this.currentMove);
//             if (moveIndex !== -1) {
//                 this.kifu.splice(moveIndex, 1);
//                 this.updateKifuList();
//                 this.clearForm();
//                 this.updateMoveNumber();
//             }
//         }
//     }
    
//     selectMove(moveElement) {
//         // 既存の選択を解除
//         document.querySelectorAll('.kifu-item').forEach(item => {
//             item.classList.remove('selected');
//         });
        
//         // 新しい選択
//         moveElement.classList.add('selected');
//         this.currentMove = moveElement.moveData;
        
//         // フォームに値を設定
//         this.populateForm(this.currentMove);
//     }
    
//     populateForm(move) {
//         document.getElementById('moveNumber').value = move.moveNumber;
//         document.getElementById('fromSquare').value = move.from;
//         document.getElementById('toSquare').value = move.to;
//         document.getElementById('piece').value = move.piece;
//         document.getElementById('promotion').checked = move.promotion;
//         document.getElementById('drop').checked = move.drop;
//     }
    
//     clearForm() {
//         document.getElementById('kifuForm').reset();
//         document.getElementById('moveNumber').value = this.kifu.length + 1;
//         this.currentMove = null;
//     }
    
//     updateMoveNumber() {
//         document.getElementById('moveNumber').value = this.kifu.length + 1;
//     }
    
//     updateKifuList() {
//         const kifuList = document.getElementById('kifuList');
//         kifuList.innerHTML = '';
        
//         if (this.kifu.length === 0) {
//             kifuList.innerHTML = '<p class="text-muted">棋譜がありません</p>';
//             return;
//         }
        
//         this.kifu.forEach((move, index) => {
//             const moveElement = document.createElement('div');
//             moveElement.className = 'kifu-item';
//             moveElement.moveData = move;
            
//             let moveText = `${move.moveNumber}. ${move.piece}`;
//             if (move.drop) {
//                 moveText += `打`;
//             } else {
//                 moveText += `${move.from}→${move.to}`;
//             }
//             if (move.promotion) {
//                 moveText += `成`;
//             }
            
//             moveElement.innerHTML = `
//                 <div class="move-number">${move.moveNumber}手目</div>
//                 <div class="move-text">${moveText}</div>
//             `;
            
//             kifuList.appendChild(moveElement);
//         });
//     }
    
//     showSaveModal() {
//         const modal = new bootstrap.Modal(document.getElementById('saveKifuModal'));
//         modal.show();
//     }
    
//     saveKifu() {
//         const title = document.getElementById('kifuTitle').value || '無題の棋譜';
//         const description = document.getElementById('kifuDescription').value;
        
//         fetch('/shogi/api/save', {
//             method: 'POST',
//             headers: {
//                 'Content-Type': 'application/json',
//             },
//             body: JSON.stringify({
//                 title: title,
//                 description: description,
//                 kifu: this.kifu,
//                 timestamp: new Date().toISOString()
//             })
//         })
//         .then(response => response.json())
//         .then(data => {
//             if (data.success) {
//                 alert(data.message);
//                 const modal = bootstrap.Modal.getInstance(document.getElementById('saveKifuModal'));
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
//                 this.updateKifuList();
//                 this.updateMoveNumber();
//             }
//         });
//     }
    
//     exportKifu() {
//         if (this.kifu.length === 0) {
//             alert('エクスポートする棋譜がありません');
//             return;
//         }
        
//         const kifuText = this.kifu.map(move => {
//             let moveText = `${move.moveNumber}. ${move.piece}`;
//             if (move.drop) {
//                 moveText += `打`;
//             } else {
//                 moveText += `${move.from}→${move.to}`;
//             }
//             if (move.promotion) {
//                 moveText += `成`;
//             }
//             return moveText;
//         }).join('\n');
        
//         const blob = new Blob([kifuText], { type: 'text/plain' });
//         const url = URL.createObjectURL(blob);
//         const a = document.createElement('a');
//         a.href = url;
//         a.download = `kifu_${new Date().toISOString().split('T')[0]}.txt`;
//         a.click();
//         URL.revokeObjectURL(url);
//     }
    
//     clearKifu() {
//         if (confirm('すべての棋譜を削除しますか？')) {
//             this.kifu = [];
//             this.updateKifuList();
//             this.clearForm();
//         }
//     }
// }

// // ページ読み込み時に棋譜入力を初期化
// document.addEventListener('DOMContentLoaded', () => {
//     new KifuInput();
// });
