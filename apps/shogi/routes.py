"""
将棋機能のルート定義

棋譜入力、将棋盤表示、棋譜管理などの機能を提供します。
"""

from flask import render_template, request, jsonify, session, current_app, flash, redirect, url_for
from werkzeug.utils import secure_filename
import re
import os
import datetime
from .utils import _nl, _to_kif_safe, _ensure_dir
from . import shogi_bp


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

@shogi_bp.route('/')
def index():
    """将棋機能のトップページ"""
    return render_template('shogi/index.html')

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
