// 即座にログ出力（スクリプト読み込み確認用）
// 最終確認
console.log("=== KIFU-VIEW.JS LOADED ===");
console.log("downloadKifu is available:", typeof window.downloadKifu === 'function');

// グローバル変数をwindowオブジェクトに明示的に割り当て
window.kifuData = null;
window.currentMove = 0;
window.totalMoves = 0;
window.isPlaying = false;
window.playInterval = null;

// 棋譜ダウンロード機能
window.downloadKifu = function(filename = null) {
    console.log("=== DOWNLOAD DEBUG - START ===");
    console.log("Function called with filename:", filename);
    
    try {
        // 1. 棋譜テキスト要素を取得
        const kifuTextElement = document.getElementById('kifu-text');
        console.log("kifu-text element found:", kifuTextElement ? "Yes" : "No");
        
        if (kifuTextElement) {
            // 2. コンテンツを取得
            const content = kifuTextElement.textContent;
            console.log("Content length:", content.length);
            console.log("Content first 100 chars:", content.substring(0, 100));
            
            if (content && content.trim().length > 0) {
                try {
                    // 3. Blobを作成
                    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
                    console.log("Blob created:", blob.size, "bytes");
                    
                    // 4. URLを作成
                    const url = window.URL.createObjectURL(blob);
                    console.log("URL created:", url);
                    
                    // 5. リンク要素を作成
                    const a = document.createElement('a');
                    a.href = url;
                    // ファイル名をdata-filename属性から取得、または引数から取得
                    const downloadFilename = filename || kifuTextElement.dataset.filename;
                    a.download = downloadFilename;
                    console.log("Download filename:", downloadFilename);
                    
                    // 6. DOMに追加
                    document.body.appendChild(a);
                    console.log("Link added to DOM");
                    
                    // 7. クリックをシミュレート
                    a.click();
                    console.log("Click simulated");
                    
                    // 8. DOMから削除
                    document.body.removeChild(a);
                    console.log("Link removed from DOM");
                    
                    // 9. URLを解放
                    window.URL.revokeObjectURL(url);
                    console.log("URL revoked");
                    
                    console.log("=== DOWNLOAD DEBUG - SUCCESS ===");
                    return true;
                } catch (error) {
                    console.error("Download operation failed:", error);
                    alert('ダウンロード処理中にエラーが発生しました: ' + error.message);
                    console.log("=== DOWNLOAD DEBUG - FAILED ===");
                    return false;
                }
            } else {
                console.error("No content to download (empty)");
                alert('ダウンロードする棋譜データがありません。');
                console.log("=== DOWNLOAD DEBUG - NO CONTENT ===");
                return false;
            }
        } else {
            console.error("kifu-text element not found in DOM");
            // #kifu-textがない場合、APIからデータを取得してみる
            console.log("Trying to fetch from API...");
            if (filename) {
                fetchAndDownloadKifu(filename);
                return true;
            } else {
                alert('棋譜テキスト要素が見つからず、ファイル名も指定されていません。');
                console.log("=== DOWNLOAD DEBUG - NO ELEMENT ===");
                return false;
            }
        }
    } catch (error) {
        console.error("Unexpected error in downloadKifu:", error);
        alert('予期せぬエラーが発生しました: ' + error.message);
        console.log("=== DOWNLOAD DEBUG - ERROR ===");
        return false;
    }
}

// APIから棋譜を取得してダウンロード
window.fetchAndDownloadKifu = function(filename) {
    console.log("Fetching kifu from API:", filename);
    
    fetch(`/shogi/api/kifu/${filename}`)
        .then(response => {
            console.log("API response status:", response.status);
            return response.json();
        })
        .then(data => {
            console.log("API data received:", !!data);
            
            if (data.success && data.content) {
                const blob = new Blob([data.content], { type: 'text/plain;charset=utf-8' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                console.log("Download from API completed");
            } else {
                console.error("API error:", data.error || "Unknown error");
                alert('ファイルのダウンロードに失敗しました: ' + (data.error || "Unknown error"));
            }
        })
        .catch(error => {
            console.error('API fetch error:', error);
            alert('ファイルのダウンロードに失敗しました: ' + error.message);
        });
}

// 棋譜操作機能
function updateMoveInfo() {
    const boardElement = document.getElementById('board-1');
    if (boardElement && boardElement.kifu) {
        try {
            const kifu = boardElement.kifu;
            totalMoves = kifu.getMoves ? kifu.getMoves().length : 0;
            currentMove = kifu.getCurrentMove ? kifu.getCurrentMove() : 0;
            console.log(`Move info: ${currentMove} / ${totalMoves}`);
        } catch (error) {
            console.error('Error updating move info:', error);
        }
    } else {
        console.log('KifuForJS not ready yet');
    }
}

function goToStart() {
    try {
        const board = document.getElementById('board-1');
        if (board && board.kifu && typeof board.kifu.goTo === 'function') {
            board.kifu.goTo(0);
            updateMoveInfo();
        }
    } catch (error) {
        console.error('Error in goToStart:', error);
    }
}

function goToPrevious() {
    try {
        const board = document.getElementById('board-1');
        if (board && board.kifu && typeof board.kifu.goTo === 'function') {
            board.kifu.goTo(Math.max(0, currentMove - 1));
            updateMoveInfo();
        }
    } catch (error) {
        console.error('Error in goToPrevious:', error);
    }
}

function goToNext() {
    try {
        const board = document.getElementById('board-1');
        if (board && board.kifu && typeof board.kifu.goTo === 'function') {
            board.kifu.goTo(Math.min(totalMoves, currentMove + 1));
            updateMoveInfo();
        }
    } catch (error) {
        console.error('Error in goToNext:', error);
    }
}

function goToEnd() {
    try {
        const board = document.getElementById('board-1');
        if (board && board.kifu && typeof board.kifu.goTo === 'function') {
            board.kifu.goTo(totalMoves);
            updateMoveInfo();
        }
    } catch (error) {
        console.error('Error in goToEnd:', error);
    }
}

function togglePlayPause() {
    if (isPlaying) {
        pausePlayback();
    } else {
        startPlayback();
    }
}

function startPlayback() {
    if (currentMove >= totalMoves) {
        goToStart();
    }
    
    isPlaying = true;
    console.log('Playback started');
    
    playInterval = setInterval(() => {
        if (currentMove < totalMoves) {
            goToNext();
        } else {
            pausePlayback();
        }
    }, 1000);
}

function pausePlayback() {
    isPlaying = false;
    console.log('Playback paused');
    
    if (playInterval) {
        clearInterval(playInterval);
        playInterval = null;
    }
}

// グローバルオブジェクトの確認
console.log("Global downloadKifu:", typeof window.downloadKifu);

// ページ読み込み時の初期化
document.addEventListener('DOMContentLoaded', function() {
    console.log("=== KIFU DEBUG - DOMContentLoaded ===");
    console.log("Page URL:", window.location.href);
    
    // ダウンロードボタンの設定
    const downloadButtons = document.querySelectorAll('.download-kifu-btn');
    console.log("Download buttons found:", downloadButtons.length);
    
    downloadButtons.forEach((btn, index) => {
        console.log(`Button ${index + 1} filename:`, btn.dataset.filename);
        
        btn.addEventListener('click', function(event) {
            event.preventDefault();
            console.log("Download button clicked:", btn.dataset.filename);
            downloadKifu(btn.dataset.filename);  // data-filename属性から取得
        });
        
        console.log(`Event listener added to button ${index + 1}`);
    });
    
    // 棋譜の読み込み
    try {
        console.log("Loading kifu...");
        const boardElement = document.getElementById('board-1');
        if (boardElement) {
            const filename = boardElement.dataset.filename;  // data-filename属性から取得
            const isTsume = filename.includes("詰") || filename.toLowerCase().includes("tsume");
            
            const loadOptions = {
                src: `/shogi/api/kifu/${filename}`
            };
            
            if (isTsume) {
                loadOptions.mode = "tsume";
                console.log("Enabling tsume mode");
            }
            
            KifuForJS.load(loadOptions, "board-1");
            console.log("Kifu loaded successfully");
            
            setTimeout(updateMoveInfo, 2000);
        }
    } catch (error) {
        console.error("Failed to load kifu:", error);
        alert('棋譜の読み込みに失敗しました。');
    }
});
