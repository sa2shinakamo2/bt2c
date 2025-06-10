#!/usr/bin/env python3
"""
Display BT2C Seed Phrase

This script displays the seed phrase for a BT2C wallet in a readable format.
"""

import sys
import os
from pathlib import Path

def display_seed_phrase(seed_file_path):
    """Display the seed phrase from the given file."""
    try:
        # Check if the file exists
        if not os.path.exists(seed_file_path):
            print(f"❌ Error: Seed phrase file not found at {seed_file_path}")
            return False
        
        # Read the seed phrase file
        with open(seed_file_path, 'r') as f:
            content = f.read()
        
        # Extract the seed phrase
        seed_phrase_section = content.split("SEED PHRASE (KEEP SECURE):\n")[1].split("\n\n")[0]
        
        # Print the seed phrase
        print("\n🔐 BT2C Wallet Seed Phrase")
        print("========================")
        print("\nYour seed phrase is:")
        print("\n" + seed_phrase_section + "\n")
        print("⚠️  IMPORTANT: Keep this seed phrase secure!")
        print("It's recommended to write it down on paper and store it in a safe place.")
        print("Anyone with access to this seed phrase can access your funds.")
        
        return True
    
    except Exception as e:
        print(f"❌ Error: Failed to display seed phrase: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python display_seed_phrase.py <path_to_seed_phrase_file>")
        sys.exit(1)
    
    seed_file_path = sys.argv[1]
    display_seed_phrase(seed_file_path)
