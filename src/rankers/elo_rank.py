"""
ELO ranking system for creative writing stories.

This module implements an ELO rating system that uses LLM judges to compare stories
and update ratings accordingly. Stories compete in tournaments to establish rankings.
"""

import asyncio
import json
import random
import gc
import psutil
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

from ..generators.judge_response import judge_responses, ModelComparison


@dataclass
class Match:
    """Represents a single match between two stories."""
    story1_id: str
    story2_id: str
    winner_id: str
    story1_elo_before: float
    story2_elo_before: float
    story1_elo_after: float
    story2_elo_after: float
    reasoning: str
    timestamp: str


@dataclass
class Story:
    """Represents a story with its current ELO rating."""
    story_id: str
    piece: str
    model_used: str
    elo: float
    matches_played: int = 0
    wins: int = 0
    losses: int = 0


class EloRankingSystem:
    """ELO ranking system for creative writing stories."""
    
    def __init__(self, k_factor: float = 32):
        """
        Initialize the ELO ranking system.
        
        Args:
            k_factor: The K-factor determines how much ratings change after each match
        """
        self.k_factor = k_factor
        self.match_history: List[Match] = []
    
    def log_memory_usage(self, context: str = ""):
        """Log current memory usage for debugging."""
        try:
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent()
            print(f"📊 {context} - Memory: {memory_mb:.1f}MB, CPU: {cpu_percent:.1f}%")
        except Exception:
            pass  # psutil might not be available
    
    def cleanup_memory(self):
        """Force garbage collection to free memory."""
        gc.collect()
        print("🧹 Memory cleanup performed")
    
    def calculate_expected_score(self, rating_a: float, rating_b: float) -> float:
        """
        Calculate the expected score for player A against player B.
        
        Args:
            rating_a: ELO rating of player A
            rating_b: ELO rating of player B
            
        Returns:
            Expected score (0-1) for player A
        """
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    
    def update_ratings(self, winner_rating: float, loser_rating: float) -> Tuple[float, float]:
        """
        Update ELO ratings after a match.
        
        Args:
            winner_rating: Current rating of the winner
            loser_rating: Current rating of the loser
            
        Returns:
            Tuple of (new_winner_rating, new_loser_rating)
        """
        expected_winner = self.calculate_expected_score(winner_rating, loser_rating)
        expected_loser = self.calculate_expected_score(loser_rating, winner_rating)
        
        new_winner_rating = winner_rating + self.k_factor * (1 - expected_winner)
        new_loser_rating = loser_rating + self.k_factor * (0 - expected_loser)
        
        return new_winner_rating, new_loser_rating
    
    async def conduct_match(
        self,
        story1: Story,
        story2: Story,
        judge_model: str,
        rubric_file: str = "rubric.txt",
        original_prompt: str = None
    ) -> Match:
        """
        Conduct a single match between two stories.
        
        Args:
            story1: First story to compare
            story2: Second story to compare
            judge_model: Model to use for judging
            rubric_file: Path to the rubric file
            original_prompt: The original prompt that generated these stories
            
        Returns:
            Match object with results and updated ratings
        """
        try:
            # Randomize order to avoid judge bias toward first position
            if random.choice([True, False]):
                # Normal order
                first_story, second_story = story1, story2
                is_swapped = False
            else:
                # Swapped order
                first_story, second_story = story2, story1
                is_swapped = True
            
            # Get judge decision with timeout
            comparison = await asyncio.wait_for(
                judge_responses(
                    model_1_response=first_story.piece,
                    model_2_response=second_story.piece,
                    judge_model=judge_model,
                    rubric_file=rubric_file,
                    original_prompt=original_prompt
                ),
                timeout=120.0  # 2 minute timeout per individual match
            )
        except asyncio.TimeoutError:
            raise Exception(f"Judge timeout for match {story1.story_id[:8]} vs {story2.story_id[:8]}")
        except Exception as e:
            raise Exception(f"Judge error for match {story1.story_id[:8]} vs {story2.story_id[:8]}: {e}")
        
        # Determine winner, accounting for potential order swap
        if is_swapped:
            # If order was swapped, model_1 actually refers to story2, model_2 to story1
            winner_story = story2 if comparison.winner == "model_1" else story1
            loser_story = story1 if comparison.winner == "model_1" else story2
        else:
            # Normal order: model_1 refers to story1, model_2 to story2
            winner_story = story1 if comparison.winner == "model_1" else story2
            loser_story = story2 if comparison.winner == "model_1" else story1
        
        # Calculate new ratings
        new_winner_rating, new_loser_rating = self.update_ratings(
            winner_story.elo, loser_story.elo
        )
        
        # Store original ratings
        story1_elo_before = story1.elo
        story2_elo_before = story2.elo
        
        # Update story ratings and stats
        winner_story.elo = new_winner_rating
        loser_story.elo = new_loser_rating
        
        story1.matches_played += 1
        story2.matches_played += 1
        
        if winner_story == story1:
            story1.wins += 1
            story2.losses += 1
        else:
            story2.wins += 1
            story1.losses += 1
        
        # Create match record
        match = Match(
            story1_id=story1.story_id,
            story2_id=story2.story_id,
            winner_id=winner_story.story_id,
            story1_elo_before=story1_elo_before,
            story2_elo_before=story2_elo_before,
            story1_elo_after=story1.elo,
            story2_elo_after=story2.elo,
            reasoning=comparison.reasoning,
            timestamp=datetime.now().isoformat()
        )
        
        self.match_history.append(match)
        return match
    
    def get_match_pairs(
        self,
        stories: List[Story],
        num_rounds: int,
        min_elo_difference: float = 0
    ) -> List[Tuple[Story, Story]]:
        """
        Generate match pairs for tournament rounds.
        
        Args:
            stories: List of stories to create matches for
            num_rounds: Number of tournament rounds
            min_elo_difference: Minimum ELO difference to allow matches
            
        Returns:
            List of story pairs for matches
        """
        pairs = []
        
        for _ in range(num_rounds):
            # Randomly select two different stories
            available_stories = stories.copy()
            
            while len(available_stories) >= 2:
                story1 = random.choice(available_stories)
                available_stories.remove(story1)
                
                # Find a suitable opponent
                valid_opponents = [
                    s for s in available_stories 
                    if abs(s.elo - story1.elo) >= min_elo_difference
                ]
                
                if not valid_opponents:
                    valid_opponents = available_stories
                
                if valid_opponents:
                    story2 = random.choice(valid_opponents)
                    available_stories.remove(story2)
                    pairs.append((story1, story2))
        
        return pairs
    
    async def run_tournament(
        self,
        stories: List[Story],
        num_rounds: int,
        judge_model: str,
        max_concurrent_matches: int = 0,
        min_elo_difference: float = 0,
        stories_file_path: str = None,
        update_after_each_round: bool = True,
        rubric_file: str = "rubric.txt",
        original_prompt: str = None
    ) -> List[Match]:
        """
        Run a tournament with multiple rounds of matches.
        
        Args:
            stories: List of stories to compete
            num_rounds: Number of rounds to play
            judge_model: Model to use for judging
            max_concurrent_matches: Maximum concurrent matches. If 0, unlimited.
            min_elo_difference: Minimum ELO difference for matchmaking
            stories_file_path: Path to stories file to update after each round
            update_after_each_round: Whether to update the stories file after each round
            rubric_file: Path to the rubric file
            original_prompt: The original prompt that generated these stories
            
        Returns:
            List of all matches played
        """
        print(f"Starting tournament with {len(stories)} stories for {num_rounds} rounds")
        self.log_memory_usage("Tournament start")
        
        # Generate match pairs
        match_pairs = self.get_match_pairs(stories, num_rounds, min_elo_difference)
        
        print(f"Generated {len(match_pairs)} matches")
        
        # Determine concurrency. If 0 or less, set to total number of matches for a single batch.
        concurrency = max_concurrent_matches if max_concurrent_matches > 0 else len(match_pairs)
        if concurrency == 0: # handle case where there are no matches
             concurrency = 1

        # Run matches in batches to control concurrency
        all_matches = []
        total_batches = (len(match_pairs) + concurrency - 1) // concurrency
        
        print(f"🔢 Total batches to process: {total_batches}")
        print(f"⚙️  Concurrency setting: {concurrency} matches per batch")
        
        for i in range(0, len(match_pairs), concurrency):
            batch = match_pairs[i:i + concurrency]
            batch_num = i//concurrency + 1
            
            print(f"🏆 Running match batch {batch_num}/{total_batches} ({len(batch)} matches)")
            print(f"   Concurrency: {len(batch)} parallel matches")
            self.log_memory_usage(f"Batch {batch_num} start")
            
            # Special attention to batch 4 where freezing occurs
            if batch_num == 4:
           
                self.cleanup_memory()
                self.log_memory_usage("Batch 4 after cleanup")
            
            try:
                # Create tasks for parallel execution
                tasks = [
                    self.conduct_match(story1, story2, judge_model, rubric_file, original_prompt)
                    for story1, story2 in batch
                ]
                
                print(f"   ⏳ Executing {len(tasks)} matches in parallel...")
                
                # Execute matches in parallel with timeout
                batch_results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=300.0  # 5 minute timeout per batch
                )
                
                print(f"   ✅ Batch {batch_num} completed")
                
                # Process results
                successful_matches = 0
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        error_msg = str(result)
                        # Truncate very long error messages to avoid printing full stories
                        if len(error_msg) > 200:
                            error_msg = error_msg[:200] + "... [truncated]"
                        print(f"   ❌ Match {i+j+1} failed: {error_msg}")
                    else:
                        all_matches.append(result)
                        match = result
                        print(f"   🎯 Match {i+j+1}: {match.winner_id[:8]} wins")
                        successful_matches += 1
                
                print(f"   📊 Batch {batch_num} summary: {successful_matches}/{len(batch)} matches successful")
                
                # Update stories file after each batch if requested
                if update_after_each_round and stories_file_path and len(all_matches) > 0:
                    print(f"   💾 Updating ELO rankings...")
                    self._update_stories_file(stories, stories_file_path)
                    print(f"   ✅ Updated ELO rankings in {stories_file_path}")
                    
            except asyncio.TimeoutError:
                print(f"   ⏰ Batch {batch_num} timed out after 5 minutes")
                print(f"   💡 Consider reducing max_concurrent_matches in config")
                break
            except Exception as e:
                print(f"   💥 Batch {batch_num} failed with error: {e}")
                print(f"   🔄 Continuing with next batch...")
                continue
        
        print(f"Tournament complete! {len(all_matches)} matches played")
        return all_matches
    
    def _update_stories_file(self, stories: List[Story], stories_file_path: str) -> None:
        """
        Update the stories file with current ELO ratings and match stats.
        
        Args:
            stories: List of stories with updated ratings
            stories_file_path: Path to the stories file to update
        """
        import os
        
        # Load original data to preserve metadata
        with open(stories_file_path, "r") as f:
            original_data = json.load(f)
        
        # Create a mapping of story_id to story object for quick lookup
        story_map = {story.story_id: story for story in stories}
        
        # Update the stories in the original data
        for story_data in original_data.get("stories", []):
            story_id = story_data.get("story_id")
            if story_id in story_map:
                story = story_map[story_id]
                story_data["elo"] = story.elo
                story_data["matches_played"] = story.matches_played
                story_data["wins"] = story.wins
                story_data["losses"] = story.losses
        
        # Add tournament update timestamp
        original_data["last_elo_update"] = datetime.now().isoformat()
        
        # Save updated data back to file
        with open(stories_file_path, "w") as f:
            json.dump(original_data, f, indent=2)
    
    def get_leaderboard(self, stories: List[Story]) -> List[Dict[str, Any]]:
        """
        Generate a leaderboard sorted by ELO rating.
        
        Args:
            stories: List of stories to rank
            
        Returns:
            List of story data sorted by ELO (highest first)
        """
        leaderboard = []
        
        for story in sorted(stories, key=lambda s: s.elo, reverse=True):
            win_rate = story.wins / story.matches_played if story.matches_played > 0 else 0
            
            leaderboard.append({
                "rank": len(leaderboard) + 1,
                "story_id": story.story_id,
                "model_used": story.model_used,
                "elo": round(story.elo, 2),
                "matches_played": story.matches_played,
                "wins": story.wins,
                "losses": story.losses,
                "win_rate": round(win_rate, 3)
            })
        
        return leaderboard
    
    def save_results(
        self,
        stories: List[Story],
        output_dir: str,
        elo_results_file: str,
        match_history_file: str,
        save_match_history: bool = True
    ) -> None:
        """
        Save tournament results to files.
        
        Args:
            stories: List of stories with updated ratings
            output_dir: Output directory
            elo_results_file: Filename for ELO results
            match_history_file: Filename for match history
            save_match_history: Whether to save detailed match history
        """
        import os
        
        # Generate leaderboard
        leaderboard = self.get_leaderboard(stories)
        
        # Save ELO results
        elo_data = {
            "tournament_completed_at": datetime.now().isoformat(),
            "total_matches": len(self.match_history),
            "leaderboard": leaderboard,
            "stories": [
                {
                    "story_id": story.story_id,
                    "model_used": story.model_used,
                    "elo": story.elo,
                    "matches_played": story.matches_played,
                    "wins": story.wins,
                    "losses": story.losses
                }
                for story in stories
            ]
        }
        
        elo_path = os.path.join(output_dir, elo_results_file)
        with open(elo_path, "w") as f:
            json.dump(elo_data, f, indent=2)
        
        print(f"ELO results saved to: {elo_path}")
        
        # Save match history if requested
        if save_match_history:
            match_data = {
                "tournament_completed_at": datetime.now().isoformat(),
                "total_matches": len(self.match_history),
                "matches": [
                    {
                        "story1_id": match.story1_id,
                        "story2_id": match.story2_id,
                        "winner_id": match.winner_id,
                        "story1_elo_before": match.story1_elo_before,
                        "story2_elo_before": match.story2_elo_before,
                        "story1_elo_after": match.story1_elo_after,
                        "story2_elo_after": match.story2_elo_after,
                        "reasoning": match.reasoning,
                        "timestamp": match.timestamp
                    }
                    for match in self.match_history
                ]
            }
            
            match_path = os.path.join(output_dir, match_history_file)
            with open(match_path, "w") as f:
                json.dump(match_data, f, indent=2)
            
            print(f"Match history saved to: {match_path}")


def load_stories_from_json(json_path: str) -> List[Story]:
    """
    Load stories from JSON file and convert to Story objects.
    
    Args:
        json_path: Path to the stories JSON file
        
    Returns:
        List of Story objects
    """
    with open(json_path, "r") as f:
        data = json.load(f)
    
    stories = []
    for story_data in data.get("stories", []):
        story = Story(
            story_id=story_data["story_id"],
            piece=story_data["piece"],
            model_used=story_data["model_used"],
            elo=story_data["elo"]
        )
        stories.append(story)
    
    return stories