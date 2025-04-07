"""BT2C Wallet Commands"""
import sys
import click
from blockchain.client import BT2CClient

@click.group()
def wallet():
    """Manage BT2C wallet"""
    pass

@wallet.command()
@click.option("--type", type=click.Choice(["developer", "validator"]), default="developer", help="Node type")
def init(type: str):
    """Initialize a new BT2C wallet"""
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
        click.echo("\nDeveloper Node Rewards (will be enabled on mainnet):")
        click.echo("- One-time reward: 100 BT2C")
        click.echo("- Early validator reward: 1.0 BT2C")
        click.echo("- Must be claimed within 14 days")
        click.echo("- All rewards are automatically staked")
