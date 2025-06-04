"""
Rank two model responses for creative writing based on a rubric.

This module compares two model responses and determines which one is better
based on a hardcoded evaluation rubric.
"""

from typing import Dict, Any
from dataclasses import dataclass
from utils.inference import generate_text


def load_rubric(rubric_file: str = "rubric.txt") -> str:
    """Load rubric from file."""
    try:
        with open(rubric_file, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        # Fallback to a basic rubric if file not found
        return """Creative writing evaluation should consider:
1. Creativity and Originality (25%) - Unique ideas, fresh perspectives, innovative storytelling
2. Writing Quality (25%) - Grammar, style, flow, vocabulary, sentence structure  
3. Engagement (20%) - How compelling and interesting the piece is to read
4. Character Development (15%) - Believable, well-developed characters with clear motivations
5. Plot Structure (15%) - Logical progression, pacing, resolution of conflicts"""


@dataclass
class ModelComparison:
    """Represents the comparison of two model responses."""
    winner: str  # "model_1" or "model_2"
    reasoning: str  # Detailed explanation of the ranking decision


async def judge_responses(
    model_1_response: str,
    model_2_response: str,
    judge_model: str = "gpt-4o-mini",
    rubric_file: str = "rubric.txt"
) -> ModelComparison:
    """
    Compare two model responses and determine which is better based on the rubric.
    
    Args:
        model_1_response: First model's creative writing response
        model_2_response: Second model's creative writing response
        judge_model: The model to use for evaluation
        rubric_file: Path to the rubric file
        
    Returns:
        ModelComparison object with winner and reasoning
    """
    
    rubric = load_rubric(rubric_file)
    
    prompt = f"""You are an expert creative writing judge. Your task is to compare two creative writing pieces and determine which one is better based on the provided rubric.

## Evaluation Rubric
{rubric}

## Model 1 Response:
{model_1_response}

## Model 2 Response:
{model_2_response}

## Your Task:
Carefully evaluate both responses against the rubric criteria. Consider each category and determine which response performs better overall.

## Output Format:
WINNER: model_1 or model_2
REASONING: <Provide a detailed explanation of your decision, referencing specific aspects of each response and how they align with the rubric criteria. Be specific about what makes the winning response better.>

Now compare the responses and make your judgment."""

    response = await generate_text(judge_model, prompt)
    
    # Parse the response
    lines = response.strip().split('\n')
    winner = None
    reasoning = ""
    
    for i, line in enumerate(lines):
        if line.startswith('WINNER:'):
            winner = line.split(':', 1)[1].strip()
        elif line.startswith('REASONING:'):
            reasoning = line.split(':', 1)[1].strip()
            # Include any additional lines as part of reasoning
            if i + 1 < len(lines):
                reasoning += '\n' + '\n'.join(lines[i+1:])
            break
    
    if not winner or winner not in ['model_1', 'model_2']:
        raise ValueError(f"Failed to parse winner from response. Got: {response}")
    
    return ModelComparison(
        winner=winner,
        reasoning=reasoning
    )
