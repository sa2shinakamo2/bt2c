"""
BT2C Client module for interacting with the BT2C blockchain.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union

from .p2p.peer import Peer
from .p2p.manager import P2PManager
from .p2p.message import MessageType, create_message
from .wallet import Wallet
from .transaction import Transaction

logger = logging.getLogger(__name__)

class BT2CClient:
    """
    Client for interacting with the BT2C blockchain network.
    Provides high-level methods for sending transactions, querying the blockchain,
    and managing wallet operations.
    """
    
    def __init__(
        self,
        p2p_manager: P2PManager,
        wallet: Optional[Wallet] = None,
        network_type: str = "testnet"
    ):
        """
        Initialize the BT2C client.
        
        Args:
            p2p_manager: The P2P network manager
            wallet: Optional wallet for signing transactions
            network_type: Network type (mainnet, testnet)
        """
        self.p2p_manager = p2p_manager
        self.wallet = wallet
        self.network_type = network_type
        self.pending_requests: Dict[str, asyncio.Future] = {}
        
    async def connect(self) -> bool:
        """
        Connect to the BT2C network.
        
        Returns:
            True if connected successfully, False otherwise
        """
        return await self.p2p_manager.start()
        
    async def disconnect(self) -> None:
        """
        Disconnect from the BT2C network.
        """
        await self.p2p_manager.stop()
        
    async def send_transaction(self, transaction: Transaction) -> str:
        """
        Send a transaction to the network.
        
        Args:
            transaction: The transaction to send
            
        Returns:
            Transaction hash
        """
        if not self.wallet:
            raise ValueError("Wallet is required to send transactions")
            
        # Sign the transaction if not already signed
        if not transaction.signature:
            transaction = self.wallet.sign_transaction(transaction)
            
        # Create a new transaction message
        message = create_message(
            MessageType.NEW_TRANSACTION,
            self.p2p_manager.node_id,
            self.network_type,
            transaction=transaction.to_dict()
        )
        
        # Broadcast the transaction to the network
        await self.p2p_manager.broadcast_message(message)
        
        return transaction.hash
        
    async def get_blockchain_status(self) -> Dict[str, Any]:
        """
        Get the current status of the blockchain.
        
        Returns:
            Dictionary with blockchain status information
        """
        # Create a status request message
        message = create_message(
            MessageType.GET_STATUS,
            self.p2p_manager.node_id,
            self.network_type
        )
        
        # Send to a random peer and wait for response
        future = asyncio.Future()
        request_id = message.id
        self.pending_requests[request_id] = future
        
        # Find a peer to send the request to
        peers = self.p2p_manager.get_connected_peers()
        if not peers:
            raise ConnectionError("No connected peers available")
            
        # Send to the first peer
        peer = peers[0]
        await peer.send_message(message)
        
        try:
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=10.0)
            return response.payload
        except asyncio.TimeoutError:
            del self.pending_requests[request_id]
            raise TimeoutError("Timeout waiting for blockchain status")
        
    async def get_balance(self, address: Optional[str] = None) -> float:
        """
        Get the balance for an address or the current wallet.
        
        Args:
            address: Optional address to check balance for. If None, uses the wallet address.
            
        Returns:
            Balance in BT2C
        """
        if not address and not self.wallet:
            raise ValueError("Either address or wallet must be provided")
            
        target_address = address or self.wallet.address
        
        # Implementation would typically query the blockchain for UTXO or account balance
        # This is a simplified placeholder
        return 0.0
        
    def handle_status_response(self, message: Any) -> None:
        """
        Handle a status response message.
        
        Args:
            message: The status response message
        """
        if message.id in self.pending_requests:
            future = self.pending_requests[message.id]
            future.set_result(message)
            del self.pending_requests[message.id]
