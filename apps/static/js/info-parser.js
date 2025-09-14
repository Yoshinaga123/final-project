// tools/info-parser.js (browser copy)
// USI info行の解析ユーティリティ

function parseInfoLine(line) {
  if (typeof line !== 'string' || !line.startsWith('info ')) return null;
  const result = {};
  const mCp = line.match(/\bscore\s+cp\s+(-?\d+)\b/);
  if (mCp) {
    const v = parseInt(mCp[1]);
    result.score = { type: 'cp', value: v, display: formatCpScore(v) };
  }
  const mMate = line.match(/\bscore\s+mate\s+(-?\d+)\b/);
  if (mMate) {
    const v = parseInt(mMate[1]);
    result.score = { type: 'mate', value: v, display: formatMateScore(v) };
  }
  const mDepth = line.match(/\bdepth\s+(\d+)\b/);
  if (mDepth) result.depth = parseInt(mDepth[1]);
  const mNps = line.match(/\bnps\s+(\d+)\b/);
  if (mNps) result.nps = parseInt(mNps[1]);
  const mPv = line.match(/\bpv\s+(.+)$/);
  if (mPv) {
    result.pv = mPv[1].split(' ').filter(Boolean);
    result.mainMove = result.pv[0] || null;
  }
  const mTime = line.match(/\btime\s+(\d+)\b/);
  if (mTime) result.time = parseInt(mTime[1]);
  const mNodes = line.match(/\bnodes\s+(\d+)\b/);
  if (mNodes) result.nodes = parseInt(mNodes[1]);
  return Object.keys(result).length ? result : null;
}

function formatCpScore(cp) { if (cp > 0) return `+${cp}`; if (cp < 0) return `${cp}`; return '0'; }
function formatMateScore(mate) { if (mate > 0) return `先手勝ち ${mate}手詰`; if (mate < 0) return `後手勝ち ${Math.abs(mate)}手詰`; return '詰み'; }

function parseInfoLines(infoLines) {
  const result = { depth: 0, score: null, nps: 0, pv: [], mainMove: null, time: 0, nodes: 0 };
  (infoLines||[]).forEach(line => {
    const parsed = parseInfoLine(line);
    if (parsed && parsed.depth && parsed.depth >= result.depth) Object.assign(result, parsed);
  });
  return result;
}

window.USIInfoParser = { parseInfoLine, parseInfoLines, formatCpScore, formatMateScore };
