"""
Run ELO tournament to rank creative writing stories.

This script loads stories from the generated batch, runs an ELO tournament using
LLM judges to compare stories, and saves the updated rankings.
"""

import asyncio
import json
import os
import glob
from typing import List, Dict, Any

from lib.elo_rank import EloRankingSystem, load_stories_from_json


def load_config() -> Dict[str, Any]:
    """Load configuration from config.json."""
    with open("config.json", "r") as f:
        return json.load(f)


def find_most_recent_batch(output_dir: str) -> str:
    """
    Find the most recent batch file based on modification time.
    
    Args:
        output_dir: Output directory to search in
        
    Returns:
        Path to the most recent batch file
    """
    # Look for story batch files
    batch_patterns = [
        "batch*_stories.json",
        "*stories.json"
    ]
    
    all_batch_files = []
    for pattern in batch_patterns:
        pattern_path = os.path.join(output_dir, pattern)
        files = glob.glob(pattern_path)
        all_batch_files.extend(files)
    
    if not all_batch_files:
        raise FileNotFoundError(f"No batch files found in {output_dir}")
    
    # Sort by modification time (most recent first)
    all_batch_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    
    most_recent = all_batch_files[0]
    print(f"Found {len(all_batch_files)} batch files, using most recent: {os.path.basename(most_recent)}")
    
    # Show all available files for reference
    if len(all_batch_files) > 1:
        print("Available batch files (by modification time):")
        for i, file_path in enumerate(all_batch_files):
            import datetime
            mtime = os.path.getmtime(file_path)
            mtime_str = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            status = "← USING" if i == 0 else ""
            print(f"  {os.path.basename(file_path)} ({mtime_str}) {status}")
    
    return most_recent


async def main():
    """Main function to run ELO tournament."""
    try:
        # Load configuration
        config = load_config()
        elo_config = config["elo_ranking"]
        output_config = config["output"]
        
        print("Starting ELO Tournament System")
        print(f"Configuration: K-factor={elo_config['k_factor']}, Rounds={elo_config['tournament_rounds']}")
        
        # Find and load most recent batch
        output_dir = output_config["directory"]
        stories_path = find_most_recent_batch(output_dir)
        
        stories = load_stories_from_json(stories_path)
        print(f"Loaded {len(stories)} stories from {os.path.basename(stories_path)}")
        
        if len(stories) < 2:
            print("Need at least 2 stories to run tournament")
            return
        
        # Extract original prompt from stories data
        original_prompt = None
        with open(stories_path, "r") as f:
            stories_data = json.load(f)
            if "stories" in stories_data and len(stories_data["stories"]) > 0:
                original_prompt = stories_data["stories"][0].get("prompt")
        
        if original_prompt:
            print(f"Using original prompt: {original_prompt[:100]}...")
        else:
            print("Warning: No original prompt found in stories data")
        
        # Display initial standings
        print("\nInitial ELO Standings:")
        for i, story in enumerate(sorted(stories, key=lambda s: s.elo, reverse=True)):
            print(f"  {i+1}. {story.story_id[:8]} (Model: {story.model_used}) - ELO: {story.elo}")
        
        # Initialize ELO system
        elo_system = EloRankingSystem(k_factor=elo_config["k_factor"])
        
        # Get rubric file path
        rubric_file = config["input_files"]["rubric_file"]
        print(f"Using rubric from: {rubric_file}")
        
        # Run tournament
        print(f"\nStarting tournament...")
        matches = await elo_system.run_tournament(
            stories=stories,
            num_rounds=elo_config["tournament_rounds"],
            judge_model=elo_config["judge_model"],
            max_concurrent_matches=elo_config["max_concurrent_matches"],
            min_elo_difference=elo_config["min_elo_difference"],
            stories_file_path=stories_path,
            update_after_each_round=elo_config["update_rankings_after_each_round"],
            rubric_file=rubric_file,
            original_prompt=original_prompt
        )
        
        # Display final standings
        print(f"\nTournament Complete! {len(matches)} matches played")
        print("\nFinal ELO Standings:")
        
        leaderboard = elo_system.get_leaderboard(stories)
        for entry in leaderboard:
            print(f"  {entry['rank']}. {entry['story_id'][:8]} (Model: {entry['model_used']}) - "
                  f"ELO: {entry['elo']} | W/L: {entry['wins']}/{entry['losses']} "
                  f"({entry['win_rate']:.1%})")
        
        # Show biggest ELO changes
        print("\nBiggest ELO Changes:")
        elo_changes = []
        for story in stories:
            original_elo = config["batch_generation"]["initial_elo"]
            change = story.elo - original_elo
            elo_changes.append((story, change))
        
        # Sort by absolute change
        elo_changes.sort(key=lambda x: abs(x[1]), reverse=True)
        
        for i, (story, change) in enumerate(elo_changes[:5]):
            direction = "UP" if change > 0 else "DOWN"
            print(f"  {direction}: {story.story_id[:8]} (Model: {story.model_used}): "
                  f"{change:+.1f} (Now: {story.elo:.1f})")
        
        # Show model performance summary
        print("\nModel Performance Summary:")
        model_stats = {}
        for story in stories:
            model = story.model_used
            if model not in model_stats:
                model_stats[model] = {
                    'count': 0, 'total_elo': 0, 'total_wins': 0, 
                    'total_matches': 0, 'stories': []
                }
            
            stats = model_stats[model]
            stats['count'] += 1
            stats['total_elo'] += story.elo
            stats['total_wins'] += story.wins
            stats['total_matches'] += story.matches_played
            stats['stories'].append(story)
        
        for model, stats in model_stats.items():
            avg_elo = stats['total_elo'] / stats['count']
            win_rate = stats['total_wins'] / stats['total_matches'] if stats['total_matches'] > 0 else 0
            print(f"  {model}: Avg ELO: {avg_elo:.1f}, Win Rate: {win_rate:.1%}, Stories: {stats['count']}")
        
        # Save results
        print(f"\nSaving results...")
        elo_system.save_results(
            stories=stories,
            output_dir=output_config["directory"],
            elo_results_file=output_config["elo_results_file"],
            match_history_file=output_config["match_history_file"],
            save_match_history=elo_config["save_match_history"]
        )
        
        # Update original stories file with new ELO ratings
        updated_stories_data = {
            "generated_at": None,  # Will be set from original file
            "tournament_completed_at": elo_system.match_history[-1].timestamp if elo_system.match_history else None,
            "total_stories": len(stories),
            "stories": [
                {
                    "story_id": story.story_id,
                    "prompt": None,  # Will be set from original file
                    "piece": story.piece,
                    "model_used": story.model_used,
                    "elo": story.elo,
                    "created_at": None,  # Will be set from original file
                    "generation_attempt": None,  # Will be set from original file
                    "matches_played": story.matches_played,
                    "wins": story.wins,
                    "losses": story.losses
                }
                for story in stories
            ]
        }
        
        # Load original data to preserve metadata
        with open(stories_path, "r") as f:
            original_data = json.load(f)
        
        # Merge original metadata with updated ELO data
        updated_stories_data["generated_at"] = original_data.get("generated_at")
        
        for i, original_story in enumerate(original_data.get("stories", [])):
            if i < len(updated_stories_data["stories"]):
                updated_story = updated_stories_data["stories"][i]
                updated_story["prompt"] = original_story.get("prompt")
                updated_story["created_at"] = original_story.get("created_at")
                updated_story["generation_attempt"] = original_story.get("generation_attempt")
        
        # Save updated stories file
        with open(stories_path, "w") as f:
            json.dump(updated_stories_data, f, indent=2)
        
        print(f"Updated stories file with new ELO ratings: {stories_path}")
        
        print(f"\nTournament complete! Check {output_config['directory']} for detailed results.")
        
    except Exception as e:
        print(f"Error during tournament: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())