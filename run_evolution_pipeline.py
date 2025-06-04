#!/usr/bin/env python3
"""
Automated Evolution Pipeline

This script runs the complete story evolution pipeline:
1. Generate initial batch of stories
2. Run ELO tournament to rank them
3. Generate next batch based on top performers
4. Repeat for N iterations

The pipeline evolves stories through multiple generations, using randomized
missions and author styles to create diverse, high-quality creative writing.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, List
import argparse

# Import the pipeline components
from generate_initial_batch import main as generate_initial_main
from run_elo_tournament import main as run_tournament_main
from generate_next_batch import main as generate_next_main


class EvolutionPipeline:
    """Manages the automated story evolution pipeline."""
    
    def __init__(self, config_file: str = "config.json"):
        """
        Initialize the evolution pipeline.
        
        Args:
            config_file: Path to the configuration file
        """
        self.config_file = config_file
        self.config = self.load_config()
        self.iteration = 0
        self.start_time = None
        self.existing_batches = self.detect_existing_batches()
        self.stats = {
            "iterations_completed": 0,
            "total_stories_generated": 0,
            "total_matches_played": 0,
            "pipeline_start_time": None,
            "pipeline_end_time": None,
            "iteration_times": []
        }
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        with open(self.config_file, "r") as f:
            return json.load(f)
    
    def detect_existing_batches(self) -> List[str]:
        """
        Detect existing story batch files in the output directory.
        
        Returns:
            List of existing batch file paths, sorted by creation/modification time
        """
        import glob
        
        try:
            output_dir = self.config["output"]["directory"]
            
            # Look for story batch files
            batch_patterns = [
                os.path.join(output_dir, "initial_stories.json"),
                os.path.join(output_dir, "batch*_stories.json"),
                os.path.join(output_dir, "*stories.json")
            ]
            
            all_batch_files = []
            for pattern in batch_patterns:
                files = glob.glob(pattern)
                all_batch_files.extend(files)
            
            # Remove duplicates and sort by modification time
            all_batch_files = list(set(all_batch_files))
            all_batch_files.sort(key=lambda f: os.path.getmtime(f))
            
            return all_batch_files
            
        except Exception as e:
            self.log(f"Warning: Could not detect existing batches: {e}", "WARN")
            return []
    
    def get_latest_batch_number(self) -> int:
        """
        Get the number of the latest batch.
        
        Returns:
            The batch number (0 if no batches exist, 1 for initial, 2+ for batch2, etc.)
        """
        if not self.existing_batches:
            return 0
        
        latest_batch = self.existing_batches[-1]
        filename = os.path.basename(latest_batch)
        
        # Extract batch number from filename
        if "initial_stories.json" in filename:
            return 1
        elif "batch" in filename:
            import re
            match = re.search(r'batch(\d+)_stories\.json', filename)
            if match:
                return int(match.group(1))
        
        return 1  # Default to 1 if we can't parse
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def log_iteration_start(self, iteration: int):
        """Log the start of an iteration."""
        self.log("=" * 80)
        self.log(f"🚀 STARTING ITERATION {iteration}")
        self.log("=" * 80)
    
    def log_iteration_end(self, iteration: int, duration: float):
        """Log the end of an iteration."""
        self.log(f"✅ ITERATION {iteration} COMPLETED in {duration:.1f}s")
        self.log("=" * 80)
    
    def log_pipeline_summary(self):
        """Log final pipeline statistics."""
        total_time = time.time() - self.start_time
        avg_iteration_time = sum(self.stats["iteration_times"]) / len(self.stats["iteration_times"]) if self.stats["iteration_times"] else 0
        
        self.log("\n" + "=" * 80)
        self.log("🏁 EVOLUTION PIPELINE COMPLETED")
        self.log("=" * 80)
        self.log(f"Total iterations: {self.stats['iterations_completed']}")
        self.log(f"Total stories generated: {self.stats['total_stories_generated']}")
        self.log(f"Total time: {total_time:.1f}s ({total_time/60:.1f}m)")
        self.log(f"Average iteration time: {avg_iteration_time:.1f}s")
        self.log("=" * 80)
    
    async def run_initial_generation(self) -> bool:
        """Run initial story generation."""
        self.log("📝 Step 1: Generating initial batch of stories...")
        try:
            await generate_initial_main()
            
            # Count stories generated
            output_dir = self.config["output"]["directory"]
            stories_file = os.path.join(output_dir, self.config["output"]["stories_file"])
            if os.path.exists(stories_file):
                with open(stories_file, "r") as f:
                    data = json.load(f)
                    story_count = len(data.get("stories", []))
                    self.stats["total_stories_generated"] += story_count
                    self.log(f"✅ Generated {story_count} initial stories")
            
            return True
        except Exception as e:
            self.log(f"❌ Failed to generate initial batch: {e}", "ERROR")
            return False
    
    async def run_tournament(self) -> bool:
        """Run ELO tournament."""
        self.log("🏆 Step 2: Running ELO tournament...")
        try:
            await run_tournament_main()
            
            # Count matches played (estimate from config)
            tournament_config = self.config["elo_ranking"]
            estimated_matches = tournament_config.get("tournament_rounds", 0)
            self.stats["total_matches_played"] += estimated_matches
            self.log(f"✅ Tournament completed (~{estimated_matches} matches)")
            
            return True
        except Exception as e:
            self.log(f"❌ Failed to run tournament: {e}", "ERROR")
            return False
    
    async def run_next_generation(self) -> bool:
        """Generate next batch of stories."""
        self.log("🧬 Step 3: Generating next batch from top performers...")
        try:
            await generate_next_main()
            
            # Count new stories generated
            batch_config = self.config["batch_generation"]
            estimated_new_stories = batch_config.get("num_stories", 0)
            self.stats["total_stories_generated"] += estimated_new_stories
            self.log(f"✅ Generated ~{estimated_new_stories} new story variants")
            
            return True
        except Exception as e:
            self.log(f"❌ Failed to generate next batch: {e}", "ERROR")
            return False
    
    async def run_iteration(self, iteration: int, skip_initial: bool = False) -> bool:
        """
        Run a single iteration of the evolution pipeline.
        
        Args:
            iteration: Current iteration number
            skip_initial: Whether to skip initial generation (if batches already exist)
            
        Returns:
            True if iteration completed successfully
        """
        iteration_start = time.time()
        self.log_iteration_start(iteration)
        
        # Step 1: Generate initial batch (only on first iteration and if no existing batches)
        if iteration == 1 and not skip_initial:
            if not await self.run_initial_generation():
                return False
        elif iteration == 1 and skip_initial:
            self.log("⏭️  Skipping initial generation - using existing batches")
        
        # Step 2: Run tournament
        if not await self.run_tournament():
            return False
        
        # Step 3: Generate next batch (skip on last iteration)
        # We'll handle this logic in the main loop
        
        iteration_time = time.time() - iteration_start
        self.stats["iteration_times"].append(iteration_time)
        self.log_iteration_end(iteration, iteration_time)
        
        return True
    
    async def run_pipeline(self, max_iterations: int = None, generate_final_batch: bool = None) -> bool:
        """
        Run the complete evolution pipeline.
        
        Args:
            max_iterations: Maximum number of iterations to run (overrides config if provided)
            generate_final_batch: Whether to generate a final batch after the last tournament (overrides config if provided)
            
        Returns:
            True if pipeline completed successfully
        """
        self.start_time = time.time()
        self.stats["pipeline_start_time"] = datetime.now().isoformat()
        
        # Get pipeline configuration from config file
        pipeline_config = self.config.get("evolution_pipeline", {})
        
        # Use config defaults if not overridden
        if max_iterations is None:
            max_iterations = pipeline_config.get("max_iterations", 3)
        if generate_final_batch is None:
            generate_final_batch = pipeline_config.get("generate_final_batch", True)
        
        # Check if we should auto-continue from existing batches
        auto_continue = pipeline_config.get("auto_continue_from_existing", True)
        
        # Check existing state
        latest_batch_number = self.get_latest_batch_number()
        
        self.log(f"🧬 Starting Evolution Pipeline with {max_iterations} iterations")
        self.log(f"Configuration: {self.config['batch_generation']['num_stories']} stories per batch")
        self.log(f"Tournament: {self.config['elo_ranking']['tournament_rounds']} rounds per tournament")
        
        if self.existing_batches:
            self.log(f"📁 Found {len(self.existing_batches)} existing batch(es)")
            for i, batch_file in enumerate(self.existing_batches):
                filename = os.path.basename(batch_file)
                mtime = datetime.fromtimestamp(os.path.getmtime(batch_file)).strftime("%Y-%m-%d %H:%M:%S")
                self.log(f"  {i+1}. {filename} (modified: {mtime})")
            self.log(f"🔄 Continuing evolution from batch {latest_batch_number}")
        else:
            self.log("📝 No existing batches found - starting fresh")
        
        success = True
        
        for iteration in range(1, max_iterations + 1):
            # Skip initial generation if auto-continue is enabled and batches exist
            skip_initial = auto_continue and (latest_batch_number > 0)
            if not await self.run_iteration(iteration, skip_initial=skip_initial):
                success = False
                break
            
            self.stats["iterations_completed"] = iteration
            
            # Generate next batch after tournament (except after final iteration)
            if iteration < max_iterations or generate_final_batch:
                if not await self.run_next_generation():
                    success = False
                    break
        
        self.stats["pipeline_end_time"] = datetime.now().isoformat()
        self.log_pipeline_summary()
        
        return success


async def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(description="Run automated story evolution pipeline")
    parser.add_argument(
        "--iterations", 
        type=int, 
        default=None, 
        help="Number of evolution iterations to run (default: from config.json)"
    )
    parser.add_argument(
        "--config", 
        type=str, 
        default="config.json", 
        help="Path to configuration file (default: config.json)"
    )
    parser.add_argument(
        "--no-final-batch", 
        action="store_true", 
        help="Skip generating final batch after last tournament"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Show what would be done without actually running"
    )
    parser.add_argument(
        "--fresh-start", 
        action="store_true", 
        help="Start fresh even if existing batches are found"
    )
    
    args = parser.parse_args()
    
    # Load config to show accurate dry run info
    if args.dry_run:
        try:
            with open(args.config, "r") as f:
                config = json.load(f)
            pipeline_config = config.get("evolution_pipeline", {})
            iterations = args.iterations if args.iterations is not None else pipeline_config.get("max_iterations", 3)
            print(f"🔍 DRY RUN: Would run {iterations} iterations")
            if args.iterations is None:
                print(f"   (using default from {args.config})")
            print(f"Config file: {args.config}")
            print(f"Generate final batch: {not args.no_final_batch}")
            return
        except Exception as e:
            print(f"❌ Error reading config for dry run: {e}")
            return 1
    
    # Validate config file exists
    if not os.path.exists(args.config):
        print(f"❌ Config file not found: {args.config}")
        return 1
    
    # Initialize and run pipeline
    pipeline = EvolutionPipeline(args.config)
    
    # Override existing batch detection if fresh start requested
    if args.fresh_start:
        pipeline.existing_batches = []
        print("🔄 Fresh start requested - ignoring existing batches")
    
    try:
        success = await pipeline.run_pipeline(
            max_iterations=args.iterations,
            generate_final_batch=not args.no_final_batch
        )
        
        if success:
            print("\n🎉 Evolution pipeline completed successfully!")
            return 0
        else:
            print("\n💥 Evolution pipeline failed!")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️  Pipeline interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Pipeline failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)