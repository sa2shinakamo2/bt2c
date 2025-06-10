from prometheus_client import Counter, Gauge, Histogram

class BlockchainMetrics:
    def __init__(self, network_type):
        self.network_type = network_type
        self.metrics = PrometheusMetrics()
        
        # Block metrics
        self.block_counter = self.metrics.block_counter
        self.block_size = self.metrics.block_size
        
        # Transaction metrics
        self.transaction_counter = self.metrics.transaction_counter
        self.transaction_size = self.metrics.transaction_size
        
        # Validator metrics
        self.active_validator_count = self.metrics.active_validator_count
        self.total_stake = self.metrics.total_stake
        self.validator_uptime = self.metrics.validator_uptime
        
        # Performance metrics
        self.block_time = self.metrics.block_time
        self.transaction_latency = self.metrics.transaction_latency

class PrometheusMetrics:
    def __init__(self):
        # Block metrics
        self.block_counter = Counter(
            'bt2c_blocks_total',
            'Total number of blocks produced'
        )
        self.block_size = Histogram(
            'bt2c_block_size_bytes',
            'Block size in bytes',
            buckets=[1024, 2048, 4096, 8192, 16384, 32768, 65536]
        )
        
        # Transaction metrics
        self.transaction_counter = Counter(
            'bt2c_transactions_total',
            'Total number of transactions processed'
        )
        self.transaction_size = Histogram(
            'bt2c_transaction_size_bytes',
            'Transaction size in bytes',
            buckets=[128, 256, 512, 1024, 2048, 4096]
        )
        
        # Validator metrics
        self.active_validator_count = Gauge(
            'bt2c_active_validators',
            'Number of active validators'
        )
        self.total_stake = Gauge(
            'bt2c_total_stake',
            'Total stake across all validators'
        )
        self.validator_uptime = Gauge(
            'bt2c_validator_uptime',
            'Validator uptime percentage'
        )
        
        # Performance metrics
        self.block_time = Histogram(
            'bt2c_block_time_seconds',
            'Time between blocks',
            buckets=[1, 2, 5, 10, 30, 60]
        )
        self.transaction_latency = Histogram(
            'bt2c_transaction_latency_seconds',
            'Time from transaction submission to confirmation',
            buckets=[0.1, 0.5, 1, 2, 5, 10]
        )
        
    def update_active_validators(self, count: int):
        """Update the number of active validators."""
        self.active_validator_count.set(count)
        
    def update_total_stake(self, stake: float):
        """Update the total stake."""
        self.total_stake.set(stake)
        
    def update_validator_uptime(self, uptime: float):
        """Update validator uptime percentage."""
        self.validator_uptime.set(uptime)
        
    def record_block_time(self, seconds: float):
        """Record time between blocks."""
        self.block_time.observe(seconds)
        
    def record_transaction_latency(self, seconds: float):
        """Record transaction confirmation latency."""
        self.transaction_latency.observe(seconds)
