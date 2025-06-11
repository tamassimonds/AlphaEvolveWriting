"""
Generate initial batch of creative writing stories.

This script reads a prompt from prompt.txt, generates multiple stories using different models,
and saves them to a JSON file with unique IDs and initial ELO ratings.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any
import shutil

import os

# Conditional import based on USE_GENERAL_MODE environment variable
if os.environ.get('USE_GENERAL_MODE'):
    from lib.generate_response_general import generate_initial_piece
else:
    from lib.generate_response import generate_initial_piece


async def generate_single_story(
    prompt: str,
    story_index: int,
    model: str,
    max_attempts: int,
    initial_elo: int,
    rubric_file: str
) -> Dict[str, Any]:
    """
    Generate a single story with error handling.
    
    Args:
        prompt: The story prompt/description
        story_index: Index of this story (for logging)
        model: The model to use for generation
        max_attempts: Maximum attempts per story
        initial_elo: Initial ELO rating
        
    Returns:
        Story dictionary with metadata or None if failed
    """
    try:
        print(f"🚀 Starting generation of story {story_index + 1}...")
        
        # Generate the story
        piece = await generate_initial_piece(
            story_description=prompt,
            model=model,
            rubric_file=rubric_file
        )
        
        # Create story object with metadata
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


async def generate_story_batch(
    prompt: str,
    num_stories: int,
    model: str,
    max_attempts: int,
    initial_elo: int,
    rubric_file: str
) -> List[Dict[str, Any]]:
    """
    Generate a batch of stories in parallel based on the given prompt.
    
    Args:
        prompt: The story prompt/description
        num_stories: Number of stories to generate
        model: The model to use for generation
        max_attempts: Maximum attempts per story
        initial_elo: Initial ELO rating for all stories
        
    Returns:
        List of story dictionaries with metadata
    """
    print(f"🔄 Generating {num_stories} stories in parallel...")
    
    # Create tasks for parallel generation
    tasks = [
        generate_single_story(prompt, i, model, max_attempts, initial_elo, rubric_file)
        for i in range(num_stories)
    ]
    
    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out None results and exceptions
    stories = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"❌ Story {i + 1} failed with exception: {result}")
        elif result is not None:
            stories.append(result)
    
    print(f"✅ Successfully generated {len(stories)} out of {num_stories} stories")
    return stories


def load_config() -> Dict[str, Any]:
    """Load configuration from config.json."""
    with open("config.json", "r") as f:
        return json.load(f)


def load_prompt(prompt_file: str) -> str:
    """Load the story prompt from file."""
    if not os.path.exists(prompt_file):
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
    
    with open(prompt_file, "r") as f:
        return f.read().strip()


def setup_output_directory(output_dir: str, prompt_file: str) -> None:
    """Create output directory and copy prompt file."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Copy prompt.txt to output directory for reference
    if os.path.exists(prompt_file):
        shutil.copy2(prompt_file, os.path.join(output_dir, "prompt.txt"))


def save_stories(stories: List[Dict[str, Any]], output_path: str) -> None:
    """Save stories to JSON file."""
    batch_data = {
        "generated_at": datetime.now().isoformat(),
        "total_stories": len(stories),
        "stories": stories
    }
    
    with open(output_path, "w") as f:
        json.dump(batch_data, f, indent=2, ensure_ascii=False)


async def main():
    """Main function to generate initial story batch."""
    try:
        # Load configuration
        config = load_config()
        batch_config = config["batch_generation"]
        input_config = config["input_files"]
        output_config = config["output"]
        
        print("🚀 Starting story batch generation...")
        print(f"Configuration: {batch_config['num_stories']} stories using {batch_config['model']}")
        
        # Load prompt
        prompt = load_prompt(input_config["prompt_file"])
        print(f"📖 Loaded prompt from {input_config['prompt_file']}")
        print(f"Prompt preview: {prompt[:100]}...")
        
        # Setup output directory
        output_dir = output_config["directory"]
        setup_output_directory(output_dir, input_config["prompt_file"])
        print(f"📁 Output directory prepared: {output_dir}")
        
        # Copy rubric file to output directory for reference
        rubric_file = input_config["rubric_file"]
        if os.path.exists(rubric_file):
            shutil.copy2(rubric_file, os.path.join(output_dir, "rubric.txt"))
            print(f"📋 Copied rubric to output directory")
        
        # Generate stories
        stories = await generate_story_batch(
            prompt=prompt,
            num_stories=batch_config["num_stories"],
            model=batch_config["model"],
            max_attempts=batch_config["max_attempts"],
            initial_elo=batch_config["initial_elo"],
            rubric_file=rubric_file
        )
        
        if not stories:
            print("❌ No stories were successfully generated!")
            return
        
        # Save stories
        output_path = os.path.join(output_dir, output_config["stories_file"])
        save_stories(stories, output_path)
        
        print(f"✅ Successfully generated {len(stories)} stories!")
        print(f"📄 Stories saved to: {output_path}")
        print(f"📋 Prompt saved to: {os.path.join(output_dir, 'prompt.txt')}")
        
        # Print summary
        print("\n📊 Generation Summary:")
        print(f"  - Total stories: {len(stories)}")
        print(f"  - Model used: {batch_config['model']}")
        print(f"  - Initial ELO: {batch_config['initial_elo']}")
        print(f"  - Output file: {output_path}")
        
    except Exception as e:
        print(f"❌ Error during batch generation: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())