print("WebSocket test starting...")

import socket

# ポート8787でリスニングしているか確認
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        result = s.connect_ex(('127.0.0.1', 8787))
        if result == 0:
            print("✓ Port 8787 is listening")
        else:
            print(f"✗ Port 8787 connection failed: {result}")
except Exception as e:
    print(f"✗ Socket test failed: {e}")

print("Test completed.")
