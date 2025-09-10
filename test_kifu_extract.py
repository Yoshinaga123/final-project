import sys
sys.path.append('.')

# KIF内容抽出のテスト
def _extract_kifu_title(kifu_content):
    """KIFファイル内容からタイトル情報を抽出"""
    if not kifu_content:
        return None
    
    lines = kifu_content.split('\n')
    metadata = {}
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        # 各種メタデータ抽出
        if line.startswith('作品名：') and len(line) > 4:
            work_name = line[4:].strip()
            if work_name and work_name != 'デフォルト':
                metadata['work_name'] = work_name
        elif line.startswith('作者：') and len(line) > 3:
            author = line[3:].strip()
            if author:
                metadata['author'] = author
        elif line.startswith('発表誌：') and len(line) > 4:
            magazine = line[4:].strip()
            if magazine:
                metadata['magazine'] = magazine
        elif line.startswith('発表年月：') and len(line) > 5:
            date = line[5:].strip()
            if date:
                metadata['date'] = date
        elif line.startswith('受賞：') and len(line) > 3:
            award = line[3:].strip()
            if award:
                metadata['award'] = award
        elif line.startswith('手数：') and len(line) > 3:
            moves = line[3:].strip()
            if moves:
                metadata['moves'] = moves
        elif '詰' in line and ('手詰' in line or 'まで' in line):
            # 詰将棋判定
            metadata['is_tsume'] = True
    
    # タイトル生成優先順位
    if 'work_name' in metadata:
        return metadata['work_name']
    elif 'author' in metadata and 'magazine' in metadata:
        return f"{metadata['author']}作_{metadata['magazine']}"
    elif 'author' in metadata and metadata.get('is_tsume'):
        moves_info = f"_{metadata['moves']}手" if 'moves' in metadata else ""
        return f"詰将棋_{metadata['author']}作{moves_info}"
    elif 'author' in metadata:
        return f"{metadata['author']}作品"
    elif metadata.get('is_tsume'):
        moves_info = f"_{metadata['moves']}手" if 'moves' in metadata else ""
        return f"詰将棋{moves_info}"
    elif 'magazine' in metadata:
        return f"{metadata['magazine']}_作品"
    
    return None

# 実際のKIFファイルでテスト
with open('詰将棋_NO_GUARD_OPENING_急須屋2号店_43手.kif', 'r', encoding='utf-8') as f:
    kif_content = f.read()

result = _extract_kifu_title(kif_content)
print(f"抽出されたタイトル: {result}")

# メタデータを詳しく確認
lines = kif_content.split('\n')
print("\n検出されたメタデータ:")
for line in lines[:20]:  # 最初の20行
    line = line.strip()
    if line.startswith(('作品名：', '作者：', '発表誌：', '手数：', '受賞：')):
        print(f"  {line}")
