from werkzeug.utils import secure_filename

# 漢字テストケース
test_cases = [
    '相馬康幸　「デフォルト」　詰パラ２００３年８月 *看寿賞中編賞',
    '相馬康幸',
    '詰将棋',
    '２００３年',
    'test123',
    '相馬康幸作_詰パラ'
]

print("=== secure_filename テスト ===")
for case in test_cases:
    result = secure_filename(case)
    print(f'Input: "{case}"')
    print(f'Output: "{result}"')
    print(f'Length: {len(result)}')
    # 文字ごとの分析
    if result != case:
        print(f'Characters in result: {[c for c in result]}')
    print('---')

# 実際のログのケースをテスト
actual_title = '相馬康幸　「デフォルト」　詰パラ２００３年８月 *看寿賞中編賞'
secure_result = secure_filename(actual_title)
print(f"\n実際のケース:")
print(f'Title: "{actual_title}"')
print(f'Secure: "{secure_result}"')
print(f'Characters: {list(secure_result)}')

# 全角数字の確認
fullwidth_numbers = '０１２３４５６７８９'
halfwidth_numbers = '0123456789'
print(f"\n全角数字テスト:")
print(f'Full: {secure_filename(fullwidth_numbers)}')
print(f'Half: {secure_filename(halfwidth_numbers)}')
