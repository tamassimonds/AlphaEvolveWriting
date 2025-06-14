"""
Generate general writing pieces and their improvements.

This module creates various types of writing pieces (essays, academic papers, reports, etc.)
based on topic descriptions and can generate improved versions of existing pieces while
maintaining the core arguments and structure.
"""

import re
import random
from typing import Dict, Any, List, Optional


# Writing approaches that provide different goals and methodologies
WRITING_APPROACHES = [
    {
        "name": "analytical_depth",
        "description": "Focus on logical analysis and critical thinking",
        "goals": [
            "Develop clear and compelling arguments",
            "Support claims with strong evidence and reasoning",
            "Analyze complex topics with systematic methodology",
            "Build logical connections between ideas",
            "Present balanced perspectives on the topic"
        ]
    },
    {
        "name": "research_synthesis", 
        "description": "Emphasize thorough research integration and synthesis",
        "goals": [
            "Integrate diverse sources effectively",
            "Synthesize complex information clearly",
            "Present balanced coverage of existing literature",
            "Connect different theoretical perspectives",
            "Draw insightful conclusions from research"
        ]
    },
    {
        "name": "structural_innovation",
        "description": "Experiment with effective organizational techniques", 
        "goals": [
            "Use clear and logical organization",
            "Create smooth transitions between ideas",
            "Structure arguments for maximum impact",
            "Balance different types of evidence",
            "Maintain coherent flow throughout"
        ]
    }
]

# Writing style variations to add diverse approaches
WRITING_STYLES = [
    {
        "name": "academic_precision",
        "description": "Clear, precise academic writing with strong scholarly foundation",
        "characteristics": [
            "Use precise, technical language appropriate to the field",
            "Structure arguments with clear thesis and supporting evidence",
            "Employ proper academic citations and references",
            "Maintain objective, scholarly tone throughout",
            "Build arguments systematically with clear reasoning",
            "Address potential counterarguments effectively"
        ]
    },
    {
        "name": "journalistic_clarity",
        "description": "Clear, engaging journalistic style that informs and explains",
        "characteristics": [
            "Present information in clear, accessible language",
            "Use strong topic sentences and clear structure",
            "Incorporate relevant quotes and examples effectively",
            "Balance detail with readability",
            "Maintain objectivity while engaging readers",
            "Use active voice and direct language"
        ]
    },
    {
        "name": "analytical_depth",
        "description": "Deep analytical writing that examines complex topics thoroughly",
        "characteristics": [
            "Break down complex ideas into clear components",
            "Build logical arguments step by step",
            "Use precise definitions and careful distinctions",
            "Support claims with strong evidence",
            "Address multiple perspectives fairly",
            "Draw insightful conclusions from analysis"
        ]
    },
    {
        "name": "technical_expertise",
        "description": "Clear technical writing that explains complex topics effectively",
        "characteristics": [
            "Present technical information clearly and precisely",
            "Use appropriate field-specific terminology",
            "Structure information logically and systematically",
            "Include helpful examples and illustrations",
            "Define technical terms when needed",
            "Balance detail with accessibility"
        ]
    },
    {
        "name": "persuasive_argument",
        "description": "Strong argumentative writing that convinces through logic and evidence",
        "characteristics": [
            "Present clear, compelling thesis statements",
            "Support arguments with strong evidence",
            "Address counterarguments effectively",
            "Use rhetorical techniques strategically",
            "Build to powerful conclusions",
            "Maintain professional, authoritative tone"
        ]
    },
    {
        "name": "explanatory_clarity",
        "description": "Clear explanatory writing that makes complex topics accessible",
        "characteristics": [
            "Break down complex topics into understandable parts",
            "Use clear examples and analogies",
            "Progress logically from simple to complex",
            "Anticipate and address reader questions",
            "Use clear transitions and signposting",
            "Balance depth with accessibility"
        ]
    },
    {
        "name": "research_synthesis",
        "description": "Effective research synthesis that integrates multiple sources",
        "characteristics": [
            "Synthesize information from multiple sources clearly",
            "Compare and contrast different perspectives",
            "Identify key themes and patterns",
            "Present balanced coverage of the literature",
            "Draw meaningful conclusions from research",
            "Maintain clear organization of sources"
        ]
    },
    {
        "name": "policy_analysis",
        "description": "Clear policy analysis that examines issues systematically",
        "characteristics": [
            "Present clear policy context and background",
            "Analyze problems systematically",
            "Evaluate policy options objectively",
            "Support recommendations with evidence",
            "Consider implementation challenges",
            "Address stakeholder concerns"
        ]
    },
    {
        "name": "business_professional",
        "description": "Professional business writing that is clear and action-oriented",
        "characteristics": [
            "Present information concisely and clearly",
            "Focus on key actionable points",
            "Use professional business terminology",
            "Structure documents for quick understanding",
            "Include clear recommendations",
            "Maintain professional tone throughout"
        ]
    },
    {
        "name": "scientific_method",
        "description": "Clear scientific writing that presents research effectively",
        "characteristics": [
            "Present methods and results clearly",
            "Use appropriate scientific terminology",
            "Structure papers according to scientific conventions",
            "Present data and findings accurately",
            "Discuss implications of results",
            "Maintain scientific objectivity"
        ]
    }
]

IMPROVEMENT_SETS = [
    {
        "name": "argument_strength",
        "description": "Strengthen arguments and logical flow",
        "goals": [
            "Clarify main thesis and supporting arguments",
            "Strengthen evidence and reasoning",
            "Address potential counterarguments",
            "Improve logical flow between ideas",
            "Enhance conclusion impact",
            "Ensure claims are well-supported"
        ]
    },
    {
        "name": "research_integration",
        "description": "Improve research integration and citation",
        "goals": [
            "Integrate sources more effectively",
            "Strengthen citation practices",
            "Balance different types of evidence",
            "Synthesize research findings clearly",
            "Connect sources to arguments",
            "Present balanced literature coverage"
        ]
    },
    {
        "name": "clarity_improvement",
        "description": "Enhance clarity and readability",
        "goals": [
            "Clarify complex concepts",
            "Improve sentence structure",
            "Strengthen topic sentences",
            "Use clearer transitions",
            "Define terms effectively",
            "Balance detail with accessibility"
        ]
    },
    {
        "name": "structure_organization",
        "description": "Perfect document structure and organization",
        "goals": [
            "Improve overall organization",
            "Strengthen paragraph structure",
            "Create better transitions",
            "Balance different sections",
            "Enhance introduction and conclusion",
            "Maintain consistent focus"
        ]
    },
    {
        "name": "language_precision",
        "description": "Enhance language precision and professionalism",
        "goals": [
            "Use more precise terminology",
            "Improve word choice",
            "Maintain consistent tone",
            "Eliminate unnecessary words",
            "Use appropriate field-specific language",
            "Balance technical and accessible language"
        ]
    },
    {
        "name": "analysis_depth",
        "description": "Deepen analysis and critical thinking",
        "goals": [
            "Strengthen analytical framework",
            "Deepen critical analysis",
            "Consider multiple perspectives",
            "Improve theoretical connections",
            "Enhance methodology discussion",
            "Draw more insightful conclusions"
        ]
    },
    {
        "name": "evidence_support",
        "description": "Strengthen evidence and support",
        "goals": [
            "Improve evidence quality",
            "Strengthen data presentation",
            "Better integrate examples",
            "Support claims more effectively",
            "Balance different types of evidence",
            "Connect evidence to arguments clearly"
        ]
    },
    {
        "name": "audience_engagement",
        "description": "Enhance audience engagement and accessibility",
        "goals": [
            "Adjust to audience level",
            "Improve readability",
            "Add relevant examples",
            "Clarify complex concepts",
            "Maintain reader interest",
            "Balance depth with accessibility"
        ]
    },
    {
        "name": "technical_precision",
        "description": "Improve technical accuracy and detail",
        "goals": [
            "Enhance technical accuracy",
            "Improve methodology description",
            "Clarify technical concepts",
            "Use proper terminology",
            "Present data effectively",
            "Balance technical detail with clarity"
        ]
    },
    {
        "name": "persuasive_impact",
        "description": "Strengthen persuasive impact and argumentation",
        "goals": [
            "Enhance argument structure",
            "Strengthen rhetorical techniques",
            "Improve persuasive flow",
            "Address objections effectively",
            "Build to stronger conclusions",
            "Balance logic and persuasion"
        ]
    }
]


def get_random_approach() -> Dict[str, Any]:
    """Get a randomly selected writing approach."""
    return random.choice(WRITING_APPROACHES)


def get_random_writing_style() -> Dict[str, Any]:
    """Get a randomly selected writing style."""
    return random.choice(WRITING_STYLES)


def get_random_improvement_sets(n: int = 2) -> List[Dict[str, Any]]:
    """Get n randomly selected improvement sets."""
    return random.sample(IMPROVEMENT_SETS, k=min(n, len(IMPROVEMENT_SETS)))


def load_rubric(rubric_file: str = "rubric.txt") -> str:
    """Load rubric from file."""
    try:
        with open(rubric_file, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        # Fallback to basic guidelines if file not found
        return """Focus on clear argumentation, strong evidence, logical organization, appropriate language, and proper citation."""


async def generate_initial_piece(
    topic_description: str, 
    model: str = "gpt-4", 
    rubric_file: str = "rubric.txt",
    use_random_approach: bool = True,
    use_random_style: bool = True
) -> str:
    """
    Generate a writing piece based on a topic description and rubric.
    
    Args:
        topic_description: Detailed description of the topic and requirements
        model: The model to use for generation
        rubric_file: Path to the rubric file
        use_random_approach: Whether to use a random writing approach
        use_random_style: Whether to use a random writing style
        
    Returns:
        The generated piece as a string
    """
    
    rubric = load_rubric(rubric_file)
    
    # Get random approach and style if enabled
    approach_section = ""
    style_section = ""
    
    if use_random_approach:
        approach = get_random_approach()
        approach_goals = "\n".join(f"• {goal}" for goal in approach["goals"])
        approach_section = f"""
## Writing Approach: {approach["description"]}
Your specific writing goals:
{approach_goals}
"""

    if use_random_style:
        style = get_random_writing_style()
        style_characteristics = "\n".join(f"• {char}" for char in style["characteristics"])
        style_section = f"""
## Writing Style: {style["description"]}
Follow these stylistic characteristics:
{style_characteristics}
"""

    prompt = f"""Write a piece based on this topic description: {topic_description}
{approach_section}{style_section}
## Evaluation Rubric
{rubric}

Create a clear, well-structured piece that addresses the topic while meeting the criteria in the evaluation rubric{" and your writing approach" if use_random_approach else ""}{" in your chosen style" if use_random_style else ""}. 

Write only the piece - no analysis or commentary needed."""

    from ..utils.inference import generate_text
    response = await generate_text(model, prompt, temperature=1)
    return response.strip()


async def generate_piece_variant(
    original_piece: str,
    original_prompt: str,
    model: str = "gpt-4",
    rubric_file: str = "rubric.txt",
    temperature: float = 1.2
) -> str:
    """
    Generate a variant of an existing piece with moderate improvements.
    
    Args:
        original_piece: The original piece to create a variant from
        original_prompt: The original prompt that generated the piece
        model: The model to use for generation
        rubric_file: Path to the rubric file
        temperature: Temperature for more variation
        
    Returns:
        A new piece variant as a string with moderate improvements
    """
    
    rubric = load_rubric(rubric_file)

    prompt = f"""You are tasked with creating an improved variant of an existing piece. Make meaningful improvements while keeping the core arguments and structure recognizable.

## Original Prompt:
{original_prompt}

## Original Piece:
{original_piece}

## Evaluation Rubric:
{rubric}

## Your Task:
Create a variant that makes MODERATE improvements such as:
- Strengthen the argumentation and evidence
- Improve organization and flow
- Enhance clarity and precision
- Refine language and terminology
- Add or improve key supporting points
- Better integrate research and citations
- Improve technical accuracy
- Enhance logical connections
- Strengthen conclusions
- Add relevant examples or data

## Guidelines:
- Keep the core thesis and main arguments the same
- You can modify 20-30% of the piece for improvements
- Focus on making the writing more effective and professional
- Improve weak areas while preserving what works well
- Enhance rather than completely change major points
- Make the piece more polished and convincing overall
- Ensure all changes serve to improve clarity and impact

Write only the improved piece variant - no analysis or commentary needed."""

    from ..utils.inference import generate_text
    response = await generate_text(model, prompt, temperature=temperature)
    return response.strip()


# Alias for compatibility with story-focused modules
generate_story_variant = generate_piece_variant

