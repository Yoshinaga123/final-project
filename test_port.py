#!/usr/bin/env python3
import socket

def test_port(host, port):
    """Test if a port is open"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            result = s.connect_ex((host, port))
            return result == 0
    except Exception as e:
        print(f"Error testing port {port}: {e}")
        return False

if __name__ == "__main__":
    host = "127.0.0.1"
    ports_to_test = [8787, 8803, 8804, 8805]
    
    print("Testing port connectivity:")
    for port in ports_to_test:
        status = "OPEN" if test_port(host, port) else "CLOSED"
        print(f"  {host}:{port} - {status}")
    
    # Test reading last_port.txt
    try:
        with open('logs/usi-bridge/last_port.txt', 'r') as f:
            content = f.read().strip()
            print(f"\nlast_port.txt content: '{content}'")
    except Exception as e:
        print(f"\nError reading last_port.txt: {e}")
