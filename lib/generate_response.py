"""
Generate creative writing pieces and their improvements.

This module creates creative writing pieces based on story descriptions and can generate
improved versions of existing pieces while maintaining the core narrative elements.
"""

import re
from typing import Dict, Any, List, Optional
from utils.inference import generate_text


def load_rubric(rubric_file: str = "rubric.txt") -> str:
    """Load rubric from file."""
    try:
        with open(rubric_file, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        # Fallback to basic guidelines if file not found
        return """Focus on strong narrative flow, compelling characters, vivid imagery, natural dialogue, and proper pacing."""


async def generate_simple_piece(story_description: str, model: str = "gpt-4", rubric_file: str = "rubric.txt") -> str:
    """
    Generate a simple creative writing piece based on a story description and rubric.
    
    Args:
        story_description: Detailed description of the desired story elements
        model: The model to use for generation
        rubric_file: Path to the rubric file
        
    Returns:
        The generated story as a string
    """
    
    rubric = load_rubric(rubric_file)
    
    prompt = f"""Write a creative story based on this description: {story_description}

You will be evaluated according to this rubric:

{rubric}

Create an engaging, well-written story that captures the essence of the description while meeting the criteria in the evaluation rubric. 

Write only the story - no analysis or commentary needed."""

    response = await generate_text(model, prompt, temperature=1)
    return response.strip()


async def generate_story_variant(
    original_story: str,
    original_prompt: str,
    model: str = "gpt-4",
    rubric_file: str = "rubric.txt",
    temperature: float = 1.2
) -> str:
    """
    Generate a variant of an existing story while maintaining the core narrative.
    
    Args:
        original_story: The original story to create a variant from
        original_prompt: The original prompt that generated the story
        model: The model to use for generation
        rubric_file: Path to the rubric file
        temperature: Temperature for more creative variations
        
    Returns:
        A new story variant as a string
    """
    
    rubric = load_rubric(rubric_file)
    
    prompt = f"""You are tasked with creating a creative variant of an existing story. The goal is to maintain the core narrative elements while exploring different approaches, perspectives, or stylistic choices.

## Original Prompt:
{original_prompt}

## Original Story:
{original_story}

## Evaluation Rubric:
{rubric}

## Your Task:
Create a new variant of this story that:
- Maintains the core premise and key narrative elements
- Explores different stylistic approaches, perspectives, or narrative techniques
- Could be told from a different character's viewpoint
- Might emphasize different themes or emotional beats
- Uses different pacing, structure, or descriptive language
- Still targets the evaluation rubric for quality

## Guidelines:
- Keep the fundamental story concept intact
- Feel free to change narrative perspective, tense, or style
- Explore different character dynamics or emotional emphasis
- Vary the pacing, structure, or descriptive detail
- Maintain high quality according to the rubric criteria

Write only the story variant - no analysis or commentary needed."""

    response = await generate_text(model, prompt, temperature=temperature)
    return response.strip()


async def generate_initial_piece(story_description: str, model: str = "gpt-4") -> Dict[str, Any]:
    """
    Generate an initial creative writing piece based on a story description.
    
    Args:
        story_description: Detailed description of the desired story elements
        model: The model to use for generation
        
    Returns:
        Dict with 'piece', 'analysis', and 'suggestions' keys
    """
    
    prompt = """# Generate Creative Writing Piece

You are given a story description. Your task is to create an engaging creative writing piece
that captures the essence of the description while maintaining strong narrative elements.

## Story Description
{story_description}

## Your Task
Create a creative writing piece that:
- Has a clear narrative arc and engaging plot
- Develops compelling characters with distinct voices
- Uses vivid imagery and sensory details
- Maintains consistent tone and style
- Has natural dialogue and pacing
- Includes meaningful themes and motifs

## Output Format
Return your response in this exact format:

PIECE:
[Write your creative writing piece here - a complete, well-formed narrative]

ANALYSIS:
[Provide a brief analysis of the key narrative elements, themes, and techniques used]

SUGGESTIONS:
[Note any potential areas for improvement or expansion]

## Requirements
- Write a complete, self-contained piece
- Ensure proper grammar and punctuation
- Create engaging and natural dialogue
- Use varied sentence structure and vocabulary
- Include sensory details and imagery
- Maintain consistent point of view and tense

Generate your creative writing piece now.""".format(story_description=story_description)

    response = await generate_text(model, prompt, temperature=1)
    
    # Parse the response to extract piece, analysis, and suggestions
    piece_match = re.search(r'PIECE:\s*(.*?)(?=ANALYSIS:)', response, re.DOTALL)
    analysis_match = re.search(r'ANALYSIS:\s*(.*?)(?=SUGGESTIONS:)', response, re.DOTALL)
    suggestions_match = re.search(r'SUGGESTIONS:\s*(.*?)$', response, re.DOTALL)
    
    if not piece_match or not analysis_match or not suggestions_match:
        raise ValueError(f"Failed to parse response format. Got: {response}")
    
    return {
        'piece': piece_match.group(1).strip(),
        'analysis': analysis_match.group(1).strip(),
        'suggestions': suggestions_match.group(1).strip()
    }


async def generate_improvement(
    previous_pieces: List[Dict[str, Any]],
    story_description: str,
    
    model: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """
    Generate an improved version of previous creative writing pieces.
    
    Args:
        previous_pieces: List of previous writing pieces with their analyses
        story_description: Original story description
        focus_areas: Optional list of specific areas to focus on improving
        model: The model to use for generation
        
    Returns:
        Dict with 'improved_piece', 'analysis', and 'improvements' keys
    """
    
    # Format previous pieces for context
    previous_context = "\n\n".join([
        f"Piece {i+1}:\n{p['piece']}\nAnalysis: {p['analysis']}"
        for i, p in enumerate(previous_pieces)
    ])
    
    focus_areas_text = ""
    if focus_areas:
        focus_areas_text = "\nFocus Areas for Improvement:\n" + "\n".join(f"- {area}" for area in focus_areas)
    
    prompt = """# Generate Improved Creative Writing Piece

You are given previous creative writing pieces and their analyses. Your task is to create
an improved version that builds upon the strengths while addressing areas for enhancement.

## Original Story Description
{story_description}

## Previous Pieces
{previous_context}

## Your Task
Create an improved version that:
- Maintains the core narrative and themes
- Addresses previous suggestions for improvement
- Enhances character development and dialogue
- Strengthens plot structure and pacing
- Deepens thematic elements
- Improves descriptive language and imagery


## Output Format
Return your response in this exact format:

IMPROVED_PIECE:
[Write your improved creative writing piece here]

ANALYSIS:
[Provide a brief analysis of the improvements and key elements]

IMPROVEMENTS:
[Detail the specific improvements made and why they enhance the piece]

## Requirements
- Build upon the strengths of previous versions
- Address identified areas for improvement
- Maintain consistency with the original vision
- Create a more polished and engaging narrative
- Ensure all improvements serve the story's purpose

Generate your improved creative writing piece now.""".format(
        story_description=story_description,
        previous_context=previous_context,
        focus_areas_text=focus_areas_text
    )

    response = await generate_text(model, prompt)
    
    # Parse the response to extract improved piece, analysis, and improvements
    piece_match = re.search(r'IMPROVED_PIECE:\s*(.*?)(?=ANALYSIS:)', response, re.DOTALL)
    analysis_match = re.search(r'ANALYSIS:\s*(.*?)(?=IMPROVEMENTS:)', response, re.DOTALL)
    improvements_match = re.search(r'IMPROVEMENTS:\s*(.*?)$', response, re.DOTALL)
    
    if not piece_match or not analysis_match or not improvements_match:
        raise ValueError(f"Failed to parse response format. Got: {response}")
    
    return {
        'improved_piece': piece_match.group(1).strip(),
        'analysis': analysis_match.group(1).strip(),
        'improvements': improvements_match.group(1).strip()
    }


def validate_piece(piece: str) -> bool:
    """
    Basic validation that the creative writing piece is well-formed.
    
    Args:
        piece: The writing piece to validate
        
    Returns:
        True if the piece appears valid
    """
    # Check that piece is not empty and has reasonable length
    if not piece or len(piece.strip()) < 200:
        return False
    
    # Check for basic narrative elements
    narrative_indicators = ['said', 'thought', 'felt', 'walked', 'looked', 'saw']
    if not any(indicator in piece.lower() for indicator in narrative_indicators):
        return False
    
    # Check for proper sentence structure
    if not re.search(r'[.!?]', piece):
        return False
    
    return True


async def generate_validated_piece(
    story_description: str,
    max_attempts: int = 3,
    model: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """
    Generate a validated creative writing piece with retry logic.
    
    Args:
        story_description: The story description to base the piece on
        max_attempts: Maximum number of generation attempts
        model: The model to use for generation
        
    Returns:
        Dict with 'piece', 'analysis', and 'suggestions' keys
        
    Raises:
        ValueError: If unable to generate valid piece after max_attempts
    """
    for attempt in range(max_attempts):
        try:
            result = await generate_initial_piece(story_description, model)
            
            if validate_piece(result['piece']):
                return result
            else:
                print(f"Attempt {attempt + 1} failed validation, retrying...")
                
        except Exception as e:
            print(f"Attempt {attempt + 1} failed with error: {e}")
            
    raise ValueError(f"Failed to generate valid piece after {max_attempts} attempts")
