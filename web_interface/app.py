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

def get_random_story_pair(batch1_name: str, batch2_name: str) -> Tuple[Dict[str, Any], Dict[str, Any], str, str]:
    """Get a random story from each batch for comparison."""
    batch1_stories = story_batches.get(batch1_name, [])
    batch2_stories = story_batches.get(batch2_name, [])
    
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
    
    # Save to file
    with open("../output/preference_data.json", "w") as f:
        json.dump(preference_data, f, indent=2)

def load_preferences() -> None:
    """Load existing preference data if available."""
    global preference_data
    
    try:
        with open("../output/preference_data.json", "r") as f:
            preference_data = json.load(f)
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
    
    # Store current comparison for preference submission
    current_comparison = {
        "story1": story1,
        "story2": story2,
        "batch1": b1,
        "batch2": b2
    }
    
    # Get statistics for this batch comparison
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
    
    if not current_comparison:
        return jsonify({"error": "No active comparison"}), 400
    
    preferred_story = request.json.get('preferred_story')
    if preferred_story not in ['story1', 'story2']:
        return jsonify({"error": "Invalid preference"}), 400
    
    # Generate a simple user session ID (in a real app, use proper session management)
    user_session = request.headers.get('User-Agent', 'unknown')[:50]
    
    # Save the preference
    save_preference(
        story1_id=current_comparison['story1']['story_id'],
        story2_id=current_comparison['story2']['story_id'],
        batch1=current_comparison['batch1'],
        batch2=current_comparison['batch2'],
        preferred_story=preferred_story,
        user_session=user_session
    )
    
    return jsonify({"success": True})

@app.route('/next_comparison/<batch1>/<batch2>')
def next_comparison(batch1: str, batch2: str):
    """Get the next random comparison for the same batch pair."""
    return redirect(url_for('compare_batches', batch1=batch1, batch2=batch2))

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
    print("Visit http://localhost:5000 to use the preference testing interface")
    
    app.run(debug=True, host='0.0.0.0', port=5000)