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
import sqlite3
from datetime import datetime
from typing import Dict, Any, List

from ..generators.story_generator import InitialStoryGenerator, NextBatchGenerator
from ..rankers.tournament_runner import TournamentRunner


class EvolutionPipeline:
    """Manages the automated story evolution pipeline."""
    
    def __init__(self, config_file: str = "config.json", db_connection: sqlite3.Connection = None):
        """
        Initialize the evolution pipeline.
        
        Args:
            config_file: Path to the configuration file
            db_connection: An active sqlite3 connection object
        """
        self.config_file = config_file
        self.config = self.load_config()
        if db_connection is None:
            raise ValueError("A database connection must be provided to EvolutionPipeline.")
        self.conn = db_connection
        self.iteration = 0
        self.start_time = None
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

    def get_latest_batch_number(self) -> int:
        """Get the number of the latest batch from the database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(batch_number) FROM stories")
        result = cursor.fetchone()
        if result and result[0] is not None:
            return int(result[0])
        return -1  # Use -1 to indicate no batches exist

    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def log_iteration_start(self, iteration: int):
        """Log the start of an iteration."""
        self.log("=" * 80)
        self.log(f"🚀 STARTING EVOLUTION CYCLE {iteration}")
        self.log("=" * 80)
    
    def log_iteration_end(self, iteration: int, duration: float):
        """Log the end of an iteration."""
        self.log(f"✅ EVOLUTION CYCLE {iteration} COMPLETED in {duration:.1f}s")
        self.log("=" * 80)
    
    def log_pipeline_summary(self):
        """Log final pipeline statistics."""
        if not self.start_time:
            self.log("Pipeline did not run, no summary to show.")
            return

        total_time = time.time() - self.start_time
        avg_iteration_time = sum(self.stats["iteration_times"]) / len(self.stats["iteration_times"]) if self.stats["iteration_times"] else 0
        
        self.log("\n" + "=" * 80)
        self.log("🏁 EVOLUTION PIPELINE COMPLETED")
        self.log("=" * 80)
        self.log(f"Total evolution cycles: {self.stats['iterations_completed']}")
        self.log(f"Total stories generated: {self.stats['total_stories_generated']}")
        self.log(f"Total time: {total_time:.1f}s ({total_time/60:.1f}m)")
        self.log(f"Average cycle time: {avg_iteration_time:.1f}s")
        self.log("=" * 80)
    
    async def run_initial_generation(self) -> bool:
        """Run initial story generation."""
        self.log("📝 Step 1: Generating initial batch of stories...")
        try:
            generator = InitialStoryGenerator(self.config, self.conn)
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
            runner = TournamentRunner(self.config, self.conn)
            matches_played = await runner.run_tournament()
            
            self.stats["total_matches_played"] += matches_played
            self.log(f"✅ Tournament completed (~{matches_played} matches)")
            
            return True
        except Exception as e:
            self.log(f"❌ Failed to run tournament: {e}", "ERROR")
            return False
    
    async def run_next_generation(self) -> bool:
        """Generate next batch of stories."""
        self.log("🧬 Step 1: Generating next batch from top performers...")
        try:
            generator = NextBatchGenerator(self.config, self.conn)
            stories = await generator.generate_batch()
            
            self.stats["total_stories_generated"] += len(stories)
            self.log(f"✅ Generated {len(stories)} new story variants")
            
            return True
        except Exception as e:
            self.log(f"❌ Failed to generate next batch: {e}", "ERROR")
            return False
    
    async def export_top_stories(self, top_n: int = 5):
        """
        Queries the final batch, selects the top N stories by rating, and saves
        them to human-readable text files.
        """
        try:
            output_dir = self.config["output"]["directory"]
            os.makedirs(output_dir, exist_ok=True)

            latest_batch_num = self.get_latest_batch_number()
            if latest_batch_num == -1:
                self.log("No batches found to export from.", "WARN")
                return

            self.log(f"Fetching top {top_n} stories from final batch ({latest_batch_num})...")

            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT story_id, piece, rating, model_used, wins, losses, matches_played
                FROM stories
                WHERE batch_number = ?
                ORDER BY rating DESC
                LIMIT ?
            """, (latest_batch_num, top_n))
            
            top_stories = cursor.fetchall()

            if not top_stories:
                self.log(f"No stories found in batch {latest_batch_num} to export.", "WARN")
                return

            for i, story_row in enumerate(top_stories):
                rank = i + 1
                story = dict(story_row)
                
                # The text from the database is a standard Python string.
                # Special characters like \u2019 are already decoded.
                # We just need to write it to a file with UTF-8 encoding
                # to preserve all characters correctly.
                clean_piece = story['piece']

                header = (
                    f"--- AlphaEvolve Top Story ---\n"
                    f"Rank: {rank}\n"
                    f"Rating: {story['rating']:.1f}\n"
                    f"Record (W/L): {story['wins']}/{story['losses']} ({story['matches_played']} matches)\n"
                    f"Model: {story['model_used']}\n"
                    f"Story ID: {story['story_id']}\n"
                    f"-----------------------------\n\n"
                )
                
                file_content = header + clean_piece
                
                filename = f"rank_{rank}_story.txt"
                filepath = os.path.join(output_dir, filename)

                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(file_content)
                    self.log(f"  -> Saved Rank {rank} story to {filepath}")
                except Exception as e:
                    self.log(f"Failed to write file {filepath}: {e}", "ERROR")

            self.log(f"✅ Successfully exported top {len(top_stories)} stories.")

        except Exception as e:
            self.log(f"❌ Failed to export top stories: {e}", "ERROR")

    async def run_pipeline(self, max_iterations: int = None) -> bool:
        """
        Run the complete evolution pipeline.
        
        The pipeline consists of a one-time setup phase (initial generation +
        initial tournament), followed by N evolution cycles (next generation -> tournament).

        Args:
            max_iterations: Maximum number of evolution cycles to run (overrides config if provided).
                            An iteration is one step of generation + tournament.
            
        Returns:
            True if pipeline completed successfully.
        """
        self.start_time = time.time()
        self.stats["pipeline_start_time"] = datetime.now().isoformat()
        
        pipeline_config = self.config.get("evolution_pipeline", {})
        
        if max_iterations is None:
            max_iterations = pipeline_config.get("max_iterations", 3)
        
        start_batch_number = self.get_latest_batch_number()
        
        self.log(f"🧬 Starting Evolution Pipeline for {max_iterations} evolution cycles.")
        self.log(f"Configuration: {self.config['batch_generation']['num_stories']} stories per batch")
        self.log(f"Tournament: {self.config['glicko_ranking']['tournament_rounds']} rounds per tournament")
        
        # --- Initial Setup ---
        if start_batch_number == -1:
            self.log("📝 No existing batches found in DB. Performing initial setup...")
            
            # Step 1: Initial Generation
            self.log("--- SETUP STEP 1 of 2: Initial Generation ---")
            if not await self.run_initial_generation():
                self.log_pipeline_summary()
                return False
            
            # Step 2: Initial Tournament/Judgement
            self.log("--- SETUP STEP 2 of 2: Initial Judgement ---")
            if not await self.run_tournament():
                self.log_pipeline_summary()
                return False
            
            self.log("✅ Initial setup complete. Starting evolution cycles.")
        else:
            self.log(f"📁 Found existing data up to judged batch {start_batch_number}.")
            self.log(f"🔄 Continuing evolution from batch {start_batch_number}.")
        
        # --- Evolution Loop ---
        success = True
        for i in range(1, max_iterations + 1):
            iteration_start = time.time()
            self.log_iteration_start(i)
            
            # Each evolution cycle is: Next Generation -> Tournament
            
            if not await self.run_next_generation():
                success = False
                break
            
            if not await self.run_tournament():
                success = False
                break
                
            self.stats["iterations_completed"] = i
            iteration_time = time.time() - iteration_start
            self.stats["iteration_times"].append(iteration_time)
            self.log_iteration_end(i, iteration_time)
        
        # --- Final Export ---
        if success:
            self.log("🏅 Exporting final top stories...")
            await self.export_top_stories()

        self.stats["pipeline_end_time"] = datetime.now().isoformat()
        self.log_pipeline_summary()
        
        return success