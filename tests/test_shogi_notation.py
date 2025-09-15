import json


def post_candidates(client, moves=None, current_player='b'):
    payload = {
        'position': 'startpos',
        'moves': moves or [],
        'current_player': current_player,
    }
    return client.post('/shogi/api/candidate-moves',
                       data=json.dumps(payload),
                       content_type='application/json')


def test_notation_pawn_from_startpos(client):
    # No prior moves; expect first candidate notation contains 歩 (not ？)
    res = post_candidates(client)
    assert res.status_code == 200
    data = res.get_json()
    assert data and 'candidate_moves' in data
    cms = data['candidate_moves']
    assert isinstance(cms, list)
    if cms:
        n = cms[0].get('notation', '')
        assert '？' not in n
        # Either classic opening pawn like ７六歩 or other piece; ensure kanji is known
        known = ['歩', '香', '桂', '銀', '金', '角', '飛', '玉', 'と', '成香', '成桂', '成銀', '馬', '竜']
        assert any(k in n for k in known)


def test_notation_drop_syntax(client):
    # Craft a position where a drop is possible is complex; here we only verify formatter for drop USI
    from apps.shogi.candidates import usi_to_notation_simple
    n = usi_to_notation_simple('P*7f', 'b')
    assert n.endswith('歩打')