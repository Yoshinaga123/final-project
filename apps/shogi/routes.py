"""
将棋機能のルート定義

棋譜入力、将棋盤表示、棋譜管理、USIエンジン対戦などの機能を提供します。
"""

from flask import render_template, request, jsonify, session, current_app, flash, redirect, url_for, make_response
from werkzeug.utils import secure_filename
import re
import os
import datetime
from .utils import _nl, _to_kif_safe, _ensure_dir

# 循環インポートを避けるため、ここでBlueprintを取得
from . import shogi_bp, bp
from flask import Blueprint

# エンジン機能専用の軽量BP（/engine または /shogi/engine で利用可能）
engine_bp = Blueprint('shogi_engine', __name__)

try:
    from flask_login import login_required
except Exception:
    # fallback: no-op decorator if flask_login isn't available
    def login_required(f):
        return f


def safe_filename_jp(filename):
    """
    日本語文字を保持しつつ、ファイルシステムに安全なファイル名を生成
    
    Args:
        filename (str): 元のファイル名
        
    Returns:
        str: 安全なファイル名
    """
    if not filename:
        return ""
    
    # 危険な文字を除去 (ファイルシステムで問題となる文字)
    unsafe_chars = r'[<>:"/\\|?*\x00-\x1f]'
    filename = re.sub(unsafe_chars, '', filename)
    
    # 連続する空白を単一のアンダースコアに変換
    filename = re.sub(r'\s+', '_', filename.strip())
    
    # ファイル名が空の場合のフォールバック
    if not filename:
        return "kifu"
    
    # 長すぎる場合は切り詰め (Windowsの制限を考慮)
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename


UPLOAD_DIR = "apps/static/kifu"
ALLOWED_FORMATS = {"kif", "ki2", "csa", "jkf", "kifu"}

def _detect_bridge_port(cfg, root_path: str) -> int:
    """logs/usi-bridge/last_port.txt があればそれを優先して返す。無ければ USI_BRIDGE_PORT（既定 8787）。"""
    # ポートは固定（要件）: 8787 のみ許可
    try:
        # 明示的に固定。必要なら環境変数で上書き（ただし既定は 8787）
        return int(cfg.get('USI_BRIDGE_PORT', 8787))
    except Exception:
        return 8787

@shogi_bp.route('/')
def index():
    """将棋機能のトップページ"""
    return render_template('shogi/index.html')

@shogi_bp.route('/engine/start', methods=['GET', 'POST'])
@login_required
def start_engine_bridge():
    """USIブリッジ(別プロジェクト)をPowerShellから起動するヘルパー。
    - Engine パスは環境変数またはデフォルトパスを利用。
    - 既にポートがLISTEN中なら起動はスキップ。
    """
    try:
        import subprocess, sys
        host = current_app.config.get('USI_BRIDGE_HOST', '127.0.0.1')
        port = int(current_app.config.get('USI_BRIDGE_PORT', 8787))
        token = current_app.config.get('USI_BRIDGE_TOKEN')

        # 既定エンジンパス（必要に応じて config からも取得可能）
        engine_path = current_app.config.get(
            'USI_ENGINE_PATH',
            r"C:\Users\yoshinaga_kosuke\Downloads\Suisho5-ZEN2.exe"
        )

        # PowerShell スクリプトの絶対パス
        ps_script = os.path.join(current_app.root_path, 'scripts', 'run-bridge.ps1')

        # PowerShell 経由で起動（DryRunなし）
        args = [
            'powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', ps_script,
            '-Engine', engine_path,
            '-Port', str(port)
        ]
        if token:
            args += ['-Token', token]

        # 非同期で起動（サーバをブロックしない）
        subprocess.Popen(args, cwd=current_app.root_path)
        return jsonify({'success': True, 'message': 'USI bridge starting', 'port': port})
    except Exception as e:
        current_app.logger.error(f"USI bridge start failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@shogi_bp.route('/engine/health')
# @login_required  # DEBUGGING: 認証をバイパスしてエンジンヘルスチェックを可能にする
def engine_health():
    """簡易ヘルス: 指定ポートがLISTEN中かを返す。"""
    try:
        import socket
        host = current_app.config.get('USI_BRIDGE_HOST', '127.0.0.1')
        port = _detect_bridge_port(current_app.config, current_app.root_path)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            result = s.connect_ex((host, port))
            healthy = (result == 0)
        return jsonify({'success': True, 'healthy': healthy, 'host': host, 'port': port})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@engine_bp.get('/health')
def engine_health2():
    try:
        cfg = current_app.config
        host = cfg.get('USI_BRIDGE_HOST', '127.0.0.1')
        port = _detect_bridge_port(cfg, current_app.root_path)

        # TCP レベルの疎通確認（LISTEN中かどうか）
        import socket
        healthy = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.6)
                healthy = (s.connect_ex((host, port)) == 0)
        except Exception:
            healthy = False

        # WS エンドポイントは既定で /ws。token があれば付与（空なら省略）
        token = cfg.get('USI_BRIDGE_TOKEN') or ''
        qs = f"?token={token}" if token else ""
        # 固定ポート 8787 を採用（誤設定の混入を避ける）
        fixed_port = 8787
        ws_url = f"ws://{host}:{fixed_port}/ws{qs}"

        # 状態は WS ブリッジの HTTP /health を使わず UNKNOWN 扱いにする（環境によっては未提供のため）
        payload = {
            'ok': healthy,
            'status': 'UNKNOWN',
            'bridge_host': host,
            'bridge_port': port,
            'ws_url': ws_url,
        }
        return jsonify(payload), (200 if healthy else 503)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 503

@shogi_bp.route('/board')
def board():
    """棋譜管理ページ"""
    return render_template('shogi/board.html')

@shogi_bp.route('/kifu-examples')
def kifu_examples():
    """棋譜読み込み方法の例ページ"""
    return render_template('shogi/kifu_examples.html')

@shogi_bp.route('/new',methods=['GET','POST'])
def new():

    """棋譜入力ページ"""
    if request.method == "POST":
        current_app.logger.info("POST request received for new kifu")
        title = (request.form.get("title") or "game").strip() or "game"
        fmt = (request.form.get("format") or "kif").lower()
        raw = request.form.get("kifu") or ""
        current_app.logger.info(f"Form data - title: {title}, format: {fmt}, kifu length: {len(raw)}")
        
        if not raw.strip():
            flash("棋譜データが入力されていません", "error")
            return redirect(url_for("shogi.new"))
        
        if fmt not in ALLOWED_FORMATS:
            flash("未対応の形式です", "error")
            return redirect(url_for("shogi.new"))
        
        text = _nl(raw)
        if fmt == "kif":
            text = _to_kif_safe(text)
        
        # タイトルが空の場合のフォールバック処理
        if not title.strip():
            fname = f"棋譜.{fmt}"
        else:
            fname = safe_filename_jp(f"{title}.{fmt}")
        outdir = os.path.join(current_app.root_path, UPLOAD_DIR)
        current_app.logger.info(f"Output directory: {outdir}")
        
        _ensure_dir(outdir)
        filepath = os.path.join(outdir, fname)
        current_app.logger.info(f"Saving to: {filepath}")
        
        try:
            with open(filepath, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            
            current_app.logger.info(f"File saved successfully: {fname}")
            flash(f"棋譜を保存しました: {fname}", "success")
            return redirect(url_for("shogi.kifu_list"))
        except Exception as e:
            current_app.logger.error(f"Failed to save kifu file: {e}")
            flash("ファイルの保存に失敗しました", "error")
            return redirect(url_for("shogi.new"))
    return render_template('shogi/new.html')


import json
from urllib.parse import urljoin

# 新しい候補手機能モジュール
from .candidates import generate_candidates, emergency_candidates


@shogi_bp.route('/api/candidate-moves', methods=['POST'])
def get_candidate_moves():
    """現在の盤面から候補手を取得するAPI（CSRF保護除外）"""
    try:
        # リクエストデータの安全な取得
        try:
            data = request.get_json()
            if data is None:
                data = {}
                current_app.logger.warning("JSON data is None, using empty dict")
        except Exception as json_error:
            current_app.logger.error(f"JSON parse error: {json_error}")
            data = {}
        
        # パラメータの安全な取得とバリデーション
        position = data.get('position', 'startpos')
        moves = data.get('moves', [])
        current_player = data.get('current_player', 'b')
        
        # 入力値の検証
        if not isinstance(moves, list):
            moves = []
            current_app.logger.warning("moves is not a list, using empty list")
        
        if current_player not in ['b', 'w']:
            current_player = 'b'
            current_app.logger.warning(f"Invalid current_player, using 'b'")
        
        current_app.logger.info(f"候補手リクエスト: moves={len(moves)}手, player={current_player}")
        current_app.logger.debug(f"Request data: {data}")
        current_app.logger.debug(f"Raw moves: {moves[:5] if len(moves) > 5 else moves}...")  # 最初の5手のみログ
        
        # 候補手生成（USIエンジン優先 → 定義済み → フォールバック → 緊急）
        candidate_moves = generate_candidates(
            moves=moves,
            current_player=current_player,
            limit=int(current_app.config.get('CANDIDATE_LIMIT', 4)),
            movetime_ms=int(current_app.config.get('CANDIDATE_MOVETIME_MS', current_app.config.get('MOVETIME_MS', 1000))),
            logger=current_app.logger,
            config=current_app.config,
            root_path=current_app.root_path,
        )
        
        # 最終的な安全性チェック
        if not candidate_moves:
            candidate_moves = emergency_candidates(current_player)
            current_app.logger.warning("Using emergency candidate moves")
        
        current_app.logger.info(f"候補手生成完了: {len(candidate_moves)}手, 局面={len(moves)}手目")
        
        return jsonify({
            'success': True,
            'candidate_moves': candidate_moves,
            'position': position,
            'moves_count': len(moves),
            'current_player': current_player,
            'phase': get_game_phase(len(moves)),
            'debug': {
                'moves_length': len(moves),
                'moves_type': type(moves).__name__,
                'data_keys': list(data.keys()) if isinstance(data, dict) else []
            }
        })
        
    except Exception as e:
        # 最終的なエラーハンドリング
        current_app.logger.error(f"Critical error in get_candidate_moves: {e}")
        emergency_moves = emergency_candidates('b')
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'candidate_moves': emergency_moves,
            'debug_error': str(e)
        }), 200  # 500エラーを避けるため200で返す


def get_game_phase(move_count):
    """ゲームの局面を判定"""
    if move_count == 0:
        return '初期配置'
    elif move_count <= 10:
        return '序盤'
    elif move_count <= 30:
        return '中盤'
    else:
        return '終盤'


@shogi_bp.route('/api/move', methods=['POST'])
def make_move():
    """手を打つAPI"""
    data = request.get_json()
    
    # 棋譜データをセッションに保存
    if 'kifu' not in session:
        session['kifu'] = []
    
    move_data = {
        'move_number': len(session['kifu']) + 1,
        'from_pos': data.get('from'),
        'to_pos': data.get('to'),
        'piece': data.get('piece'),
        'promotion': data.get('promotion', False),
        'timestamp': data.get('timestamp')
    }
    
    session['kifu'].append(move_data)
    session.modified = True
    
    return jsonify({
        'success': True,
        'move': move_data,
        'total_moves': len(session['kifu'])
    })

@shogi_bp.route('/api/kifu', methods=['GET'])
def get_kifu():
    """棋譜データを取得するAPI"""
    kifu = session.get('kifu', [])
    
    # 初期棋譜データ（例）
    if not kifu:
        kifu = [
            {
                'move_number': 1,
                'from': '77',
                'to': '76',
                'piece': '歩',
                'promotion': False,
                'player': 'sente',
                'timestamp': '2025-01-01T00:00:00Z'
            },
            {
                'move_number': 2,
                'from': '33',
                'to': '34',
                'piece': '歩',
                'promotion': False,
                'player': 'gote',
                'timestamp': '2025-01-01T00:01:00Z'
            }
        ]
        session['kifu'] = kifu
        session.modified = True
    
    return jsonify({
        'success': True,
        'kifu': kifu,
        'total_moves': len(kifu)
    })

@shogi_bp.route('/api/reset', methods=['POST'])
def reset_board():
    """盤面をリセットするAPI"""
    session['kifu'] = []
    session.modified = True
    
    return jsonify({
        'success': True,
        'message': '盤面をリセットしました'
    })

@shogi_bp.route('/api/save', methods=['POST'])
def save_kifu():
    """棋譜を保存するAPI"""
    data = request.get_json()
    title = data.get('title', '無題の棋譜')
    
    # ここでデータベースに保存する処理を実装
    # 現在はセッションに保存された棋譜を返すだけ
    
    kifu_data = {
        'title': title,
        'kifu': session.get('kifu', []),
        'created_at': data.get('timestamp')
    }
    
    return jsonify({
        'success': True,
        'message': f'棋譜「{title}」を保存しました',
        'kifu': kifu_data
    })

@shogi_bp.route('/kifu')
def kifu_list():
    """棋譜ファイル一覧ページ"""
    kifu_dir = os.path.join(current_app.root_path, UPLOAD_DIR)
    kifu_files = []
    
    if os.path.exists(kifu_dir):
        for filename in os.listdir(kifu_dir):
            if filename.endswith(('.kif', '.ki2', '.csa', '.jkf', '.kifu')):
                filepath = os.path.join(kifu_dir, filename)
                stat = os.stat(filepath)
                file_ext = filename.split('.')[-1].lower()
                kifu_files.append({
                    'filename': filename,
                    'size': stat.st_size,
                    'modified': datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'format': file_ext.upper(),
                    'url': url_for('shogi.kifu_view', filename=filename)
                })
    
    # 更新日時でソート（新しい順）
    kifu_files.sort(key=lambda x: x['modified'], reverse=True)
    
    return render_template('shogi/kifu_list.html', kifu_files=kifu_files)

@shogi_bp.route('/kifu/<filename>')
def kifu_view(filename):
    """個別棋譜表示・再生ページ"""
    # ファイル名の安全性チェック
    if not filename or '..' in filename or '/' in filename or '\\' in filename:
        current_app.logger.error(f"Invalid filename: {filename}")
        flash("無効なファイル名です", "error")
        return redirect(url_for('shogi.kifu_list'))
    
    kifu_dir = os.path.join(current_app.root_path, UPLOAD_DIR)
    filepath = os.path.join(kifu_dir, filename)
    
    # デバッグログを追加
    current_app.logger.info(f"Looking for file: {filename}")
    current_app.logger.info(f"Kifu dir: {kifu_dir}")
    current_app.logger.info(f"Full filepath: {filepath}")
    current_app.logger.info(f"File exists: {os.path.exists(filepath)}")
    
    if not os.path.exists(filepath):
        current_app.logger.error(f"File not found: {filepath}")
        flash("ファイルが見つかりません", "error")
        return redirect(url_for('shogi.kifu_list'))
    
    # ファイル内容を読み込み
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            kifu_content = f.read()
    except Exception as e:
        current_app.logger.error(f"Failed to read kifu file {filename}: {e}")
        flash("ファイルの読み込みに失敗しました", "error")
        return redirect(url_for('shogi.kifu_list'))
    
    # ファイル情報を取得
    stat = os.stat(filepath)
    file_info = {
        'filename': filename,
        'size': stat.st_size,
        'modified': datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
        'format': filename.split('.')[-1].lower()
    }
    
    # 詰将棋かどうかのフラグを判定
    is_tsume = '詰' in filename or 'tsume' in filename.lower()
    
    return render_template('shogi/kifu_view.html', 
                         kifu_content=kifu_content, 
                         file_info=file_info,
                         is_tsume=is_tsume)

@shogi_bp.route('/api/kifu/<filename>')
def api_kifu_content(filename):
    """棋譜ファイル内容を取得するAPI"""
    # ファイル名の安全性チェック
    if not filename or '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'success': False, 'error': 'Invalid filename'}), 400
    
    kifu_dir = os.path.join(current_app.root_path, UPLOAD_DIR)
    filepath = os.path.join(kifu_dir, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'success': False, 'error': 'File not found'}), 404
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            kifu_content = f.read()
        
        return jsonify({
            'success': True,
            'content': kifu_content,
            'filename': filename,
            'format': filename.split('.')[-1].lower()
        })
    except Exception as e:
        current_app.logger.error(f"Failed to read kifu file {filename}: {e}")
        return jsonify({'success': False, 'error': 'Failed to read file'}), 500

# 正規URL: /engine/shogi （既存テンプレを再利用し、必ず ws_url と movetime_ms を渡す）
@engine_bp.get('/shogi')
def engine_shogi():
    cfg = current_app.config
    host = cfg.get('USI_BRIDGE_HOST', '127.0.0.1')
    port = _detect_bridge_port(cfg, current_app.root_path)
    token = cfg.get('USI_BRIDGE_TOKEN') or ''
    qs = f"?token={token}" if token else ""
    ws_url = f"ws://{host}:{port}/ws{qs}"
    movetime_ms = int(cfg.get('MOVETIME_MS', 2000))
    # センシティブなクエリをキャッシュさせない（token混在対策）
    masked = (ws_url.replace(f"token={token}", "token=***") if token else ws_url)
    current_app.logger.info("/engine/shogi: ws_url=%s movetime_ms=%s", masked, movetime_ms)
    resp = make_response(render_template('shogi_vs_engine.html', ws_url=ws_url, movetime_ms=movetime_ms, token=token))
    resp.headers['Cache-Control'] = 'no-store'
    return resp

# 互換: /engine/vs-engine -> /engine/shogi へ寄せる（任意）
@engine_bp.get('/vs-engine')
def engine_alias_vsengine():
    return redirect(url_for('shogi_engine.engine_shogi'), code=302)

@shogi_bp.route('/vs-engine')
def shogi_vs_engine():
    host = current_app.config.get('USI_BRIDGE_HOST', '127.0.0.1')
    port = _detect_bridge_port(current_app.config, current_app.root_path)
    token = current_app.config.get('USI_BRIDGE_TOKEN')
    qs = f"?token={token}" if token else ""
    ws_url = f"ws://{host}:{port}/ws{qs}"
    movetime_ms = int(current_app.config.get('MOVETIME_MS', 2000))
    resp = make_response(render_template('shogi_vs_engine.html', ws_url=ws_url, movetime_ms=movetime_ms, token=token))
    resp.headers['Cache-Control'] = 'no-store'
    return resp

# SVG盤面版（参照HTMLに近いUI）
@engine_bp.get('/shogi-svg')
def engine_shogi_svg():
    cfg = current_app.config
    host = cfg.get('USI_BRIDGE_HOST', '127.0.0.1')
    port = _detect_bridge_port(cfg, current_app.root_path)
    token = cfg.get('USI_BRIDGE_TOKEN') or ''
    qs = f"?token={token}" if token else ""
    ws_url = f"ws://{host}:{port}/ws{qs}"
    movetime_ms = int(cfg.get('MOVETIME_MS', 2000))
    resp = make_response(render_template('shogi_svg.html', ws_url=ws_url, movetime_ms=movetime_ms, token=token))
    resp.headers['Cache-Control'] = 'no-store'
    return resp

# 作業依頼仕様: 新しいbp用のルート（/shogiでアクセス）
@bp.route('/shogi')
# @login_required  # DEBUGGING: 認証をバイパスしてUIテストを可能にする
def shogi():
    """USI Bridge連携の将棋対戦UI - 作業依頼仕様"""
    host = current_app.config.get('USI_BRIDGE_HOST', '127.0.0.1')
    port = _detect_bridge_port(current_app.config, current_app.root_path)
    token = current_app.config.get('USI_BRIDGE_TOKEN')
    qs = f"?token={token}" if token else ""
    ws_url = f"ws://{host}:{port}/ws{qs}"
    movetime_ms = int(current_app.config.get('MOVETIME_MS', 2000))
    resp = make_response(render_template('shogi_vs_engine.html', ws_url=ws_url, movetime_ms=movetime_ms, token=token))
    resp.headers['Cache-Control'] = 'no-store'
    return resp
