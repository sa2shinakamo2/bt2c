"""
BT2C Monitoring System

This module provides monitoring capabilities for the BT2C blockchain.
"""

import os
import time
import json
import psutil
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects metrics for the BT2C blockchain"""
    
    def __init__(self, metrics_dir: str):
        """
        Initialize metrics collector
        
        Args:
            metrics_dir: Directory to store metrics
        """
        self.metrics_dir = metrics_dir
        os.makedirs(metrics_dir, exist_ok=True)
        
        # Initialize metrics
        self.metrics = {
            "requests": defaultdict(int),
            "responses": defaultdict(lambda: defaultdict(int)),
            "response_times": defaultdict(list),
            "rate_limits": defaultdict(int),
            "circuit_breaks": defaultdict(int),
            "resource_usage": [],
            "security_events": [],
        }
        
        # Initialize lock
        self.lock = threading.RLock()
        
        # Start resource monitoring thread
        self.stop_monitoring = False
        self.monitoring_thread = threading.Thread(
            target=self._monitor_resources,
            daemon=True
        )
        self.monitoring_thread.start()
    
    def track_request(self, endpoint: str, client_ip: str):
        """
        Track a request
        
        Args:
            endpoint: API endpoint
            client_ip: Client IP address
        """
        with self.lock:
            self.metrics["requests"][endpoint] += 1
    
    def track_response(self, endpoint: str, status_code: int, response_time: float):
        """
        Track a response
        
        Args:
            endpoint: API endpoint
            status_code: HTTP status code
            response_time: Response time in seconds
        """
        with self.lock:
            self.metrics["responses"][endpoint][status_code] += 1
            self.metrics["response_times"][endpoint].append(response_time)
    
    def track_rate_limit(self, client_ip: str, endpoint: str):
        """
        Track a rate limit event
        
        Args:
            client_ip: Client IP address
            endpoint: API endpoint
        """
        with self.lock:
            self.metrics["rate_limits"][endpoint] += 1
    
    def track_circuit_break(self, endpoint: str):
        """
        Track a circuit break event
        
        Args:
            endpoint: API endpoint
        """
        with self.lock:
            self.metrics["circuit_breaks"][endpoint] += 1
    
    def track_security_event(self, event_type: str, details: Dict[str, Any]):
        """
        Track a security event
        
        Args:
            event_type: Type of security event
            details: Event details
        """
        with self.lock:
            self.metrics["security_events"].append({
                "timestamp": datetime.now().isoformat(),
                "type": event_type,
                "details": details
            })
    
    def _monitor_resources(self):
        """Monitor system resources"""
        while not self.stop_monitoring:
            try:
                # Get CPU and memory usage
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil.virtual_memory().percent
                
                # Get disk usage
                disk_usage = psutil.disk_usage('/').percent
                
                # Get network stats
                net_io = psutil.net_io_counters()
                
                # Record metrics
                with self.lock:
                    self.metrics["resource_usage"].append({
                        "timestamp": datetime.now().isoformat(),
                        "cpu_percent": cpu_percent,
                        "memory_percent": memory_percent,
                        "disk_percent": disk_usage,
                        "net_bytes_sent": net_io.bytes_sent,
                        "net_bytes_recv": net_io.bytes_recv
                    })
                
                # Sleep for 5 seconds
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error monitoring resources: {e}")
                time.sleep(10)  # Sleep longer on error
    
    def save_metrics(self):
        """Save metrics to disk"""
        with self.lock:
            # Create a copy of metrics
            metrics_copy = {
                "requests": dict(self.metrics["requests"]),
                "responses": {k: dict(v) for k, v in self.metrics["responses"].items()},
                "response_times": {k: list(v) for k, v in self.metrics["response_times"].items()},
                "rate_limits": dict(self.metrics["rate_limits"]),
                "circuit_breaks": dict(self.metrics["circuit_breaks"]),
                "resource_usage": list(self.metrics["resource_usage"][-100:]),  # Last 100 entries
                "security_events": list(self.metrics["security_events"]),
                "timestamp": datetime.now().isoformat()
            }
        
        # Save to file
        date_str = datetime.now().strftime("%Y-%m-%d")
        file_path = os.path.join(self.metrics_dir, f"metrics_{date_str}.json")
        
        try:
            with open(file_path, 'w') as f:
                json.dump(metrics_copy, f, indent=2)
            logger.info("saved_metrics", file=file_path)
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics
        
        Returns:
            Current metrics
        """
        with self.lock:
            # Create a summary of metrics
            summary = {
                "requests": {
                    "total": sum(self.metrics["requests"].values()),
                    "by_endpoint": dict(self.metrics["requests"])
                },
                "responses": {
                    "total": sum(sum(v.values()) for v in self.metrics["responses"].values()),
                    "by_status": defaultdict(int)
                },
                "response_times": {
                    "average": sum(sum(times) for times in self.metrics["response_times"].values()) / 
                              max(1, sum(len(times) for times in self.metrics["response_times"].values())),
                    "by_endpoint": {k: sum(v) / max(1, len(v)) for k, v in self.metrics["response_times"].items()}
                },
                "rate_limits": {
                    "total": sum(self.metrics["rate_limits"].values()),
                    "by_endpoint": dict(self.metrics["rate_limits"])
                },
                "circuit_breaks": {
                    "total": sum(self.metrics["circuit_breaks"].values()),
                    "by_endpoint": dict(self.metrics["circuit_breaks"])
                },
                "resource_usage": {
                    "current": self.metrics["resource_usage"][-1] if self.metrics["resource_usage"] else {},
                    "average": {
                        "cpu_percent": sum(entry["cpu_percent"] for entry in self.metrics["resource_usage"]) / 
                                      max(1, len(self.metrics["resource_usage"])),
                        "memory_percent": sum(entry["memory_percent"] for entry in self.metrics["resource_usage"]) / 
                                         max(1, len(self.metrics["resource_usage"])),
                        "disk_percent": sum(entry["disk_percent"] for entry in self.metrics["resource_usage"]) / 
                                       max(1, len(self.metrics["resource_usage"]))
                    }
                },
                "security_events": {
                    "total": len(self.metrics["security_events"]),
                    "recent": self.metrics["security_events"][-10:] if self.metrics["security_events"] else []
                }
            }
            
            # Calculate response status counts
            for endpoint_responses in self.metrics["responses"].values():
                for status, count in endpoint_responses.items():
                    summary["responses"]["by_status"][status] += count
            
            return summary
    
    def stop(self):
        """Stop the metrics collector"""
        self.stop_monitoring = True
        if self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=1)
        self.save_metrics()


class MetricsVisualizer:
    """Visualizes metrics for the BT2C blockchain"""
    
    def __init__(self, metrics_collector: MetricsCollector, output_dir: str):
        """
        Initialize metrics visualizer
        
        Args:
            metrics_collector: Metrics collector
            output_dir: Directory to store visualizations
        """
        self.metrics_collector = metrics_collector
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_report(self) -> str:
        """
        Generate a metrics report
        
        Returns:
            Path to the generated report
        """
        # Get metrics
        metrics = self.metrics_collector.get_metrics()
        
        # Create report directory
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_dir = os.path.join(self.output_dir, f"report_{timestamp}")
        os.makedirs(report_dir, exist_ok=True)
        
        # Generate visualizations
        self._generate_request_chart(metrics, report_dir)
        self._generate_response_time_chart(metrics, report_dir)
        self._generate_resource_usage_chart(metrics, report_dir)
        self._generate_security_events_chart(metrics, report_dir)
        
        # Generate HTML report
        report_path = os.path.join(report_dir, "report.html")
        self._generate_html_report(metrics, report_dir, report_path)
        
        return report_path
    
    def _generate_request_chart(self, metrics: Dict[str, Any], report_dir: str):
        """
        Generate request chart
        
        Args:
            metrics: Metrics data
            report_dir: Report directory
        """
        plt.figure(figsize=(10, 6))
        
        # Get top 10 endpoints by request count
        top_endpoints = sorted(
            metrics["requests"]["by_endpoint"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        endpoints = [endpoint for endpoint, _ in top_endpoints]
        counts = [count for _, count in top_endpoints]
        
        plt.bar(endpoints, counts)
        plt.title("Top 10 Endpoints by Request Count")
        plt.xlabel("Endpoint")
        plt.ylabel("Request Count")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        
        # Save chart
        plt.savefig(os.path.join(report_dir, "requests.png"))
        plt.close()
    
    def _generate_response_time_chart(self, metrics: Dict[str, Any], report_dir: str):
        """
        Generate response time chart
        
        Args:
            metrics: Metrics data
            report_dir: Report directory
        """
        plt.figure(figsize=(10, 6))
        
        # Get top 10 endpoints by response time
        top_endpoints = sorted(
            metrics["response_times"]["by_endpoint"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        endpoints = [endpoint for endpoint, _ in top_endpoints]
        times = [time for _, time in top_endpoints]
        
        plt.bar(endpoints, times)
        plt.title("Top 10 Endpoints by Average Response Time")
        plt.xlabel("Endpoint")
        plt.ylabel("Response Time (seconds)")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        
        # Save chart
        plt.savefig(os.path.join(report_dir, "response_times.png"))
        plt.close()
    
    def _generate_resource_usage_chart(self, metrics: Dict[str, Any], report_dir: str):
        """
        Generate resource usage chart
        
        Args:
            metrics: Metrics data
            report_dir: Report directory
        """
        plt.figure(figsize=(10, 6))
        
        # Get resource usage data
        resource_usage = self.metrics_collector.metrics["resource_usage"]
        
        if not resource_usage:
            return
        
        # Extract timestamps and values
        timestamps = [datetime.fromisoformat(entry["timestamp"]) for entry in resource_usage]
        cpu_values = [entry["cpu_percent"] for entry in resource_usage]
        memory_values = [entry["memory_percent"] for entry in resource_usage]
        disk_values = [entry["disk_percent"] for entry in resource_usage]
        
        # Plot resource usage
        plt.plot(timestamps, cpu_values, label="CPU")
        plt.plot(timestamps, memory_values, label="Memory")
        plt.plot(timestamps, disk_values, label="Disk")
        
        plt.title("Resource Usage Over Time")
        plt.xlabel("Time")
        plt.ylabel("Usage (%)")
        plt.legend()
        plt.grid(True)
        
        # Format x-axis
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        plt.gcf().autofmt_xdate()
        
        plt.tight_layout()
        
        # Save chart
        plt.savefig(os.path.join(report_dir, "resource_usage.png"))
        plt.close()
    
    def _generate_security_events_chart(self, metrics: Dict[str, Any], report_dir: str):
        """
        Generate security events chart
        
        Args:
            metrics: Metrics data
            report_dir: Report directory
        """
        plt.figure(figsize=(10, 6))
        
        # Get security events data
        security_events = self.metrics_collector.metrics["security_events"]
        
        if not security_events:
            return
        
        # Count events by type
        event_types = defaultdict(int)
        for event in security_events:
            event_types[event["type"]] += 1
        
        # Plot security events
        types = list(event_types.keys())
        counts = list(event_types.values())
        
        plt.bar(types, counts)
        plt.title("Security Events by Type")
        plt.xlabel("Event Type")
        plt.ylabel("Count")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        
        # Save chart
        plt.savefig(os.path.join(report_dir, "security_events.png"))
        plt.close()
    
    def _generate_html_report(self, metrics: Dict[str, Any], report_dir: str, report_path: str):
        """
        Generate HTML report
        
        Args:
            metrics: Metrics data
            report_dir: Report directory
            report_path: Path to save the report
        """
        # Create HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>BT2C Monitoring Report</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    padding: 0;
                    color: #333;
                }}
                h1, h2, h3 {{
                    color: #0066cc;
                }}
                .section {{
                    margin-bottom: 30px;
                    border: 1px solid #ddd;
                    padding: 20px;
                    border-radius: 5px;
                }}
                .chart {{
                    margin: 20px 0;
                    text-align: center;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                th, td {{
                    padding: 8px;
                    border: 1px solid #ddd;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                }}
                .summary {{
                    font-weight: bold;
                    margin-bottom: 10px;
                }}
            </style>
        </head>
        <body>
            <h1>BT2C Monitoring Report</h1>
            <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            
            <div class="section">
                <h2>Request Statistics</h2>
                <p class="summary">Total Requests: {metrics["requests"]["total"]}</p>
                <div class="chart">
                    <img src="requests.png" alt="Request Chart">
                </div>
                <h3>Top Endpoints</h3>
                <table>
                    <tr>
                        <th>Endpoint</th>
                        <th>Count</th>
                    </tr>
        """
        
        # Add top endpoints
        for endpoint, count in sorted(
            metrics["requests"]["by_endpoint"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]:
            html_content += f"""
                    <tr>
                        <td>{endpoint}</td>
                        <td>{count}</td>
                    </tr>
            """
        
        html_content += f"""
                </table>
            </div>
            
            <div class="section">
                <h2>Response Statistics</h2>
                <p class="summary">Total Responses: {metrics["responses"]["total"]}</p>
                <h3>By Status Code</h3>
                <table>
                    <tr>
                        <th>Status Code</th>
                        <th>Count</th>
                    </tr>
        """
        
        # Add status codes
        for status, count in sorted(
            metrics["responses"]["by_status"].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            html_content += f"""
                    <tr>
                        <td>{status}</td>
                        <td>{count}</td>
                    </tr>
            """
        
        html_content += f"""
                </table>
                
                <h3>Response Times</h3>
                <p>Average Response Time: {metrics["response_times"]["average"]:.6f} seconds</p>
                <div class="chart">
                    <img src="response_times.png" alt="Response Time Chart">
                </div>
            </div>
            
            <div class="section">
                <h2>Resource Usage</h2>
                <div class="chart">
                    <img src="resource_usage.png" alt="Resource Usage Chart">
                </div>
                <h3>Current Usage</h3>
                <table>
                    <tr>
                        <th>Resource</th>
                        <th>Usage</th>
                    </tr>
        """
        
        # Add current resource usage
        current = metrics["resource_usage"]["current"]
        if current:
            html_content += f"""
                    <tr>
                        <td>CPU</td>
                        <td>{current.get("cpu_percent", 0):.2f}%</td>
                    </tr>
                    <tr>
                        <td>Memory</td>
                        <td>{current.get("memory_percent", 0):.2f}%</td>
                    </tr>
                    <tr>
                        <td>Disk</td>
                        <td>{current.get("disk_percent", 0):.2f}%</td>
                    </tr>
            """
        
        html_content += f"""
                </table>
            </div>
            
            <div class="section">
                <h2>Security Events</h2>
                <p class="summary">Total Security Events: {metrics["security_events"]["total"]}</p>
                <div class="chart">
                    <img src="security_events.png" alt="Security Events Chart">
                </div>
                <h3>Recent Events</h3>
                <table>
                    <tr>
                        <th>Timestamp</th>
                        <th>Type</th>
                        <th>Details</th>
                    </tr>
        """
        
        # Add recent security events
        for event in metrics["security_events"]["recent"]:
            html_content += f"""
                    <tr>
                        <td>{event["timestamp"]}</td>
                        <td>{event["type"]}</td>
                        <td>{json.dumps(event["details"])}</td>
                    </tr>
            """
        
        html_content += f"""
                </table>
            </div>
            
            <div class="section">
                <h2>DoS Protection</h2>
                <h3>Rate Limits</h3>
                <p class="summary">Total Rate Limits: {metrics["rate_limits"]["total"]}</p>
                <table>
                    <tr>
                        <th>Endpoint</th>
                        <th>Count</th>
                    </tr>
        """
        
        # Add rate limits
        for endpoint, count in sorted(
            metrics["rate_limits"]["by_endpoint"].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            html_content += f"""
                    <tr>
                        <td>{endpoint}</td>
                        <td>{count}</td>
                    </tr>
            """
        
        html_content += f"""
                </table>
                
                <h3>Circuit Breaks</h3>
                <p class="summary">Total Circuit Breaks: {metrics["circuit_breaks"]["total"]}</p>
                <table>
                    <tr>
                        <th>Endpoint</th>
                        <th>Count</th>
                    </tr>
        """
        
        # Add circuit breaks
        for endpoint, count in sorted(
            metrics["circuit_breaks"]["by_endpoint"].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            html_content += f"""
                    <tr>
                        <td>{endpoint}</td>
                        <td>{count}</td>
                    </tr>
            """
        
        html_content += f"""
                </table>
            </div>
        </body>
        </html>
        """
        
        # Write HTML to file
        with open(report_path, 'w') as f:
            f.write(html_content)


class MonitoringSystem:
    """Comprehensive monitoring system for the BT2C blockchain"""
    
    def __init__(self, metrics_dir: str, retention_days: int = 7, report_interval: int = 86400):
        """
        Initialize monitoring system
        
        Args:
            metrics_dir: Directory to store metrics
            retention_days: Number of days to retain metrics
            report_interval: Interval in seconds to generate reports
        """
        self.metrics_dir = metrics_dir
        self.reports_dir = os.path.join(metrics_dir, "reports")
        os.makedirs(self.reports_dir, exist_ok=True)
        
        self.retention_days = retention_days
        self.report_interval = report_interval
        
        # Initialize components
        self.metrics_collector = MetricsCollector(metrics_dir)
        self.metrics_visualizer = MetricsVisualizer(
            metrics_collector=self.metrics_collector,
            output_dir=self.reports_dir
        )
        
        # Start background tasks
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background tasks"""
        # Start metrics saving thread
        self.stop_tasks = False
        self.save_thread = threading.Thread(
            target=self._periodic_save,
            daemon=True
        )
        self.save_thread.start()
        
        # Start report generation thread
        self.report_thread = threading.Thread(
            target=self._periodic_report,
            daemon=True
        )
        self.report_thread.start()
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(
            target=self._periodic_cleanup,
            daemon=True
        )
        self.cleanup_thread.start()
    
    def _periodic_save(self):
        """Periodically save metrics"""
        while not self.stop_tasks:
            try:
                # Save metrics
                self.metrics_collector.save_metrics()
                
                # Sleep for 5 minutes
                time.sleep(300)
            except Exception as e:
                logger.error(f"Error saving metrics: {e}")
                time.sleep(60)  # Sleep for 1 minute on error
    
    def _periodic_report(self):
        """Periodically generate reports"""
        while not self.stop_tasks:
            try:
                # Generate report
                self.generate_report()
                
                # Sleep for report interval
                time.sleep(self.report_interval)
            except Exception as e:
                logger.error(f"Error generating report: {e}")
                time.sleep(3600)  # Sleep for 1 hour on error
    
    def _periodic_cleanup(self):
        """Periodically clean up old metrics"""
        while not self.stop_tasks:
            try:
                # Clean up old metrics
                self._cleanup_old_metrics()
                
                # Sleep for 1 day
                time.sleep(86400)
            except Exception as e:
                logger.error(f"Error cleaning up metrics: {e}")
                time.sleep(3600)  # Sleep for 1 hour on error
    
    def _cleanup_old_metrics(self):
        """Clean up old metrics"""
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")
        
        # Find old metric files
        for filename in os.listdir(self.metrics_dir):
            if filename.startswith("metrics_") and filename.endswith(".json"):
                file_date = filename[8:-5]  # Extract date from filename
                if file_date < cutoff_str:
                    # Delete old file
                    os.remove(os.path.join(self.metrics_dir, filename))
        
        # Find old report directories
        for dirname in os.listdir(self.reports_dir):
            if dirname.startswith("report_"):
                parts = dirname.split("_")
                if len(parts) >= 2:
                    file_date = parts[1]  # Extract date from dirname
                    if file_date < cutoff_str:
                        # Delete old directory
                        report_dir = os.path.join(self.reports_dir, dirname)
                        for filename in os.listdir(report_dir):
                            os.remove(os.path.join(report_dir, filename))
                        os.rmdir(report_dir)
    
    def track_request(self, endpoint: str, client_ip: str):
        """
        Track a request
        
        Args:
            endpoint: API endpoint
            client_ip: Client IP address
        """
        self.metrics_collector.track_request(endpoint, client_ip)
    
    def track_response(self, endpoint: str, status_code: int, response_time: float):
        """
        Track a response
        
        Args:
            endpoint: API endpoint
            status_code: HTTP status code
            response_time: Response time in seconds
        """
        self.metrics_collector.track_response(endpoint, status_code, response_time)
    
    def track_rate_limit(self, client_ip: str, endpoint: str):
        """
        Track a rate limit event
        
        Args:
            client_ip: Client IP address
            endpoint: API endpoint
        """
        self.metrics_collector.track_rate_limit(client_ip, endpoint)
    
    def track_circuit_break(self, endpoint: str):
        """
        Track a circuit break event
        
        Args:
            endpoint: API endpoint
        """
        self.metrics_collector.track_circuit_break(endpoint)
    
    def track_security_event(self, event_type: str, details: Dict[str, Any]):
        """
        Track a security event
        
        Args:
            event_type: Type of security event
            details: Event details
        """
        self.metrics_collector.track_security_event(event_type, details)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics
        
        Returns:
            Current metrics
        """
        return self.metrics_collector.get_metrics()
    
    def generate_report(self) -> str:
        """
        Generate a metrics report
        
        Returns:
            Path to the generated report
        """
        return self.metrics_visualizer.generate_report()
    
    def stop(self):
        """Stop the monitoring system"""
        self.stop_tasks = True
        self.metrics_collector.stop()
        
        # Wait for threads to terminate
        if self.save_thread.is_alive():
            self.save_thread.join(timeout=1)
        if self.report_thread.is_alive():
            self.report_thread.join(timeout=1)
        if self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=1)
