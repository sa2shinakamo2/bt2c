#!/usr/bin/env python3

import socket
import threading
import json
import time
import os
import sys
from datetime import datetime
import argparse

# Configuration
HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 8333       # BT2C port
MAX_CONNECTIONS = 100
PEER_LIST = []

def log_message(message):
    """Log a message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    sys.stdout.flush()

def handle_client(client_socket, address):
    """Handle client connection"""
    log_message(f"New connection from {address[0]}:{address[1]}")
    
    try:
        # Send peer list to new client
        peer_data = json.dumps({"peers": PEER_LIST})
        client_socket.send(peer_data.encode())
        
        # Add this client to peer list if not already present
        peer_info = {"ip": address[0], "port": address[1], "last_seen": time.time()}
        if peer_info not in PEER_LIST:
            PEER_LIST.append(peer_info)
            log_message(f"Added {address[0]}:{address[1]} to peer list")
        
        # Keep connection open for a while to receive any messages
        client_socket.settimeout(30)
        data = client_socket.recv(1024)
        if data:
            try:
                message = json.loads(data.decode())
                log_message(f"Received message from {address[0]}:{address[1]}: {message}")
                
                # Handle any specific message types here
                if "get_peers" in message:
                    peer_data = json.dumps({"peers": PEER_LIST})
                    client_socket.send(peer_data.encode())
            except json.JSONDecodeError:
                log_message(f"Received invalid JSON from {address[0]}:{address[1]}")
    
    except Exception as e:
        log_message(f"Error handling client {address[0]}:{address[1]}: {str(e)}")
    
    finally:
        client_socket.close()

def clean_peer_list():
    """Remove peers that haven't been seen in a while"""
    global PEER_LIST
    current_time = time.time()
    PEER_LIST = [peer for peer in PEER_LIST if (current_time - peer["last_seen"]) < 3600]  # 1 hour timeout

def main():
    """Main seed node function"""
    parser = argparse.ArgumentParser(description='BT2C Seed Node')
    parser.add_argument('--port', type=int, default=8333, help='Port to listen on')
    args = parser.parse_args()
    
    global PORT
    PORT = args.port
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((HOST, PORT))
        server.listen(5)
        log_message(f"BT2C Seed Node listening on {HOST}:{PORT}")
        
        # Start a thread to periodically clean the peer list
        def clean_peers_periodically():
            while True:
                time.sleep(300)  # Clean every 5 minutes
                clean_peer_list()
                log_message(f"Cleaned peer list. Current peers: {len(PEER_LIST)}")
        
        cleaner_thread = threading.Thread(target=clean_peers_periodically)
        cleaner_thread.daemon = True
        cleaner_thread.start()
        
        # Main loop to accept connections
        while True:
            client_sock, address = server.accept()
            client_handler = threading.Thread(target=handle_client, args=(client_sock, address))
            client_handler.daemon = True
            client_handler.start()
            
    except KeyboardInterrupt:
        log_message("Shutting down seed node...")
        server.close()
        sys.exit(0)
    except Exception as e:
        log_message(f"Error: {str(e)}")
        server.close()
        sys.exit(1)

if __name__ == "__main__":
    main()
