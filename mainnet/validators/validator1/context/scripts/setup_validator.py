#!/usr/bin/env python3

import os
import sys
import json
import subprocess
from pathlib import Path
import structlog
import docker
from datetime import datetime

logger = structlog.get_logger()

class ValidatorSetup:
    def __init__(self, node_id):
        self.node_id = node_id
        self.project_root = Path(__file__).parent.parent
        self.config_dir = self.project_root / "mainnet" / "config"
        self.validator_dir = self.project_root / "mainnet" / "validators" / node_id
        self.validator_dir.mkdir(parents=True, exist_ok=True)
        self.docker_client = docker.from_env()

    def setup_validator_config(self):
        """Set up validator-specific configuration."""
        logger.info("setting_up_validator_config", node_id=self.node_id)
        
        # Load base validator config
        with open(self.config_dir / "validator.json") as f:
            config = json.load(f)
        
        # Customize for this validator
        config["node"] = {
            "id": self.node_id,
            "moniker": f"bt2c-validator-{self.node_id}",
            "data_dir": str(self.validator_dir / "data"),
            "log_level": "info"
        }
        
        # Save validator-specific config
        config_path = self.validator_dir / "config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return config

    def setup_security(self):
        """Set up security configuration for the validator."""
        logger.info("setting_up_security", node_id=self.node_id)
        
        # Load security config
        with open(self.config_dir / "security.json") as f:
            security = json.load(f)
        
        # Generate SSL certificates
        cert_dir = self.validator_dir / "certs"
        cert_dir.mkdir(exist_ok=True)
        
        # In production, you would use proper CA-signed certificates
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", str(cert_dir / "node.key"),
            "-out", str(cert_dir / "node.crt"),
            "-days", "365", "-nodes",
            "-subj", f"/CN={self.node_id}.bt2c.network"
        ])
        
        return {"cert_dir": str(cert_dir)}

    def setup_monitoring(self):
        """Set up monitoring for the validator."""
        logger.info("setting_up_monitoring", node_id=self.node_id)
        
        # Load monitoring config
        with open(self.config_dir / "monitoring.json") as f:
            monitoring = json.load(f)
        
        # Create monitoring directories
        metrics_dir = self.validator_dir / "metrics"
        metrics_dir.mkdir(exist_ok=True)
        
        # Configure Prometheus
        prometheus_config = {
            "global": {
                "scrape_interval": "15s",
                "evaluation_interval": "15s"
            },
            "scrape_configs": [
                {
                    "job_name": f"validator_{self.node_id}",
                    "static_configs": [
                        {
                            "targets": ["localhost:9090"]
                        }
                    ]
                }
            ]
        }
        
        prometheus_path = metrics_dir / "prometheus.yml"
        with open(prometheus_path, 'w') as f:
            json.dump(prometheus_config, f, indent=2)
        
        return {"metrics_dir": str(metrics_dir)}

    def setup_docker_compose(self):
        """Generate docker-compose configuration for the validator."""
        logger.info("setting_up_docker", node_id=self.node_id)
        
        compose_config = {
            "version": "3.8",
            "services": {
                "validator": {
                    "build": {
                        "context": ".",
                        "dockerfile": "Dockerfile"
                    },
                    "container_name": f"bt2c-validator-{self.node_id}",
                    "volumes": [
                        f"{self.validator_dir}/data:/data",
                        f"{self.validator_dir}/certs:/certs",
                        f"{self.validator_dir}/config.json:/config/validator.json"
                    ],
                    "ports": [
                        "8000:8000",
                        "26656:26656"
                    ],
                    "environment": [
                        "NODE_ID=${self.node_id}",
                        "NETWORK=mainnet"
                    ],
                    "restart": "unless-stopped"
                },
                "prometheus": {
                    "image": "prom/prometheus:latest",
                    "container_name": f"bt2c-prometheus-{self.node_id}",
                    "volumes": [
                        f"{self.validator_dir}/metrics/prometheus.yml:/etc/prometheus/prometheus.yml"
                    ],
                    "ports": [
                        "9090:9090"
                    ]
                },
                "grafana": {
                    "image": "grafana/grafana:latest",
                    "container_name": f"bt2c-grafana-{self.node_id}",
                    "volumes": [
                        f"{self.validator_dir}/metrics/grafana:/var/lib/grafana"
                    ],
                    "ports": [
                        "3000:3000"
                    ],
                    "environment": [
                        "GF_SECURITY_ADMIN_PASSWORD=secure_password"
                    ]
                }
            }
        }
        
        compose_path = self.validator_dir / "docker-compose.yml"
        with open(compose_path, 'w') as f:
            json.dump(compose_config, f, indent=2)
        
        return {"compose_file": str(compose_path)}

    def setup_validator(self):
        """Complete validator setup process."""
        try:
            logger.info("starting_validator_setup", node_id=self.node_id)
            
            # Run all setup steps
            validator_config = self.setup_validator_config()
            security_config = self.setup_security()
            monitoring_config = self.setup_monitoring()
            docker_config = self.setup_docker_compose()
            
            logger.info("validator_setup_completed", 
                       node_id=self.node_id,
                       config_dir=str(self.validator_dir))
            
            print(f"\n✅ Validator {self.node_id} setup completed!")
            print(f"\nConfiguration directory: {self.validator_dir}")
            print("\nNext steps:")
            print("1. Review the configuration files")
            print("2. Start the validator using:")
            print(f"   cd {self.validator_dir} && docker-compose up -d")
            print("3. Monitor the validator status:")
            print("   - Metrics: http://localhost:9090")
            print("   - Dashboard: http://localhost:3000")
            
        except Exception as e:
            logger.error("validator_setup_failed", 
                        node_id=self.node_id,
                        error=str(e))
            raise

def main():
    if len(sys.argv) != 2:
        print("Usage: setup_validator.py <node_id>")
        sys.exit(1)
    
    node_id = sys.argv[1]
    setup = ValidatorSetup(node_id)
    setup.setup_validator()

if __name__ == "__main__":
    main()
