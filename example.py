"""
Example usage of the Ravelry Fiber Analysis tools.
"""

import logging.config
from pathlib import Path

from ravelry_fiber_analysis.api import RavelryClient
from ravelry_fiber_analysis.analysis import (
    FiberAnalyzer,
    PatternAnalyzer,
    ProjectAnalyzer
)
from ravelry_fiber_analysis.config import settings

# Setup logging
logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger(__name__)

def main():
    # Initialize the Ravelry client
    client = RavelryClient(
        client_key=settings.RAVELRY_CLIENT_KEY,
        client_secret=settings.RAVELRY_CLIENT_SECRET,
        oauth_token=settings.RAVELRY_OAUTH_TOKEN,
        oauth_secret=settings.RAVELRY_OAUTH_SECRET,
        cache_dir=settings.CACHE_DIR
    )

    # Search for patterns
    logger.info("Searching for sweater patterns...")
    patterns = client.search_patterns(
        craft="knitting",
        pattern_type="sweater",
        sort="popularity",
        page_size=100
    )

    # Initialize analyzers
    pattern_analyzer = PatternAnalyzer()
    project_analyzer = ProjectAnalyzer()
    fiber_analyzer = FiberAnalyzer()

    # Download projects for each pattern
    logger.info("Downloading project data...")
    all_projects = client.download_pattern_projects(
        patterns,
        checkpoint_file=settings.DATA_DIR / "download_checkpoint.json"
    )

    # Flatten projects list
    projects = [proj for proj_list in all_projects.values() for proj in proj_list]

    # Perform analysis
    logger.info("Analyzing patterns...")
    pattern_analyzer.analyze_patterns(patterns, projects)
    
    logger.info("Analyzing projects...")
    project_analyzer.analyze_projects(projects)
    
    logger.info("Analyzing fiber content...")
    fiber_analyzer.analyze_projects(projects)

    # Export results
    output_base = settings.DATA_DIR / "analysis_results"
    pattern_analyzer.export_analysis(str(output_base))
    project_analyzer.export_analysis(str(output_base))
    fiber_analyzer.export_analysis(str(output_base))

    logger.info("Analysis complete! Results saved to %s", output_base)

if __name__ == "__main__":
    main()