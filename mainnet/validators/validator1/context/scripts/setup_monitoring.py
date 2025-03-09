#!/usr/bin/env python3

import os
import sys
import json
import subprocess
from pathlib import Path
import structlog
import requests
import time

logger = structlog.get_logger()

class MonitoringSetup:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.config_dir = self.project_root / "mainnet" / "config"
        self.monitoring_dir = self.project_root / "mainnet" / "monitoring"
        self.monitoring_dir.mkdir(parents=True, exist_ok=True)

    def setup_prometheus(self):
        """Set up Prometheus configuration."""
        logger.info("setting_up_prometheus")
        
        prometheus_config = {
            "global": {
                "scrape_interval": "15s",
                "evaluation_interval": "15s"
            },
            "rule_files": [
                "rules/*.yml"
            ],
            "scrape_configs": [
                {
                    "job_name": "bt2c_validators",
                    "static_configs": [
                        {
                            "targets": ["localhost:8000"]
                        }
                    ],
                    "metrics_path": "/metrics"
                }
            ],
            "alerting": {
                "alertmanagers": [
                    {
                        "static_configs": [
                            {
                                "targets": ["localhost:9093"]
                            }
                        ]
                    }
                ]
            }
        }
        
        # Save Prometheus config
        prom_dir = self.monitoring_dir / "prometheus"
        prom_dir.mkdir(exist_ok=True)
        
        with open(prom_dir / "prometheus.yml", 'w') as f:
            json.dump(prometheus_config, f, indent=2)
        
        # Create alert rules
        rules_dir = prom_dir / "rules"
        rules_dir.mkdir(exist_ok=True)
        
        alert_rules = {
            "groups": [
                {
                    "name": "bt2c_alerts",
                    "rules": [
                        {
                            "alert": "HighCPUUsage",
                            "expr": "process_cpu_seconds_total > 80",
                            "for": "5m",
                            "labels": {"severity": "warning"},
                            "annotations": {
                                "summary": "High CPU usage detected",
                                "description": "CPU usage is above 80% for 5 minutes"
                            }
                        },
                        {
                            "alert": "HighMemoryUsage",
                            "expr": "process_resident_memory_bytes > 1e9",
                            "for": "5m",
                            "labels": {"severity": "warning"},
                            "annotations": {
                                "summary": "High memory usage detected",
                                "description": "Memory usage is above 1GB for 5 minutes"
                            }
                        }
                    ]
                }
            ]
        }
        
        with open(rules_dir / "alerts.yml", 'w') as f:
            json.dump(alert_rules, f, indent=2)
        
        return {"prometheus_dir": str(prom_dir)}

    def setup_grafana(self):
        """Set up Grafana dashboards and datasources."""
        logger.info("setting_up_grafana")
        
        grafana_dir = self.monitoring_dir / "grafana"
        grafana_dir.mkdir(exist_ok=True)
        
        # Grafana datasource configuration
        datasource = {
            "apiVersion": 1,
            "datasources": [
                {
                    "name": "Prometheus",
                    "type": "prometheus",
                    "access": "proxy",
                    "url": "http://prometheus:9090",
                    "isDefault": True
                }
            ]
        }
        
        datasource_dir = grafana_dir / "provisioning" / "datasources"
        datasource_dir.mkdir(parents=True, exist_ok=True)
        
        with open(datasource_dir / "prometheus.yml", 'w') as f:
            json.dump(datasource, f, indent=2)
        
        # Grafana dashboard configuration
        dashboard = {
            "apiVersion": 1,
            "providers": [
                {
                    "name": "BT2C Dashboards",
                    "folder": "",
                    "type": "file",
                    "options": {
                        "path": "/etc/grafana/dashboards"
                    }
                }
            ]
        }
        
        dashboard_dir = grafana_dir / "provisioning" / "dashboards"
        dashboard_dir.mkdir(parents=True, exist_ok=True)
        
        with open(dashboard_dir / "dashboards.yml", 'w') as f:
            json.dump(dashboard, f, indent=2)
        
        # Create sample dashboard
        sample_dashboard = {
            "title": "BT2C Network Overview",
            "panels": [
                {
                    "title": "Active Validators",
                    "type": "gauge",
                    "datasource": "Prometheus",
                    "targets": [
                        {
                            "expr": "bt2c_active_validators"
                        }
                    ]
                },
                {
                    "title": "Transaction Rate",
                    "type": "graph",
                    "datasource": "Prometheus",
                    "targets": [
                        {
                            "expr": "rate(bt2c_transactions_total[5m])"
                        }
                    ]
                }
            ]
        }
        
        dashboards_dir = grafana_dir / "dashboards"
        dashboards_dir.mkdir(exist_ok=True)
        
        with open(dashboards_dir / "network_overview.json", 'w') as f:
            json.dump(sample_dashboard, f, indent=2)
        
        return {"grafana_dir": str(grafana_dir)}

    def setup_alertmanager(self):
        """Set up Alertmanager configuration."""
        logger.info("setting_up_alertmanager")
        
        alertmanager_dir = self.monitoring_dir / "alertmanager"
        alertmanager_dir.mkdir(exist_ok=True)
        
        config = {
            "global": {
                "resolve_timeout": "5m"
            },
            "route": {
                "group_by": ["alertname"],
                "group_wait": "30s",
                "group_interval": "5m",
                "repeat_interval": "12h",
                "receiver": "email-notifications"
            },
            "receivers": [
                {
                    "name": "email-notifications",
                    "email_configs": [
                        {
                            "to": "alerts@bt2c.network",
                            "from": "alertmanager@bt2c.network",
                            "smarthost": "smtp.example.com:587",
                            "auth_username": "alertmanager@bt2c.network",
                            "auth_identity": "alertmanager@bt2c.network",
                            "auth_password": "secure_password"
                        }
                    ]
                }
            ]
        }
        
        with open(alertmanager_dir / "alertmanager.yml", 'w') as f:
            json.dump(config, f, indent=2)
        
        return {"alertmanager_dir": str(alertmanager_dir)}

    def generate_docker_compose(self):
        """Generate docker-compose file for monitoring stack."""
        logger.info("generating_docker_compose")
        
        compose = {
            "version": "3.8",
            "services": {
                "prometheus": {
                    "image": "prom/prometheus:latest",
                    "volumes": [
                        "./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml",
                        "./prometheus/rules:/etc/prometheus/rules"
                    ],
                    "ports": ["9090:9090"],
                    "command": [
                        "--config.file=/etc/prometheus/prometheus.yml",
                        "--storage.tsdb.retention.time=15d"
                    ]
                },
                "grafana": {
                    "image": "grafana/grafana:latest",
                    "volumes": [
                        "./grafana/provisioning:/etc/grafana/provisioning",
                        "./grafana/dashboards:/etc/grafana/dashboards"
                    ],
                    "ports": ["3000:3000"],
                    "environment": [
                        "GF_SECURITY_ADMIN_PASSWORD=secure_password"
                    ]
                },
                "alertmanager": {
                    "image": "prom/alertmanager:latest",
                    "volumes": [
                        "./alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml"
                    ],
                    "ports": ["9093:9093"],
                    "command": [
                        "--config.file=/etc/alertmanager/alertmanager.yml"
                    ]
                }
            }
        }
        
        with open(self.monitoring_dir / "docker-compose.yml", 'w') as f:
            json.dump(compose, f, indent=2)
        
        return {"compose_file": str(self.monitoring_dir / "docker-compose.yml")}

    def setup_monitoring(self):
        """Complete monitoring setup process."""
        try:
            logger.info("starting_monitoring_setup")
            
            # Run all setup steps
            prometheus_config = self.setup_prometheus()
            grafana_config = self.setup_grafana()
            alertmanager_config = self.setup_alertmanager()
            docker_config = self.generate_docker_compose()
            
            logger.info("monitoring_setup_completed",
                       monitoring_dir=str(self.monitoring_dir))
            
            print("\n✅ Monitoring setup completed!")
            print(f"\nConfiguration directory: {self.monitoring_dir}")
            print("\nNext steps:")
            print("1. Review the configuration files")
            print("2. Update email settings in alertmanager.yml")
            print("3. Start the monitoring stack:")
            print(f"   cd {self.monitoring_dir} && docker-compose up -d")
            print("4. Access the services:")
            print("   - Prometheus: http://localhost:9090")
            print("   - Grafana: http://localhost:3000")
            print("   - Alertmanager: http://localhost:9093")
            
        except Exception as e:
            logger.error("monitoring_setup_failed", error=str(e))
            raise

def main():
    setup = MonitoringSetup()
    setup.setup_monitoring()

if __name__ == "__main__":
    main()
