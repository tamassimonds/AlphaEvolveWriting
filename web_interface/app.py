"""
Web application for human preference testing of story batches.

This Flask app allows users to compare stories from different batches and track
human preferences to validate the evolutionary story generation process.
"""

import json
import os
import random
import glob
import sys
from datetime import datetime
from typing import List, Dict, Any, Tuple
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)

# Add parent directory to path to access story files
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Global variables for story data
story_batches = {}
preference_data = []
current_comparison = None

def load_all_batches() -> Dict[str, List[Dict[str, Any]]]:
    """Load all story batch files from the output directory."""
    batch_files = {}
    output_dir = "../output"  # Relative to web_interface folder
    
    # Find all story batch files
    pattern = os.path.join(output_dir, "*stories.json")
    files = glob.glob(pattern)
    
    for file_path in files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            batch_name = os.path.basename(file_path).replace('.json', '')
            stories = data.get('stories', [])
            
            if stories:
                batch_files[batch_name] = stories
                print(f"Loaded {len(stories)} stories from {batch_name}")
        
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    
    return batch_files

def get_top_stories_from_batch(batch_name: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Get top K stories from a batch based on ELO rating."""
    stories = story_batches.get(batch_name, [])
    if not stories:
        return []
    
    # Sort by ELO rating (highest first), fallback to 1200 if no ELO
    sorted_stories = sorted(stories, key=lambda s: s.get("elo", 1200), reverse=True)
    return sorted_stories[:top_k]

def get_stories_for_comparison(batch_name: str) -> List[Dict[str, Any]]:
    """Get stories for comparison - all stories for initial batch, top 5 ELO for evolved batches."""
    stories = story_batches.get(batch_name, [])
    if not stories:
        return []
    
    # For initial stories, use all stories (no ELO filtering)
    if "initial" in batch_name.lower():
        return stories
    
    # For evolved batches (batch2, batch3, etc.), use top 5 ELO stories
    sorted_stories = sorted(stories, key=lambda s: s.get("elo", 1200), reverse=True)
    return sorted_stories[:5]

def get_random_story_pair(batch1_name: str, batch2_name: str) -> Tuple[Dict[str, Any], Dict[str, Any], str, str]:
    """Get a random story pair - any story from initial batch, top 5 ELO from evolved batches."""
    batch1_stories = get_stories_for_comparison(batch1_name)
    batch2_stories = get_stories_for_comparison(batch2_name)
    
    if not batch1_stories or not batch2_stories:
        return None, None, None, None
    
    story1 = random.choice(batch1_stories)
    story2 = random.choice(batch2_stories)
    
    return story1, story2, batch1_name, batch2_name

def save_preference(story1_id: str, story2_id: str, batch1: str, batch2: str, 
                   preferred_story: str, user_session: str) -> None:
    """Save a user preference to the preference data."""
    preference = {
        "timestamp": datetime.now().isoformat(),
        "story1_id": story1_id,
        "story2_id": story2_id,
        "batch1": batch1,
        "batch2": batch2,
        "preferred_story": preferred_story,  # "story1" or "story2"
        "preferred_batch": batch1 if preferred_story == "story1" else batch2,
        "user_session": user_session
    }
    
    preference_data.append(preference)
    
    # Ensure output directory exists
    os.makedirs("../output", exist_ok=True)
    
    # Save to file with metadata
    preference_file_data = {
        "last_updated": datetime.now().isoformat(),
        "total_preferences": len(preference_data),
        "preferences": preference_data
    }
    
    with open("../output/preference_data.json", "w") as f:
        json.dump(preference_file_data, f, indent=2, ensure_ascii=False)
    
    # Also save real-time percentages for easy viewing
    save_live_percentages()

def save_live_percentages() -> None:
    """Save live percentage statistics for easy viewing."""
    batch_names = list(story_batches.keys())
    live_stats = {
        "last_updated": datetime.now().isoformat(),
        "total_preferences": len(preference_data),
        "batch_comparisons": {}
    }
    
    # Calculate all batch vs batch statistics
    for i, batch1 in enumerate(batch_names):
        for batch2 in batch_names[i+1:]:
            key = f"{batch1}_vs_{batch2}"
            stats = calculate_batch_stats(batch1, batch2)
            live_stats["batch_comparisons"][key] = {
                "batch1": batch1,
                "batch2": batch2,
                "total_comparisons": stats["total_comparisons"],
                "batch1_wins": stats["batch1_wins"],
                "batch2_wins": stats["batch2_wins"],
                "batch1_percentage": stats["batch1_percentage"],
                "batch2_percentage": stats["batch2_percentage"]
            }
    
    # Save live stats
    with open("../output/live_percentages.json", "w") as f:
        json.dump(live_stats, f, indent=2)

def load_preferences() -> None:
    """Load existing preference data if available."""
    global preference_data
    
    try:
        with open("../output/preference_data.json", "r") as f:
            data = json.load(f)
        
        # Handle both old format (list) and new format (dict with preferences key)
        if isinstance(data, list):
            preference_data = data
        elif isinstance(data, dict) and "preferences" in data:
            preference_data = data["preferences"]
        else:
            preference_data = []
            
        print(f"Loaded {len(preference_data)} existing preferences")
    except FileNotFoundError:
        preference_data = []
        print("No existing preference data found")

def calculate_batch_stats(batch1_name: str, batch2_name: str) -> Dict[str, Any]:
    """Calculate preference statistics between two batches."""
    relevant_prefs = [
        p for p in preference_data 
        if (p['batch1'] == batch1_name and p['batch2'] == batch2_name) or
           (p['batch1'] == batch2_name and p['batch2'] == batch1_name)
    ]
    
    if not relevant_prefs:
        return {"total_comparisons": 0}
    
    batch1_wins = 0
    batch2_wins = 0
    
    for pref in relevant_prefs:
        if pref.get('preferred_batch') == batch1_name:
            batch1_wins += 1
        elif pref.get('preferred_batch') == batch2_name:
            batch2_wins += 1
    
    total = len(relevant_prefs)
    batch1_percentage = (batch1_wins / total * 100) if total > 0 else 0
    batch2_percentage = (batch2_wins / total * 100) if total > 0 else 0
    
    return {
        "total_comparisons": total,
        "batch1_wins": batch1_wins,
        "batch2_wins": batch2_wins,
        "batch1_percentage": round(batch1_percentage, 1),
        "batch2_percentage": round(batch2_percentage, 1)
    }

@app.route('/')
def index():
    """Main page showing available batches and overall statistics."""
    batch_names = list(story_batches.keys())
    
    # Calculate overall statistics
    total_preferences = len(preference_data)
    
    # Calculate batch vs batch statistics
    batch_comparisons = {}
    if len(batch_names) >= 2:
        for i, batch1 in enumerate(batch_names):
            for batch2 in batch_names[i+1:]:
                key = f"{batch1}_vs_{batch2}"
                batch_comparisons[key] = calculate_batch_stats(batch1, batch2)
    
    return render_template('index.html', 
                         batches=batch_names, 
                         total_preferences=total_preferences,
                         batch_comparisons=batch_comparisons)

@app.route('/compare/<batch1>/<batch2>')
def compare_batches(batch1: str, batch2: str):
    """Compare stories from two different batches."""
    global current_comparison
    
    if batch1 not in story_batches or batch2 not in story_batches:
        return "Batch not found", 404
    
    story1, story2, b1, b2 = get_random_story_pair(batch1, batch2)
    
    if not story1 or not story2:
        return "No stories available for comparison", 404
    
    # Use a deterministic approach to avoid swapping on reload
    # Base swap decision on story IDs to be consistent across reloads
    swap_stories = hash(story1['story_id'] + story2['story_id']) % 2 == 0
    if swap_stories:
        # Swap the stories and their batch assignments
        story1, story2 = story2, story1
        b1, b2 = b2, b1
    
    # Store current comparison for preference submission
    current_comparison = {
        "story1": story1,
        "story2": story2,
        "batch1": b1,
        "batch2": b2,
        "original_batch1": batch1,  # Store original batch order for stats
        "original_batch2": batch2
    }
    
    # Get statistics for this batch comparison (using original batch order)
    stats = calculate_batch_stats(batch1, batch2)
    
    return render_template('compare.html',
                         story1=story1,
                         story2=story2,
                         batch1=b1,
                         batch2=b2,
                         stats=stats)

@app.route('/submit_preference', methods=['POST'])
def submit_preference():
    """Submit a user preference for the current comparison."""
    global current_comparison
    
    try:
        if not current_comparison:
            return jsonify({"error": "No active comparison"}), 400
        
        # Handle both JSON and form data
        if request.is_json:
            preferred_story = request.json.get('preferred_story')
        else:
            preferred_story = request.form.get('preferred_story')
            
        if preferred_story not in ['story1', 'story2']:
            return jsonify({"error": "Invalid preference"}), 400
        
        # Generate a simple user session ID (in a real app, use proper session management)
        user_session = request.headers.get('User-Agent', 'unknown')[:50]
        
        # Use original batch order for statistics (before any swapping)
        original_batch1 = current_comparison.get('original_batch1', current_comparison['batch1'])
        original_batch2 = current_comparison.get('original_batch2', current_comparison['batch2'])
        
        # Map the preferred story back to the original batch order for accurate stats
        if preferred_story == 'story1':
            preferred_batch = current_comparison['batch1']
        else:
            preferred_batch = current_comparison['batch2']
        
        # Determine which story was preferred in terms of original batch assignment
        if preferred_batch == original_batch1:
            mapped_preferred_story = 'story1'  # Original batch1 was preferred
        else:
            mapped_preferred_story = 'story2'  # Original batch2 was preferred
        
        # Save the preference using original batch order for consistent statistics
        save_preference(
            story1_id=current_comparison['story1']['story_id'],
            story2_id=current_comparison['story2']['story_id'],
            batch1=original_batch1,
            batch2=original_batch2,
            preferred_story=mapped_preferred_story,
            user_session=user_session
        )
        
        return jsonify({"success": True})
        
    except Exception as e:
        print(f"Error in submit_preference: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/next_comparison/<batch1>/<batch2>')
def next_comparison(batch1: str, batch2: str):
    """Get the next random comparison for the same batch pair."""
    return redirect(url_for('compare_batches', batch1=batch1, batch2=batch2))

@app.route('/reset_preferences', methods=['POST'])
def reset_preferences():
    """Reset all preference data."""
    global preference_data
    
    try:
        preference_data = []
        
        # Remove preference files
        files_to_remove = [
            "../output/preference_data.json",
            "../output/live_percentages.json"
        ]
        
        for file_path in files_to_remove:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        return jsonify({"success": True, "message": "Preference data reset successfully"})
        
    except Exception as e:
        print(f"Error resetting preferences: {e}")
        return jsonify({"error": "Failed to reset preferences"}), 500

@app.route('/stats')
def detailed_stats():
    """Show detailed statistics about all preferences."""
    # Overall stats
    total_prefs = len(preference_data)
    
    # Batch vs batch breakdown
    batch_names = list(story_batches.keys())
    detailed_stats = {}
    
    for i, batch1 in enumerate(batch_names):
        for batch2 in batch_names[i+1:]:
            key = f"{batch1} vs {batch2}"
            detailed_stats[key] = calculate_batch_stats(batch1, batch2)
    
    # Recent preferences
    recent_prefs = sorted(preference_data, key=lambda x: x['timestamp'], reverse=True)[:20]
    
    return render_template('stats.html',
                         total_preferences=total_prefs,
                         detailed_stats=detailed_stats,
                         recent_preferences=recent_prefs,
                         batch_names=batch_names)

if __name__ == '__main__':
    print("Loading story batches...")
    story_batches = load_all_batches()
    
    if not story_batches:
        print("No story batches found! Please run story generation first.")
        exit(1)
    
    print(f"Loaded {len(story_batches)} batches: {list(story_batches.keys())}")
    
    load_preferences()
    
    print("Starting web server...")
    print("Visit http://localhost:8080 to use the preference testing interface")
    
    app.run(debug=True, host='0.0.0.0', port=8080)