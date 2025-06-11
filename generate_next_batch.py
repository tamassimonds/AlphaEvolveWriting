"""
Generate next batch of creative writing stories based on top performers.

This script reads the previous batch of stories, selects the top performers by ELO rating,
generates variants of those stories, and creates a new batch for continued evolution.
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
    from lib.generate_response_general import generate_story_variant
else:
    from lib.generate_response import generate_story_variant


async def generate_all_variants_parallel(
    top_stories: List[Dict[str, Any]],
    variants_per_story: int,
    model: str,
    initial_elo: int,
    rubric_file: str,
    temperature: float
) -> List[Dict[str, Any]]:
    """
    Generate all variants for all stories in parallel.
    
    Args:
        top_stories: List of top-performing stories to create variants from
        variants_per_story: Number of variants to generate per story
        model: Model to use for generation
        initial_elo: Initial ELO rating for new variants
        rubric_file: Path to rubric file
        temperature: Temperature for variant generation
        
    Returns:
        List of all generated story variants
    """
    total_variants = len(top_stories) * variants_per_story
    print(f"Creating {total_variants} variants ({len(top_stories)} stories × {variants_per_story} variants each)")
    
    # Create all tasks for parallel execution
    all_tasks = []
    
    for story_idx, story in enumerate(top_stories):
        for variant_idx in range(variants_per_story):
            task = generate_single_variant(
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
    
    # Execute all tasks in parallel
    results = await asyncio.gather(*all_tasks, return_exceptions=True)
    
    # Filter out None results and exceptions
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
    
    # Show breakdown by original story
    story_variant_counts = {}
    for variant in variants:
        parent_id = variant.get("parent_story_id", "unknown")
        story_variant_counts[parent_id] = story_variant_counts.get(parent_id, 0) + 1
    
    print(f"\nVariants generated per story:")
    for i, story in enumerate(top_stories):
        story_id = story["story_id"]
        count = story_variant_counts.get(story_id, 0)
        print(f"  Story {i+1} ({story_id[:8]}): {count}/{variants_per_story} variants")
    
    return variants


async def generate_variant_batch(
    original_story: Dict[str, Any],
    num_variants: int,
    model: str,
    max_attempts: int,
    initial_elo: int,
    rubric_file: str,
    temperature: float
) -> List[Dict[str, Any]]:
    """
    Generate multiple variants of a single story in parallel.
    
    Args:
        original_story: The original story to create variants from
        num_variants: Number of variants to generate
        model: Model to use for generation
        max_attempts: Maximum attempts per variant
        initial_elo: Initial ELO rating for new variants
        rubric_file: Path to rubric file
        temperature: Temperature for variant generation
        
    Returns:
        List of story variant dictionaries
    """
    print(f"Generating {num_variants} variants of story {original_story['story_id'][:8]}...")
    
    # Create tasks for parallel generation
    tasks = [
        generate_single_variant(
            original_story, i, 0, model, initial_elo, rubric_file, temperature
        )
        for i in range(num_variants)
    ]
    
    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out None results and exceptions
    variants = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"  Variant {i + 1} failed with exception: {result}")
        elif result is not None:
            variants.append(result)
    
    print(f"  Successfully generated {len(variants)} out of {num_variants} variants")
    return variants


async def generate_single_variant(
    original_story: Dict[str, Any],
    variant_index: int,
    story_index: int,
    model: str,
    initial_elo: int,
    rubric_file: str,
    temperature: float
) -> Dict[str, Any]:
    """
    Generate a single story variant with error handling.
    
    Args:
        original_story: The original story to create a variant from
        variant_index: Index of this variant (for logging)
        story_index: Index of the parent story (for logging)
        model: Model to use for generation
        initial_elo: Initial ELO rating
        rubric_file: Path to rubric file
        temperature: Temperature for generation
        
    Returns:
        Story variant dictionary or None if failed
    """
    try:
        # Generate the story variant
        variant_piece = await generate_story_variant(
            original_story=original_story["piece"],
            original_prompt=original_story["prompt"],
            model=model,
            rubric_file=rubric_file,
            temperature=temperature
        )
        
        # Create variant story object with metadata
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


def find_latest_batch_file() -> str:
    """Find the most recent batch file based on modification time."""
    output_dir = "output"
    
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
    
    latest_file = all_batch_files[0]
    print(f"Found latest batch file: {os.path.basename(latest_file)}")
    return latest_file

def determine_next_batch_filename() -> str:
    """Determine the filename for the next batch based on existing files."""
    output_dir = "output"
    
    # Find all existing batch files and extract numbers
    batch_files = glob.glob(os.path.join(output_dir, "batch*_stories.json"))
    
    max_batch_num = 1  # Default to batch2 if no numbered batches exist
    
    for file_path in batch_files:
        filename = os.path.basename(file_path)
        # Extract number from filename like "batch2_stories.json"
        match = re.search(r'batch(\d+)_stories\.json', filename)
        if match:
            batch_num = int(match.group(1))
            max_batch_num = max(max_batch_num, batch_num)
    
    next_batch_num = max_batch_num + 1
    next_filename = f"batch{next_batch_num}_stories.json"
    
    print(f"Next batch will be saved as: {next_filename}")
    return next_filename

def load_config() -> Dict[str, Any]:
    """Load configuration from config.json."""
    with open("config.json", "r") as f:
        return json.load(f)


def load_previous_batch(stories_path: str) -> List[Dict[str, Any]]:
    """Load stories from the previous batch."""
    if not os.path.exists(stories_path):
        raise FileNotFoundError(f"Previous batch file not found: {stories_path}")
    
    with open(stories_path, "r") as f:
        data = json.load(f)
    
    return data.get("stories", [])


def select_top_stories(stories: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    """
    Select the top K stories based on ELO rating.
    
    Args:
        stories: List of story dictionaries
        top_k: Number of top stories to select
        
    Returns:
        List of top K stories sorted by ELO (highest first)
    """
    # Sort by ELO rating (highest first)
    sorted_stories = sorted(stories, key=lambda s: s.get("elo", 0), reverse=True)
    
    # Select top K
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


def prepare_final_batch(
    top_stories: List[Dict[str, Any]],
    variants: List[Dict[str, Any]],
    include_originals: bool,
    initial_elo: int
) -> List[Dict[str, Any]]:
    """
    Prepare the final batch combining original stories and variants with reset ELO.
    
    Args:
        top_stories: Original top-performing stories
        variants: Generated variants
        include_originals: Whether to include original stories in the batch
        initial_elo: ELO rating to reset all stories to
        
    Returns:
        Combined list of stories for the next batch with reset ELO
    """
    final_batch = []
    
    if include_originals:
        # Add original top stories with reset ELO but preserved history
        for story in top_stories:
            story_copy = story.copy()
            
            # Reset ELO but preserve previous performance
            story_copy["previous_batch_elo"] = story_copy["elo"]
            story_copy["previous_batch_wins"] = story_copy.get("wins", 0)
            story_copy["previous_batch_losses"] = story_copy.get("losses", 0)
            story_copy["previous_batch_matches"] = story_copy.get("matches_played", 0)
            
            # Reset current ELO and match stats
            story_copy["elo"] = initial_elo
            story_copy["matches_played"] = 0
            story_copy["wins"] = 0
            story_copy["losses"] = 0
            
            # Update metadata
            story_copy["generation_type"] = "original_top_performer"
            story_copy["selected_for_next_batch"] = True
            story_copy["elo_reset_at"] = datetime.now().isoformat()
            
            final_batch.append(story_copy)
    
    # Add all variants (they already have reset ELO and parent history)
    final_batch.extend(variants)
    
    print(f"\nFinal batch composition:")
    print(f"  Original top stories: {len(top_stories) if include_originals else 0} (ELO reset to {initial_elo})")
    print(f"  Generated variants: {len(variants)} (ELO set to {initial_elo})")
    print(f"  Total stories: {len(final_batch)}")
    
    if include_originals:
        print(f"\nPrevious batch performance preserved as metadata:")
        for i, story in enumerate(top_stories):
            prev_elo = story.get("elo", 0)
            wins = story.get("wins", 0)
            losses = story.get("losses", 0)
            matches = story.get("matches_played", 0)
            story_id = story.get("story_id", "unknown")[:8]
            print(f"  {story_id}: Previous ELO {prev_elo:.1f} | W/L: {wins}/{losses} ({matches} matches)")
    
    return final_batch


def save_next_batch(
    stories: List[Dict[str, Any]],
    output_path: str,
    generation_config: Dict[str, Any]
) -> None:
    """Save the next batch to JSON file."""
    batch_data = {
        "generated_at": datetime.now().isoformat(),
        "generation_type": "next_batch",
        "config_used": generation_config,
        "total_stories": len(stories),
        "stories": stories
    }
    
    with open(output_path, "w") as f:
        json.dump(batch_data, f, indent=2, ensure_ascii=False)


async def main():
    """Main function to generate next batch of stories."""
    try:
        # Load configuration
        config = load_config()
        next_batch_config = config["next_batch_generation"]
        output_config = config["output"]
        input_config = config["input_files"]
        
        print("Starting Next Batch Generation System")
        print(f"Configuration: Top {next_batch_config['top_stories_to_select']} stories, "
              f"{next_batch_config['variants_per_story']} variants each")
        
        # Find and load the latest batch
        latest_batch_path = find_latest_batch_file()
        stories = load_previous_batch(latest_batch_path)
        print(f"Loaded {len(stories)} stories from {os.path.basename(latest_batch_path)}")
        
        if len(stories) == 0:
            print("No stories found in previous batch!")
            return
        
        # Select top stories by ELO
        top_stories = select_top_stories(stories, next_batch_config["top_stories_to_select"])
        
        if len(top_stories) == 0:
            print("No top stories selected!")
            return
        
        # Generate all variants in parallel
        print(f"\nGenerating all variants in parallel...")
        all_variants = await generate_all_variants_parallel(
            top_stories=top_stories,
            variants_per_story=next_batch_config["variants_per_story"],
            model=next_batch_config["model"],
            initial_elo=config["batch_generation"]["initial_elo"],
            rubric_file=input_config["rubric_file"],
            temperature=next_batch_config["variant_temperature"]
        )
        
        print(f"\nGenerated {len(all_variants)} total variants")
        
        # Prepare final batch with reset ELO
        final_batch = prepare_final_batch(
            top_stories=top_stories,
            variants=all_variants,
            include_originals=next_batch_config["include_original_stories"],
            initial_elo=config["batch_generation"]["initial_elo"]
        )
        
        # Determine next batch filename and save
        next_batch_filename = determine_next_batch_filename()
        output_path = os.path.join(output_config["directory"], next_batch_filename)
        save_next_batch(final_batch, output_path, next_batch_config)
        
        print(f"\nNext batch generation complete!")
        print(f"Saved {len(final_batch)} stories to: {output_path}")
        
        # Show generation summary
        print(f"\nGeneration Summary:")
        print(f"  Source: {len(top_stories)} top stories from previous batch")
        print(f"  Variants generated: {len(all_variants)}")
        print(f"  Originals included: {'Yes' if next_batch_config['include_original_stories'] else 'No'}")
        print(f"  Total next batch size: {len(final_batch)}")
        
        # Show model breakdown
        model_counts = {}
        for story in final_batch:
            model = story.get("model_used", "unknown")
            model_counts[model] = model_counts.get(model, 0) + 1
        
        print(f"\nModel distribution:")
        for model, count in model_counts.items():
            print(f"  {model}: {count} stories")
        
    except Exception as e:
        print(f"Error during next batch generation: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())