#!/usr/bin/env python3
"""
BT2C Node Installation Script
Similar to Bitcoin's approach - simple, direct OS installation
"""
import os
import sys
import shutil
import hashlib
import platform
import subprocess
from pathlib import Path

def check_python_version():
    """Ensure Python 3.9+ is being used"""
    if sys.version_info < (3, 9):
        sys.exit("Python 3.9 or higher is required")

def check_system_requirements():
    """Check basic system requirements"""
    # Check CPU cores
    cpu_count = os.cpu_count()
    if cpu_count < 2:
        print(f"Warning: Found {cpu_count} CPU cores, recommended minimum is 2")
    
    # Check RAM (in GB)
    try:
        if platform.system() == 'Linux':
            with open('/proc/meminfo') as f:
                mem = float(next(line.split()[1] for line in f if 'MemTotal' in line)) / 1024 / 1024
            if mem < 2:
                print(f"Warning: Found {mem:.1f}GB RAM, recommended minimum is 2GB")
        else:
            import psutil
            mem = psutil.virtual_memory().total / (1024**3)
            if mem < 2:
                print(f"Warning: Found {mem:.1f}GB RAM, recommended minimum is 2GB")
    except FileNotFoundError:
        print("Warning: Could not check RAM size - /proc/meminfo not found")
    except ImportError:
        print("Warning: Could not check RAM size - psutil module not available")
    except (ValueError, IndexError):
        print("Warning: Could not check RAM size - unexpected format in memory information")
    except Exception as e:
        print(f"Warning: Could not check RAM size - {str(e)}")
    
    # Check disk space
    path = os.path.expanduser("~/.bt2c")
    disk = shutil.disk_usage(os.path.dirname(path))
    free_gb = disk.free / (1024**3)
    if free_gb < 50:
        print(f"Warning: Found {free_gb:.1f}GB free space, recommended minimum is 50GB")

def create_data_directory():
    """Create .bt2c directory in user's home"""
    bt2c_dir = os.path.expanduser("~/.bt2c")
    os.makedirs(bt2c_dir, exist_ok=True)
    os.makedirs(os.path.join(bt2c_dir, "data"), exist_ok=True)
    os.makedirs(os.path.join(bt2c_dir, "wallets"), exist_ok=True)
    return bt2c_dir

def create_config(bt2c_dir):
    """Create default configuration file"""
    config = {
        "network": {
            "listen": "0.0.0.0",
            "port": 26656,
            "rpc_port": 8332,  # Similar to Bitcoin's default RPC port
            "max_connections": 125  # Similar to Bitcoin's default
        },
        "blockchain": {
            "max_supply": 21000000,
            "block_reward": 21.0,
            "halving_period": 126144000,  # 4 years in seconds
            "block_time": 300  # 5 minutes
        },
        "validation": {
            "min_stake": 1.0,
            "early_reward": 1.0,
            "dev_reward": 100.0,
            "distribution_period": 1209600  # 14 days
        },
        "security": {
            "rsa_bits": 2048,
            "seed_bits": 256
        }
    }
    
    config_file = os.path.join(bt2c_dir, "bt2c.conf")
    with open(config_file, "w") as f:
        for section, values in config.items():
            f.write(f"[{section}]\n")
            for key, value in values.items():
                f.write(f"{key}={value}\n")
            f.write("\n")

def install_dependencies():
    """Install minimal required Python packages"""
    requirements = [
        "cryptography==44.0.2",  # For RSA and other crypto operations
        "coincurve==19.0.1",     # For secp256k1 operations
        "base58==2.1.1",         # For address encoding
        "structlog==24.1.0",     # For logging
        "mnemonic==0.21",        # For BIP39 support
        "hdwallet==2.2.1"        # For BIP44 HD wallets
    ]
    
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", *requirements
    ])

def create_startup_script(bt2c_dir):
    """Create bt2cd startup script"""
    script_content = f"""#!/bin/bash
# BT2C Node Daemon
export BT2C_HOME="{bt2c_dir}"
export PYTHONPATH="{os.path.dirname(os.path.dirname(__file__))}"

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

python3 -m blockchain.node "$@"
"""
    
    script_path = os.path.join(bt2c_dir, "bt2cd")
    with open(script_path, "w") as f:
        f.write(script_content)
    os.chmod(script_path, 0o755)

def main():
    print("Installing BT2C Node...")
    
    # Basic checks
    check_python_version()
    check_system_requirements()
    
    # Setup
    bt2c_dir = create_data_directory()
    create_config(bt2c_dir)
    install_dependencies()
    create_startup_script(bt2c_dir)
    
    print(f"""
BT2C Node installed successfully!
Data directory: {bt2c_dir}

To start the node:
    ~/.bt2c/bt2cd

To start with custom config:
    ~/.bt2c/bt2cd --config /path/to/config

To run as validator:
    ~/.bt2c/bt2cd --validator --stake 1.0
""")

if __name__ == "__main__":
    main()
