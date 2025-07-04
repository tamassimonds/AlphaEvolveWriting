"""
Web application for human preference testing of story batches.

This Flask app allows users to compare stories from different batches and track
human preferences to validate the evolutionary story generation process.
"""

import json
import os
import random
import re
import sqlite3
import sys
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from flask import Flask, render_template, request, jsonify, redirect, url_for, g

app = Flask(__name__)

# Add parent directory to path to access story files
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = "../output/alphaevolve.db"

def get_db() -> sqlite3.Connection:
    """Opens a new database connection if there is none yet for the current application context."""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    """Closes the database again at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def get_batch_names() -> List[str]:
    """
    Get all unique batch names from the database, formatted for display.
    DB batch_number 0 -> 'initial_stories'
    DB batch_number 1 -> 'batch2_stories', etc.
    """
    cursor = get_db().cursor()
    cursor.execute("SELECT DISTINCT batch_number FROM stories ORDER BY batch_number")
    rows = cursor.fetchall()
    return [f"{'initial_stories' if r['batch_number'] == 0 else f'batch{r['batch_number'] + 1}_stories'}" for r in rows]

def get_batch_number_from_name(batch_name: str) -> int:
    """
    Convert a display batch name string to its integer number for DB queries.
    'initial_stories' -> 0
    'batch2_stories' -> 1, etc.
    """
    if "initial" in batch_name:
        return 0
    match = re.search(r'batch(\d+)', batch_name)
    if match:
        return int(match.group(1)) - 1
    raise ValueError(f"Could not parse batch number from name: {batch_name}")


def get_stories_for_comparison(batch_name: str) -> List[Dict[str, Any]]:
    """Get stories for comparison: all for initial, top 5 for evolved batches."""
    batch_number = get_batch_number_from_name(batch_name)
    cursor = get_db().cursor()
    
    if "initial" in batch_name.lower():
        cursor.execute("SELECT * FROM stories WHERE batch_number = ?", (batch_number,))
    else:
        cursor.execute("SELECT * FROM stories WHERE batch_number = ? ORDER BY rating DESC LIMIT 5", (batch_number,))
    
    return [dict(row) for row in cursor.fetchall()]

def get_random_story_pair(batch1_name: str, batch2_name: str) -> Tuple[Dict[str, Any], Dict[str, Any], str, str]:
    """Get a random story pair for comparison."""
    batch1_stories = get_stories_for_comparison(batch1_name)
    batch2_stories = get_stories_for_comparison(batch2_name)
    
    if not batch1_stories or not batch2_stories:
        return None, None, None, None
    
    story1 = random.choice(batch1_stories)
    story2 = random.choice(batch2_stories)
    
    return story1, story2, batch1_name, batch2_name

def calculate_batch_stats(batch1_name: str, batch2_name: str) -> Dict[str, Any]:
    """Calculate preference statistics between two batches from the database."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN preferred_batch_name = ? THEN 1 ELSE 0 END) as b1_wins,
            SUM(CASE WHEN preferred_batch_name = ? THEN 1 ELSE 0 END) as b2_wins
        FROM human_preferences
        WHERE (batch1_name = ? AND batch2_name = ?) OR (batch1_name = ? AND batch2_name = ?)
    """, (batch1_name, batch2_name, batch1_name, batch2_name, batch2_name, batch1_name))
    
    row = cursor.fetchone()
    if not row or row['total'] == 0:
        return {"total_comparisons": 0, "batch1_wins": 0, "batch2_wins": 0, "batch1_percentage": 0, "batch2_percentage": 0}
    
    total = row['total']
    b1_wins = row['b1_wins'] or 0
    b2_wins = row['b2_wins'] or 0
    
    return {
        "total_comparisons": total,
        "batch1_wins": b1_wins,
        "batch2_wins": b2_wins,
        "batch1_percentage": round((b1_wins / total * 100), 1) if total > 0 else 0,
        "batch2_percentage": round((b2_wins / total * 100), 1) if total > 0 else 0
    }

def get_random_match_for_testing() -> Optional[Dict[str, Any]]:
    """Get a random match from match history for judge testing."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM matches ORDER BY RANDOM() LIMIT 1")
    match = cursor.fetchone()
    if not match:
        return None
    
    match_data = dict(match)
    
    cursor.execute("SELECT * FROM stories WHERE story_id IN (?, ?)", (match_data['story1_id'], match_data['story2_id']))
    stories = {dict(row)['story_id']: dict(row) for row in cursor.fetchall()}
    
    if not stories or len(stories) != 2:
        return None
        
    match_data['story1'] = stories[match_data['story1_id']]
    match_data['story2'] = stories[match_data['story2_id']]
    
    return match_data

# Global variables to hold transient state for a user's comparison
current_comparison = None
current_judge_test = None

@app.route('/')
def index():
    """Main page showing available batches and overall statistics."""
    conn = get_db()
    cursor = conn.cursor()
    
    batch_names = get_batch_names()
    
    cursor.execute("SELECT COUNT(*) FROM human_preferences")
    total_preferences = cursor.fetchone()[0]
    
    batch_comparisons = {}
    if len(batch_names) >= 2:
        for i, batch1 in enumerate(batch_names):
            for batch2 in batch_names[i+1:]:
                key = f"{batch1}_vs_{batch2}"
                batch_comparisons[key] = calculate_batch_stats(batch1, batch2)

    cursor.execute("SELECT COUNT(*), SUM(correct) FROM judge_tests")
    total_tests, correct_tests = cursor.fetchone()
    total_judge_tests = total_tests or 0
    correct_judge_tests = correct_tests or 0
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
    
    story1, story2, b1_name, b2_name = get_random_story_pair(batch1, batch2)
    
    if not story1 or not story2:
        return "No stories available for comparison", 404
    
    # Randomize which story appears on the left (story A) vs right (story B)
    if random.choice([True, False]):
        storyA, storyB, batchA, batchB = story1, story2, b1_name, b2_name
    else:
        storyA, storyB, batchA, batchB = story2, story1, b2_name, b1_name
    
    current_comparison = {
        "storyA": storyA, "storyB": storyB, 
        "batchA": batchA, "batchB": batchB,
        "original_batch1": batch1, "original_batch2": batch2
    }
    
    stats = calculate_batch_stats(batch1, batch2)
    
    return render_template('compare.html',
                         story1=storyA, story2=storyB, batch1=batchA, batch2=batchB, stats=stats)

@app.route('/submit_preference', methods=['POST'])
def submit_preference():
    """Submit a user preference for the current comparison."""
    global current_comparison
    
    try:
        if not current_comparison:
            return jsonify({"error": "No active comparison"}), 400
        
        preferred_story_pos = request.json.get('preferred_story') # "story1" or "story2"
        
        if preferred_story_pos not in ['story1', 'story2']:
            return jsonify({"error": "Invalid preference"}), 400

        story1 = current_comparison['storyA']
        story2 = current_comparison['storyB']
        
        if preferred_story_pos == 'story1':
            preferred_id = story1['story_id']
            preferred_batch = current_comparison['batchA']
        else:
            preferred_id = story2['story_id']
            preferred_batch = current_comparison['batchB']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO human_preferences (timestamp, story1_id, story2_id, preferred_story_id, user_session, batch1_name, batch2_name, preferred_batch_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(), story1['story_id'], story2['story_id'], preferred_id,
            request.headers.get('User-Agent', 'unknown')[:100],
            current_comparison['original_batch1'], current_comparison['original_batch2'], preferred_batch
        ))
        conn.commit()
        
        return jsonify({"success": True})
        
    except Exception as e:
        print(f"Error in submit_preference: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/next_comparison/<batch1>/<batch2>')
def next_comparison(batch1: str, batch2: str):
    return redirect(url_for('compare_batches', batch1=batch1, batch2=batch2))

@app.route('/reset_preferences', methods=['POST'])
def reset_preferences():
    """Reset all human preference and judge test data."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM human_preferences")
        cursor.execute("DELETE FROM judge_tests")
        conn.commit()
        return jsonify({"success": True, "message": "All human-generated data has been reset."})
    except Exception as e:
        return jsonify({"error": f"Failed to reset data: {e}"}), 500

@app.route('/judge_test')
def judge_test():
    """Test yourself against the LLM judge."""
    global current_judge_test
    
    match_data = get_random_match_for_testing()
    
    if not match_data:
        return "No match history available for testing", 404
    
    story1, story2 = match_data['story1'], match_data['story2']
    llm_winner_id = match_data['winner_id']

    # Randomize positions
    if random.choice([True, False]):
        storyA, storyB = story1, story2
        llm_winner_pos = "story1" if llm_winner_id == storyA['story_id'] else "story2"
    else:
        storyA, storyB = story2, story1
        llm_winner_pos = "story1" if llm_winner_id == storyA['story_id'] else "story2"

    current_judge_test = {
        "storyA": storyA, "storyB": storyB, 
        "llm_winner_pos": llm_winner_pos, "match_data": match_data
    }
    
    cursor = get_db().cursor()
    cursor.execute("SELECT COUNT(*), SUM(correct) FROM judge_tests")
    total_tests, correct_tests = cursor.fetchone()
    total_tests = total_tests or 0
    correct_tests = correct_tests or 0
    accuracy = round((correct_tests / total_tests * 100), 1) if total_tests > 0 else 0
    
    return render_template('judge_test.html',
                         story1=storyA, story2=storyB, total_tests=total_tests,
                         correct_tests=correct_tests, accuracy=accuracy)

@app.route('/submit_judge_test', methods=['POST'])
def submit_judge_test():
    """Submit a judge test prediction."""
    global current_judge_test
    try:
        if not current_judge_test: return jsonify({"error": "No active judge test"}), 400
        
        user_prediction_pos = request.json.get('predicted_winner') # story1 or story2
        if user_prediction_pos not in ['story1', 'story2']: return jsonify({"error": "Invalid prediction"}), 400
        
        storyA = current_judge_test["storyA"]
        storyB = current_judge_test["storyB"]
        llm_winner_pos = current_judge_test["llm_winner_pos"]

        user_prediction_id = storyA['story_id'] if user_prediction_pos == 'story1' else storyB['story_id']
        llm_winner_id = storyA['story_id'] if llm_winner_pos == 'story1' else storyB['story_id']
        correct = (user_prediction_id == llm_winner_id)
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO judge_tests (timestamp, story1_id, story2_id, user_prediction_id, llm_winner_id, correct, user_session)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(), storyA['story_id'], storyB['story_id'], user_prediction_id,
            llm_winner_id, correct, request.headers.get('User-Agent', 'unknown')[:100]
        ))
        conn.commit()
        
        explanation = "Correct! You matched the LLM judge." if correct else f"Incorrect. The LLM judge preferred {'Story A' if llm_winner_pos == 'story1' else 'Story B'}."
        
        return jsonify({"success": True, "correct": correct, "user_prediction": user_prediction_pos,
                        "llm_winner": llm_winner_pos, "explanation": explanation})
    except Exception as e:
        return jsonify({"error": f"Server error: {e}"}), 500

if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        print(f"Database file not found at {DB_PATH}.")
        print("Please run the evolution pipeline (`python evolve.py`) at least once to generate data.")
        exit(1)
        
    print("Starting web server...")
    print("Visit http://localhost:8080 to use the preference testing interface")
    
    app.run(debug=True, host='0.0.0.0', port=8080)