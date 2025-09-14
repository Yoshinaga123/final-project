# tools/ws_smoke.py
import asyncio, json, time, sys, pathlib, os
import websockets

# WS URL 自動解決: env USI_BRIDGE_PORT > logs/usi-bridge/last_port.txt > 8787
DEFAULT_HOST = os.environ.get('USI_BRIDGE_HOST', '127.0.0.1')
DEFAULT_PORT = None
if os.environ.get('USI_BRIDGE_PORT'):
    try:
        DEFAULT_PORT = int(os.environ['USI_BRIDGE_PORT'])
    except Exception:
        DEFAULT_PORT = None
if DEFAULT_PORT is None:
    try:
        # tools/ の1つ上がプロジェクトルート(final-project)
        root = pathlib.Path(__file__).resolve().parents[1]
        # ログの既定位置: <repo>/final-project/logs/usi-bridge/last_port.txt
        last = root / 'logs' / 'usi-bridge' / 'last_port.txt'
        if last.exists():
            DEFAULT_PORT = int(last.read_text(encoding='utf-8').strip())
    except Exception:
        DEFAULT_PORT = None
if DEFAULT_PORT is None:
    DEFAULT_PORT = 8787
WS = f"ws://{DEFAULT_HOST}:{DEFAULT_PORT}/ws"


def now():
    return time.strftime('%H:%M:%S')

async def wait_until(ws, pred, timeout=5.0, label=""):
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < timeout:
        msg = await ws.recv()
        data = json.loads(msg)
        # ログも残す
        print(f"[{now()}] {data.get('type')} {data.get('event','')} {data.get('phase','')}")
        if pred(data):
            return data
    raise TimeoutError(f"timeout waiting {label}")

async def run():
    # 1) 接続
    async with websockets.connect(WS, max_size=4*1024*1024) as ws:
        print("[*] connected", WS)

        # 2) READYOK まで（usiok→setoption→isready→readyok）
        st = await wait_until(ws, lambda d: d.get("type")=="status" and d.get("phase") in ("READYOK","ERROR","IN_GAME"), 10, "READYOK")
        if st.get("phase")=="ERROR":
            print("ERROR phase:", st); sys.exit(1)
        print("[OK] handshake READYOK/IN_GAME")

        # 3) 新規ゲーム→開始局面送信
        await ws.send(json.dumps({"type":"gameNew","position":"startpos","movetime":1500,"engineStarts":False}))
        await wait_until(ws, lambda d: d.get("type")=="game" and d.get("event")=="new", 3, "game new")
        print("[OK] gameNew")

        # 4) 人間の初手（7g7f）→ エンジン bestmove を受信
        await ws.send(json.dumps({"type":"humanMove","move":"7g7f","movetime":1200}))
        # 位置同期だけ先に来る
        await wait_until(ws, lambda d: d.get("type")=="game" and d.get("event")=="humanMove", 3, "humanMove ack")

        # bestmove応答を待つ（game typeのbestmoveイベント）
        bm = await wait_until(ws, lambda d: d.get("type")=="game" and d.get("event")=="bestmove", 8, "bestmove")
        bestmove_move = bm.get("lastMove", "")
        print("[OK] engine bestmove:", bestmove_move)

        # 5) 合法手ゲート（反則テスト）— 同筋二歩（python-shogiに依存し許容/拒否が変わる）
        await ws.send(json.dumps({"type":"humanMove","move":"P*5e"}))
        await ws.send(json.dumps({"type":"humanMove","move":"P*5e"}))
        try:
            err = await wait_until(ws, lambda d: d.get("type")=="error" and d.get("code") in ("ILLEGAL_MOVE","PARSE_ERROR"), 3, "illegal")
            print("[OK] illegal gate:", err.get("code"))
        except Exception:
            print("[WARN] illegal gate not triggered (engine/state dependent)")

        # 6) 成れない成り（例）：2i2h+
        await ws.send(json.dumps({"type":"humanMove","move":"2i2h+"}))
        try:
            err2 = await wait_until(ws, lambda d: d.get("type")=="error" and d.get("code") in ("ILLEGAL_MOVE","PARSE_ERROR"), 3, "promotion illegal")
            print("[OK] promotion gate:", err2.get("code"))
        except Exception:
            print("[WARN] promotion gate not triggered (state dependent)")

        # 7) info行の集計
        nps_max = 0; depth_max = 0
        t0 = time.perf_counter()
        while time.perf_counter()-t0 < 2.5:
            data = json.loads(await ws.recv())
            if data.get("type")=="parsed":
                nps_max = max(nps_max, data.get("nps",0))
                depth_max = max(depth_max, data.get("depth",0))
        print(f"[OK] info stats: nps_max={nps_max:,} depth_max={depth_max}")

        # 8) KIF 生成
        reqid = "kif1"
        await ws.send(json.dumps({"type":"generateKIF","requestId":reqid,"moves":[],"gameInfo":{"sente":"YaneuraOu NNUE","gote":"人間"}}))
        kif = await wait_until(ws, lambda d: d.get("type")=="kifGenerated" and d.get("requestId")==reqid, 5, "kif")
        path = pathlib.Path("out.kif"); path.write_text(kif["kifContent"], encoding="utf-8")
        print("[OK] KIF saved:", path.resolve())

    # 9) 再接続テスト
    async with websockets.connect(WS) as ws2:
        await ws2.send(json.dumps({"type":"getState"}))
        st2 = await wait_until(ws2, lambda d: d.get("type")=="game" and d.get("event")=="state", 3, "state")
        mvlen = len(st2["state"]["moves"])
        print("[OK] reconnect: moves =", mvlen)

if __name__ == '__main__':
    asyncio.run(run())
