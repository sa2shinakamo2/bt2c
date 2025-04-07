"""
CLI commands for node management.
"""
import click
import json
import os
import logging
from typing import Dict, Any, Optional

from ..p2p.manager import P2PManager
from ..p2p.discovery import NodeDiscovery
from ..config import BT2CConfig, NetworkType

logger = logging.getLogger(__name__)

@click.group()
def node():
    """Node management commands."""
    pass

@node.command()
@click.option('--config', '-c', type=str, help='Path to node configuration file')
@click.option('--network', '-n', type=click.Choice(['mainnet', 'testnet']), default='testnet', 
              help='Network to connect to')
@click.option('--seed', is_flag=True, help='Run as a seed node')
def start(config: Optional[str], network: str, seed: bool):
    """Start a BT2C node."""
    try:
        # Load configuration
        if config and os.path.exists(config):
            with open(config, 'r') as f:
                config_data = json.load(f)
        else:
            config_data = {}
            
        # Set up network type
        network_type = NetworkType.TESTNET if network == 'testnet' else NetworkType.MAINNET
        
        # Initialize node configuration
        node_config = BT2CConfig.get_config(network_type)
        
        # Override with provided config
        if config_data:
            # Apply config overrides here
            pass
            
        # Set up P2P manager
        discovery = NodeDiscovery(network_type=network_type)
        p2p_manager = P2PManager(
            node_id=config_data.get('node_id', 'bt2c-node'),
            discovery=discovery,
            listen_addr=config_data.get('listen_addr', '0.0.0.0:8337'),
            external_addr=config_data.get('external_addr', '127.0.0.1:8337'),
            network_type=network_type,
            is_seed=seed
        )
        
        # Start the node
        click.echo(f"Starting BT2C node on {network} network")
        click.echo(f"Node ID: {p2p_manager.node_id}")
        click.echo(f"Listening on: {p2p_manager.listen_address}")
        click.echo(f"External address: {p2p_manager.external_address}")
        click.echo(f"Seed node: {seed}")
        
        # This would normally be in an async context
        click.echo("Node started. Press Ctrl+C to stop.")
        
    except Exception as e:
        click.echo(f"Error starting node: {str(e)}", err=True)
        
@node.command()
def status():
    """Get the status of the running node."""
    try:
        # This would normally connect to a running node
        click.echo("Node status: Running")
        click.echo("Connected peers: 0")
        click.echo("Blockchain height: 0")
        
    except Exception as e:
        click.echo(f"Error getting node status: {str(e)}", err=True)
        
@node.command()
def stop():
    """Stop the running node."""
    try:
        # This would normally connect to a running node and stop it
        click.echo("Node stopped.")
        
    except Exception as e:
        click.echo(f"Error stopping node: {str(e)}", err=True)
