#!/usr/bin/env python3

import os
import sys
import json
import subprocess
from pathlib import Path
import structlog
import ssl
import socket
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

logger = structlog.get_logger()

class SecurityAuditor:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.config_dir = self.project_root / "mainnet" / "config"
        self.results_dir = self.project_root / "security" / "audit_results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def check_ssl_configuration(self, host="localhost", port=8000):
        """Verify SSL/TLS configuration."""
        try:
            context = ssl.create_default_context()
            with socket.create_connection((host, port)) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    return {
                        "status": "success",
                        "cipher": ssock.cipher(),
                        "protocol": ssock.version(),
                        "cert_expiry": cert["notAfter"]
                    }
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def check_firewall_rules(self):
        """Verify firewall configuration."""
        required_ports = [8000, 26656, 9090, 3000]
        results = {}
        
        for port in required_ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                result = sock.connect_ex(('127.0.0.1', port))
                status = "open" if result == 0 else "closed"
                results[port] = status
            finally:
                sock.close()
        return results

    def check_consensus_parameters(self):
        """Verify consensus parameter configuration."""
        try:
            with open(self.config_dir / "validator.json") as f:
                config = json.load(f)
            
            checks = {
                "block_time": config["consensus"]["block_time"] >= 5,
                "max_validators": 10 <= config["consensus"]["max_validators"] <= 100,
                "minimum_stake": config["consensus"]["minimum_stake"] >= 10000
            }
            return checks
        except Exception as e:
            return {"error": str(e)}

    def check_genesis_configuration(self):
        """Verify genesis configuration."""
        try:
            with open(self.config_dir / "genesis.json") as f:
                genesis = json.load(f)
            
            checks = {
                "initial_supply": genesis.get("initial_supply") > 0,
                "validators": len(genesis.get("validators", [])) > 0,
                "stake_minimum": genesis.get("validator_stake_minimum") > 0
            }
            return checks
        except Exception as e:
            return {"error": str(e)}

    def check_monitoring_setup(self):
        """Verify monitoring configuration."""
        try:
            # Check Prometheus
            prom_response = requests.get("http://localhost:9090/-/healthy")
            prometheus_status = prom_response.status_code == 200

            # Check Grafana
            grafana_response = requests.get("http://localhost:3000/api/health")
            grafana_status = grafana_response.status_code == 200

            return {
                "prometheus": prometheus_status,
                "grafana": grafana_status
            }
        except Exception as e:
            return {"error": str(e)}

    def run_security_scan(self):
        """Run comprehensive security scan."""
        logger.info("starting_security_audit")
        
        results = {
            "ssl": self.check_ssl_configuration(),
            "firewall": self.check_firewall_rules(),
            "consensus": self.check_consensus_parameters(),
            "genesis": self.check_genesis_configuration(),
            "monitoring": self.check_monitoring_setup()
        }
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.results_dir / f"security_audit_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info("security_audit_completed", results_file=str(results_file))
        return results

    def generate_security_report(self, results):
        """Generate human-readable security report."""
        report = []
        report.append("BT2C Security Audit Report")
        report.append("=" * 30 + "\n")

        # SSL/TLS Configuration
        report.append("SSL/TLS Configuration:")
        if results["ssl"]["status"] == "success":
            report.append("✅ SSL/TLS properly configured")
            report.append(f"   Protocol: {results['ssl']['protocol']}")
            report.append(f"   Cipher: {results['ssl']['cipher']}")
        else:
            report.append("❌ SSL/TLS configuration issues detected")
            report.append(f"   Error: {results['ssl']['error']}")

        # Firewall Rules
        report.append("\nFirewall Configuration:")
        for port, status in results["firewall"].items():
            icon = "✅" if status == "open" else "❌"
            report.append(f"{icon} Port {port}: {status}")

        # Consensus Parameters
        report.append("\nConsensus Configuration:")
        for param, status in results["consensus"].items():
            icon = "✅" if status else "❌"
            report.append(f"{icon} {param}")

        # Genesis Configuration
        report.append("\nGenesis Configuration:")
        for param, status in results["genesis"].items():
            icon = "✅" if status else "❌"
            report.append(f"{icon} {param}")

        # Monitoring Setup
        report.append("\nMonitoring Configuration:")
        if "error" not in results["monitoring"]:
            for service, status in results["monitoring"].items():
                icon = "✅" if status else "❌"
                report.append(f"{icon} {service}")
        else:
            report.append(f"❌ Monitoring error: {results['monitoring']['error']}")

        return "\n".join(report)

def main():
    auditor = SecurityAuditor()
    results = auditor.run_security_scan()
    report = auditor.generate_security_report(results)
    
    print("\nSecurity Audit Report:")
    print(report)
    
    # Save report
    report_path = auditor.results_dir / "latest_audit_report.txt"
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"\nDetailed report saved to: {report_path}")

if __name__ == "__main__":
    main()
