#!/usr/bin/env python3
"""WebSocket接続テスト"""

import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://127.0.0.1:8787/ws"
    
    try:
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✓ WebSocket connection established!")
            
            # usiコマンドを送信
            print("Sending 'usi' command...")
            await websocket.send("usi")
            
            # 応答を受信
            for i in range(10):  # 最大10回まで応答を受信
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    print(f"← {response}")
                    if "usiok" in response:
                        break
                except asyncio.TimeoutError:
                    print("Timeout waiting for response")
                    break
            
            # isreadyコマンドを送信
            print("\nSending 'isready' command...")
            await websocket.send("isready")
            
            # readyokを待機
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"← {response}")
            except asyncio.TimeoutError:
                print("Timeout waiting for readyok")
                
            print("✓ WebSocket test completed successfully!")
            
    except Exception as e:
        print(f"✗ WebSocket connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
