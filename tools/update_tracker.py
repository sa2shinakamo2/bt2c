#!/usr/bin/env python3
"""
BT2C Improvement Tracker Update Tool

This script helps update the IMPROVEMENT_TRACKER.md file when improvements are completed.
It parses the markdown file, updates the status of specified improvements, and recalculates
the progress summary.
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Status emojis
STATUS_EMOJIS = {
    "not_started": "🔴 Not Started",
    "in_progress": "🟡 In Progress",
    "testing": "🔵 Testing",
    "completed": "🟢 Completed"
}

def parse_tracker_file(file_path):
    """Parse the tracker markdown file into sections and tables."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Split into sections
    sections = {}
    current_section = None
    section_content = []
    
    for line in content.split('\n'):
        if line.startswith('## Phase'):
            if current_section:
                sections[current_section] = '\n'.join(section_content)
            current_section = line
            section_content = [line]
        elif line.startswith('## Progress Summary'):
            if current_section:
                sections[current_section] = '\n'.join(section_content)
            current_section = line
            section_content = [line]
        elif line.startswith('## Implementation Notes'):
            if current_section:
                sections[current_section] = '\n'.join(section_content)
            current_section = line
            section_content = [line]
        elif line.startswith('## Last Updated'):
            if current_section:
                sections[current_section] = '\n'.join(section_content)
            current_section = line
            section_content = [line]
        elif current_section:
            section_content.append(line)
    
    if current_section:
        sections[current_section] = '\n'.join(section_content)
    
    # Extract header (everything before the first section)
    header_end = content.find('## Phase 1')
    header = content[:header_end].strip()
    
    return header, sections

def update_improvement_status(sections, improvement_id, new_status, assigned_to=None, completion_date=None, notes=None):
    """Update the status of a specific improvement in the sections."""
    phase_num = int(improvement_id.split('.')[0])
    section_key = f"## Phase {phase_num}: " + {
        1: "Critical Security Fundamentals",
        2: "Core Infrastructure & Testing",
        3: "Validator & Network Enhancements",
        4: "Monitoring & Documentation"
    }[phase_num]
    
    if section_key not in sections:
        print(f"Error: Section {section_key} not found")
        return False
    
    section_lines = sections[section_key].split('\n')
    table_start = next((i for i, line in enumerate(section_lines) if line.startswith('| ID |')), -1)
    
    if table_start == -1:
        print(f"Error: Table not found in section {section_key}")
        return False
    
    # Find the row with the improvement ID
    row_index = -1
    for i, line in enumerate(section_lines[table_start+2:], table_start+2):
        if line.startswith(f'| {improvement_id} |'):
            row_index = i
            break
    
    if row_index == -1:
        print(f"Error: Improvement ID {improvement_id} not found")
        return False
    
    # Parse the current row
    row = section_lines[row_index]
    columns = [col.strip() for col in row.split('|')[1:-1]]
    
    # Update status
    columns[3] = STATUS_EMOJIS[new_status]
    
    # Update assigned to if provided
    if assigned_to is not None:
        columns[5] = assigned_to
    
    # Update completion date if provided
    if completion_date is not None:
        columns[7] = completion_date
    elif new_status == "completed" and not columns[7]:
        columns[7] = datetime.now().strftime("%Y-%m-%d")
    
    # Update notes if provided
    if notes is not None:
        columns[8] = notes
    
    # Reconstruct the row
    new_row = '| ' + ' | '.join(columns) + ' |'
    section_lines[row_index] = new_row
    
    # Update the section
    sections[section_key] = '\n'.join(section_lines)
    return True

def calculate_progress_summary(sections):
    """Calculate the progress summary based on the current status of all improvements."""
    phase_stats = {}
    
    # Initialize stats for each phase
    for i in range(1, 5):
        phase_stats[i] = {"total": 0, "not_started": 0, "in_progress": 0, "testing": 0, "completed": 0}
    
    # Count improvements by status for each phase
    for phase_num in range(1, 5):
        section_key = f"## Phase {phase_num}: " + {
            1: "Critical Security Fundamentals",
            2: "Core Infrastructure & Testing",
            3: "Validator & Network Enhancements",
            4: "Monitoring & Documentation"
        }[phase_num]
        
        if section_key not in sections:
            continue
        
        section_lines = sections[section_key].split('\n')
        table_start = next((i for i, line in enumerate(section_lines) if line.startswith('| ID |')), -1)
        
        if table_start == -1:
            continue
        
        # Count improvements by status
        for line in section_lines[table_start+2:]:
            if not line.startswith('|'):
                break
            
            columns = [col.strip() for col in line.split('|')[1:-1]]
            if len(columns) < 4:
                continue
            
            phase_stats[phase_num]["total"] += 1
            
            status = columns[3].lower()
            if "not started" in status:
                phase_stats[phase_num]["not_started"] += 1
            elif "in progress" in status:
                phase_stats[phase_num]["in_progress"] += 1
            elif "testing" in status:
                phase_stats[phase_num]["testing"] += 1
            elif "completed" in status:
                phase_stats[phase_num]["completed"] += 1
    
    # Calculate totals
    totals = {
        "total": sum(stats["total"] for stats in phase_stats.values()),
        "not_started": sum(stats["not_started"] for stats in phase_stats.values()),
        "in_progress": sum(stats["in_progress"] for stats in phase_stats.values()),
        "testing": sum(stats["testing"] for stats in phase_stats.values()),
        "completed": sum(stats["completed"] for stats in phase_stats.values())
    }
    
    # Generate progress summary table
    summary_lines = [
        "## Progress Summary",
        "",
        "| Phase | Total Items | Not Started | In Progress | Testing | Completed | Progress |",
        "|-------|------------|-------------|-------------|---------|-----------|----------|"
    ]
    
    for phase_num in range(1, 5):
        stats = phase_stats[phase_num]
        if stats["total"] > 0:
            progress = round((stats["completed"] / stats["total"]) * 100)
        else:
            progress = 0
        
        summary_lines.append(
            f"| Phase {phase_num} | {stats['total']} | {stats['not_started']} | {stats['in_progress']} | "
            f"{stats['testing']} | {stats['completed']} | {progress}% |"
        )
    
    # Add total row
    if totals["total"] > 0:
        total_progress = round((totals["completed"] / totals["total"]) * 100)
    else:
        total_progress = 0
    
    summary_lines.append(
        f"| **Total** | **{totals['total']}** | **{totals['not_started']}** | **{totals['in_progress']}** | "
        f"**{totals['testing']}** | **{totals['completed']}** | **{total_progress}%** |"
    )
    
    summary_lines.append("")
    
    return "\n".join(summary_lines)

def update_last_updated(sections):
    """Update the last updated section with the current date."""
    sections["## Last Updated"] = f"## Last Updated\n\n{datetime.now().strftime('%B %d, %Y')}"
    return sections

def save_tracker_file(file_path, header, sections):
    """Save the updated tracker file."""
    # Order of sections
    section_order = [
        "## Phase 1: Critical Security Fundamentals",
        "## Phase 2: Core Infrastructure & Testing",
        "## Phase 3: Validator & Network Enhancements",
        "## Phase 4: Monitoring & Documentation",
        "## Progress Summary",
        "## Implementation Notes",
        "## Last Updated"
    ]
    
    # Recalculate progress summary
    sections["## Progress Summary"] = calculate_progress_summary(sections)
    
    # Update last updated date
    sections = update_last_updated(sections)
    
    # Combine all sections in order
    content = header + "\n\n"
    for section_key in section_order:
        if section_key in sections:
            content += sections[section_key] + "\n\n"
    
    with open(file_path, 'w') as f:
        f.write(content.strip() + "\n")

def print_usage():
    """Print usage instructions."""
    print("Usage: python update_tracker.py <improvement_id> <status> [options]")
    print("\nArguments:")
    print("  improvement_id    ID of the improvement to update (e.g., 1.1, 2.3)")
    print("  status           New status: not_started, in_progress, testing, completed")
    print("\nOptions:")
    print("  --assigned-to <name>    Person assigned to the improvement")
    print("  --notes <text>          Notes about the implementation")
    print("\nExample:")
    print("  python update_tracker.py 1.1 in_progress --assigned-to 'John Doe'")
    print("  python update_tracker.py 1.1 completed --notes 'Implemented with SHA-256 nonces'")

def main():
    """Main function."""
    if len(sys.argv) < 3:
        print_usage()
        return
    
    improvement_id = sys.argv[1]
    new_status = sys.argv[2].lower()
    
    if new_status not in STATUS_EMOJIS:
        print(f"Error: Invalid status '{new_status}'. Must be one of: not_started, in_progress, testing, completed")
        return
    
    # Parse optional arguments
    assigned_to = None
    notes = None
    
    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == "--assigned-to" and i + 1 < len(sys.argv):
            assigned_to = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--notes" and i + 1 < len(sys.argv):
            notes = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    # Get the tracker file path
    project_root = Path(__file__).parent.parent
    tracker_file = project_root / "docs" / "IMPROVEMENT_TRACKER.md"
    
    if not tracker_file.exists():
        print(f"Error: Tracker file not found at {tracker_file}")
        return
    
    # Parse the tracker file
    header, sections = parse_tracker_file(tracker_file)
    
    # Update the improvement status
    completion_date = datetime.now().strftime("%Y-%m-%d") if new_status == "completed" else None
    success = update_improvement_status(sections, improvement_id, new_status, assigned_to, completion_date, notes)
    
    if not success:
        return
    
    # Save the updated tracker file
    save_tracker_file(tracker_file, header, sections)
    
    print(f"Successfully updated improvement {improvement_id} to status '{new_status}'")
    print(f"Tracker file updated: {tracker_file}")

if __name__ == "__main__":
    main()
