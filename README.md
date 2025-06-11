# AlphaEvolve Writing

An evolutionary writing system that uses AI models to generate, evaluate, and evolve creative stories or general writing pieces through iterative competitions.

## Installation

### 1. Install Dependencies
Install the required Python packages:

```bash
pip install -r requirements.txt
```

For the web interface, install additional dependencies:
```bash
cd web_interface
pip install -r requirements.txt
```

### 2. API Keys Setup
Set up your API keys in your environment. The system supports multiple AI providers:

```bash
export OPENAI_API_KEY="your-openai-key"        # For GPT models (o1, o3, o4, gpt-4, gpt-3.5-turbo, etc.)
export ANTHROPIC_API_KEY="your-anthropic-key"  # For Claude models (claude-3, claude-2, etc.)
export DEEPINFRA_API_KEY="your-deepinfra-key"  # For Llama models (meta-llama/*, Meta-Llama/*, Qwen/*)
export DEEPSEEK_API_KEY="your-deepseek-key"    # For DeepSeek models (deepseek-*)
```

You only need to set the API keys for the models you plan to use.

### 3. Configure Your Writing Settings
Edit these key files to customize your story generation:

- **`prompt.txt`** - Define your story prompt/theme
- **`rubric.txt`** - Set judging criteria for story evaluation
- **`config.json`** - Configure all system settings:
  - Models to use for generation and judging
  - Number of stories per batch
  - Tournament parameters
  - Evolution settings

## How It Works

The system follows a three-stage evolution cycle:

1. **Generate Initial Batch** - Create multiple stories from a prompt
2. **Run ELO Tournament** - Stories compete in pairwise comparisons judged by AI
3. **Generate Next Batch** - Top-performing stories spawn improved variants

This process repeats for multiple iterations, evolving better stories over time.

## Quick Start

### Automated Evolution (Recommended)

Run the complete evolution pipeline:

```bash
python evolve.py 5                    # Run 5 evolution iterations
python evolve.py 3 --fresh            # Fresh start with 3 iterations
python evolve.py 5 --general          # Use general writing mode instead of creative stories
python evolve.py 3 --fresh --general  # Fresh start with general writing mode
```

#### Writing Modes

- **Creative Writing Mode (default)**: Focuses on storytelling, character development, and narrative techniques
- **General Writing Mode (`--general`)**: Focuses on academic papers, essays, reports, and professional writing

### Manual Step-by-Step

1. **Generate initial stories:**
   ```bash
   python generate_initial_batch.py
   ```

2. **Run ELO tournament:**
   ```bash
   python run_elo_tournament.py
   ```

3. **Generate next batch:**
   ```bash
   python generate_next_batch.py
   ```

4. **Repeat steps 2-3** for additional evolution cycles

## Web Interface for Story Rankings

The web interface allows you to manually test and validate the AI's story rankings through human preference testing:

```bash
cd web_interface
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000 to access the interface.

### Features:
- **Compare Stories Side-by-Side**: Read stories from different generations and choose your preference
- **View Rankings**: See ELO rankings and statistics for all story batches
- **Track Evolution Progress**: Validate that later generations actually improve over earlier ones
- **Export Data**: Download preference data for analysis

This interface is crucial for verifying that your evolutionary process is working correctly - you should see later batches consistently outperforming earlier ones.

## Configuration

### Basic Configuration

All settings are controlled via `config.json`:

- **batch_generation**: Number of stories, model, initial ELO rating
- **elo_ranking**: Tournament settings, judge model, K-factor
- **next_batch_generation**: How many top stories to evolve, variants per story
- **evolution_pipeline**: Maximum iterations, automation settings

### Advanced Configuration

#### Customizing Writing Styles and Approaches

The system uses different generation strategies depending on the mode:

##### Creative Writing Mode (`lib/generate_response.py`)

**Mission Sets** - Define creative goals and approaches:
- `emotional_depth`: Focus on psychological depth and character emotions
- `atmospheric_immersion`: Emphasize setting and sensory details
- `narrative_innovation`: Experiment with unique storytelling techniques

**Author Styles** - Simulate different writing voices:
- Various author styles with specific characteristics and techniques
- Randomly selected for each story generation to create diversity

**Improvement Sets** - Define how stories evolve:
- `character_development`: Enhance character depth and relationships
- `plot_structure`: Improve narrative flow and pacing
- `dialogue_enhancement`: Strengthen character voices and conversations

##### General Writing Mode (`lib/generate_response_general.py`)

**Writing Approaches** - Different analytical and research methods:
- `analytical_depth`: Focus on logical analysis and critical thinking
- `research_synthesis`: Emphasize thorough research integration
- `structural_innovation`: Experiment with organizational techniques

**Writing Styles** - Professional writing approaches:
- `academic_precision`: Scholarly writing with strong foundation
- `journalistic_clarity`: Clear, engaging informational style
- `technical_expertise`: Complex topics explained effectively
- `policy_analysis`: Systematic policy examination
- `business_professional`: Action-oriented business writing

**Improvement Sets** - How general writing evolves:
- `argument_strength`: Strengthen logic and evidence
- `research_integration`: Better source integration
- `clarity_improvement`: Enhance readability and structure

#### Customizing Generation Prompts

To modify how the AI generates content, edit the prompt templates in:

1. **Creative Writing** (`lib/generate_response.py`):
   - Edit the `generate_initial_piece()` function around line 370
   - Modify mission/style selection logic in `get_random_mission()` and `get_random_author_style()`
   - Customize improvement prompts in `generate_story_variant()` around line 430

2. **General Writing** (`lib/generate_response_general.py`):
   - Edit the `generate_initial_piece()` function around line 369
   - Modify approach/style selection in `get_random_approach()` and `get_random_writing_style()`
   - Customize improvement prompts in `generate_piece_variant()` around line 406

#### Adding New Writing Styles

1. **For Creative Writing**: Add new entries to `MISSION_SETS`, `AUTHOR_STYLES`, or `IMPROVEMENT_SETS` arrays
2. **For General Writing**: Add new entries to `WRITING_APPROACHES`, `WRITING_STYLES`, or `IMPROVEMENT_SETS` arrays

Each entry should include:
- `name`: Unique identifier
- `description`: Brief explanation
- `goals` or `characteristics`: List of specific attributes

#### Example: Adding a New Creative Writing Style

```python
{
    "name": "horror_atmospheric",
    "description": "Dark, suspenseful horror writing",
    "characteristics": [
        "Build tension through pacing and atmosphere",
        "Use sensory details to create unease",
        "Develop psychological horror elements",
        "Create compelling supernatural or psychological threats"
    ]
}
```

## Output

- `initial_stories.json` - First generation of stories
- `batch2_stories.json`, `batch3_stories.json`, etc. - Evolved generations
- `elo_rankings.json` - Current story rankings
- `match_history.json` - Tournament match results
