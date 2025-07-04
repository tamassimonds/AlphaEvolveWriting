"""
Tournament Runner Module

Handles Glicko-2 tournament operations for ranking stories.
"""

import asyncio
import json
import os
import sqlite3
from typing import List, Dict, Any
from datetime import datetime

from .glicko_rank import GlickoRankingSystem, load_stories_from_db, Story


class TournamentRunner:
    """Manages Glicko-2 tournament operations."""
    
    def __init__(self, config: Dict[str, Any], db_connection: sqlite3.Connection):
        self.config = config
        self.conn = db_connection
    
    def _get_latest_batch_number(self) -> int:
        """Find the most recent batch number from the database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(batch_number) FROM stories")
        result = cursor.fetchone()
        return result[0] if result and result[0] is not None else -1

    def _update_stories_in_db(self, stories: List[Story]):
        """Update the stories in the database with current Glicko ratings and match stats."""
        cursor = self.conn.cursor()
        update_data = [
            (s.rating, s.rd, s.sigma, s.matches_played, s.wins, s.losses, s.story_id)
            for s in stories
        ]
        cursor.executemany("""
            UPDATE stories
            SET rating = ?, rd = ?, sigma = ?, matches_played = ?, wins = ?, losses = ?
            WHERE story_id = ?
        """, update_data)
        self.conn.commit()
        print(f"\nUpdated {len(stories)} stories in the database with new ratings.")

    async def run_tournament(self) -> int:
        """Run Glicko-2 tournament and return number of matches played."""
        glicko_config = self.config["glicko_ranking"]
        batch_config = self.config["batch_generation"]
        
        print("Starting Glicko-2 Tournament System")
        print(f"Configuration: Tau={glicko_config['tau']}, Rounds={glicko_config['tournament_rounds']}")
        
        latest_batch_number = self._get_latest_batch_number()
        if latest_batch_number == -1:
            print("Warning: No batches found in the database. Skipping tournament.")
            return 0
        
        stories = load_stories_from_db(self.conn, latest_batch_number)
        print(f"Loaded {len(stories)} stories from batch {latest_batch_number}")
        
        if len(stories) < 2:
            print("Warning: Need at least 2 stories to run tournament. Skipping.")
            return 0
        
        initial_ratings = {story.story_id: story.rating for story in stories}
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT prompt FROM stories WHERE batch_number = ? LIMIT 1", (latest_batch_number,))
        res = cursor.fetchone()
        original_prompt = res['prompt'] if res else None
        
        print("\nInitial Glicko Standings:")
        for i, story in enumerate(sorted(stories, key=lambda s: s.rating, reverse=True)[:10]):
            print(f"  {i+1}. {story.story_id[:8]} (Model: {story.model_used}) - Rating: {story.rating:.1f} (RD: {story.rd:.1f})")
        
        glicko_system = GlickoRankingSystem(config=self.config, tau=glicko_config['tau'])
        
        rubric_file = self.config["input_files"]["rubric_file"]
        
        print(f"\nStarting tournament...")
        matches_played = await glicko_system.run_tournament(
            conn=self.conn,
            stories=stories,
            num_rounds=glicko_config["tournament_rounds"],
            judge_model=glicko_config["judge_model"],
            max_concurrent_matches=glicko_config["max_concurrent_matches"],
            rubric_file=rubric_file,
            original_prompt=original_prompt
        )
        
        parent_stories = [s for s in stories if s.previous_batch_rating is not None]

        if parent_stories:
            print("\n🔄 Normalizing ratings to prevent score drift...")
            rating_diffs = [s.rating - s.previous_batch_rating for s in parent_stories]
            
            if rating_diffs:
                average_drift = sum(rating_diffs) / len(rating_diffs)
                print(f"  - Average rating drift of parents: {average_drift:+.1f} points.")
                
                for story in stories:
                    story.rating -= average_drift
                    story._mu = (story.rating - 1500) / 173.7178
                print(f"  - All {len(stories)} story ratings in this batch have been adjusted to compensate.")
        
        print(f"\nTournament Complete! {matches_played} matches played")
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
        
        for model, stats in sorted(model_stats.items()):
            if stats['count'] > 0:
                avg_rating = stats['total_rating'] / stats['count']
                win_rate = stats['total_wins'] / stats['total_matches'] if stats['total_matches'] > 0 else 0
                print(f"  - {model}: Avg Rating: {avg_rating:.1f}, Win Rate: {win_rate:.1%}, Stories: {stats['count']}")

        self._update_stories_in_db(stories)
        
        print(f"\nTournament complete! All results saved to the database.")
        
        return matches_played