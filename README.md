# AlphaEvolve Writing

An evolutionary creative writing system that uses AI models to generate, evaluate, and evolve stories through iterative competitions.

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

## Configuration

All settings are controlled via `config.json`:

- **batch_generation**: Number of stories, model, initial ELO rating
- **elo_ranking**: Tournament settings, judge model, K-factor
- **next_batch_generation**: How many top stories to evolve, variants per story
- **evolution_pipeline**: Maximum iterations, automation settings

## Files

- `prompt.txt` - The story prompt/theme
- `rubric.txt` - Judging criteria for story evaluation
- `output/` - Generated stories, rankings, and match history

## Web Interface

View rankings and compare stories:

```bash
cd web_interface
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000 to view the interface.

## Output

- `initial_stories.json` - First generation of stories
- `batch2_stories.json`, `batch3_stories.json`, etc. - Evolved generations
- `elo_rankings.json` - Current story rankings
- `match_history.json` - Tournament match results
