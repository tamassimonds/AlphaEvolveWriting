"""
Story Generation Module

Handles initial story generation and variant creation.
"""

import asyncio
import json
import os
import uuid
import glob
import re
from datetime import datetime
from typing import List, Dict, Any
import shutil

import os

# Conditional import based on USE_GENERAL_MODE environment variable
if os.environ.get('USE_GENERAL_MODE'):
    from .generate_response_general import generate_initial_piece, generate_story_variant
else:
    from .generate_response import generate_initial_piece, generate_story_variant


class BaseStoryGenerator:
    """Base class for story generators."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
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
    
    def save_stories(self, stories: List[Dict[str, Any]], output_path: str, generation_type: str = "initial") -> None:
        """Save stories to JSON file."""
        batch_data = {
            "generated_at": datetime.now().isoformat(),
            "generation_type": generation_type,
            "total_stories": len(stories),
            "stories": stories
        }
        
        with open(output_path, "w") as f:
            json.dump(batch_data, f, indent=2, ensure_ascii=False)


class InitialStoryGenerator(BaseStoryGenerator):
    """Generates initial batch of stories."""
    
    async def generate_single_story(
        self,
        prompt: str,
        story_index: int,
        model: str,
        initial_elo: int,
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
                "elo": initial_elo,
                "created_at": datetime.now().isoformat(),
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
        
        print(f"🔄 Generating {batch_config['num_stories']} stories in parallel...")
        
        tasks = [
            self.generate_single_story(
                prompt, i, batch_config['model'], 
                batch_config['initial_elo'], rubric_file
            )
            for i in range(batch_config['num_stories'])
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        stories = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Story {i + 1} failed with exception: {result}")
            elif result is not None:
                stories.append(result)
        
        if not stories:
            raise Exception("No stories were successfully generated!")
        
        output_path = os.path.join(output_dir, output_config["stories_file"])
        self.save_stories(stories, output_path, "initial")
        
        print(f"✅ Successfully generated {len(stories)} stories!")
        print(f"📄 Stories saved to: {output_path}")
        
        return stories


class NextBatchGenerator(BaseStoryGenerator):
    """Generates next batch of stories based on top performers."""
    
    def find_latest_batch_file(self) -> str:
        """Find the most recent batch file based on modification time."""
        output_dir = self.config["output"]["directory"]
        
        batch_patterns = ["batch*_stories.json", "*stories.json"]
        
        all_batch_files = []
        for pattern in batch_patterns:
            pattern_path = os.path.join(output_dir, pattern)
            files = glob.glob(pattern_path)
            all_batch_files.extend(files)
        
        if not all_batch_files:
            raise FileNotFoundError(f"No batch files found in {output_dir}")
        
        all_batch_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        
        latest_file = all_batch_files[0]
        print(f"Found latest batch file: {os.path.basename(latest_file)}")
        return latest_file
    
    def determine_next_batch_filename(self) -> str:
        """Determine the filename for the next batch based on existing files."""
        output_dir = self.config["output"]["directory"]
        
        batch_files = glob.glob(os.path.join(output_dir, "batch*_stories.json"))
        
        max_batch_num = 1
        
        for file_path in batch_files:
            filename = os.path.basename(file_path)
            match = re.search(r'batch(\d+)_stories\.json', filename)
            if match:
                batch_num = int(match.group(1))
                max_batch_num = max(max_batch_num, batch_num)
        
        next_batch_num = max_batch_num + 1
        next_filename = f"batch{next_batch_num}_stories.json"
        
        print(f"Next batch will be saved as: {next_filename}")
        return next_filename
    
    def load_previous_batch(self, stories_path: str) -> List[Dict[str, Any]]:
        """Load stories from the previous batch."""
        if not os.path.exists(stories_path):
            raise FileNotFoundError(f"Previous batch file not found: {stories_path}")
        
        with open(stories_path, "r") as f:
            data = json.load(f)
        
        return data.get("stories", [])
    
    def select_top_stories(self, stories: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        """Select the top K stories based on ELO rating."""
        sorted_stories = sorted(stories, key=lambda s: s.get("elo", 0), reverse=True)
        top_stories = sorted_stories[:top_k]
        
        print(f"\nSelected top {len(top_stories)} stories by ELO:")
        for i, story in enumerate(top_stories):
            elo = story.get("elo", 0)
            model = story.get("model_used", "unknown")
            story_id = story.get("story_id", "unknown")[:8]
            wins = story.get("wins", 0)
            losses = story.get("losses", 0)
            matches = story.get("matches_played", 0)
            print(f"  {i+1}. {story_id} (Model: {model}) - ELO: {elo:.1f} | W/L: {wins}/{losses} ({matches} matches)")
        
        return top_stories
    
    async def generate_single_variant(
        self,
        original_story: Dict[str, Any],
        variant_index: int,
        story_index: int,
        model: str,
        initial_elo: int,
        rubric_file: str,
        temperature: float
    ) -> Dict[str, Any]:
        """Generate a single story variant with error handling."""
        try:
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
                "elo": initial_elo,
                "created_at": datetime.now().isoformat(),
                "generation_type": "variant",
                "parent_story_id": original_story["story_id"],
                "parent_elo": original_story["elo"],
                "parent_wins": original_story.get("wins", 0),
                "parent_losses": original_story.get("losses", 0),
                "parent_matches_played": original_story.get("matches_played", 0),
                "variant_index": variant_index + 1,
                "parent_story_index": story_index + 1,
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
        initial_elo: int,
        rubric_file: str,
        temperature: float
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
                    initial_elo=initial_elo,
                    rubric_file=rubric_file,
                    temperature=temperature
                )
                all_tasks.append(task)
        
        print(f"Executing {len(all_tasks)} variant generation tasks in parallel...")
        
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
    
    def prepare_final_batch(
        self,
        top_stories: List[Dict[str, Any]],
        variants: List[Dict[str, Any]],
        include_originals: bool,
        initial_elo: int
    ) -> List[Dict[str, Any]]:
        """Prepare the final batch combining original stories and variants with reset ELO."""
        final_batch = []
        
        if include_originals:
            for story in top_stories:
                story_copy = story.copy()
                
                story_copy["previous_batch_elo"] = story_copy["elo"]
                story_copy["previous_batch_wins"] = story_copy.get("wins", 0)
                story_copy["previous_batch_losses"] = story_copy.get("losses", 0)
                story_copy["previous_batch_matches"] = story_copy.get("matches_played", 0)
                
                story_copy["elo"] = initial_elo
                story_copy["matches_played"] = 0
                story_copy["wins"] = 0
                story_copy["losses"] = 0
                
                story_copy["generation_type"] = "original_top_performer"
                story_copy["selected_for_next_batch"] = True
                story_copy["elo_reset_at"] = datetime.now().isoformat()
                
                final_batch.append(story_copy)
        
        final_batch.extend(variants)
        
        print(f"\nFinal batch composition:")
        print(f"  Original top stories: {len(top_stories) if include_originals else 0} (ELO reset to {initial_elo})")
        print(f"  Generated variants: {len(variants)} (ELO set to {initial_elo})")
        print(f"  Total stories: {len(final_batch)}")
        
        return final_batch
    
    async def generate_batch(self) -> List[Dict[str, Any]]:
        """Generate next batch of stories based on top performers."""
        next_batch_config = self.config["next_batch_generation"]
        output_config = self.config["output"]
        input_config = self.config["input_files"]
        
        print("Starting Next Batch Generation System")
        print(f"Configuration: Top {next_batch_config['top_stories_to_select']} stories, "
              f"{next_batch_config['variants_per_story']} variants each")
        
        latest_batch_path = self.find_latest_batch_file()
        stories = self.load_previous_batch(latest_batch_path)
        print(f"Loaded {len(stories)} stories from {os.path.basename(latest_batch_path)}")
        
        if len(stories) == 0:
            raise Exception("No stories found in previous batch!")
        
        top_stories = self.select_top_stories(stories, next_batch_config["top_stories_to_select"])
        
        if len(top_stories) == 0:
            raise Exception("No top stories selected!")
        
        print(f"\nGenerating all variants in parallel...")
        all_variants = await self.generate_all_variants_parallel(
            top_stories=top_stories,
            variants_per_story=next_batch_config["variants_per_story"],
            model=next_batch_config["model"],
            initial_elo=self.config["batch_generation"]["initial_elo"],
            rubric_file=input_config["rubric_file"],
            temperature=next_batch_config["variant_temperature"]
        )
        
        print(f"\nGenerated {len(all_variants)} total variants")
        
        final_batch = self.prepare_final_batch(
            top_stories=top_stories,
            variants=all_variants,
            include_originals=next_batch_config["include_original_stories"],
            initial_elo=self.config["batch_generation"]["initial_elo"]
        )
        
        next_batch_filename = self.determine_next_batch_filename()
        output_path = os.path.join(output_config["directory"], next_batch_filename)
        
        batch_data = {
            "generated_at": datetime.now().isoformat(),
            "generation_type": "next_batch",
            "config_used": next_batch_config,
            "total_stories": len(final_batch),
            "stories": final_batch
        }
        
        with open(output_path, "w") as f:
            json.dump(batch_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nNext batch generation complete!")
        print(f"Saved {len(final_batch)} stories to: {output_path}")
        
        return final_batch