#!/usr/bin/env python3
"""
BT2C Codebase Cleanup Script

This script identifies and optionally removes obsolete components from the BT2C codebase
that are no longer needed after the remodeling. It also checks API consistency.

Usage:
    python cleanup_codebase.py [--dry-run] [--execute] [--check-api]

Options:
    --dry-run    Show what would be removed without actually removing anything (default)
    --execute    Actually remove the identified obsolete components
    --check-api  Check API consistency across the codebase
"""

import os
import sys
import shutil
import argparse
import re
from pathlib import Path
import json
import structlog

logger = structlog.get_logger()

# Components to preserve (relative to project root)
PRESERVE = [
    # Core new architecture
    "blockchain/core",
    "blockchain/models.py",
    "blockchain/api.py",
    "blockchain/__init__.py",
    
    # Scripts
    "scripts/unified_validator_registration.py",
    "scripts/cleanup_codebase.py",
    "scripts/setup_home_seed_node.py",
    "scripts/fix_circular_imports.py",
    
    # Documentation
    "docs/seed_nodes.md",
    "README.md",
    
    # Configuration
    "config",
    
    # Docker related
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.validator.yml",
    
    # Dependencies
    "requirements.txt",
    
    # Data directories
    "data",
    "certs",
    "mainnet",
    "testnet"
]

# Obsolete validator scripts to remove
OBSOLETE_VALIDATOR_SCRIPTS = [
    "scripts/register_validator.py",
    "scripts/deploy_validator.py",
    "scripts/check_validators.py",
    "scripts/setup_validator.py",
    "manual_validator_registration.py"
]

# Obsolete blockchain modules with circular dependencies
OBSOLETE_BLOCKCHAIN_MODULES = [
    "blockchain/validator.py",
    "blockchain/staking.py"
]

# Expected API endpoints based on our remodeled architecture
EXPECTED_API_ENDPOINTS = [
    # Core endpoints
    {"method": "GET", "path": "/health", "description": "Health check endpoint"},
    {"method": "GET", "path": "/info", "description": "Node information"},
    {"method": "GET", "path": "/metrics", "description": "Prometheus metrics"},
    
    # Blockchain endpoints
    {"method": "POST", "path": "/blockchain/transaction", "description": "Create a new transaction"},
    {"method": "GET", "path": "/blockchain/transaction/{transaction_id}", "description": "Get transaction details"},
    {"method": "GET", "path": "/blockchain/status", "description": "Get blockchain status"},
    {"method": "GET", "path": "/blockchain/wallet/{address}", "description": "Get wallet information"},
    
    # Validator endpoints
    {"method": "POST", "path": "/blockchain/validator/register", "description": "Register a new validator"},
    {"method": "GET", "path": "/blockchain/validator/{address}", "description": "Get validator information"},
    {"method": "GET", "path": "/blockchain/validators", "description": "List all validators"}
]

def is_preserved(path, preserve_list):
    """Check if a path should be preserved."""
    path_str = str(path)
    
    # Always preserve directories in the preserve list
    for preserved in preserve_list:
        if path_str.startswith(preserved):
            return True
    
    return False

def identify_obsolete_files(project_root, preserve_list):
    """Identify obsolete files that can be safely removed."""
    obsolete_files = []
    
    # First, add the explicitly identified obsolete files
    for file_path in OBSOLETE_VALIDATOR_SCRIPTS + OBSOLETE_BLOCKCHAIN_MODULES:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            obsolete_files.append(full_path)
    
    return obsolete_files

def backup_file(file_path):
    """Create a backup of a file before removing it."""
    backup_path = f"{file_path}.bak"
    shutil.copy2(file_path, backup_path)
    logger.info("file_backed_up", original=file_path, backup=backup_path)
    return backup_path

def remove_file(file_path, create_backup=True):
    """Remove a file, optionally creating a backup first."""
    if create_backup:
        backup_file(file_path)
    
    os.remove(file_path)
    logger.info("file_removed", path=file_path)

def extract_api_endpoints(api_file):
    """Extract API endpoints from the FastAPI file."""
    endpoints = []
    
    with open(api_file, 'r') as f:
        content = f.read()
    
    # Find all route decorators
    route_patterns = [
        (r'@app\.get\(["\']([^"\']+)["\']', 'GET'),
        (r'@app\.post\(["\']([^"\']+)["\']', 'POST'),
        (r'@app\.put\(["\']([^"\']+)["\']', 'PUT'),
        (r'@app\.delete\(["\']([^"\']+)["\']', 'DELETE')
    ]
    
    for pattern, method in route_patterns:
        matches = re.findall(pattern, content)
        for path in matches:
            # Extract function name (comes after the decorator)
            func_match = re.search(rf'@app\.{method.lower()}\(["\'{path}["\'].*?\)\s*\n\s*(?:async\s+)?def\s+([a-zA-Z0-9_]+)', 
                                  content, re.DOTALL)
            
            func_name = func_match.group(1) if func_match else "unknown"
            
            # Convert function name to description
            description = " ".join(word.capitalize() for word in func_name.split('_'))
            
            endpoints.append({
                "method": method,
                "path": path,
                "function": func_name,
                "description": description
            })
    
    return endpoints

def check_api_consistency(project_root):
    """Check API consistency across the codebase."""
    api_file = os.path.join(project_root, "blockchain", "api.py")
    
    if not os.path.exists(api_file):
        print("❌ API file not found: blockchain/api.py")
        return False
    
    # Extract actual endpoints from the API file
    actual_endpoints = extract_api_endpoints(api_file)
    
    # Compare with expected endpoints
    missing_endpoints = []
    for expected in EXPECTED_API_ENDPOINTS:
        found = False
        for actual in actual_endpoints:
            if expected["method"] == actual["method"] and expected["path"] == actual["path"]:
                found = True
                break
        
        if not found:
            missing_endpoints.append(expected)
    
    # Find extra endpoints not in our expected list
    extra_endpoints = []
    for actual in actual_endpoints:
        found = False
        for expected in EXPECTED_API_ENDPOINTS:
            if expected["method"] == actual["method"] and expected["path"] == actual["path"]:
                found = True
                break
        
        if not found:
            extra_endpoints.append(actual)
    
    # Generate report
    report = {
        "total_expected": len(EXPECTED_API_ENDPOINTS),
        "total_actual": len(actual_endpoints),
        "missing_endpoints": missing_endpoints,
        "extra_endpoints": extra_endpoints,
        "is_consistent": len(missing_endpoints) == 0
    }
    
    # Save report to file
    report_path = os.path.join(project_root, "api_consistency_report.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    return report

def main():
    parser = argparse.ArgumentParser(description="BT2C Codebase Cleanup")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be removed without actually removing anything")
    parser.add_argument("--execute", action="store_true", help="Actually remove the identified obsolete components")
    parser.add_argument("--check-api", action="store_true", help="Check API consistency across the codebase")
    
    args = parser.parse_args()
    
    # Default to dry run if neither option is specified
    if not args.dry_run and not args.execute and not args.check_api:
        args.dry_run = True
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    # Check API consistency if requested
    if args.check_api:
        print("\n🔍 Checking API consistency...")
        report = check_api_consistency(project_root)
        
        if report["is_consistent"]:
            print("✅ API is consistent with expected endpoints!")
            print(f"   Total endpoints: {report['total_actual']}")
        else:
            print("⚠️  API inconsistencies found:")
            
            if report["missing_endpoints"]:
                print(f"\n   Missing endpoints ({len(report['missing_endpoints'])}):")
                for endpoint in report["missing_endpoints"]:
                    print(f"     - {endpoint['method']} {endpoint['path']} ({endpoint['description']})")
            
            if report["extra_endpoints"]:
                print(f"\n   Extra endpoints ({len(report['extra_endpoints'])}):")
                for endpoint in report["extra_endpoints"]:
                    print(f"     - {endpoint['method']} {endpoint['path']} ({endpoint['description']})")
            
            print(f"\n   Report saved to: api_consistency_report.json")
    
    # Identify obsolete files
    obsolete_files = identify_obsolete_files(project_root, PRESERVE)
    
    # Print summary
    print(f"\n🧹 BT2C Codebase Cleanup")
    print("=======================")
    print(f"Found {len(obsolete_files)} obsolete files that can be safely removed.")
    
    # Print details
    if obsolete_files:
        print("\nObsolete files:")
        for file_path in obsolete_files:
            rel_path = os.path.relpath(file_path, project_root)
            print(f"  - {rel_path}")
    
    # Execute removal if requested
    if args.execute:
        print("\n🔄 Executing cleanup...")
        for file_path in obsolete_files:
            rel_path = os.path.relpath(file_path, project_root)
            print(f"  - Removing {rel_path}...")
            remove_file(file_path)
        print("\n✅ Cleanup complete!")
    elif args.dry_run and not args.check_api:
        print("\n📝 This was a dry run. No files were actually removed.")
        print("To execute the cleanup, run with the --execute flag:")
        print("  python scripts/cleanup_codebase.py --execute")
        print("\nTo check API consistency, run with the --check-api flag:")
        print("  python scripts/cleanup_codebase.py --check-api")

if __name__ == "__main__":
    main()
