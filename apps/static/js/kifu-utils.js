/**
 * 棋譜読み込みユーティリティ
 * 様々な方法で棋譜を読み込むためのヘルパー関数を提供
 */

class KifuUtils {
    /**
     * 棋譜文字列から棋譜を読み込む
     * @param {string} kifuString - 棋譜文字列
     * @param {string} targetElementId - 対象要素のID
     * @param {Object} options - KifuForJSのオプション
     */
    static loadFromString(kifuString, targetElementId, options = {}) {
        const targetElement = document.getElementById(targetElementId);
        if (!targetElement) {
            console.error(`要素 ${targetElementId} が見つかりません`);
            return null;
        }

        try {
            const kifu = new KifuForJS(targetElement, options);
            kifu.load(kifuString);
            return kifu;
        } catch (error) {
            console.error('棋譜の読み込みに失敗しました:', error);
            return null;
        }
    }

    /**
     * ファイルから棋譜を読み込む
     * @param {string} filePath - ファイルパス
     * @param {string} targetElementId - 対象要素のID
     * @param {Object} options - KifuForJSのオプション
     */
    static async loadFromFile(filePath, targetElementId, options = {}) {
        try {
            const response = await fetch(filePath);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const kifuString = await response.text();
            return this.loadFromString(kifuString, targetElementId, options);
        } catch (error) {
            console.error('棋譜ファイルの読み込みに失敗しました:', error);
            return null;
        }
    }

    /**
     * URLから棋譜を読み込む
     * @param {string} url - URL
     * @param {string} targetElementId - 対象要素のID
     * @param {Object} options - KifuForJSのオプション
     */
    static async loadFromUrl(url, targetElementId, options = {}) {
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const kifuString = await response.text();
            return this.loadFromString(kifuString, targetElementId, options);
        } catch (error) {
            console.error('棋譜URLの読み込みに失敗しました:', error);
            return null;
        }
    }

    /**
     * インデントを自動処理する
     * @param {string} kifuString - 棋譜文字列
     * @returns {string} 処理済み棋譜文字列
     */
    static processIndentation(kifuString) {
        const lines = kifuString.split('\n');
        
        // 最初の非空行のインデントを取得
        let commonIndent = 0;
        for (const line of lines) {
            if (line.trim()) {
                commonIndent = line.length - line.trimStart().length;
                break;
            }
        }
        
        // 共通のインデントを除去
        return lines.map(line => {
            if (line.length >= commonIndent) {
                return line.substring(commonIndent);
            }
            return line;
        }).join('\n');
    }

    /**
     * 棋譜文字列を検証する
     * @param {string} kifuString - 棋譜文字列
     * @returns {Object} 検証結果
     */
    static validateKifu(kifuString) {
        const result = {
            isValid: true,
            errors: [],
            warnings: []
        };

        if (!kifuString || !kifuString.trim()) {
            result.isValid = false;
            result.errors.push('棋譜文字列が空です');
            return result;
        }

        const lines = kifuString.split('\n');
        
        // 基本的な棋譜形式のチェック
        let hasBoard = false;
        let hasMoves = false;
        
        for (const line of lines) {
            const trimmed = line.trim();
            
            // 盤面の存在チェック
            if (trimmed.includes('+---------------------------+')) {
                hasBoard = true;
            }
            
            // 手数の存在チェック
            if (/^\s*\d+\s+/.test(trimmed)) {
                hasMoves = true;
            }
        }

        if (!hasBoard) {
            result.warnings.push('盤面情報が見つかりません');
        }

        if (!hasMoves) {
            result.warnings.push('手数情報が見つかりません');
        }

        return result;
    }

    /**
     * 棋譜文字列を正規化する
     * @param {string} kifuString - 棋譜文字列
     * @returns {string} 正規化された棋譜文字列
     */
    static normalizeKifu(kifuString) {
        // インデント処理
        let normalized = this.processIndentation(kifuString);
        
        // 行末の空白を除去
        normalized = normalized.split('\n')
            .map(line => line.trimEnd())
            .join('\n');
        
        // 連続する空行を1つにまとめる
        normalized = normalized.replace(/\n\s*\n\s*\n/g, '\n\n');
        
        return normalized;
    }

    /**
     * 棋譜の基本情報を抽出する
     * @param {string} kifuString - 棋譜文字列
     * @returns {Object} 基本情報
     */
    static extractKifuInfo(kifuString) {
        const info = {
            sente: '',
            gote: '',
            result: '',
            moves: 0,
            hasBoard: false,
            hasMochigoma: false
        };

        const lines = kifuString.split('\n');
        
        for (const line of lines) {
            const trimmed = line.trim();
            
            // 先手名
            if (trimmed.startsWith('先手：')) {
                info.sente = trimmed.substring(3).trim();
            }
            
            // 後手名
            if (trimmed.startsWith('後手：')) {
                info.gote = trimmed.substring(3).trim();
            }
            
            // 結果
            if (trimmed.includes('まで') && trimmed.includes('手で')) {
                info.result = trimmed;
            }
            
            // 盤面の存在
            if (trimmed.includes('+---------------------------+')) {
                info.hasBoard = true;
            }
            
            // 持ち駒の存在
            if (trimmed.includes('持駒：')) {
                info.hasMochigoma = true;
            }
            
            // 手数カウント
            if (/^\s*\d+\s+/.test(trimmed)) {
                const match = trimmed.match(/^\s*(\d+)/);
                if (match) {
                    info.moves = Math.max(info.moves, parseInt(match[1]));
                }
            }
        }

        return info;
    }
}

/**
 * 棋譜マネージャークラス
 * 複数の棋譜ボードを管理する
 */
class KifuManager {
    constructor() {
        this.boards = new Map();
        this.currentBoard = null;
        this.defaultOptions = {
            theme: 'default',
            responsive: true
        };
    }

    /**
     * 新しい棋譜ボードを作成
     * @param {string} elementId - 要素ID
     * @param {string} kifuString - 棋譜文字列（オプション）
     * @param {Object} options - KifuForJSのオプション
     * @returns {Object|null} 作成されたボード
     */
    createBoard(elementId, kifuString = null, options = {}) {
        const element = document.getElementById(elementId);
        if (!element) {
            console.error(`要素 ${elementId} が見つかりません`);
            return null;
        }

        const mergedOptions = { ...this.defaultOptions, ...options };
        const board = new KifuForJS(element, mergedOptions);
        this.boards.set(elementId, board);

        if (kifuString) {
            board.load(kifuString);
        }

        return board;
    }

    /**
     * 既存のボードに棋譜を読み込み
     * @param {string} elementId - 要素ID
     * @param {string} kifuString - 棋譜文字列
     */
    loadKifu(elementId, kifuString) {
        const board = this.boards.get(elementId);
        if (board) {
            board.load(kifuString);
        } else {
            console.error(`ボード ${elementId} が見つかりません`);
        }
    }

    /**
     * ファイルから棋譜を読み込み
     * @param {string} elementId - 要素ID
     * @param {string} filePath - ファイルパス
     */
    async loadFromFile(elementId, filePath) {
        const kifu = await KifuUtils.loadFromFile(filePath, elementId);
        if (kifu) {
            this.boards.set(elementId, kifu);
        }
        return kifu;
    }

    /**
     * URLから棋譜を読み込み
     * @param {string} elementId - 要素ID
     * @param {string} url - URL
     */
    async loadFromUrl(elementId, url) {
        const kifu = await KifuUtils.loadFromUrl(url, elementId);
        if (kifu) {
            this.boards.set(elementId, kifu);
        }
        return kifu;
    }

    /**
     * ボードを削除
     * @param {string} elementId - 要素ID
     */
    removeBoard(elementId) {
        this.boards.delete(elementId);
    }

    /**
     * 現在のボードを設定
     * @param {string} elementId - 要素ID
     */
    setCurrentBoard(elementId) {
        this.currentBoard = elementId;
    }

    /**
     * 現在のボードに棋譜を読み込み
     * @param {string} kifuString - 棋譜文字列
     */
    loadToCurrentBoard(kifuString) {
        if (this.currentBoard) {
            this.loadKifu(this.currentBoard, kifuString);
        }
    }

    /**
     * すべてのボードを取得
     * @returns {Map} ボードのマップ
     */
    getAllBoards() {
        return this.boards;
    }

    /**
     * ボードの存在確認
     * @param {string} elementId - 要素ID
     * @returns {boolean} 存在するかどうか
     */
    hasBoard(elementId) {
        return this.boards.has(elementId);
    }
}

/**
 * 棋譜フォーマッタークラス
 * 棋譜の表示形式を変更する
 */
class KifuFormatter {
    /**
     * 棋譜を簡潔な形式に変換
     * @param {string} kifuString - 棋譜文字列
     * @returns {string} 簡潔な形式の棋譜
     */
    static toCompact(kifuString) {
        const lines = kifuString.split('\n');
        const moves = [];
        
        for (const line of lines) {
            const trimmed = line.trim();
            if (/^\s*\d+\s+/.test(trimmed)) {
                const match = trimmed.match(/^\s*\d+\s+(.+?)(?:\s+\(.*\))?$/);
                if (match) {
                    moves.push(match[1].trim());
                }
            }
        }
        
        return moves.join(' ');
    }

    /**
     * 棋譜を詳細な形式に変換
     * @param {string} kifuString - 棋譜文字列
     * @returns {string} 詳細な形式の棋譜
     */
    static toDetailed(kifuString) {
        const lines = kifuString.split('\n');
        const result = [];
        
        for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed) {
                result.push(`  ${trimmed}`);
            } else {
                result.push('');
            }
        }
        
        return result.join('\n');
    }

    /**
     * 棋譜をHTML形式に変換
     * @param {string} kifuString - 棋譜文字列
     * @returns {string} HTML形式の棋譜
     */
    static toHTML(kifuString) {
        const lines = kifuString.split('\n');
        const result = [];
        
        for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed) {
                if (/^\s*\d+\s+/.test(trimmed)) {
                    // 手数行
                    result.push(`<div class="kifu-move">${trimmed}</div>`);
                } else if (trimmed.includes('+---------------------------+')) {
                    // 盤面行
                    result.push(`<div class="kifu-board">${trimmed}</div>`);
                } else {
                    // その他の行
                    result.push(`<div class="kifu-info">${trimmed}</div>`);
                }
            } else {
                result.push('<br>');
            }
        }
        
        return result.join('\n');
    }
}

// グローバルに公開
window.KifuUtils = KifuUtils;
window.KifuManager = KifuManager;
window.KifuFormatter = KifuFormatter;

// デフォルトの棋譜マネージャーを作成
window.kifuManager = new KifuManager();
