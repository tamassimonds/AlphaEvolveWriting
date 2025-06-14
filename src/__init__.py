"""
AlphaEvolve Writing - Story Evolution Pipeline

A modern Python package for evolving creative writing through AI-powered tournaments.
"""

__version__ = "1.0.0"
__author__ = "AlphaEvolve Team"
__email__ = "contact@alphaevolve.com"

from .core.pipeline import EvolutionPipeline
from .generators.story_generator import InitialStoryGenerator, NextBatchGenerator
from .rankers.tournament_runner import TournamentRunner

__all__ = [
    "EvolutionPipeline",
    "InitialStoryGenerator", 
    "NextBatchGenerator",
    "TournamentRunner"
]