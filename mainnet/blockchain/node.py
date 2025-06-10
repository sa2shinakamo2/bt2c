import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException
from prometheus_client import start_http_server
from prometheus_fastapi_instrumentator import Instrumentator

class SeedNode:
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.load_config()
        self.setup_metrics()
        self.app = FastAPI(title="BT2C Validator Node")
        self.setup_routes()
        self.setup_monitoring()
        self.start_time = time.time()
        self.balance = self.config['validator']['stake_amount'] + (100.0 if self.is_first_validator() else 1.0)  # Developer node reward + early validator reward

    def is_first_validator(self) -> bool:
        # Check if this is the first validator on mainnet
        # In a real implementation, this would check the blockchain
        return self.config['node_id'] == 'validator1' and self.config['network']['name'] == 'mainnet'

    def load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            
            # Validate required configuration
            required_fields = [
                'node_id',
                'network.name',
                'network.api_addr',
                'network.p2p_addr',
                'validator.name',
                'validator.stake_amount',
                'validator.wallet_address'
            ]
            for field in required_fields:
                parts = field.split('.')
                config = self.config
                for part in parts:
                    if part not in config:
                        raise ValueError(f"Missing required field: {field}")
                    config = config[part]
                    
        except Exception as e:
            print(f"Error loading config file: {e}")
            sys.exit(1)

    def setup_metrics(self):
        if self.config['monitoring']['prometheus_enabled']:
            prometheus_port = self.config['monitoring']['prometheus_port']
            try:
                start_http_server(prometheus_port)
            except Exception as e:
                print(f"Error starting Prometheus server: {e}")

    def setup_monitoring(self):
        if self.config['monitoring']['prometheus_enabled']:
            Instrumentator().instrument(self.app).expose(self.app)

    def setup_routes(self):
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "timestamp": self.current_time(),
                "node_id": self.config['node_id'],
                "network": self.config['network']['name'],
                "environment": "development" if "0.0.0.0" in self.config['network']['api_addr'] else "production",
                "stake_amount": self.config['validator']['stake_amount']
            }

        @self.app.get("/metrics")
        async def metrics():
            if not self.config['monitoring']['prometheus_enabled']:
                raise HTTPException(status_code=404, detail="Metrics not enabled")
            return {"metrics": "enabled"}

        @self.app.get("/status")
        async def status():
            return {
                "node_id": self.config['node_id'],
                "network": self.config['network']['name'],
                "environment": "development" if "0.0.0.0" in self.config['network']['api_addr'] else "production",
                "validator": {
                    "name": self.config['validator']['name'],
                    "stake_amount": self.config['validator']['stake_amount']
                },
                "uptime": self.get_uptime(),
                "p2p": {
                    "listen_addr": self.config['network']['p2p_addr'],
                    "external_addr": self.config['network']['external_addr']
                }
            }

        @self.app.get("/balance")
        async def get_balance():
            # Note: This is development mode with simulated rewards
            is_dev = "0.0.0.0" in self.config['network']['api_addr']
            return {
                "address": self.config['validator']['wallet_address'],
                "balance": self.balance,
                "staked": self.config['validator']['stake_amount'],
                "rewards": {
                    "early_validator": 1.0,
                    "developer_node": 100.0 if self.is_first_validator() and not is_dev else 0.0
                },
                "environment": "development" if is_dev else "production",
                "note": "Development mode - rewards are simulated" if is_dev else None,
                "timestamp": self.current_time()
            }

    def current_time(self) -> str:
        return datetime.utcnow().isoformat()

    def get_uptime(self) -> str:
        uptime = time.time() - self.start_time
        return f"{uptime:.2f} seconds"

    def run(self):
        try:
            # Get API host and port from config
            api_host, api_port = self.config['network']['api_addr'].split(':')
            api_port = int(api_port)

            # Get P2P host and port from config (for future use)
            p2p_host, p2p_port = self.config['network']['p2p_addr'].split(':')
            p2p_port = int(p2p_port)

            # Log configuration
            print(f"Starting BT2C Validator Node")
            print(f"Node ID: {self.config['node_id']}")
            print(f"Network: {self.config['network']['name']}")
            print(f"API server: {api_host}:{api_port}")
            print(f"P2P server: {p2p_host}:{p2p_port} (future use)")
            print(f"Stake amount: {self.config['validator']['stake_amount']} BT2C")
            print(f"Balance: {self.balance} BT2C")

            # Start API server
            uvicorn.run(
                app=self.app,
                host=api_host,
                port=api_port,
                log_level="info",
                access_log=True
            )
        except Exception as e:
            print(f"Error running validator node: {e}")
            sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m blockchain.node <config_file>")
        sys.exit(1)

    config_file = sys.argv[1]
    if not os.path.exists(config_file):
        print(f"Config file not found: {config_file}")
        sys.exit(1)

    node = SeedNode(config_file)
    node.run()
