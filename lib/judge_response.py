"""
Rank two model responses for creative writing based on a rubric.

This module compares two model responses and determines which one is better
based on a hardcoded evaluation rubric.
"""

from typing import Dict, Any
from dataclasses import dataclass


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
    rubric_file: str = "rubric.txt",
    original_prompt: str = None
) -> ModelComparison:
    """
    Compare two model responses and determine which is better based on the rubric.
    
    Args:
        model_1_response: First model's creative writing response
        model_2_response: Second model's creative writing response
        judge_model: The model to use for evaluation
        rubric_file: Path to the rubric file
        original_prompt: The original prompt that generated these responses (optional)
        
    Returns:
        ModelComparison object with winner and reasoning
    """
    
    rubric = load_rubric(rubric_file)
    
    prompt_section = ""
    if original_prompt:
        prompt_section = f"""
## Original Writing Prompt:
{original_prompt}

"""

    prompt = f"""You are an expert creative writing judge. You must thoroughly analyze both responses before making any decision. Do NOT jump to conclusions or pick a default choice.

{prompt_section}
## Evaluation Rubric
{rubric}

## Model 1 Response:
{model_1_response}

## Model 2 Response:
{model_2_response}

## Required Analysis Process:
You MUST work through each step systematically. Think carefully about each response before deciding.

STEP 1 - ANALYZE MODEL 1:
First, evaluate Model 1's response against each rubric criterion. What are its specific strengths and weaknesses?

STEP 2 - ANALYZE MODEL 2: 
Next, evaluate Model 2's response against each rubric criterion. What are its specific strengths and weaknesses?

STEP 3 - DIRECT COMPARISON:
Now compare the two responses side by side. For each rubric criterion, which response performs better and why? Be specific about differences.

STEP 4 - OVERALL ASSESSMENT:
Based on your analysis, which response is better overall? Consider all criteria together, not just one aspect.

## Output Format:
You MUST format your response exactly as follows. Complete ALL steps before declaring a winner:

STEP 1 - ANALYZE MODEL 1:
[Your analysis of Model 1's strengths and weaknesses against the rubric]

STEP 2 - ANALYZE MODEL 2:
[Your analysis of Model 2's strengths and weaknesses against the rubric]

STEP 3 - DIRECT COMPARISON:
[Side-by-side comparison showing which response is better for each criterion]

STEP 4 - OVERALL ASSESSMENT:
[Your final judgment with clear reasoning]

WINNER: model_1 or model_2
REASONING: [Brief summary of why the winning response is better overall]

CRITICAL REMINDERS:
- You MUST analyze both responses thoroughly before deciding
- Do not default to model_1 - actually compare the content
- Use exactly "WINNER: model_1" or "WINNER: model_2" 
- Base your decision on the rubric criteria, not response order
- If responses are very close, pick the one with better overall execution

Begin your systematic analysis now:"""

    from utils.inference import generate_text
    response = await generate_text(judge_model, prompt)
    
    # Parse the response with multiple fallback methods
    winner = None
    reasoning = ""
    
    def parse_response_robust(response_text: str):
        """Robust parser that handles multiple response formats."""
        import re
        
        # Method 1: Look for WINNER: pattern (case insensitive, handles markdown formatting)
        winner_patterns = [
            r'(?:^|\*\*|\*|#)*\s*WINNER\s*:\s*(model_[12])\s*(?:\*\*|\*|#)*',
            r'(?:^|\*\*|\*|#)*\s*Winner\s*:\s*(model_[12])\s*(?:\*\*|\*|#)*',
            r'(?:^|\*\*|\*|#)*\s*THE\s+WINNER\s+IS\s*:\s*(model_[12])\s*(?:\*\*|\*|#)*',
        ]
        
        for pattern in winner_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).lower()
        
        # Method 2: Look for explicit declarations
        decision_patterns = [
            r'(?:I\s+choose|I\s+select|My\s+choice\s+is|The\s+better\s+response\s+is)\s+(?:model\s+)?([12])',
            r'(?:Response|Model)\s+([12])\s+(?:is\s+better|wins|is\s+superior)',
            r'(?:model_)?([12])\s+(?:is\s+the\s+winner|wins\s+this\s+match)',
        ]
        
        for pattern in decision_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                return f"model_{match.group(1)}"
        
        # Method 3: Look for model_1 or model_2 mentions near decision words
        if re.search(r'model_1.*(?:better|superior|wins|winner)', response_text, re.IGNORECASE):
            return "model_1"
        elif re.search(r'model_2.*(?:better|superior|wins|winner)', response_text, re.IGNORECASE):
            return "model_2"
        elif re.search(r'(?:better|superior|wins|winner).*model_1', response_text, re.IGNORECASE):
            return "model_1"
        elif re.search(r'(?:better|superior|wins|winner).*model_2', response_text, re.IGNORECASE):
            return "model_2"
        
        # Method 4: Count positive/negative mentions (last resort)
        model_1_positive = len(re.findall(r'model_1.*(?:better|good|strong|superior|excellent|wins|winner)', response_text, re.IGNORECASE))
        model_2_positive = len(re.findall(r'model_2.*(?:better|good|strong|superior|excellent|wins|winner)', response_text, re.IGNORECASE))
        
        if model_1_positive > model_2_positive:
            return "model_1"
        elif model_2_positive > model_1_positive:
            return "model_2"
        
        # Method 5: Last resort - look for any mention of model_1 or model_2 near the end
        # (assumes the final judgment mentions the winning model)
        lines = response_text.split('\n')
        for line in reversed(lines[-3:]):  # Check last 3 lines
            if 'model_1' in line.lower():
                return "model_1"
            elif 'model_2' in line.lower():
                return "model_2"
        
        # Method 6: Absolute last resort - find any occurrence and guess
        if 'model_1' in response_text.lower():
            return "model_1"
        elif 'model_2' in response_text.lower():
            return "model_2"
        
        return None
    
    def extract_reasoning(response_text: str) -> str:
        """Extract reasoning from various formats, including structured analysis."""
        import re
        
        # Method 1: Extract full structured analysis (preferred for new format)
        structured_pattern = r'(STEP 1.*?)(?=WINNER:|$)'
        match = re.search(structured_pattern, response_text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Method 2: Look for REASONING: pattern
        reasoning_patterns = [
            r'(?:^|\*\*|\*|#)*\s*REASONING\s*:\s*(.*?)(?=\n\n|\n\*|$)',
            r'(?:^|\*\*|\*|#)*\s*Reasoning\s*:\s*(.*?)(?=\n\n|\n\*|$)',
            r'(?:^|\*\*|\*|#)*\s*EXPLANATION\s*:\s*(.*?)(?=\n\n|\n\*|$)',
        ]
        
        for pattern in reasoning_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # Method 3: Take everything after winner declaration
        lines = response_text.split('\n')
        found_winner = False
        reasoning_lines = []
        
        for line in lines:
            if found_winner:
                reasoning_lines.append(line)
            elif any(word in line.lower() for word in ['winner:', 'winner is', 'choose', 'better']):
                found_winner = True
                # Include rest of this line if it has content after the winner
                remaining = re.sub(r'.*(?:winner|choose|better).*?:', '', line, flags=re.IGNORECASE).strip()
                if remaining:
                    reasoning_lines.append(remaining)
        
        if reasoning_lines:
            return '\n'.join(reasoning_lines).strip()
        
        # Method 4: Return the full response as reasoning if no clear structure
        return response_text.strip()
    
    # Try robust parsing
    winner = parse_response_robust(response)
    reasoning = extract_reasoning(response)
    
    # Check if the judge actually followed the structured analysis format
    if winner and winner in ['model_1', 'model_2']:
        # Validate that some actual analysis was done, not just a quick decision
        has_analysis = any(step in response.lower() for step in ['step 1', 'step 2', 'step 3', 'step 4'])
        
        # If no structured analysis was provided, note this in the reasoning
        if not has_analysis and len(response) < 200:
            reasoning = f"[WARNING: Judge provided minimal analysis] {reasoning}"
    
    if not winner or winner not in ['model_1', 'model_2']:
        raise ValueError(f"Failed to parse winner from response. Got: {response[:500]}{'...' if len(response) > 500 else ''}")
    
    return ModelComparison(
        winner=winner,
        reasoning=reasoning
    )
