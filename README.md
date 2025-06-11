# AlphaEvolve Writing

You can find the full explanation [here](https://tobysimonds.com/research/2025/06/06/LLM-Self-Rewarding-copy.html)

An evolutionary writing system that uses AI models to generate, evaluate, and evolve creative stories or general writing pieces through iterative competitions.

## Installation

### 1. Install Dependencies
Install the required Python packages:

```bash
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
- `