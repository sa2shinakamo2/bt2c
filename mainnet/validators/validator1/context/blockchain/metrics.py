from prometheus_client import Counter, Gauge, Histogram, Info
import structlog
from typing import Dict, Any
import time

logger = structlog.get_logger()

class BlockchainMetrics:
    def __init__(self, network_type: str):
        # Basic blockchain metrics
        self.block_height = Gauge('bt2c_block_height', 'Current block height', ['network'])
        self.total_transactions = Counter('bt2c_total_transactions', 'Total number of transactions', ['network'])
        self.active_validators = Gauge('bt2c_active_validators', 'Number of active validators', ['network'])
        self.total_staked = Gauge('bt2c_total_staked', 'Total amount staked', ['network'])
        
        # Transaction metrics
        self.transaction_size = Histogram('bt2c_transaction_size_bytes', 'Transaction size in bytes',
                                        ['network'], buckets=[64, 128, 256, 512, 1024, 2048])
        self.transaction_processing_time = Histogram('bt2c_transaction_processing_seconds',
                                                   'Time to process transaction',
                                                   ['network'], buckets=[.01, .025, .05, .1, .25, .5, 1])
        
        # Block metrics
        self.block_size = Histogram('bt2c_block_size_bytes', 'Block size in bytes',
                                  ['network'], buckets=[1024, 4096, 16384, 65536, 262144, 1048576])
        self.block_time = Histogram('bt2c_block_time_seconds', 'Time between blocks',
                                  ['network'], buckets=[1, 2, 5, 10, 30, 60])
        
        # Validator metrics
        self.validator_uptime = Gauge('bt2c_validator_uptime_ratio', 'Validator uptime ratio', 
                                    ['network', 'validator'])
        self.validator_stake = Gauge('bt2c_validator_stake', 'Validator stake amount',
                                   ['network', 'validator'])
        
        # Network metrics
        self.peer_count = Gauge('bt2c_peer_count', 'Number of connected peers', ['network'])
        self.network_latency = Histogram('bt2c_network_latency_seconds', 'Network latency',
                                       ['network'], buckets=[.01, .025, .05, .1, .25, .5, 1])
        
        # System metrics
        self.memory_usage = Gauge('bt2c_memory_usage_bytes', 'Memory usage in bytes', ['network'])
        self.cpu_usage = Gauge('bt2c_cpu_usage_ratio', 'CPU usage ratio', ['network'])
        
        self.network = network_type
        
    def record_transaction(self, tx_hash: str, size: int, processing_time: float):
        """Record transaction metrics"""
        self.total_transactions.labels(network=self.network).inc()
        self.transaction_size.labels(network=self.network).observe(size)
        self.transaction_processing_time.labels(network=self.network).observe(processing_time)
        logger.info("transaction_processed",
                   tx_hash=tx_hash,
                   size=size,
                   processing_time=processing_time)
        
    def record_block(self, block_hash: str, height: int, size: int, time_since_last: float):
        """Record block metrics"""
        self.block_height.labels(network=self.network).set(height)
        self.block_size.labels(network=self.network).observe(size)
        self.block_time.labels(network=self.network).observe(time_since_last)
        logger.info("block_created",
                   block_hash=block_hash,
                   height=height,
                   size=size,
                   time_since_last=time_since_last)
        
    def update_validator_metrics(self, validator: str, uptime: float, stake: float):
        """Update validator metrics"""
        self.validator_uptime.labels(network=self.network, validator=validator).set(uptime)
        self.validator_stake.labels(network=self.network, validator=validator).set(stake)
        logger.info("validator_metrics_updated",
                   validator=validator,
                   uptime=uptime,
                   stake=stake)
        
    def update_network_metrics(self, peer_count: int, avg_latency: float):
        """Update network metrics"""
        self.peer_count.labels(network=self.network).set(peer_count)
        self.network_latency.labels(network=self.network).observe(avg_latency)
        logger.info("network_metrics_updated",
                   peer_count=peer_count,
                   avg_latency=avg_latency)
        
    def update_system_metrics(self, memory_bytes: int, cpu_ratio: float):
        """Update system metrics"""
        self.memory_usage.labels(network=self.network).set(memory_bytes)
        self.cpu_usage.labels(network=self.network).set(cpu_ratio)
        logger.info("system_metrics_updated",
                   memory_bytes=memory_bytes,
                   cpu_ratio=cpu_ratio)
