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
import os
import asyncio
import argparse
from src.core.pipeline import EvolutionPipeline


def create_parser():
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(description="Run automated story evolution pipeline")
    parser.add_argument(
        "iterations", 
        type=int, 
        nargs='?',
        help="Number of evolution iterations to run (default: from config.json)"
    )
    parser.add_argument(
        "--fresh", 
        action="store_true", 
        help="Start fresh even if existing batches are found"
    )
    parser.add_argument(
        "--general", 
        action="store_true", 
        help="Use general writing mode instead of creative writing"
    )
    parser.add_argument(
        "--config", 
        type=str, 
        default="config.json", 
        help="Path to configuration file (default: config.json)"
    )
    
    return parser


async def main():
    """Main function for evolution pipeline."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle help manually for better formatting
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in ["--help", "-h"]):
        print(__doc__)
        print("\nOptions:")
        parser.print_help()
        return 0
    
    # Set environment variable for general mode
    if args.general:
        os.environ['USE_GENERAL_MODE'] = '1'
        print("📝 Using general writing mode")
    
    # Initialize pipeline
    try:
        pipeline = EvolutionPipeline(args.config)
    except FileNotFoundError:
        print(f"❌ Config file not found: {args.config}")
        return 1
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return 1
    
    # Handle fresh start
    if args.fresh:
        pipeline.existing_batches = []
        print("🔄 Fresh start requested")
    
    # Determine iterations
    if args.iterations is not None:
        iterations = args.iterations
    else:
        pipeline_config = pipeline.config.get("evolution_pipeline", {})
        iterations = pipeline_config.get("max_iterations", 3)
        print(f"Using default iterations from config: {iterations}")
    
    # Show what we're doing
    print(f"🧬 Running {iterations} evolution iterations...")
    
    try:
        success = await pipeline.run_pipeline(max_iterations=iterations)
        
        if success:
            print("\n🎉 Evolution completed successfully!")
            return 0
        else:
            print("\n💥 Evolution failed!")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️  Evolution interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Evolution failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))