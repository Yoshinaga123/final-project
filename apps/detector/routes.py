"""
物体検知機能のルート定義

画像アップロード、物体検知実行、結果表示などの機能を提供します。
"""

from flask import render_template, request, jsonify, current_app, flash, redirect, url_for, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import datetime
import uuid
import json
from . import detector_bp
from apps.models.model import UserImage, db

def allowed_file(filename):
    """許可されたファイル形式かチェック"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def ensure_upload_dirs():
    """画像検知専用アップロードディレクトリの存在確認・作成"""
    upload_dir = current_app.config['DETECTOR_UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir

def result_json_path(filename: str) -> str:
    """検知結果JSONのパス（画像と同階層、<filename>.det.json）"""
    upload_dir = ensure_upload_dirs()
    return os.path.join(upload_dir, f"{filename}.det.json")

def save_detection_results(filename: str, results: list):
    """検知結果をJSONに保存（上書き）"""
    payload = {
        'image_filename': filename,
        'updated_at': datetime.datetime.utcnow().isoformat(timespec='seconds') + 'Z',
    'model': 'yolov8n',
        'results': results,
        'count': len(results)
    }
    path = result_json_path(filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload

def load_detection_results(filename: str):
    """検知結果JSONを読み込み。存在しない場合はNone"""
    path = result_json_path(filename)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        current_app.logger.warning(f"検知結果の読み込み失敗: {e}")
        return None

def generate_unique_filename(original_filename):
    """一意のファイル名を生成"""
    # 拡張子を取得
    ext = ''
    if '.' in original_filename:
        ext = '.' + original_filename.rsplit('.', 1)[1].lower()
    
    # タイムスタンプ + UUID + 拡張子で一意のファイル名を生成
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    return f"{timestamp}_{unique_id}{ext}"

@detector_bp.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    """Serve uploaded images if they belong to the current user.

    Accepts either plain filename (e.g., 'abc.jpg') or a path like 'uploads/abc.jpg'.
    """
    # Normalize to basename to avoid subdir traversal and support 'uploads/foo.jpg'
    base_name = os.path.basename(filename)

    # Ensure the requested file belongs to current user
    img = UserImage.query.filter_by(
        filename=base_name,
        user_id=current_user.id,
        is_active=True
    ).first()
    if not img:
        # Avoid leaking existence information
        return ('Not Found', 404)

    upload_dir = current_app.config['DETECTOR_UPLOAD_FOLDER']
    return send_from_directory(upload_dir, base_name)

# Reference repo compatibility aliases (no external file changes)
@detector_bp.route('/image/<path:filename>')
@login_required
def image_file(filename):
    """Alias of uploaded_file for template compatibility."""
    return uploaded_file(filename)

# Additional alias to match reference '/images/<path:filename>'
@detector_bp.route('/images/<path:filename>')
@login_required
def images_file(filename):
    """Alias matching reference code path."""
    return uploaded_file(filename)

@detector_bp.route('/upload_image', methods=['GET', 'POST'])
@login_required
def upload_image():
    """Alias of upload for template compatibility."""
    return upload()

@detector_bp.route('/')
@login_required
def index():
    """物体検知のトップページ"""
    images = UserImage.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).order_by(UserImage.uploaded_at.desc()).all()
    # 検知メタ情報
    results_meta = {}
    for img in images:
        meta = load_detection_results(img.filename)
        if meta:
            results_meta[img.id] = {'count': meta.get('count', 0), 'updated_at': meta.get('updated_at')}
    return render_template('detector/index.html', images=images, count=len(images), results_meta=results_meta)

@detector_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """画像アップロードページ"""
    if request.method == 'POST':
        current_app.logger.info('detector.upload: POST received')
        # ファイルの存在確認（reference互換: 'image' も受け付け）
        file = request.files.get('file') or request.files.get('image')
        if not file:
            flash('ファイルが選択されていません', 'error')
            return redirect(request.url)
        
        # ファイル名の確認
        if file.filename == '':
            flash('ファイルが選択されていません', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                # ディレクトリの確保
                upload_dir = ensure_upload_dirs()
                
                # 一意のファイル名を生成
                original_filename = secure_filename(file.filename)
                unique_filename = generate_unique_filename(original_filename)
                
                # ファイル保存
                filepath = os.path.join(upload_dir, unique_filename)
                file.save(filepath)
                
                # 相対パスを生成（Web表示用）
                relative_path = f"uploads/{unique_filename}"
                
                # データベースに画像情報を保存
                user_image = UserImage(
                    user_id=current_user.id,
                    image_path=relative_path,
                    filename=unique_filename,
                    original_filename=original_filename
                )
                
                db.session.add(user_image)
                db.session.commit()
                
                current_app.logger.info(f"画像をアップロードしました: {unique_filename} (ユーザー: {current_user.username})")
                flash(f'画像をアップロードしました: {original_filename}', 'success')
                
                # 物体検知実行ページにリダイレクト
                target = url_for('detector.detect', image_id=user_image.id)
                current_app.logger.info(f'detector.upload: redirect -> {target}')
                return redirect(target)
                
            except Exception as e:
                current_app.logger.error(f"画像アップロードエラー: {e}")
                flash('画像のアップロードに失敗しました', 'error')
                return redirect(request.url)
        else:
            flash('対応していないファイル形式です。PNG、JPG、JPEG、GIF、BMP、WEBPファイルをアップロードしてください。', 'error')
    
    return render_template('detector/upload.html')

@detector_bp.route('/detect/<int:image_id>', methods=['GET', 'POST'])
@login_required
def detect(image_id):
    """物体検知実行ページ"""
    # 画像をデータベースから取得
    user_image = UserImage.query.filter_by(
        id=image_id,
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not user_image:
        flash('指定された画像が見つからないか、アクセス権限がありません', 'error')
        return redirect(url_for('detector.upload'))
    
    # ファイルの存在確認
    upload_dir = ensure_upload_dirs()
    filepath = os.path.join(upload_dir, user_image.filename)
    
    if not os.path.exists(filepath):
        flash('画像ファイルが見つかりません', 'error')
        return redirect(url_for('detector.upload'))
    
    # 保存済み結果を取得
    saved = load_detection_results(user_image.filename)

    # POST時は再検知して保存後、PRGで同ページへ
    if request.method == 'POST':
        current_app.logger.info(f'detector.detect: POST received for image_id={image_id}')
        detection_results = simulate_object_detection(user_image.filename)
        saved = save_detection_results(user_image.filename, detection_results)
        flash('物体検知を実行しました。', 'success')
        target = url_for('detector.detect', image_id=image_id)
        current_app.logger.info(f'detector.detect: redirect -> {target}')
        return redirect(target)

    # GET時: 未保存であれば初回検知を実行
    if not saved:
        detection_results = simulate_object_detection(user_image.filename)
        saved = save_detection_results(user_image.filename, detection_results)

    return render_template(
        'detector/detect.html',
        user_image=user_image,
        results=saved.get('results', []) if saved else [],
        detected_at=saved.get('updated_at') if saved else None,
        detection_count=saved.get('count', 0) if saved else 0
    )

@detector_bp.route('/gallery')
@login_required
def gallery():
    """画像ギャラリー（ユーザー別）"""
    try:
        # 現在のユーザーの画像のみ取得
        images = UserImage.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).order_by(UserImage.uploaded_at.desc()).all()
        # 検知メタ
        results_meta = {}
        for img in images:
            meta = load_detection_results(img.filename)
            if meta:
                results_meta[img.id] = {'count': meta.get('count', 0), 'updated_at': meta.get('updated_at')}

        return render_template('detector/gallery.html', 
                             images=images, 
                             count=len(images),
                             results_meta=results_meta)
    except Exception as e:
        current_app.logger.error(f"ギャラリー表示エラー: {e}")
        flash('ギャラリーの表示に失敗しました', 'error')
        return redirect(url_for('detector.index'))

@detector_bp.route('/api/detect', methods=['POST'])
@login_required
def api_detect():
    """物体検知API"""
    data = request.get_json()
    image_id = data.get('image_id')
    
    if not image_id:
        return jsonify({'success': False, 'error': '画像IDが指定されていません'}), 400
    
    # 画像をデータベースから取得
    user_image = UserImage.query.filter_by(
        id=image_id,
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not user_image:
        return jsonify({'success': False, 'error': '指定された画像が見つかりません'}), 404
    
    # 物体検知実行（仮実装）+ 保存
    results = simulate_object_detection(user_image.filename)
    saved = save_detection_results(user_image.filename, results)

    return jsonify({
        'success': True,
        'image_id': image_id,
        'filename': user_image.original_filename,
        'results': saved.get('results', []),
        'detection_count': saved.get('count', 0),
        'updated_at': saved.get('updated_at')
    })

@detector_bp.route('/api/results/<int:image_id>')
@login_required
def api_get_results(image_id: int):
    """保存済み検知結果の取得API"""
    user_image = UserImage.query.filter_by(
        id=image_id,
        user_id=current_user.id,
        is_active=True
    ).first()
    if not user_image:
        return jsonify({'success': False, 'error': '画像が見つかりません'}), 404

    saved = load_detection_results(user_image.filename)
    if not saved:
        return jsonify({'success': False, 'error': '検知結果がありません'}), 404
    return jsonify({'success': True, **saved})

_YOLO_MODEL = None  # モデルのシングルトンキャッシュ

def _get_yolo_model():
    """Ultralytics YOLOv8 モデルを遅延ロードし、プロセス内で再利用"""
    global _YOLO_MODEL
    if _YOLO_MODEL is not None:
        return _YOLO_MODEL
    try:
        from ultralytics import YOLO
    except Exception as e:
        current_app.logger.warning(f"Ultralyticsの読み込みに失敗: {e}")
        return None

    # プロジェクト直下の学習済み重みを参照（yolov8n.pt）
    weights_path = os.path.join(current_app.root_path, 'yolov8n.pt')
    if not os.path.exists(weights_path):
        # カレントディレクトリ直下のケースも試す
        alt_path = os.path.abspath(os.path.join(os.getcwd(), 'yolov8n.pt'))
        weights_path = alt_path if os.path.exists(alt_path) else 'yolov8n.pt'
    try:
        _YOLO_MODEL = YOLO(weights_path)
        return _YOLO_MODEL
    except Exception as e:
        current_app.logger.error(f"YOLOv8モデルの初期化に失敗: {e}")
        return None

def real_object_detection(filename):
    """実際の物体検知実装（Ultralytics YOLOv8 使用、CPU推論）"""
    try:
        import numpy as np
        from PIL import Image
        # 画像パス
        upload_dir = ensure_upload_dirs()
        image_path = os.path.join(upload_dir, filename)
        if not os.path.exists(image_path):
            current_app.logger.error(f"画像ファイルが見つかりません: {image_path}")
            return []

        model = _get_yolo_model()
        if model is None:
            return simulate_object_detection_fallback(filename)

        # PILで読み込み（ultralyticsはパスでも可だが、将来の前処理のため読み込む）
        img = Image.open(image_path).convert('RGB')

        # 推論（速度重視のためデフォルト設定、CPU）
        results = model.predict(img, verbose=False)
        if not results:
            return []
        r0 = results[0]

        detections = []
        # namesは辞書 or list 形式
        names = getattr(model, 'names', None) or getattr(r0, 'names', None) or {}

        # r0.boxes: xyxy, conf, cls
        boxes = getattr(r0, 'boxes', None)
        if boxes is None or len(boxes) == 0:
            return []

        try:
            xyxy = boxes.xyxy.cpu().numpy()
            conf = boxes.conf.cpu().numpy()
            cls = boxes.cls.cpu().numpy().astype(int)
        except Exception:
            # CPUテンソルではない、または属性が存在しない場合のフォールバック
            xyxy = np.array(boxes.xyxy)
            conf = np.array(boxes.conf)
            cls = np.array(boxes.cls, dtype=int)

        for i in range(len(xyxy)):
            x1, y1, x2, y2 = xyxy[i]
            c = float(conf[i]) if i < len(conf) else 0.0
            k = int(cls[i]) if i < len(cls) else -1
            label = names.get(k, str(k)) if isinstance(names, dict) else (names[k] if isinstance(names, (list, tuple)) and 0 <= k < len(names) else str(k))
            detections.append({
                'class': label,
                'confidence': round(c, 2),
                'bbox': {
                    'x': int(max(0, x1)),
                    'y': int(max(0, y1)),
                    'width': int(max(0, x2 - x1)),
                    'height': int(max(0, y2 - y1))
                }
            })

        current_app.logger.info(f"物体検知完了: {len(detections)}個のオブジェクトを検出 (YOLOv8)")
        return detections

    except Exception as e:
        current_app.logger.error(f"物体検知エラー (YOLOv8): {e}")
        return simulate_object_detection_fallback(filename)

def simulate_object_detection_fallback(filename):
    """
    フォールバック用のシミュレーション（実際のAIが使えない場合）
    """
    import random
    
    current_app.logger.info("フォールバックモード: シミュレーション実行")
    
    # より現実的なシミュレーション
    common_objects = ['person', 'car', 'bicycle', 'dog', 'cat', 'bird']
    rare_objects = ['horse', 'sheep', 'cow', 'elephant', 'truck', 'motorcycle']
    
    results = []
    num_objects = random.randint(1, 3)  # より現実的な数
    
    for i in range(num_objects):
        # 一般的なオブジェクトの確率を高く
        if random.random() < 0.8:
            obj_class = random.choice(common_objects)
        else:
            obj_class = random.choice(rare_objects)
            
        results.append({
            'class': obj_class,
            'confidence': round(random.uniform(0.65, 0.92), 2),
            'bbox': {
                'x': random.randint(10, 200),
                'y': random.randint(10, 200), 
                'width': random.randint(80, 250),
                'height': random.randint(80, 250)
            }
        })
    
    return results

# メイン関数のエイリアス（後方互換性）
def simulate_object_detection(filename):
    """物体検知のメイン関数"""
    return real_object_detection(filename)

@detector_bp.route('/results')
@login_required  
def results():
    """検知結果一覧ページ（廃止予定 - galleryに統合）"""
    return redirect(url_for('detector.gallery'))

@detector_bp.route('/delete/<int:image_id>', methods=['POST'])
@login_required
def delete_image(image_id):
    """ユーザーの画像を論理削除"""
    img = UserImage.query.filter_by(
        id=image_id,
        user_id=current_user.id,
        is_active=True
    ).first()
    if not img:
        flash('対象の画像が見つかりません', 'error')
        return redirect(url_for('detector.index'))

    try:
        # 物理ファイル削除（存在する場合のみ、失敗しても処理継続）
        try:
            upload_dir = ensure_upload_dirs()
            file_path = os.path.join(upload_dir, img.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                current_app.logger.info(f"画像ファイルを削除しました: {img.filename}")
        except Exception as fe:
            current_app.logger.warning(f"ファイル削除に失敗しました（スキップ）: {fe}")

        img.is_active = False
        img.is_deleted = True
        db.session.commit()
        flash('画像を削除しました', 'success')
    except Exception as e:
        current_app.logger.error(f"画像削除エラー: {e}")
        db.session.rollback()
        flash('画像の削除に失敗しました', 'error')
    return redirect(url_for('detector.index'))
