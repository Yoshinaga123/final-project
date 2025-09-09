"""将棋機能のユーティリティ関数"""

def _nl(text):
    """改行を正規化"""
    return text.replace('\r\n', '\n').replace('\r', '\n')

def _to_kif_safe(text):
    """KIF形式に安全な形式に変換"""
    return text

def _ensure_dir(directory):
    """ディレクトリが存在しない場合は作成"""
    import os
    if not os.path.exists(directory):
        os.makedirs(directory)
