#!/usr/bin/env python3
import os
import sys
import click
from pathlib import Path
from blockchain.client import BT2CClient

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

if __name__ == "__main__":
    cli()
