"""
Tournament Runner Module

Handles Glicko-2 tournament operations for ranking stories.
"""

import asyncio
import json
import os
import glob
from typing import List, Dict, Any
from datetime import datetime

from .glicko_rank import GlickoRankingSystem, load_stories_from_json


class TournamentRunner:
    """Manages Glicko-2 tournament operations."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def find_most_recent_batch(self, output_dir: str) -> str:
        """Find the most recent batch file based on modification time."""
        batch_patterns = ["batch*_stories.json", "*stories.json"]
        
        all_batch_files = []
        for pattern in batch_patterns:
            pattern_path = os.path.join(output_dir, pattern)
            files = glob.glob(pattern_path)
            all_batch_files.extend(files)
        
        if not all_batch_files:
            raise FileNotFoundError(f"No batch files found in {output_dir}")
        
        all_batch_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        
        most_recent = all_batch_files[0]
        print(f"Found {len(all_batch_files)} batch files, using most recent: {os.path.basename(most_recent)}")
        
        if len(all_batch_files) > 1:
            print("Available batch files (by modification time):")
            for i, file_path in enumerate(all_batch_files):
                mtime = os.path.getmtime(file_path)
                mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                status = "← USING" if i == 0 else ""
                print(f"  {os.path.basename(file_path)} ({mtime_str}) {status}")
        
        return most_recent
    
    def _update_stories_file(self, stories: List[Dict[str, Any]], stories_file_path: str):
        """Update the stories file with current Glicko ratings and match stats."""
        try:
            with open(stories_file_path, "r") as f:
                original_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            original_data = {"stories": []}
            
        story_map = {story['story_id']: story for story in stories}
        
        updated_stories = []
        for story_data in original_data.get("stories", []):
            story_id = story_data.get("story_id")
            if story_id in story_map:
                updated_story = story_map[story_id]
                story_data.update(updated_story)
            updated_stories.append(story_data)

        original_data["stories"] = updated_stories
        original_data["last_rating_update"] = datetime.now().isoformat()

        with open(stories_file_path, "w") as f:
            json.dump(original_data, f, indent=2)

    async def run_tournament(self) -> int:
        """Run Glicko-2 tournament and return number of matches played."""
        glicko_config = self.config["glicko_ranking"]
        batch_config = self.config["batch_generation"]
        output_config = self.config["output"]
        
        print("Starting Glicko-2 Tournament System")
        print(f"Configuration: Tau={glicko_config['tau']}, Rounds={glicko_config['tournament_rounds']}")
        
        output_dir = output_config["directory"]
        stories_path = self.find_most_recent_batch(output_dir)
        
        stories = load_stories_from_json(
            stories_path,
            default_rating=batch_config['glicko_initial_rating'],
            default_rd=batch_config['glicko_initial_rd'],
            default_sigma=batch_config['glicko_initial_volatility']
        )
        print(f"Loaded {len(stories)} stories from {os.path.basename(stories_path)}")
        
        if len(stories) < 2:
            print("Warning: Need at least 2 stories to run tournament. Skipping.")
            return 0
        
        # Capture initial ratings for change calculation
        initial_ratings = {story.story_id: story.rating for story in stories}
        
        original_prompt = None
        if stories:
            # A bit of a hack to get prompt from the first story's data
            with open(stories_path, "r") as f:
                data = json.load(f)
                story_data = next((s for s in data.get("stories", []) if s.get("story_id") == stories[0].story_id), None)
                if story_data:
                    original_prompt = story_data.get("prompt")
        
        print("\nInitial Glicko Standings:")
        for i, story in enumerate(sorted(stories, key=lambda s: s.rating, reverse=True)[:10]):
            print(f"  {i+1}. {story.story_id[:8]} (Model: {story.model_used}) - Rating: {story.rating:.1f} (RD: {story.rd:.1f})")
        
        glicko_system = GlickoRankingSystem(tau=glicko_config["tau"])
        
        rubric_file = self.config["input_files"]["rubric_file"]
        
        print(f"\nStarting tournament...")
        matches_played = await glicko_system.run_tournament(
            stories=stories,
            num_rounds=glicko_config["tournament_rounds"],
            judge_model=glicko_config["judge_model"],
            max_concurrent_matches=glicko_config["max_concurrent_matches"],
            rubric_file=rubric_file,
            original_prompt=original_prompt
        )
        
        print("\nTournament Complete! {len(matches_played)} matches played")
        print("\nFinal Glicko Standings:")
        
        leaderboard = glicko_system.get_leaderboard(stories)
        for entry in leaderboard[:15]: # Show top 15
            print(f"  {entry['rank']}. {entry['story_id'][:8]} (M: {entry['model_used']}) - "
                  f"Rating: {entry['rating']:.1f} (±{entry['rd']:.0f}) | W/L: {entry['wins']}/{entry['losses']} "
                  f"({entry['win_rate']:.1%})")
        
        print("\nBiggest Rating Changes:")
        rating_changes = []
        for story in stories:
            initial_rating = initial_ratings.get(story.story_id, batch_config['glicko_initial_rating'])
            change = story.rating - initial_rating
            rating_changes.append((story, change))
        
        rating_changes.sort(key=lambda x: abs(x[1]), reverse=True)
        
        for i, (story, change) in enumerate(rating_changes[:5]):
            direction = "UP" if change > 0 else "DOWN"
            print(f"  {direction}: {story.story_id[:8]} (M: {story.model_used}): "
                  f"{change:+.1f} (Now: {story.rating:.1f})")
        
        print("\nModel Performance Summary:")
        model_stats = {}
        for story in stories:
            model = story.model_used
            if model not in model_stats:
                model_stats[model] = {
                    'count': 0, 'total_rating': 0, 'total_wins': 0, 
                    'total_matches': 0
                }
            
            stats = model_stats[model]
            stats['count'] += 1
            stats['total_rating'] += story.rating
            stats['total_wins'] += story.wins
            stats['total_matches'] += story.matches_played
        
        for model, stats in model_stats.items():
            if stats['count'] > 0:
                avg_rating = stats['total_rating'] / stats['count']
                win_rate = stats['total_wins'] / stats['total_matches'] if stats['total_matches'] > 0 else 0
                print(f"  - {model}: Avg Rating: {avg_rating:.1f}, Win Rate: {win_rate:.1%}, Stories: {stats['count']}")

        updated_story_data = [s.__dict__ for s in stories]
        self._update_stories_file(updated_story_data, stories_path)
        print(f"\nUpdated stories file with new ratings: {stories_path}")

        print(f"\nSaving results...")
        glicko_system.save_results(
            stories=stories,
            output_dir=output_config["directory"],
            results_file=output_config["elo_results_file"],
            history_file=output_config["match_history_file"],
            save_history=glicko_config["save_match_history"]
        )
        
        print(f"\nTournament complete! Check {output_config['directory']} for detailed results.")
        
        return matches_played