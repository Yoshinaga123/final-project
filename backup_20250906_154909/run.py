"""
アプリケーション起動ファイル

このファイルは、アプリケーションを起動するためのエントリーポイントです。
アプリケーションの「中身」には一切関知せず、単に起動するだけの役割です。
"""

import os

# Ensure external FLASK_APP setting doesn't interfere (e.g., 'apps.app').
os.environ.pop('FLASK_APP', None)
from app import create_app

# アプリケーションファクトリを実行してappインスタンスを作成
app = create_app()

# サーバーを起動する（デバッグモードなど）
if __name__ == "__main__":
    # 環境変数から設定を取得、デフォルトは開発モード
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    app.run(
        debug=debug_mode,
        use_reloader=debug_mode,
        host=host,
        port=port,
        threaded=True
    )
