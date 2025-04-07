#!/usr/bin/env python3
import os
import sys
import json
import click
from pathlib import Path
from blockchain.client import BT2CClient
from blockchain.core.validator_manager import ValidatorManager, ValidatorInfo, ValidatorStatus

@click.group()
def cli():
    """BT2C Command Line Interface"""
    pass

@cli.group()
def wallet():
    """Manage BT2C wallet"""
    pass

@wallet.command()
@click.option("--mainnet", is_flag=True, help="Initialize wallet for mainnet")
@click.option("--type", type=click.Choice(["developer", "validator"]), default="developer", help="Node type")
def init(mainnet: bool, type: str):
    """Initialize a new BT2C wallet"""
    if not mainnet:
        click.echo("Error: Only mainnet is supported")
        sys.exit(1)
    
    client = BT2CClient()
    
    # Check seed nodes
    click.echo("\nChecking seed nodes...")
    if not client.check_seed_nodes():
        click.echo("Error: Could not connect to seed nodes")
        sys.exit(1)
    
    # Initialize wallet
    click.echo("\nInitializing wallet...")
    wallet, seed_phrase = client.init_wallet()
    
    click.echo("\n✓ Wallet created successfully!")
    click.echo(f"Address: {wallet.address()}")
    click.echo("\nIMPORTANT: Save your seed phrase securely!")
    click.echo(f"Seed phrase: {seed_phrase}")
    
    if type == "developer":
        click.echo("\nDeveloper Node Rewards:")
        click.echo("- One-time reward: 100 BT2C")
        click.echo("- Early validator reward: 1.0 BT2C")
        click.echo("- Must be claimed within 14 days")
        click.echo("- All rewards are automatically staked")

@cli.group()
def node():
    """Manage BT2C node"""
    pass

@node.command()
@click.option("--type", type=click.Choice(["developer", "validator"]), default="developer", help="Node type")
@click.option("--config", type=str, required=True, help="Path to validator config file")
def start(type: str, config: str):
    """Start a BT2C node"""
    client = BT2CClient()
    
    # Check seed nodes
    click.echo("\nChecking seed nodes...")
    if not client.check_seed_nodes():
        click.echo("Error: Could not connect to seed nodes")
        sys.exit(1)
    
    # Load validator config
    try:
        with open(config, 'r') as f:
            validator_config = json.load(f)
    except Exception as e:
        click.echo(f"Error loading validator config: {e}")
        sys.exit(1)
    
    # Initialize validator set
    validator_set = ValidatorSet()
    validator_set.minimum_stake = float(os.getenv('MIN_STAKE', 1.0))
    
    # Add validator to set
    if not validator_set.add_validator(
        validator_config['wallet_address'],
        validator_config['stake_amount']
    ):
        click.echo("Error: Failed to add validator")
        sys.exit(1)
    
    click.echo("\n✓ Node started successfully!")
    click.echo(f"Address: {validator_config['wallet_address']}")
    click.echo(f"Stake Amount: {validator_config['stake_amount']} BT2C")
    click.echo(f"Network: {validator_config['network']['listen_addr']}")
    click.echo(f"Connected Seeds: {', '.join(validator_config['network']['seeds'])}")
    click.echo("\nOperating in testnet mode - mainnet is currently disabled")
    
    if type == "developer":
        click.echo("\nDeveloper Node Rewards (will be enabled on mainnet):")
        click.echo("- One-time reward: 100 BT2C")
        click.echo("- Early validator reward: 1.0 BT2C")
        click.echo("- Must be claimed within 14 days")
        click.echo("- All rewards are automatically staked")
    
    # Start validator node (blocking)
    try:
        import asyncio
        asyncio.run(client.run_validator(validator_config, validator_set))
    except KeyboardInterrupt:
        click.echo("\nShutting down node...")
    except Exception as e:
        click.echo(f"\nError running node: {e}")
        sys.exit(1)

if __name__ == "__main__":
    cli()
