"""BT2C CLI Commands"""
import click
from .wallet import wallet
from .node import node

@click.group()
def cli():
    """BT2C Command Line Interface"""
    pass

# Register commands
cli.add_command(wallet)
cli.add_command(node)
