# Ravelry Fiber Analysis

This project provides tools for analyzing patterns, projects, and fiber content from Ravelry using their API. It includes functionality for downloading data, analyzing trends, and generating insights about knitting patterns, projects, and yarn usage.

## Features

- Object-oriented API client with proper error handling and rate limiting
- Efficient data downloading with caching and checkpointing
- Progress tracking using tqdm
- Comprehensive logging system
- Analysis tools for:
  - Patterns (popularity, difficulty, ratings)
  - Projects (completion times, trends, user activity)
  - Fiber content (common fibers, combinations, correlations)
- Data export to CSV for further analysis

## Setup

1. Create a Python virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with your Ravelry API credentials:
```
RAVELRY_CLIENT_KEY=your_client_key
RAVELRY_CLIENT_SECRET=your_client_secret
RAVELRY_OAUTH_TOKEN=your_oauth_token
RAVELRY_OAUTH_SECRET=your_oauth_secret
```

## Usage

See `example.py` for a complete example of how to use the library. Here's a quick overview:

```python
from ravelry_fiber_analysis.api import RavelryClient
from ravelry_fiber_analysis.analysis import (
    FiberAnalyzer,
    PatternAnalyzer,
    ProjectAnalyzer
)

# Initialize client
client = RavelryClient(
    client_key="your_key",
    client_secret="your_secret",
    oauth_token="your_token",
    oauth_secret="your_secret"
)

# Search for patterns
patterns = client.search_patterns(
    craft="knitting",
    pattern_type="sweater",
    sort="popularity",
    page_size=100
)

# Download and analyze projects
projects = client.download_pattern_projects(patterns)

# Analyze the data
analyzer = FiberAnalyzer()
analyzer.analyze_projects(projects)
analyzer.export_analysis("output/fiber_analysis")
```

## Project Structure

- `api/`: Contains the Ravelry API client and data models
- `analysis/`: Analysis tools for patterns, projects, and fibers
- `config/`: Configuration and settings management
- `data/`: Data storage directory
- `logs/`: Log files directory

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.