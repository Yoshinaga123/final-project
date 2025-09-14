from werkzeug.utils import secure_filename
import datetime
import re

def generate_filename(raw_title: str | None) -> str:
    title = (raw_title or '').strip() or '棋譜'
    ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    safe = secure_filename(title) or 'kifu'
    return f"{safe}_{ts}.kif"

def test_filename_generation_cases():
    cases = ['', '   ', 'test', '詰将棋_相馬康幸作', '!!!invalid!!!']
    for c in cases:
        fname = generate_filename(c)
        assert fname.endswith('.kif')
        # タイムスタンプ部分 (末尾 15+4 = 19 文字含む) の基本フォーマット確認 YYYYMMDD-HHMMSS
        parts = fname.rsplit('_', 1)
        assert len(parts) == 2
        ts_part = parts[1].removesuffix('.kif')
        assert re.match(r'^\d{8}-\d{6}$', ts_part)
