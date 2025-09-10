#!/usr/bin/env python3
"""
日本語ファイル名生成のテスト
"""

import re

def safe_filename_jp(filename):
    """
    日本語文字を保持しつつ、ファイルシステムに安全なファイル名を生成
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

# テストケース
test_cases = [
    "相馬康幸　「デフォルト」　詰パラ２００３年８月 *看寿賞中編賞",
    "相馬康幸作_詰パラ",
    "棋譜",
    "",
    "Test<>:\"/\\|?*File",
    "普通の棋譜タイトル",
    "   空白だらけ   の   タイトル   "
]

print("日本語ファイル名生成テスト")
print("=" * 50)

for i, title in enumerate(test_cases, 1):
    ts = "20250910-195223"
    fmt = "kif"
    original_filename = f"{title}-{ts}.{fmt}"
    safe_filename = safe_filename_jp(original_filename)
    
    print(f"テスト {i}:")
    print(f"  元のタイトル: '{title}'")
    print(f"  生成されるファイル名: '{safe_filename}'")
    print()
