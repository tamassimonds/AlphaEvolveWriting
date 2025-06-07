# AlphaEvolve Writing

An evolutionary creative writing system that uses AI models to generate, evaluate, and evolve stories through iterative competitions.

## Setup

### 1. API Keys
First, set up your API keys in your environment. Check `utils/inference.py` to see supported models and their required keys:

```bash
export OPENAI_API_KEY="your-openai-key"        # For GPT models
export ANTHROPIC_API_KEY="your-anthropic-key"  # For Claude models  
export DEEPINFRA_API_KEY="your-deepinfra-key"  # For Llama models
export DEEPSEEK_API_KEY="your-deepseek-key"    # For DeepSeek models
```

### 2. Configure Your Story Settings
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
python evolve.py 5          # Run 5 evolution iterations
python evolve.py 3 --fresh  # Fresh start with 3 iterations
```

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

All settings are controlled via `config.json`:

- **batch_generation**: Number of stories, model, initial ELO rating
- **elo_ranking**: Tournament settings, judge model, K-factor
- **next_batch_generation**: How many top stories to evolve, variants per story
- **evolution_pipeline**: Maximum iterations, automation settings

## Output

- `initial_stories.json` - First generation of stories
- `batch2_stories.json`, `batch3_stories.json`, etc. - Evolved generations
- `elo_rankings.json` - Current story rankings
- `match_history.json` - Tournament match results
