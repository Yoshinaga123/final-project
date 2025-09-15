import json

def test_candidate_moves_empty_payload(client):
    # Empty JSON payload should be accepted and not error
    res = client.post('/shogi/api/candidate-moves',
                      data=json.dumps({}),
                      content_type='application/json')
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, dict)
    assert 'candidate_moves' in data
    assert data.get('success') in (True, False)  # route may return False with emergency moves but still 200
    # candidate_moves should be a list with items that at least have 'usi'
    assert isinstance(data['candidate_moves'], list)
    if data['candidate_moves']:
        assert 'usi' in data['candidate_moves'][0]
