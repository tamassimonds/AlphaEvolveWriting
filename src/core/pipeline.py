"""
Core Evolution Pipeline

Manages the automated story evolution pipeline:
1. Generate initial batch of stories
2. Run Glicko tournament to rank them
3. Generate next batch based on top performers
4. Repeat for N iterations
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, List
import glob

from ..generators.story_generator import InitialStoryGenerator, NextBatchGenerator
from ..rankers.tournament_runner import TournamentRunner


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
        try:
            output_dir = self.config["output"]["directory"]
            
            batch_patterns = [
                os.path.join(output_dir, "initial_stories.json"),
                os.path.join(output_dir, "batch*_stories.json"),
                os.path.join(output_dir, "*stories.json")
            ]
            
            all_batch_files = []
            for pattern in batch_patterns:
                files = glob.glob(pattern)
                all_batch_files.extend(files)
            
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
        
        if "initial_stories.json" in filename:
            return 1
        elif "batch" in filename:
            import re
            match = re.search(r'batch(\d+)_stories\.json', filename)
            if match:
                return int(match.group(1))
        
        return 1
    
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
            generator = InitialStoryGenerator(self.config)
            stories = await generator.generate_batch()
            
            self.stats["total_stories_generated"] += len(stories)
            self.log(f"✅ Generated {len(stories)} initial stories")
            
            return True
        except Exception as e:
            self.log(f"❌ Failed to generate initial batch: {e}", "ERROR")
            return False
    
    async def run_tournament(self) -> bool:
        """Run Glicko-2 tournament."""
        self.log("🏆 Step 2: Running Glicko-2 tournament...")
        try:
            runner = TournamentRunner(self.config)
            matches_played = await runner.run_tournament()
            
            self.stats["total_matches_played"] += matches_played
            self.log(f"✅ Tournament completed (~{matches_played} matches)")
            
            return True
        except Exception as e:
            self.log(f"❌ Failed to run tournament: {e}", "ERROR")
            return False
    
    async def run_next_generation(self) -> bool:
        """Generate next batch of stories."""
        self.log("🧬 Step 3: Generating next batch from top performers...")
        try:
            generator = NextBatchGenerator(self.config)
            stories = await generator.generate_batch()
            
            self.stats["total_stories_generated"] += len(stories)
            self.log(f"✅ Generated {len(stories)} new story variants")
            
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
        
        if iteration == 1 and not skip_initial:
            if not await self.run_initial_generation():
                return False
        elif iteration == 1 and skip_initial:
            self.log("⏭️  Skipping initial generation - using existing batches")
        
        if not await self.run_tournament():
            return False
        
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
        
        pipeline_config = self.config.get("evolution_pipeline", {})
        
        if max_iterations is None:
            max_iterations = pipeline_config.get("max_iterations", 3)
        if generate_final_batch is None:
            generate_final_batch = pipeline_config.get("generate_final_batch", True)
        
        auto_continue = pipeline_config.get("auto_continue_from_existing", True)
        latest_batch_number = self.get_latest_batch_number()
        
        self.log(f"🧬 Starting Evolution Pipeline with {max_iterations} iterations")
        self.log(f"Configuration: {self.config['batch_generation']['num_stories']} stories per batch")
        self.log(f"Tournament: {self.config['glicko_ranking']['tournament_rounds']} rounds per tournament")
        
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
            skip_initial = auto_continue and (latest_batch_number > 0)
            if not await self.run_iteration(iteration, skip_initial=skip_initial):
                success = False
                break
            
            self.stats["iterations_completed"] = iteration
            
            if iteration < max_iterations or generate_final_batch:
                if not await self.run_next_generation():
                    success = False
                    break
        
        self.stats["pipeline_end_time"] = datetime.now().isoformat()
        self.log_pipeline_summary()
        
        return success