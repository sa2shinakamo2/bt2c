from typing import List, Set
import structlog
from .redis_manager import RedisManager

logger = structlog.get_logger()

class CacheInvalidator:
    def __init__(self, redis_manager: RedisManager):
        self.redis = redis_manager
        self.invalidation_patterns = {
            'block': [
                'block:*',
                'latest_blocks',
                'chain_stats',
                'network_info'
            ],
            'transaction': [
                'transaction:*',
                'latest_transactions',
                'pending_transactions',
                'address:*:transactions'
            ],
            'validator': [
                'validator:*',
                'active_validators',
                'staking_info'
            ],
            'network': [
                'network_info',
                'chain_stats',
                'metrics:*'
            ],
            'address': [
                'address:*',
                'address:*:balance',
                'address:*:transactions'
            ]
        }

    async def invalidate_block(self, block_height: int = None):
        """Invalidate cache entries related to blocks."""
        patterns = self.invalidation_patterns['block']
        if block_height:
            patterns.append(f'block:{block_height}')
        await self._invalidate_patterns(patterns)
        logger.info("cache_invalidated", type="block", height=block_height)

    async def invalidate_transaction(self, tx_hash: str = None):
        """Invalidate cache entries related to transactions."""
        patterns = self.invalidation_patterns['transaction']
        if tx_hash:
            patterns.append(f'transaction:{tx_hash}')
        await self._invalidate_patterns(patterns)
        logger.info("cache_invalidated", type="transaction", hash=tx_hash)

    async def invalidate_validator(self, validator_address: str = None):
        """Invalidate cache entries related to validators."""
        patterns = self.invalidation_patterns['validator']
        if validator_address:
            patterns.append(f'validator:{validator_address}')
        await self._invalidate_patterns(patterns)
        logger.info("cache_invalidated", type="validator", address=validator_address)

    async def invalidate_address(self, address: str):
        """Invalidate cache entries related to an address."""
        patterns = [
            f'address:{address}:*',
            'latest_transactions',
            'network_info'
        ]
        await self._invalidate_patterns(patterns)
        logger.info("cache_invalidated", type="address", address=address)

    async def invalidate_network_stats(self):
        """Invalidate cache entries related to network statistics."""
        await self._invalidate_patterns(self.invalidation_patterns['network'])
        logger.info("cache_invalidated", type="network_stats")

    async def _invalidate_patterns(self, patterns: List[str]):
        """Invalidate multiple cache patterns."""
        for pattern in patterns:
            await self.redis.clear_pattern(pattern)

def invalidates_cache(*entity_types: str):
    """Decorator to automatically invalidate cache after method execution."""
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            result = await func(self, *args, **kwargs)
            
            # Get cache invalidator instance
            invalidator = getattr(self, 'cache_invalidator', None)
            if not invalidator:
                return result

            # Invalidate each specified entity type
            for entity_type in entity_types:
                if entity_type == 'block':
                    await invalidator.invalidate_block()
                elif entity_type == 'transaction':
                    await invalidator.invalidate_transaction()
                elif entity_type == 'validator':
                    await invalidator.invalidate_validator()
                elif entity_type == 'network':
                    await invalidator.invalidate_network_stats()

            return result
        return wrapper
    return decorator
