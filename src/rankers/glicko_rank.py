"""
Glicko-2 ranking system for creative writing stories.

This module implements the Glicko-2 rating system. Stories compete in tournaments 
(rating periods) to establish rankings based on their rating, rating deviation (RD),
and volatility.
"""

import asyncio
import json
import random
import gc
import psutil
import os
import math
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field

from ..generators.judge_response import judge_responses, ModelComparison

# Glicko-2 constants
Q = math.log(10) / 400

@dataclass
class MatchResult:
    """Represents a single match result before Glicko updates."""
    story1: 'Story'
    story2: 'Story'
    winner: 'Story'
    loser: 'Story'
    reasoning: str
    timestamp: str

@dataclass
class Story:
    """Represents a story with its current Glicko-2 parameters."""
    story_id: str
    piece: str
    model_used: str
    rating: float = 1500.0
    rd: float = 350.0
    sigma: float = 0.06
    
    matches_played: int = 0
    wins: int = 0
    losses: int = 0

    # Internal Glicko scale values, calculated on initialization
    _mu: float = field(init=False, repr=False)
    _phi: float = field(init=False, repr=False)

    def __post_init__(self):
        self._mu = (self.rating - 1500) / 173.7178
        self._phi = self.rd / 173.7178

    def update_public_ratings(self):
        """Update public rating/rd from internal mu/phi."""
        self.rating = 173.7178 * self._mu + 1500
        self.rd = 173.7178 * self._phi

class GlickoRankingSystem:
    """Glicko-2 ranking system for creative writing stories."""
    
    def __init__(self, tau: float = 0.5):
        """
        Initialize the Glicko-2 ranking system.
        
        Args:
            tau: System constant, determines expected change in volatility over time.
        """
        self.tau = tau
        self.match_history: List[Dict[str, Any]] = []

    def log_memory_usage(self, context: str = ""):
        """Log current memory usage for debugging."""
        try:
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent()
            print(f"📊 {context} - Memory: {memory_mb:.1f}MB, CPU: {cpu_percent:.1f}%")
        except Exception:
            pass

    def cleanup_memory(self):
        """Force garbage collection to free memory."""
        gc.collect()
        print("🧹 Memory cleanup performed")

    def _g(self, phi: float) -> float:
        """The g function in Glicko-2."""
        return 1 / math.sqrt(1 + 3 * Q**2 * phi**2 / math.pi**2)

    def _E(self, mu: float, opponent_mu: float, opponent_phi: float) -> float:
        """The E function, expected outcome."""
        return 1 / (1 + math.exp(-self._g(opponent_phi) * (mu - opponent_mu)))

    def _update_player(self, player: Story, opponents: List[Story], outcomes: List[float]):
        """Update a single player's Glicko-2 parameters after a rating period."""
        if not opponents:
            player._phi = math.sqrt(player._phi**2 + player.sigma**2)
            player.update_public_ratings()
            return

        v_sum = sum(self._g(opp._phi)**2 * self._E(player._mu, opp._mu, opp._phi) * (1 - self._E(player._mu, opp._mu, opp._phi)) for opp in opponents)
        v = 1 / v_sum

        delta_sum = sum(self._g(opponents[i]._phi) * (outcomes[i] - self._E(player._mu, opponents[i]._mu, opponents[i]._phi)) for i in range(len(opponents)))
        delta = v * delta_sum

        a = math.log(player.sigma**2)
        def f(x):
            ex = math.exp(x)
            term1 = (ex * (delta**2 - player._phi**2 - v - ex)) / (2 * (player._phi**2 + v + ex)**2)
            term2 = (x - a) / self.tau**2
            return term1 - term2

        epsilon = 0.000001
        A = a
        if delta**2 > player._phi**2 + v:
            B = math.log(delta**2 - player._phi**2 - v)
        else:
            k = 1
            while f(a - k * self.tau) < 0: k += 1
            B = a - k * self.tau

        fA, fB = f(A), f(B)
        while abs(B - A) > epsilon:
            C = A + (A - B) * fA / (fB - fA)
            fC = f(C)
            if fC * fB < 0: A, fA = B, fB
            else: fA /= 2
            B, fB = C, fC
        
        player.sigma = math.exp(A / 2)
        phi_star = math.sqrt(player._phi**2 + player.sigma**2)
        player._phi = 1 / math.sqrt(1 / phi_star**2 + 1 / v)
        player._mu += player._phi**2 * delta_sum
        player.update_public_ratings()

    async def conduct_match(
        self,
        story1: Story,
        story2: Story,
        judge_model: str,
        rubric_file: str = "rubric.txt",
        original_prompt: str = None
    ) -> Optional[MatchResult]:
        """Conduct a single match and return the result, without updating ratings."""
        try:
            if random.choice([True, False]):
                first_story, second_story, is_swapped = story1, story2, False
            else:
                first_story, second_story, is_swapped = story2, story1, True
            
            comparison = await asyncio.wait_for(
                judge_responses(
                    model_1_response=first_story.piece,
                    model_2_response=second_story.piece,
                    judge_model=judge_model,
                    rubric_file=rubric_file,
                    original_prompt=original_prompt
                ),
                timeout=120.0
            )
        except Exception as e:
            print(f"   ❌ Judge error/timeout for match {story1.story_id[:8]} vs {story2.story_id[:8]}: {e}")
            return None
        
        if is_swapped:
            winner_story = story2 if comparison.winner == "model_1" else story1
        else:
            winner_story = story1 if comparison.winner == "model_1" else story2
        
        loser_story = story2 if winner_story.story_id == story1.story_id else story1
        
        return MatchResult(story1, story2, winner_story, loser_story, comparison.reasoning, datetime.now().isoformat())

    def get_match_pairs(self, stories: List[Story], num_rounds: int) -> List[Tuple[Story, Story]]:
        """Generate random match pairs for tournament rounds."""
        if len(stories) < 2:
            return []
            
        pairs = []
        for _ in range(num_rounds):
            available_stories = stories.copy()
            random.shuffle(available_stories)
            while len(available_stories) >= 2:
                story1 = available_stories.pop()
                story2 = available_stories.pop()
                pairs.append((story1, story2))
        return pairs

    def _process_rating_period(self, stories: List[Story], results: List[MatchResult]):
        """Update all player ratings after a rating period is complete."""
        print("\n📊 Processing Glicko-2 rating period updates...")
        
        match_data = {story.story_id: {'opponents': [], 'outcomes': []} for story in stories}
        
        for res in results:
            match_data[res.winner.story_id]['opponents'].append(res.loser)
            match_data[res.winner.story_id]['outcomes'].append(1.0)
            match_data[res.loser.story_id]['opponents'].append(res.winner)
            match_data[res.loser.story_id]['outcomes'].append(0.0)

        pre_update_ratings = {s.story_id: (s.rating, s.rd, s.sigma, s.wins, s.losses, s.matches_played) for s in stories}
        
        story_map = {s.story_id: s for s in stories}
        for story_id, data in match_data.items():
            self._update_player(story_map[story_id], data['opponents'], data['outcomes'])
        
        for res in results:
            self.match_history.append({
                "story1_id": res.story1.story_id,
                "story2_id": res.story2.story_id,
                "winner_id": res.winner.story_id,
                "story1_rating_before": pre_update_ratings[res.story1.story_id][0],
                "story2_rating_before": pre_update_ratings[res.story2.story_id][0],
                "story1_rating_after": story_map[res.story1.story_id].rating,
                "story2_rating_after": story_map[res.story2.story_id].rating,
                "reasoning": res.reasoning,
                "timestamp": res.timestamp
            })

    async def run_tournament(
        self,
        stories: List[Story],
        num_rounds: int,
        judge_model: str,
        max_concurrent_matches: int = 0,
        rubric_file: str = "rubric.txt",
        original_prompt: str = None
    ) -> int:
        """Run a tournament, treating it as a single Glicko-2 rating period."""
        self.log_memory_usage("Tournament start")
        match_pairs = self.get_match_pairs(stories, num_rounds)
        print(f"Generated {len(match_pairs)} matches")
        
        concurrency = max_concurrent_matches if max_concurrent_matches > 0 else len(match_pairs)
        if concurrency == 0: concurrency = 1

        all_match_results: List[MatchResult] = []
        total_batches = (len(match_pairs) + concurrency - 1) // concurrency
        
        for i in range(0, len(match_pairs), concurrency):
            batch = match_pairs[i:i + concurrency]
            batch_num = (i // concurrency) + 1
            print(f"🏆 Running match batch {batch_num}/{total_batches} ({len(batch)} matches)")
            
            tasks = [self.conduct_match(s1, s2, judge_model, rubric_file, original_prompt) for s1, s2 in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_matches = 0
            for res in batch_results:
                if isinstance(res, MatchResult):
                    res.winner.wins += 1
                    res.loser.losses += 1
                    res.story1.matches_played += 1
                    res.story2.matches_played += 1
                    all_match_results.append(res)
                    successful_matches += 1
            print(f"   📊 Batch {batch_num} summary: {successful_matches}/{len(batch)} matches successful")
        
        self._process_rating_period(stories, all_match_results)
        
        print(f"Tournament complete! {len(all_match_results)} matches played")
        return len(all_match_results)

    def get_leaderboard(self, stories: List[Story]) -> List[Dict[str, Any]]:
        """Generate a leaderboard sorted by rating."""
        leaderboard = []
        for story in sorted(stories, key=lambda s: s.rating, reverse=True):
            win_rate = story.wins / story.matches_played if story.matches_played > 0 else 0
            leaderboard.append({
                "rank": len(leaderboard) + 1,
                "story_id": story.story_id,
                "model_used": story.model_used,
                "rating": round(story.rating, 1),
                "rd": round(story.rd, 1),
                "sigma": round(story.sigma, 4),
                "matches_played": story.matches_played,
                "wins": story.wins,
                "losses": story.losses,
                "win_rate": round(win_rate, 3)
            })
        return leaderboard

    def save_results(self, stories: List[Story], output_dir: str, results_file: str, history_file: str, save_history: bool = True):
        """Save tournament results to files."""
        os.makedirs(output_dir, exist_ok=True)
        leaderboard = self.get_leaderboard(stories)
        
        results_data = {
            "tournament_completed_at": datetime.now().isoformat(),
            "total_matches": len(self.match_history),
            "leaderboard": leaderboard
        }
        with open(os.path.join(output_dir, results_file), "w") as f:
            json.dump(results_data, f, indent=2)
        print(f"Glicko results saved to: {os.path.join(output_dir, results_file)}")
        
        if save_history:
            with open(os.path.join(output_dir, history_file), "w") as f:
                json.dump({"matches": self.match_history}, f, indent=2)
            print(f"Match history saved to: {os.path.join(output_dir, history_file)}")

def load_stories_from_json(json_path: str, default_rating: float, default_rd: float, default_sigma: float) -> List[Story]:
    """Load stories from JSON, converting to Story objects with Glicko parameters."""
    with open(json_path, "r") as f:
        data = json.load(f)
    
    stories = []
    for story_data in data.get("stories", []):
        story = Story(
            story_id=story_data["story_id"],
            piece=story_data["piece"],
            model_used=story_data["model_used"],
            rating=story_data.get("rating", story_data.get("elo", default_rating)),
            rd=story_data.get("rd", default_rd),
            sigma=story_data.get("sigma", default_sigma),
            matches_played=story_data.get("matches_played", 0),
            wins=story_data.get("wins", 0),
            losses=story_data.get("losses", 0)
        )
        stories.append(story)
    return stories