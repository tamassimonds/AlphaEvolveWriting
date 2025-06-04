#!/usr/bin/env python3
"""
Simple Evolution Runner

Quick command to run story evolution for N iterations.
Automatically detects existing batches and continues from where you left off.

Usage:
    python evolve.py 5          # Run 5 iterations  
    python evolve.py 3 --fresh  # Fresh start with 3 iterations
    python evolve.py --help     # Show all options
"""

import sys
import asyncio
from run_evolution_pipeline import EvolutionPipeline

def main():
    """Simple command line interface for evolution."""
    
    # Load config to get default iterations
    pipeline = EvolutionPipeline()
    pipeline_config = pipeline.config.get("evolution_pipeline", {})
    default_iterations = pipeline_config.get("max_iterations", 3)
    
    # Parse simple arguments
    iterations = None  # Will use config default if not specified
    fresh_start = False
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print(__doc__)
            print("\nQuick usage:")
            print("  python evolve.py [iterations] [--fresh]")
            print(f"  iterations: number of evolution cycles (default from config: {default_iterations})")
            print("  --fresh: start fresh even if existing batches found")
            print("\nFor advanced options, use: python run_evolution_pipeline.py --help")
            return 0
            
        try:
            iterations = int(sys.argv[1])
        except ValueError:
            print(f"❌ Invalid number of iterations: {sys.argv[1]}")
            return 1
    
    if "--fresh" in sys.argv:
        fresh_start = True
    
    async def run():
        # Use the pipeline we already created
        if fresh_start:
            pipeline.existing_batches = []
            print("🔄 Fresh start requested")
        
        # Show what we're doing
        actual_iterations = iterations if iterations is not None else default_iterations
        print(f"🧬 Running {actual_iterations} evolution iterations...")
        if iterations is None:
            print(f"   (using default from config.json)")
        
        success = await pipeline.run_pipeline(max_iterations=iterations)
        
        if success:
            print("\n🎉 Evolution completed successfully!")
            return 0
        else:
            print("\n💥 Evolution failed!")
            return 1
    
    return asyncio.run(run())

if __name__ == "__main__":
    sys.exit(main())