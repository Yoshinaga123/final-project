def test_engine_shogi_and_health(client):
    r = client.get('/engine/shogi')
    assert r.status_code == 200
    # テンプレ内に ws_url が埋め込まれていることをざっくり確認
    txt = r.get_data(as_text=True)
    assert 'ws_url' in txt and 'movetime_ms' in txt

    h = client.get('/engine/health')
    assert h.status_code in (200, 503)
    if h.status_code == 200:
        assert h.is_json
        data = h.get_json()
        assert isinstance(data.get('ok', None), bool)
