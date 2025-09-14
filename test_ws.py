import asyncio
import websockets
import json

async def test_connection():
    try:
        print("Testing WebSocket connection to ws://127.0.0.1:8804/ws")
        async with websockets.connect("ws://127.0.0.1:8804/ws") as ws:
            print("✓ Connected successfully!")
            
            # Send a simple test message
            test_msg = {"type": "takeControl"}
            await ws.send(json.dumps(test_msg))
            print(f"✓ Sent: {test_msg}")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(response)
                print(f"✓ Received: {data}")
                
                # Test game start
                game_msg = {"type": "gameNew", "position": "startpos", "movetime": 2000}
                await ws.send(json.dumps(game_msg))
                print(f"✓ Sent gameNew: {game_msg}")
                
                # Wait for game response
                game_response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                game_data = json.loads(game_response)
                print(f"✓ Game response: {game_data}")
                
                # Test a human move
                move_msg = {"type": "humanMove", "move": "7g7f", "movetime_ms": 2000}
                await ws.send(json.dumps(move_msg))
                print(f"✓ Sent humanMove: {move_msg}")
                
                # Wait for multiple responses (engine activity)
                for i in range(5):
                    try:
                        resp = await asyncio.wait_for(ws.recv(), timeout=3.0)
                        resp_data = json.loads(resp)
                        print(f"✓ Response {i+1}: {resp_data}")
                        
                        # Check for bestmove
                        if resp_data.get("type") == "game" and resp_data.get("event") == "bestmove":
                            print(f"🎯 BESTMOVE DETECTED: {resp_data.get('lastMove')}")
                            break
                    except asyncio.TimeoutError:
                        print(f"  Timeout waiting for response {i+1}")
                        break
                        
            except asyncio.TimeoutError:
                print("✗ Timeout waiting for response")
                
    except Exception as e:
        print(f"✗ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
