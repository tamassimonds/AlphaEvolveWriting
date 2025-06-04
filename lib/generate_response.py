"""
Generate creative writing pieces and their improvements.

This module creates creative writing pieces based on story descriptions and can generate
improved versions of existing pieces while maintaining the core narrative elements.
"""

import re
import random
from typing import Dict, Any, List, Optional


# Mission sets that provide different creative goals and approaches
MISSION_SETS = [
    {
        "name": "emotional_depth",
        "description": "Focus on emotional resonance and psychological depth",
        "goals": [
            "Create deep emotional connections between characters and readers",
            "Explore complex psychological motivations and inner conflicts",
            "Use subtle emotional cues and body language",
            "Build emotional tension through character relationships",
            "Make readers feel the characters' emotions viscerally"
        ]
    },
    {
        "name": "atmospheric_immersion", 
        "description": "Emphasize atmosphere, setting, and sensory immersion",
        "goals": [
            "Create a vivid, immersive world that readers can feel and smell",
            "Use all five senses to bring scenes to life",
            "Build atmosphere through environmental details and mood",
            "Make the setting feel like a character itself",
            "Use weather, lighting, and physical space to enhance emotion"
        ]
    },
    {
        "name": "narrative_innovation",
        "description": "Experiment with unique narrative techniques and structure", 
        "goals": [
            "Use innovative storytelling techniques or perspectives",
            "Experiment with narrative structure, pacing, or voice",
            "Find fresh approaches to familiar story elements",
            "Use literary devices in creative and unexpected ways",
            "Challenge conventional storytelling while maintaining clarity"
        ]
    }
]

# Author style variations to add diverse voices and approaches
AUTHOR_STYLES = [
    {
        "name": "hemingway_iceberg",
        "description": "Ernest Hemingway's minimalist precision - the iceberg theory where deeper meaning lies beneath simple surface",
        "characteristics": [
            "Use short, declarative sentences with powerful subtext",
            "Show emotion through action and dialogue, never state it directly",
            "Employ the 'iceberg theory' - let 90% of meaning remain beneath the surface",
            "Write with clean, unadorned prose that carries profound weight",
            "Use repetition and rhythm to create emotional undertow",
            "Focus on concrete details that suggest larger truths"
        ]
    },
    {
        "name": "morrison_lyrical_depth",
        "description": "Toni Morrison's richly layered, musical prose that weaves together beauty and profound social insight",
        "characteristics": [
            "Use language that sings - employ rhythm, repetition, and oral tradition elements",
            "Weave together multiple timeframes and perspectives seamlessly",
            "Create sentences that function as both poetry and narrative",
            "Embed deep cultural and historical resonance in every scene",
            "Use sensory details that connect to larger themes of identity and belonging",
            "Let characters' voices carry the wisdom of generations"
        ]
    },
    {
        "name": "nabokov_ornate_precision",
        "description": "Vladimir Nabokov's exquisitely crafted, multilayered literary style with perfect word choice",
        "characteristics": [
            "Choose every word with surgical precision for multiple layers of meaning",
            "Create sentences that are both beautiful and intellectually complex",
            "Use rich, sophisticated vocabulary without appearing pretentious",
            "Embed literary allusions and wordplay that reward careful readers",
            "Balance ornate description with psychological insight",
            "Craft prose that works on aesthetic, emotional, and intellectual levels simultaneously"
        ]
    },
    {
        "name": "austen_wit_observation",
        "description": "Jane Austen's brilliant social observation wrapped in elegant wit and irony",
        "characteristics": [
            "Use gentle irony and wit to reveal character and social dynamics",
            "Create dialogue that sparkles with intelligence and subtext",
            "Observe human nature with both compassion and sharp insight",
            "Balance social critique with warm humanity",
            "Employ free indirect discourse to blend narrator and character perspectives",
            "Write with elegant, measured prose that never wastes a word"
        ]
    },
    {
        "name": "marquez_magical_realism",
        "description": "Gabriel García Márquez's seamless blend of magical and mundane, creating transcendent storytelling",
        "characteristics": [
            "Present extraordinary events with matter-of-fact acceptance",
            "Use magical elements to illuminate deeper truths about human experience",
            "Create sweeping, multi-generational narratives with epic scope",
            "Employ rich, sensuous language that makes the impossible feel inevitable",
            "Blend myth, history, and reality into a unified vision",
            "Use repetition and circular narrative structures like oral storytelling"
        ]
    },
    {
        "name": "woolf_stream_consciousness",
        "description": "Virginia Woolf's flowing, introspective modernist style that captures the rhythm of thought",
        "characteristics": [
            "Let consciousness flow naturally between thoughts, memories, and observations",
            "Use long, flowing sentences that mirror the movement of the mind",
            "Capture the texture of inner life with poetic precision",
            "Blend external events with internal psychological landscapes",
            "Employ stream-of-consciousness to reveal character depth",
            "Create prose that functions as both narrative and psychological exploration"
        ]
    },
    {
        "name": "mccarthy_biblical_sparse",
        "description": "Cormac McCarthy's stark, biblical prose that achieves mythic power through restraint",
        "characteristics": [
            "Use sparse punctuation and biblical rhythms to create hypnotic flow",
            "Employ archaic and regional language for timeless, mythic quality",
            "Create vast, elemental landscapes that mirror internal states",
            "Use violence and beauty with equal stark honesty",
            "Write dialogue without quotation marks, blending speech with narrative",
            "Achieve profound meaning through carefully chosen, sometimes harsh imagery"
        ]
    },
    {
        "name": "tartt_immersive_literary",
        "description": "Donna Tartt's richly detailed, immersive literary fiction that creates complete worlds",
        "characteristics": [
            "Create incredibly detailed, atmospheric settings that become characters themselves",
            "Use classical literary techniques with contemporary psychological insight",
            "Build complex, morally ambiguous characters with depth and contradictions",
            "Employ rich, descriptive language that rewards close reading",
            "Weave together multiple plot threads with masterful pacing",
            "Reference high culture and literature to create intellectual depth"
        ]
    },
    {
        "name": "carver_precise_minimalism",
        "description": "Raymond Carver's clean, precise minimalism that finds profundity in ordinary moments",
        "characteristics": [
            "Use simple, direct language to reveal complex emotional truths",
            "Focus on ordinary people in everyday situations with extraordinary insight",
            "Let dialogue carry the weight of character development",
            "Employ careful restraint - suggest rather than explain",
            "Create stories that feel like overheard conversations with hidden depths",
            "Use precise details that illuminate larger themes about human connection"
        ]
    },
    {
        "name": "ishiguro_understated_profound",
        "description": "Kazuo Ishiguro's understated elegance that builds to devastating emotional revelations",
        "characteristics": [
            "Use deceptively simple prose that builds cumulative emotional power",
            "Employ unreliable narrators who reveal truth through what they don't say",
            "Create a sense of something important left unsaid or half-remembered",
            "Build to quiet but devastating moments of recognition and loss",
            "Use formal, polite language that masks deeper emotional currents",
            "Explore themes of memory, dignity, and the passage of time with subtle grace"
        ]
    },
    {
        "name": "atwood_speculative_literary",
        "description": "Margaret Atwood's intellectually rigorous speculative fiction with literary depth",
        "characteristics": [
            "Blend speculative elements with sharp social and political commentary",
            "Create dystopian or alternative worlds that illuminate current realities",
            "Use precise, unadorned prose that serves both story and ideas",
            "Develop complex female characters with agency and depth",
            "Embed feminist and environmental themes naturally within compelling narratives",
            "Balance literary sophistication with accessibility and page-turning engagement"
        ]
    },
    {
        "name": "baldwin_passionate_truth",
        "description": "James Baldwin's passionate, truthful prose that confronts reality with unflinching honesty and love",
        "characteristics": [
            "Write with passionate honesty about difficult truths",
            "Use personal experience to illuminate universal themes",
            "Employ biblical and jazz rhythms in prose structure",
            "Create dialogue that crackles with authenticity and emotional truth",
            "Balance anger and love, critique and compassion",
            "Use language as both weapon and healing balm for social wounds"
        ]
    }
]

IMPROVEMENT_SETS = [
    {
        "name": "tension_mastery",
        "description": "Master tension, conflict, and dramatic stakes",
        "goals": [
            "Create multiple layers of conflict (internal, interpersonal, societal)",
            "Build unbearable tension through delayed gratification and mounting stakes",
            "Use dramatic irony to create reader anticipation and dread",
            "Escalate conflict progressively with unexpected complications",
            "Make every scene either advance conflict or deepen character under pressure",
            "Create moments where characters must choose between competing values"
        ]
    },
    {
        "name": "sensory_immersion",
        "description": "Create visceral, multi-sensory world-building that transports readers",
        "goals": [
            "Engage all five senses in every significant scene",
            "Use specific, concrete details that trigger emotional memory",
            "Create atmosphere through environmental storytelling",
            "Make the physical world reflect and amplify emotional states",
            "Use weather, lighting, and space as active story elements",
            "Build sensory details that reveal character psychology and history"
        ]
    },
    {
        "name": "dialogue_excellence",
        "description": "Craft dialogue that crackles with subtext and authenticity",
        "goals": [
            "Make characters speak in distinct voices with unique speech patterns",
            "Layer dialogue with subtext - what's unsaid is as important as what's said",
            "Use dialogue to reveal character backstory and motivation indirectly",
            "Create conversations that advance plot while feeling completely natural",
            "Build tension through what characters avoid saying",
            "Make every line of dialogue serve multiple narrative purposes"
        ]
    },
    {
        "name": "narrative_architecture",
        "description": "Perfect story structure and pacing for maximum impact",
        "goals": [
            "Create a compelling hook that poses an irresistible question",
            "Structure scenes to alternate between action and reflection masterfully",
            "Use foreshadowing and callbacks to create satisfying narrative echoes",
            "Build to a climax that feels both surprising and inevitable",
            "Control pacing - know when to accelerate and when to slow down",
            "End scenes with hooks that compel readers to continue"
        ]
    },
    {
        "name": "language_artistry",
        "description": "Elevate prose to the level of poetry while serving story",
        "goals": [
            "Choose words for both meaning and musicality",
            "Vary sentence length and structure for optimal rhythm",
            "Use metaphors and imagery that illuminate character and theme",
            "Eliminate every unnecessary word - make every sentence essential",
            "Create memorable phrases that linger in readers' minds",
            "Balance beautiful language with forward narrative momentum"
        ]
    },
    {
        "name": "psychological_depth",
        "description": "Reveal the hidden depths of human nature and motivation",
        "goals": [
            "Show characters' contradictions and internal conflicts authentically",
            "Reveal how past trauma shapes present behavior subtly",
            "Create characters who surprise readers while staying true to their nature",
            "Explore the gap between who characters think they are and who they really are",
            "Use physical actions and unconscious behaviors to reveal psychology",
            "Make character growth feel earned through genuine struggle and revelation"
        ]
    },
    {
        "name": "thematic_resonance",
        "description": "Weave profound themes that elevate the story's meaning",
        "goals": [
            "Embed universal themes in specific, concrete story details",
            "Use symbolism and motifs that reinforce central themes organically",
            "Create story events that illuminate deeper truths about human nature",
            "Make the theme emerge naturally from character actions and choices",
            "Connect personal character journeys to larger universal questions",
            "Leave readers with insights that extend beyond the story itself"
        ]
    },
    {
        "name": "reader_magnetism",
        "description": "Create irresistible forward momentum and emotional connection",
        "goals": [
            "Make readers desperately need to know what happens next",
            "Create emotional investment so readers care deeply about outcomes",
            "Use cliffhangers and revelations strategically to maintain engagement",
            "Build anticipation through promises that must be fulfilled",
            "Make readers feel they're experiencing events alongside characters",
            "Create moments of catharsis that provide deep emotional satisfaction"
        ]
    },
    {
        "name": "literary_sophistication",
        "description": "Deploy advanced literary techniques with masterful precision",
        "goals": [
            "Use unreliable narration or shifting perspectives for maximum impact",
            "Employ literary devices (irony, allegory, juxtaposition) seamlessly",
            "Create multiple layers of meaning that reward close reading",
            "Use time structure (flashbacks, time jumps) to enhance storytelling",
            "Build intertextual connections that enrich the narrative",
            "Experiment with narrative voice and form while maintaining clarity"
        ]
    },
    {
        "name": "emotional_catharsis",
        "description": "Create profound emotional experiences that transform readers",
        "goals": [
            "Build to emotional moments that feel cathartic and necessary",
            "Create scenes that make readers laugh, cry, or gasp involuntarily",
            "Use character suffering and joy to create genuine emotional investment",
            "Make readers feel the characters' emotions as if they were their own",
            "Create moments of recognition where readers see themselves in characters",
            "Design emotional arcs that leave readers changed by the experience"
        ]
    }
]


def get_random_mission() -> Dict[str, Any]:
    """Get a randomly selected mission set."""
    return random.choice(MISSION_SETS)


def get_random_author_style() -> Dict[str, Any]:
    """Get a randomly selected author style."""
    return random.choice(AUTHOR_STYLES)


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
        return """Focus on strong narrative flow, compelling characters, vivid imagery, natural dialogue, and proper pacing."""


async def generate_simple_piece(
    story_description: str, 
    model: str = "gpt-4", 
    rubric_file: str = "rubric.txt",
    use_random_mission: bool = True,
    use_random_style: bool = True
) -> str:
    """
    Generate a simple creative writing piece based on a story description and rubric.
    
    Args:
        story_description: Detailed description of the desired story elements
        model: The model to use for generation
        rubric_file: Path to the rubric file
        use_random_mission: Whether to use a random mission set for creative goals
        use_random_style: Whether to use a random author style
        
    Returns:
        The generated story as a string
    """
    
    rubric = load_rubric(rubric_file)
    
    # Get random mission and style if enabled
    mission_section = ""
    style_section = ""
    
    if use_random_mission:
        mission = get_random_mission()
        mission_goals = "\n".join(f"• {goal}" for goal in mission["goals"])
        mission_section = f"""
## Creative Mission: {mission["description"]}
Your specific creative goals for this story:
{mission_goals}
"""

    if use_random_style:
        style = get_random_author_style()
        style_characteristics = "\n".join(f"• {char}" for char in style["characteristics"])
        style_section = f"""
## Writing Style: {style["description"]}
Embody these stylistic characteristics:
{style_characteristics}
"""

    prompt = f"""Write a creative story based on this description: {story_description}
{mission_section}{style_section}
## Evaluation Rubric
{rubric}

Create an engaging, well-written story that captures the essence of the description while meeting the criteria in the evaluation rubric{" and your creative mission" if use_random_mission else ""}{" in your chosen style" if use_random_style else ""}. 

Write only the story - no analysis or commentary needed."""

    from utils.inference import generate_text
    response = await generate_text(model, prompt, temperature=1)
    return response.strip()


async def generate_story_variant(
    original_story: str,
    original_prompt: str,
    model: str = "gpt-4",
    rubric_file: str = "rubric.txt",
    temperature: float = 1.2,
    use_random_mission: bool = True
) -> str:
    """
    Generate a variant of an existing story while maintaining the core narrative.
    
    Args:
        original_story: The original story to create a variant from
        original_prompt: The original prompt that generated the story
        model: The model to use for generation
        rubric_file: Path to the rubric file
        temperature: Temperature for more creative variations
        use_random_mission: Whether to use a random mission set for creative goals
        
    Returns:
        A new story variant as a string
    """
    
    rubric = load_rubric(rubric_file)
    
    # Get random mission if enabled
    mission_section = ""
    
    if use_random_mission:
        mission = get_random_mission()
        mission_goals = "\n".join(f"• {goal}" for goal in mission["goals"])
        mission_section = f"""

## Creative Mission: {mission["description"]}
Your specific creative goals for this variant:
{mission_goals}
"""

    prompt = f"""You are tasked with creating a creative variant of an existing story. The goal is to maintain the core narrative elements while exploring different approaches, perspectives, or narrative techniques.

## Original Prompt:
{original_prompt}

## Original Story:
{original_story}
{mission_section}

## Evaluation Rubric:
{rubric}

## Your Task:
Create a new variant of this story that:
- Maintains the core premise and key narrative elements
- Explores different stylistic approaches, perspectives, or narrative techniques
- Could be told from a different character's viewpoint
- Might emphasize different themes or emotional beats
- Uses different pacing, structure, or descriptive language
- Still targets the evaluation rubric for quality{" and your creative mission" if use_random_mission else ""}

## Guidelines:
- Keep the fundamental story concept intact
- Feel free to change narrative perspective, tense, or style
- Explore different character dynamics or emotional emphasis
- Vary the pacing, structure, or descriptive detail
- Maintain high quality according to the rubric criteria

Write only the story variant - no analysis or commentary needed."""

    from utils.inference import generate_text
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

    from utils.inference import generate_text
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
    focus_areas: Optional[List[str]] = None,
    model: str = "gpt-4o-mini",
    rubric_file: str = "rubric.txt",
    num_improvement_sets: int = 2
) -> Dict[str, Any]:
    """
    Generate an improved version of previous creative writing pieces.
    
    Args:
        previous_pieces: List of previous writing pieces with their analyses
        story_description: Original story description
        focus_areas: Optional list of specific areas to focus on improving
        model: The model to use for generation
        rubric_file: Path to the rubric file
        num_improvement_sets: Number of improvement sets to sample
        
    Returns:
        Dict with 'improved_piece', 'analysis', and 'improvements' keys
    """
    
    # Load rubric for quality targeting
    rubric = load_rubric(rubric_file)
    
    # Format previous pieces for context
    previous_context = "\n\n".join([
        f"Version {i+1}:\n{p['piece']}"
        for i, p in enumerate(previous_pieces)
    ])
    
    focus_areas_text = ""
    if focus_areas:
        focus_areas_text = f"\n\nSpecific Focus Areas:\n" + "\n".join(f"• {area}" for area in focus_areas)
    
    # Sample multiple improvement sets
    improvement_sets = get_random_improvement_sets(num_improvement_sets)
    improvement_sections = []
    for imp in improvement_sets:
        goals = "\n".join(f"• {goal}" for goal in imp["goals"])
        improvement_sections.append(f"### {imp['description']}\n{goals}")
    improvement_section = "\n\n".join(improvement_sections)

    prompt = f"""You are a master storyteller and literary craftsperson. Your mission is to take an existing story and elevate it to its highest potential.

## Original Story Concept
{story_description}

## Previous Versions
{previous_context}

## Excellence Standards
{rubric}

## Your Creative Missions
{improvement_section}
{focus_areas_text}

## Output Format

IMPROVED_PIECE:
[Your elevated, masterful version of the story]

ANALYSIS:
[Brief analysis of the key improvements and literary techniques employed]

IMPROVEMENTS:
[Specific enhancements made and their impact on the reader experience]

Transform this story into something readers will remember long after they finish reading."""

    from utils.inference import generate_text
    response = await generate_text(model, prompt, temperature=1.1)
    
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
