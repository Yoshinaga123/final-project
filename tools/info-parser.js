// tools/info-parser.js
// USI info行の解析ユーティリティ

/**
 * USI info行をパースして構造化データに変換
 * @param {string} line - info行の文字列
 * @returns {object} パース結果
 */
function parseInfoLine(line) {
  if (!line.startsWith('info ')) {
    return null;
  }

  const result = {};
  
  // score cp <val> ... 評価値（先手視点のセンチポーン）
  const mCp = line.match(/\bscore\s+cp\s+(-?\d+)\b/);
  if (mCp) {
    result.score = {
      type: 'cp',
      value: parseInt(mCp[1]),
      display: formatCpScore(parseInt(mCp[1]))
    };
  }

  // score mate <n> ... 詰みまでの手数（正: 先手勝ち、負: 後手勝ち）
  const mMate = line.match(/\bscore\s+mate\s+(-?\d+)\b/);
  if (mMate) {
    const mateValue = parseInt(mMate[1]);
    result.score = {
      type: 'mate',
      value: mateValue,
      display: formatMateScore(mateValue)
    };
  }

  // depth <n>
  const mDepth = line.match(/\bdepth\s+(\d+)\b/);
  if (mDepth) {
    result.depth = parseInt(mDepth[1]);
  }

  // nps <n>
  const mNps = line.match(/\bnps\s+(\d+)\b/);
  if (mNps) {
    result.nps = parseInt(mNps[1]);
  }

  // pv <moves...> ... 主変化
  const mPv = line.match(/\bpv\s+(.+)$/);
  if (mPv) {
    result.pv = mPv[1].split(' ').filter(Boolean);
    result.mainMove = result.pv[0] || null;
  }

  // time <ms>
  const mTime = line.match(/\btime\s+(\d+)\b/);
  if (mTime) {
    result.time = parseInt(mTime[1]);
  }

  // nodes <n>
  const mNodes = line.match(/\bnodes\s+(\d+)\b/);
  if (mNodes) {
    result.nodes = parseInt(mNodes[1]);
  }

  return Object.keys(result).length > 0 ? result : null;
}

/**
 * CP値を表示用文字列に変換
 * @param {number} cp - センチポーン値
 * @returns {string} 表示文字列
 */
function formatCpScore(cp) {
  if (cp > 0) {
    return `+${cp}`;
  } else if (cp < 0) {
    return `${cp}`;
  }
  return "0";
}

/**
 * 詰み値を表示用文字列に変換
 * @param {number} mate - 詰みまでの手数
 * @returns {string} 表示文字列
 */
function formatMateScore(mate) {
  if (mate > 0) {
    return `先手勝ち ${mate}手詰`;
  } else if (mate < 0) {
    return `後手勝ち ${Math.abs(mate)}手詰`;
  }
  return "詰み";
}

/**
 * 複数のinfo行から最新の情報を統合
 * @param {string[]} infoLines - info行の配列
 * @returns {object} 統合された解析結果
 */
function parseInfoLines(infoLines) {
  let result = {
    depth: 0,
    score: null,
    nps: 0,
    pv: [],
    mainMove: null,
    time: 0,
    nodes: 0
  };

  infoLines.forEach(line => {
    const parsed = parseInfoLine(line);
    if (parsed) {
      // より深い探索結果で更新
      if (parsed.depth && parsed.depth >= result.depth) {
        Object.assign(result, parsed);
      }
    }
  });

  return result;
}

// Node.js環境でのエクスポート
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    parseInfoLine,
    parseInfoLines,
    formatCpScore,
    formatMateScore
  };
}

// ブラウザ環境でのグローバル関数
if (typeof window !== 'undefined') {
  window.USIInfoParser = {
    parseInfoLine,
    parseInfoLines,
    formatCpScore,
    formatMateScore
  };
}
