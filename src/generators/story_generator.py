"""
Story Generation Module

Handles initial story generation and variant creation.
"""

import asyncio
import json
import os
import uuid
import re
import sqlite3
import shutil
from datetime import datetime
from typing import List, Dict, Any

# Conditional import based on USE_GENERAL_MODE environment variable
if os.environ.get('USE_GENERAL_MODE'):
    from .generate_response_general import generate_initial_piece, generate_story_variant
else:
    from .generate_response import generate_initial_piece, generate_story_variant


class BaseStoryGenerator:
    """Base class for story generators."""
    
    def __init__(self, config: Dict[str, Any], db_connection: sqlite3.Connection):
        self.config = config
        self.conn = db_connection
    
    def load_prompt(self, prompt_file: str) -> str:
        """Load the story prompt from file."""
        if not os.path.exists(prompt_file):
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        
        with open(prompt_file, "r") as f:
            return f.read().strip()
    
    def setup_output_directory(self, output_dir: str, prompt_file: str) -> None:
        """Create output directory and copy prompt file."""
        os.makedirs(output_dir, exist_ok=True)
        
        if os.path.exists(prompt_file):
            shutil.copy2(prompt_file, os.path.join(output_dir, "prompt.txt"))
    
    def _insert_new_stories_to_db(self, stories: List[Dict[str, Any]], batch_number: int):
        """Save a batch of new stories to the database."""
        cursor = self.conn.cursor()
        
        story_data_to_insert = []
        for story in stories:
            story['batch_number'] = batch_number
            story_data_to_insert.append(
                (
                    story.get("story_id"), story.get("batch_number"), story.get("piece"),
                    story.get("prompt"), story.get("model_used"), story.get("rating"),
                    story.get("rd"), story.get("sigma"), story.get("created_at"),
                    story.get("generation_type"), story.get("parent_story_id"),
                    story.get("matches_played", 0), story.get("wins", 0), story.get("losses", 0),
                    story.get("previous_batch_rating")
                )
            )
        
        cursor.executemany("""
            INSERT INTO stories (
                story_id, batch_number, piece, prompt, model_used, rating, rd, sigma, 
                created_at, generation_type, parent_story_id, matches_played, wins, losses,
                previous_batch_rating
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, story_data_to_insert)
        
        self.conn.commit()


class InitialStoryGenerator(BaseStoryGenerator):
    """Generates initial batch of stories."""
    
    async def generate_single_story(
        self,
        prompt: str,
        story_index: int,
        model: str,
        initial_rating: float,
        initial_rd: float,
        initial_volatility: float,
        rubric_file: str
    ) -> Dict[str, Any]:
        """Generate a single story with error handling."""
        try:
            print(f"🚀 Starting generation of story {story_index + 1}...")
            
            piece = await generate_initial_piece(
                story_description=prompt,
                model=model,
                rubric_file=rubric_file
            )
            
            story = {
                "story_id": str(uuid.uuid4()),
                "prompt": prompt,
                "piece": piece,
                "model_used": model,
                "rating": initial_rating,
                "rd": initial_rd,
                "sigma": initial_volatility,
                "created_at": datetime.now().isoformat(),
                "generation_type": "initial",
                "generation_attempt": story_index + 1
            }
            
            print(f"✅ Successfully generated story {story_index + 1}")
            return story
            
        except Exception as e:
            print(f"❌ Failed to generate story {story_index + 1}: {e}")
            return None
    
    async def generate_batch(self) -> List[Dict[str, Any]]:
        """Generate a batch of initial stories."""
        batch_config = self.config["batch_generation"]
        input_config = self.config["input_files"]
        output_config = self.config["output"]
        
        print("🚀 Starting story batch generation...")
        print(f"Configuration: {batch_config['num_stories']} stories using {batch_config['model']}")
        
        prompt = self.load_prompt(input_config["prompt_file"])
        print(f"📖 Loaded prompt from {input_config['prompt_file']}")
        
        output_dir = output_config["directory"]
        self.setup_output_directory(output_dir, input_config["prompt_file"])
        
        rubric_file = input_config["rubric_file"]
        if os.path.exists(rubric_file):
            shutil.copy2(rubric_file, os.path.join(output_dir, "rubric.txt"))
        
        num_stories = batch_config['num_stories']
        tasks = [
            self.generate_single_story(
                prompt, i, batch_config['model'], 
                batch_config['glicko_initial_rating'], 
                batch_config['glicko_initial_rd'],
                batch_config['glicko_initial_volatility'],
                rubric_file
            )
            for i in range(num_stories)
        ]
        
        concurrency_limit = self.config["glicko_ranking"].get("max_concurrent_matches", 10)
        
        if concurrency_limit > 0:
            print(f"🔄 Generating {num_stories} stories in parallel (concurrency: {concurrency_limit})...")
            semaphore = asyncio.Semaphore(concurrency_limit)
            async def wrap_task(task):
                async with semaphore:
                    return await task
            
            results = await asyncio.gather(*(wrap_task(t) for t in tasks), return_exceptions=True)
        else:
            print(f"🔄 Generating {num_stories} stories in parallel (unlimited concurrency)...")
            results = await asyncio.gather(*tasks, return_exceptions=True)

        stories = [res for res in results if res is not None and not isinstance(res, Exception)]
        
        if not stories:
            raise Exception("No stories were successfully generated!")
        
        # The first batch is always batch 0
        self._insert_new_stories_to_db(stories, batch_number=0)
        
        print(f"✅ Successfully generated and saved {len(stories)} stories to database (batch 0)!")
        
        return stories


class NextBatchGenerator(BaseStoryGenerator):
    """Generates next batch of stories based on top performers."""
    
    def _get_latest_batch_number(self) -> int:
        """Find the most recent batch number from the database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(batch_number) FROM stories")
        result = cursor.fetchone()
        return result[0] if result and result[0] is not None else -1
    
    def _load_stories_from_batch(self, batch_number: int) -> List[Dict[str, Any]]:
        """Load stories from a specific batch in the database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM stories WHERE batch_number = ?", (batch_number,))
        rows = cursor.fetchall()
        if not rows:
            raise FileNotFoundError(f"No stories found for batch {batch_number} in the database.")
        return [dict(row) for row in rows]

    def _promote_stories_to_new_batch(
        self, 
        top_stories: List[Dict[str, Any]], 
        next_batch_number: int,
        initial_rd: float,
        initial_volatility: float
    ):
        """
        Updates existing top stories to be part of the next batch, resetting their
        tournament stats.
        """
        cursor = self.conn.cursor()
        update_data = [
            (
                next_batch_number,
                initial_rd,
                initial_volatility,
                "original_top_performer",
                story['rating'], # Set previous_batch_rating to current rating
                story['story_id']
            ) for story in top_stories
        ]
        
        cursor.executemany("""
            UPDATE stories
            SET 
                batch_number = ?,
                rd = ?,
                sigma = ?,
                generation_type = ?,
                previous_batch_rating = ?,
                matches_played = 0,
                wins = 0,
                losses = 0
            WHERE story_id = ?
        """, update_data)
        
        self.conn.commit()
        print(f"✅ Promoted {len(top_stories)} top stories to batch {next_batch_number}")

    def select_top_stories(self, stories: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        """Select the top K stories based on Glicko rating."""
        sorted_stories = sorted(stories, key=lambda s: s.get("rating", 0), reverse=True)
        top_stories = sorted_stories[:top_k]
        
        print(f"\nSelected top {len(top_stories)} stories by Glicko Rating:")
        for i, story in enumerate(top_stories):
            rating = story.get("rating", 0)
            model = story.get("model_used", "unknown")
            story_id = story.get("story_id", "unknown")[:8]
            wins = story.get("wins", 0)
            losses = story.get("losses", 0)
            matches = story.get("matches_played", 0)
            print(f"  {i+1}. {story_id} (Model: {model}) - Rating: {rating:.1f} | W/L: {wins}/{losses} ({matches} matches)")
        
        return top_stories
    
    async def generate_single_variant(
        self,
        original_story: Dict[str, Any],
        variant_index: int,
        story_index: int,
        model: str,
        initial_rd: float,
        initial_volatility: float,
        rubric_file: str,
        temperature: float
    ) -> Dict[str, Any]:
        """Generate a single story variant with error handling."""
        try:
            print(f"🧬 Generating variant for story {story_index + 1}, attempt {variant_index + 1}")
            variant_piece = await generate_story_variant(
                original_story=original_story["piece"],
                original_prompt=original_story["prompt"],
                model=model,
                rubric_file=rubric_file,
                temperature=temperature
            )
            
            variant = {
                "story_id": str(uuid.uuid4()),
                "prompt": original_story["prompt"],
                "piece": variant_piece,
                "model_used": model,
                "rating": original_story["rating"], # Inherit rating
                "rd": initial_rd, # Reset RD
                "sigma": initial_volatility, # Reset volatility
                "created_at": datetime.now().isoformat(),
                "generation_type": "variant",
                "parent_story_id": original_story["story_id"],
                "previous_batch_rating": original_story["rating"], # Inherit parent's rating as previous
                "matches_played": 0,
                "wins": 0,
                "losses": 0
            }
            
            return variant
            
        except Exception as e:
            return None
    
    async def generate_all_variants_parallel(
        self,
        top_stories: List[Dict[str, Any]],
        variants_per_story: int,
        model: str,
        initial_rd: float,
        initial_volatility: float,
        rubric_file: str,
        temperature: float,
        concurrency_limit: int
    ) -> List[Dict[str, Any]]:
        """Generate all variants for all stories in parallel."""
        total_variants = len(top_stories) * variants_per_story
        print(f"Creating {total_variants} variants ({len(top_stories)} stories × {variants_per_story} variants each)")
        
        all_tasks = []
        
        for story_idx, story in enumerate(top_stories):
            for variant_idx in range(variants_per_story):
                task = self.generate_single_variant(
                    original_story=story,
                    variant_index=variant_idx,
                    story_index=story_idx,
                    model=model,
                    initial_rd=initial_rd,
                    initial_volatility=initial_volatility,
                    rubric_file=rubric_file,
                    temperature=temperature
                )
                all_tasks.append(task)
        
        if concurrency_limit > 0:
            print(f"Executing {len(all_tasks)} variant generation tasks in parallel (concurrency: {concurrency_limit})...")
            semaphore = asyncio.Semaphore(concurrency_limit)
            async def wrap_task(task):
                async with semaphore:
                    return await task
            results = await asyncio.gather(*(wrap_task(t) for t in all_tasks), return_exceptions=True)
        else:
            print(f"Executing {len(all_tasks)} variant generation tasks in parallel (unlimited concurrency)...")
            results = await asyncio.gather(*all_tasks, return_exceptions=True)

        variants = []
        successful_count = 0
        failed_count = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Task {i + 1} failed with exception: {result}")
                failed_count += 1
            elif result is not None:
                variants.append(result)
                successful_count += 1
            else:
                failed_count += 1
        
        print(f"Parallel generation complete: {successful_count} successful, {failed_count} failed")
        
        return variants
    
    async def generate_batch(self) -> List[Dict[str, Any]]:
        """Generate next batch of stories based on top performers."""
        next_batch_config = self.config["next_batch_generation"]
        batch_config = self.config["batch_generation"]
        input_config = self.config["input_files"]
        
        print("Starting Next Batch Generation System")
        print(f"Configuration: Top {next_batch_config['top_stories_to_select']} stories, "
              f"{next_batch_config['variants_per_story']} variants each")
        
        latest_batch_number = self._get_latest_batch_number()
        if latest_batch_number == -1:
            raise Exception("Cannot generate next batch, no initial batch found in database.")
        
        stories = self._load_stories_from_batch(latest_batch_number)
        print(f"Loaded {len(stories)} stories from batch {latest_batch_number} in database")
        
        top_stories = self.select_top_stories(stories, next_batch_config["top_stories_to_select"])
        
        if not top_stories:
            raise Exception("No top stories selected!")
        
        print(f"\nGenerating new variants in parallel...")
        all_variants = await self.generate_all_variants_parallel(
            top_stories=top_stories,
            variants_per_story=next_batch_config["variants_per_story"],
            model=next_batch_config["model"],
            initial_rd=batch_config["glicko_initial_rd"],
            initial_volatility=batch_config["glicko_initial_volatility"],
            rubric_file=input_config["rubric_file"],
            temperature=next_batch_config["variant_temperature"],
            concurrency_limit=self.config["glicko_ranking"].get("max_concurrent_matches", 10)
        )
        
        print(f"\nGenerated {len(all_variants)} total new variants")
        
        next_batch_number = latest_batch_number + 1
        
        # Insert the new variants into the database
        if all_variants:
            self._insert_new_stories_to_db(all_variants, batch_number=next_batch_number)
            print(f"✅ Inserted {len(all_variants)} new variants into database as batch {next_batch_number}")
        
        # Promote the original top stories to the new batch if configured to do so
        if next_batch_config["include_original_stories"]:
            self._promote_stories_to_new_batch(
                top_stories, 
                next_batch_number,
                batch_config["glicko_initial_rd"],
                batch_config["glicko_initial_volatility"]
            )
        
        final_batch_size = len(all_variants) + (len(top_stories) if next_batch_config["include_original_stories"] else 0)
        
        print(f"\nNext batch generation complete!")
        print(f"Created batch {next_batch_number} with {final_batch_size} total stories.")
        
        # Return the combination of promoted stories and new variants for the pipeline stats
        return top_stories + all_variants