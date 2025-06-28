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
judge_test_data = []
current_judge_test = None

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
    """Get top K stories from a batch based on Glicko rating."""
    stories = story_batches.get(batch_name, [])
    if not stories:
        return []
    
    # Sort by rating (highest first), fallback to 1500 if no rating
    sorted_stories = sorted(stories, key=lambda s: s.get("rating", 1500), reverse=True)
    return sorted_stories[:top_k]

def get_stories_for_comparison(batch_name: str) -> List[Dict[str, Any]]:
    """Get stories for comparison - all stories for initial batch, top 5 for evolved batches."""
    stories = story_batches.get(batch_name, [])
    if not stories:
        return []
    
    if "initial" in batch_name.lower():
        return stories
    
    # For evolved batches (batch2, etc.), use top 5 rated stories
    sorted_stories = sorted(stories, key=lambda s: s.get("rating", 1500), reverse=True)
    return sorted_stories[:5]

def get_random_story_pair(batch1_name: str, batch2_name: str) -> Tuple[Dict[str, Any], Dict[str, Any], str, str]:
    """Get a random story pair - any story from initial batch, top 5 from evolved batches."""
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
    
    os.makedirs("../output", exist_ok=True)
    
    preference_file_data = {
        "last_updated": datetime.now().isoformat(),
        "total_preferences": len(preference_data),
        "preferences": preference_data
    }
    
    with open("../output/preference_data.json", "w") as f:
        json.dump(preference_file_data, f, indent=2, ensure_ascii=False)
    
    save_live_percentages()

def save_live_percentages() -> None:
    """Save live percentage statistics for easy viewing."""
    batch_names = list(story_batches.keys())
    live_stats = {
        "last_updated": datetime.now().isoformat(),
        "total_preferences": len(preference_data),
        "batch_comparisons": {}
    }
    
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
    
    with open("../output/live_percentages.json", "w") as f:
        json.dump(live_stats, f, indent=2)

def load_preferences() -> None:
    """Load existing preference data if available."""
    global preference_data
    
    try:
        with open("../output/preference_data.json", "r") as f:
            data = json.load(f)
        
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

def load_match_history() -> List[Dict[str, Any]]:
    """Load match history from the Glicko tournament."""
    try:
        with open("../output/match_history.json", "r") as f:
            data = json.load(f)
        
        if isinstance(data, dict) and "matches" in data:
            return data["matches"]
        elif isinstance(data, list):
            return data
        else:
            return []
    except FileNotFoundError:
        return []

def load_judge_test_data() -> None:
    """Load existing judge test data if available."""
    global judge_test_data
    
    try:
        with open("../output/judge_test_data.json", "r") as f:
            data = json.load(f)
        
        if isinstance(data, dict) and "tests" in data:
            judge_test_data = data["tests"]
        elif isinstance(data, list):
            judge_test_data = data
        else:
            judge_test_data = []
            
        print(f"Loaded {len(judge_test_data)} existing judge tests")
    except FileNotFoundError:
        judge_test_data = []
        print("No existing judge test data found")

def save_judge_test(user_prediction: str, llm_winner: str, story1_id: str, story2_id: str, user_session: str) -> None:
    """Save a judge test result."""
    test_result = {
        "timestamp": datetime.now().isoformat(),
        "story1_id": story1_id,
        "story2_id": story2_id,
        "user_prediction": user_prediction,  # "story1" or "story2"
        "llm_winner": llm_winner,  # "story1" or "story2"
        "correct": user_prediction == llm_winner,
        "user_session": user_session
    }
    
    judge_test_data.append(test_result)
    
    os.makedirs("../output", exist_ok=True)
    
    judge_test_file_data = {
        "last_updated": datetime.now().isoformat(),
        "total_tests": len(judge_test_data),
        "correct_predictions": sum(1 for t in judge_test_data if t["correct"]),
        "accuracy_percentage": round((sum(1 for t in judge_test_data if t["correct"]) / len(judge_test_data) * 100), 1) if judge_test_data else 0,
        "tests": judge_test_data
    }
    
    with open("../output/judge_test_data.json", "w") as f:
        json.dump(judge_test_file_data, f, indent=2, ensure_ascii=False)

def get_random_match_for_testing() -> Tuple[Dict[str, Any], Dict[str, Any], str, str]:
    """Get a random match from match history for judge testing."""
    matches = load_match_history()
    
    if not matches:
        return None, None, None, None
    
    match = random.choice(matches)
    
    story1_id = match["story1_id"]
    story2_id = match["story2_id"]
    winner_id = match["winner_id"]
    
    story1, story2 = None, None
    for batch_name, stories in story_batches.items():
        for story in stories:
            if story["story_id"] == story1_id: story1 = story
            elif story["story_id"] == story2_id: story2 = story
    
    if not story1 or not story2:
        return None, None, None, None
    
    llm_winner_formatted = "story1" if winner_id == story1_id else "story2"
    
    return story1, story2, llm_winner_formatted, match

def calculate_batch_stats(batch1_name: str, batch2_name: str) -> Dict[str, Any]:
    """Calculate preference statistics between two batches."""
    relevant_prefs = [
        p for p in preference_data 
        if (p['batch1'] == batch1_name and p['batch2'] == batch2_name) or
           (p['batch1'] == batch2_name and p['batch2'] == batch1_name)
    ]
    
    if not relevant_prefs:
        return {"total_comparisons": 0}
    
    batch1_wins = sum(1 for p in relevant_prefs if p.get('preferred_batch') == batch1_name)
    batch2_wins = sum(1 for p in relevant_prefs if p.get('preferred_batch') == batch2_name)
    
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
    total_preferences = len(preference_data)
    
    batch_comparisons = {}
    if len(batch_names) >= 2:
        for i, batch1 in enumerate(batch_names):
            for batch2 in batch_names[i+1:]:
                key = f"{batch1}_vs_{batch2}"
                batch_comparisons[key] = calculate_batch_stats(batch1, batch2)
    
    total_judge_tests = len(judge_test_data)
    correct_judge_tests = sum(1 for t in judge_test_data if t["correct"])
    judge_accuracy = round((correct_judge_tests / total_judge_tests * 100), 1) if total_judge_tests > 0 else 0
    
    return render_template('index.html', 
                         batches=batch_names, 
                         total_preferences=total_preferences,
                         batch_comparisons=batch_comparisons,
                         total_judge_tests=total_judge_tests,
                         judge_accuracy=judge_accuracy)

@app.route('/compare/<batch1>/<batch2>')
def compare_batches(batch1: str, batch2: str):
    """Compare stories from two different batches."""
    global current_comparison
    
    if batch1 not in story_batches or batch2 not in story_batches:
        return "Batch not found", 404
    
    story1, story2, b1, b2 = get_random_story_pair(batch1, batch2)
    
    if not story1 or not story2:
        return "No stories available for comparison", 404
    
    if hash(story1['story_id'] + story2['story_id']) % 2 == 0:
        story1, story2 = story2, story1
        b1, b2 = b2, b1
    
    current_comparison = {
        "story1": story1, "story2": story2, "batch1": b1, "batch2": b2,
        "original_batch1": batch1, "original_batch2": batch2
    }
    
    stats = calculate_batch_stats(batch1, batch2)
    
    return render_template('compare.html',
                         story1=story1, story2=story2, batch1=b1, batch2=b2, stats=stats)

@app.route('/submit_preference', methods=['POST'])
def submit_preference():
    """Submit a user preference for the current comparison."""
    global current_comparison
    
    try:
        if not current_comparison:
            return jsonify({"error": "No active comparison"}), 400
        
        preferred_story = request.json.get('preferred_story') if request.is_json else request.form.get('preferred_story')
            
        if preferred_story not in ['story1', 'story2']:
            return jsonify({"error": "Invalid preference"}), 400
        
        user_session = request.headers.get('User-Agent', 'unknown')[:50]
        original_batch1 = current_comparison['original_batch1']
        original_batch2 = current_comparison['original_batch2']
        preferred_batch = current_comparison['batch1'] if preferred_story == 'story1' else current_comparison['batch2']
        mapped_preferred_story = 'story1' if preferred_batch == original_batch1 else 'story2'
        
        save_preference(
            current_comparison['story1']['story_id'], current_comparison['story2']['story_id'],
            original_batch1, original_batch2, mapped_preferred_story, user_session
        )
        
        return jsonify({"success": True})
        
    except Exception as e:
        print(f"Error in submit_preference: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/next_comparison/<batch1>/<batch2>')
def next_comparison(batch1: str, batch2: str):
    return redirect(url_for('compare_batches', batch1=batch1, batch2=batch2))

@app.route('/reset_preferences', methods=['POST'])
def reset_preferences():
    """Reset all preference data."""
    global preference_data
    try:
        preference_data = []
        for file_path in ["../output/preference_data.json", "../output/live_percentages.json"]:
            if os.path.exists(file_path):
                os.remove(file_path)
        return jsonify({"success": True, "message": "Preference data reset successfully"})
    except Exception as e:
        return jsonify({"error": f"Failed to reset preferences: {e}"}), 500

@app.route('/judge_test')
def judge_test():
    """Test yourself against the LLM judge."""
    global current_judge_test
    
    story1, story2, llm_winner, match_data = get_random_match_for_testing()
    
    if not story1 or not story2:
        return "No match history available for testing", 404
    
    if random.choice([True, False]):
        story1, story2 = story2, story1
        llm_winner = "story2" if llm_winner == "story1" else "story1"
    
    current_judge_test = {"story1": story1, "story2": story2, "llm_winner": llm_winner, "match_data": match_data}
    
    total_tests = len(judge_test_data)
    correct_tests = sum(1 for t in judge_test_data if t["correct"])
    accuracy = round((correct_tests / total_tests * 100), 1) if total_tests > 0 else 0
    
    return render_template('judge_test.html',
                         story1=story1, story2=story2, total_tests=total_tests,
                         correct_tests=correct_tests, accuracy=accuracy)

@app.route('/submit_judge_test', methods=['POST'])
def submit_judge_test():
    """Submit a judge test prediction."""
    global current_judge_test
    try:
        if not current_judge_test: return jsonify({"error": "No active judge test"}), 400
        
        user_prediction = request.json.get('predicted_winner') if request.is_json else request.form.get('predicted_winner')
        if user_prediction not in ['story1', 'story2']: return jsonify({"error": "Invalid prediction"}), 400
        
        user_session = request.headers.get('User-Agent', 'unknown')[:50]
        llm_winner = current_judge_test["llm_winner"]
        
        save_judge_test(user_prediction, llm_winner, current_judge_test["story1"]["story_id"],
                        current_judge_test["story2"]["story_id"], user_session)
        
        correct = user_prediction == llm_winner
        explanation = "Correct! You matched the LLM judge." if correct else f"Incorrect. The LLM judge preferred {'Story A' if llm_winner == 'story1' else 'Story B'}."
        
        return jsonify({"success": True, "correct": correct, "user_prediction": user_prediction,
                        "llm_winner": llm_winner, "explanation": explanation})
    except Exception as e:
        return jsonify({"error": f"Server error: {e}"}), 500

if __name__ == '__main__':
    print("Loading story batches...")
    story_batches = load_all_batches()
    
    if not story_batches:
        print("No story batches found! Please run story generation first.")
        exit(1)
    
    print(f"Loaded {len(story_batches)} batches: {list(story_batches.keys())}")
    
    load_preferences()
    load_judge_test_data()
    
    print("Starting web server...")
    print("Visit http://localhost:8080 to use the preference testing interface")
    
    app.run(debug=True, host='0.0.0.0', port=8080)