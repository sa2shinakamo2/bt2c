#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
from pathlib import Path

def build_client():
    """Build BT2C client binary."""
    print("\n=== Building BT2C Client ===")
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    # Create build directory
    build_dir = project_root / "build"
    downloads_dir = project_root / "downloads"
    os.makedirs(build_dir, exist_ok=True)
    os.makedirs(downloads_dir, exist_ok=True)
    
    # Build for current architecture
    print("\nBuilding BT2C client...")
    try:
        subprocess.run([
            "python3", "-m", "PyInstaller",
            "--clean",
            "--onefile",
            "--name", "bt2c",
            "--distpath", str(downloads_dir),
            "--workpath", str(build_dir),
            "--specpath", str(build_dir),
            "--add-data", f"{project_root}/blockchain/genesis.json:blockchain",
            "--hidden-import", "blockchain",
            "--hidden-import", "blockchain.config",
            "--hidden-import", "blockchain.security",
            "--hidden-import", "blockchain.client",
            "--hidden-import", "hdwallet",
            "--hidden-import", "mnemonic",
            "--hidden-import", "click",
            str(project_root / "blockchain/cli.py")
        ], check=True)
        
        print("✓ Built BT2C client")
        
        # Set up download endpoints
        binary_path = downloads_dir / "bt2c"
        if not binary_path.exists():
            print("⚠️ Binary not found!")
            sys.exit(1)
            
        # Create download directories
        endpoints = {
            "main": downloads_dir / "main" / "downloads",
            "api": downloads_dir / "api" / "downloads",
            "explorer": downloads_dir / "main" / "explorer" / "downloads"
        }
        
        for path in endpoints.values():
            os.makedirs(path, exist_ok=True)
        
        # Copy binary to endpoints
        version = "v1.0.0"
        arch = "amd64" if sys.platform == "darwin" else "arm64"
        binary_name = f"bt2c-client-linux-{arch}-{version}"
        
        for path in endpoints.values():
            shutil.copy2(binary_path, path / binary_name)
            os.chmod(path / binary_name, 0o755)
        
        print("\n✓ Created download endpoints:")
        print(f"1. bt2c.net/downloads/{binary_name}")
        print(f"2. api.bt2c.net/downloads/{binary_name}")
        print(f"3. bt2c.net/explorer/downloads/{binary_name}")
        
    except subprocess.CalledProcessError as e:
        print(f"Error building client: {e}")
        sys.exit(1)
    
    print("\n=== Build Complete ===")

if __name__ == "__main__":
    build_client()
