
#!/usr/bin/env python3
import http.server
import socketserver
import json
import os
import sys
import time
import threading

validator_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
p2p_port = 26656 + validator_id
api_port = 8000 + validator_id
monitoring_port = 9090 + validator_id

# Load wallet and genesis data
wallet_path = f"/data/validator{validator_id}_wallet.json"
genesis_path = "/data/genesis.json"

with open(wallet_path, "r") as f:
    wallet_data = json.load(f)
    
with open(genesis_path, "r") as f:
    genesis_data = json.load(f)

# Mock blockchain state
blockchain_state = {
    "height": 1,
    "last_block_time": time.time(),
    "validator_address": wallet_data.get("address", f"bt2c_validator_{validator_id}"),
    "network": "testnet",
    "peers": [f"127.0.0.1:{26656 + i}" for i in range(1, 3) if i != validator_id],
    "genesis": genesis_data
}

# Simulate block production
def produce_blocks():
    while True:
        time.sleep(60)  # Block time from testnet config
        blockchain_state["height"] += 1
        blockchain_state["last_block_time"] = time.time()
        print(f"Produced block {blockchain_state['height']} at {blockchain_state['last_block_time']}")

# Start block production in a separate thread
block_thread = threading.Thread(target=produce_blocks, daemon=True)
block_thread.start()

# API handler
class TestnetAPIHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "active",
                "blockchain": blockchain_state
            }).encode())
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(f"BT2C Testnet Validator {validator_id} - Block Height: {blockchain_state['height']}".encode())

# Start API server
print(f"Starting BT2C test validator {validator_id}")
print(f"API running on port {api_port}")
print(f"P2P running on port {p2p_port}")
print(f"Monitoring running on port {monitoring_port}")

with socketserver.TCPServer(("", api_port), TestnetAPIHandler) as httpd:
    httpd.serve_forever()
