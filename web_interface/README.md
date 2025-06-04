# Story Preference Testing Web Interface

A web application for human preference testing of evolved story batches to validate the effectiveness of the evolutionary story generation process.

## Features

- **Side-by-side story comparison** from different batches
- **Random story selection** for unbiased testing
- **Preference tracking** with detailed statistics
- **Batch performance analysis** with win/loss percentages
- **Real-time statistics** showing evolution effectiveness
- **Clean, responsive interface** optimized for reading

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure you have story batches generated:
```bash
cd ..
python generate_initial_batch.py
python run_elo_tournament.py
python generate_next_batch.py
```

3. Start the web server:
```bash
python app.py
```

4. Open your browser to: http://localhost:5000

## How to Use

### 1. Home Page
- View available story batches
- See overall statistics
- Select batch pairs to compare

### 2. Story Comparison
- Read stories side-by-side
- Click "I Prefer Story A/B" to record preference
- View current statistics for the batch comparison
- Continue with more comparisons or return home

### 3. Statistics Page
- View detailed win/loss percentages between batches
- See recent preference history
- Download data for further analysis
- Understand how to interpret results

## Expected Results

If the evolutionary process is working correctly, you should see:

- **Later batches > Earlier batches** (e.g., batch2_stories > initial_stories)
- **Variants sometimes > Parents** (evolved stories outperform originals)
- **Consistent improvement** across generations

## Data Storage

- Preferences saved to: `../output/preference_data.json`
- Includes timestamps, story IDs, batch names, and user sessions
- Data persists between sessions
- Can be exported from the statistics page

## Technical Notes

- Built with Flask for simplicity
- Reads story files from `../output/` directory
- Supports any number of story batches
- Mobile-responsive design for tablet/phone testing
- Basic session tracking via User-Agent headers

## File Structure

```
web_interface/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── README.md          # This file
└── templates/
    ├── base.html      # Base template with styling
    ├── index.html     # Home page
    ├── compare.html   # Story comparison page
    └── stats.html     # Statistics page
```