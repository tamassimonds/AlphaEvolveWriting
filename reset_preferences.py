#!/usr/bin/env python3
"""
Reset preference data for story testing.

This script clears all preference data when you want to start fresh.
Data normally persists between sessions - only run this when you want to reset.
"""

import os
import json
from datetime import datetime

def reset_preference_data():
    """Reset all preference data files."""
    files_to_reset = [
        "output/preference_data.json",
        "output/live_percentages.json"
    ]
    
    reset_count = 0
    
    for file_path in files_to_reset:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"✅ Deleted: {file_path}")
                reset_count += 1
            except Exception as e:
                print(f"❌ Error deleting {file_path}: {e}")
        else:
            print(f"⚠️  File not found: {file_path}")
    
    if reset_count > 0:
        print(f"\n🎉 Reset complete! Deleted {reset_count} preference files.")
        print("You can now start fresh with preference testing.")
    else:
        print("\n📭 No preference files found to reset.")

def backup_preference_data():
    """Create a backup of current preference data before resetting."""
    backup_dir = "output/backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    files_to_backup = [
        "output/preference_data.json",
        "output/live_percentages.json"
    ]
    
    backup_count = 0
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            try:
                filename = os.path.basename(file_path)
                backup_path = os.path.join(backup_dir, f"{timestamp}_{filename}")
                
                with open(file_path, 'r') as src:
                    data = json.load(src)
                
                with open(backup_path, 'w') as dst:
                    json.dump(data, dst, indent=2)
                
                print(f"💾 Backed up: {file_path} → {backup_path}")
                backup_count += 1
                
            except Exception as e:
                print(f"❌ Error backing up {file_path}: {e}")
    
    return backup_count

if __name__ == "__main__":
    print("🔄 Preference Data Reset Utility")
    print("=" * 40)
    
    # Check if there's data to backup
    has_data = os.path.exists("output/preference_data.json") and os.path.getsize("output/preference_data.json") > 0
    
    if has_data:
        response = input("📋 Existing preference data found. Create backup first? (y/n): ").lower().strip()
        
        if response in ['y', 'yes']:
            backup_count = backup_preference_data()
            if backup_count > 0:
                print(f"✅ Created backup of {backup_count} files")
        else:
            print("⚠️  Skipping backup")
    
    print("\n🗑️  Resetting preference data...")
    reset_preference_data()
    
    print("\n📊 Next steps:")
    print("1. Restart the web interface: cd web_interface && python app.py")
    print("2. Begin fresh preference testing")
    print("3. Check output/live_percentages.json for real-time stats")