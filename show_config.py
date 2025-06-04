#!/usr/bin/env python3
"""
Show Evolution Configuration

Displays current configuration settings for the evolution pipeline.
"""

import json
import sys

def main():
    """Show current configuration."""
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_file}")
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config file: {e}")
        return 1
    
    print("🔧 Evolution Pipeline Configuration")
    print("=" * 50)
    
    # Evolution Pipeline Settings
    pipeline_config = config.get("evolution_pipeline", {})
    print("\n📋 Pipeline Settings:")
    print(f"  Max iterations: {pipeline_config.get('max_iterations', 3)}")
    print(f"  Generate final batch: {pipeline_config.get('generate_final_batch', True)}")
    print(f"  Auto-continue from existing: {pipeline_config.get('auto_continue_from_existing', True)}")
    print(f"  Log level: {pipeline_config.get('log_level', 'INFO')}")
    
    # Batch Generation Settings
    batch_config = config.get("batch_generation", {})
    print("\n📝 Story Generation:")
    print(f"  Stories per batch: {batch_config.get('num_stories', 10)}")
    print(f"  Model: {batch_config.get('model', 'gpt-4')}")
    print(f"  Initial ELO: {batch_config.get('initial_elo', 1200)}")
    print(f"  Max attempts: {batch_config.get('max_attempts', 3)}")
    
    # Tournament Settings
    elo_config = config.get("elo_ranking", {})
    print("\n🏆 Tournament Settings:")
    print(f"  Tournament rounds: {elo_config.get('tournament_rounds', 30)}")
    print(f"  Judge model: {elo_config.get('judge_model', 'gpt-4o-mini')}")
    print(f"  K-factor: {elo_config.get('k_factor', 32)}")
    print(f"  Max concurrent matches: {elo_config.get('max_concurrent_matches', 5)}")
    print(f"  Save match history: {elo_config.get('save_match_history', True)}")
    
    # Next Batch Settings
    next_config = config.get("next_batch_generation", {})
    print("\n🧬 Evolution Settings:")
    print(f"  Top stories to select: {next_config.get('top_stories_to_select', 5)}")
    print(f"  Variants per story: {next_config.get('variants_per_story', 2)}")
    print(f"  Include original stories: {next_config.get('include_original_stories', True)}")
    print(f"  Variant temperature: {next_config.get('variant_temperature', 1.2)}")
    
    # Input/Output Settings
    input_config = config.get("input_files", {})
    output_config = config.get("output", {})
    print("\n📁 File Settings:")
    print(f"  Prompt file: {input_config.get('prompt_file', 'prompt.txt')}")
    print(f"  Rubric file: {input_config.get('rubric_file', 'rubric.txt')}")
    print(f"  Output directory: {output_config.get('directory', 'output')}")
    
    print("\n💡 Quick commands:")
    print(f"  python evolve.py                    # Run {pipeline_config.get('max_iterations', 3)} iterations (from config)")
    print(f"  python evolve.py 3                  # Run 3 iterations (override config)")
    print(f"  python evolve.py --fresh            # Fresh start with config iterations")
    print(f"  python run_evolution_pipeline.py    # Full pipeline with config settings")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())