from collections import defaultdict
from typing import Dict, List, Tuple
import logging
import pandas as pd
from tqdm import tqdm

from ..api.models import Project, Yarn, FiberContent

logger = logging.getLogger(__name__)

class FiberAnalyzer:
    """Analyzes fiber content across projects and patterns."""

    def __init__(self):
        self.fiber_counts = defaultdict(int)
        self.fiber_combinations = defaultdict(int)
        self.fiber_by_pattern = defaultdict(lambda: defaultdict(int))

    def analyze_projects(self, projects: List[Project]) -> None:
        """Analyze fiber content across a list of projects."""
        logger.info(f"Analyzing fiber content for {len(projects)} projects")
        
        for project in tqdm(projects, desc="Analyzing fiber content"):
            for yarn in project.yarns:
                if not yarn.fiber_content:
                    continue
                    
                # Count individual fibers
                fibers = []
                for fiber in yarn.fiber_content:
                    self.fiber_counts[fiber.fiber_type] += 1
                    fibers.append(fiber.fiber_type)
                    
                    # Track fibers by pattern
                    if project.pattern_id:
                        self.fiber_by_pattern[project.pattern_id][fiber.fiber_type] += 1
                
                # Track fiber combinations
                if len(fibers) > 1:
                    combo = tuple(sorted(fibers))
                    self.fiber_combinations[combo] += 1

    def get_top_fibers(self, n: int = 10) -> List[Tuple[str, int]]:
        """Get the most commonly used fibers."""
        return sorted(self.fiber_counts.items(), key=lambda x: x[1], reverse=True)[:n]

    def get_top_combinations(self, n: int = 10) -> List[Tuple[Tuple[str, ...], int]]:
        """Get the most common fiber combinations."""
        return sorted(self.fiber_combinations.items(), key=lambda x: x[1], reverse=True)[:n]

    def get_fiber_pattern_correlation(self) -> pd.DataFrame:
        """Get correlation between patterns and fiber types."""
        df = pd.DataFrame.from_dict(self.fiber_by_pattern, orient='index')
        df = df.fillna(0)
        return df.corr()

    def export_analysis(self, output_path: str) -> None:
        """Export analysis results to files."""
        # Create DataFrames
        fiber_df = pd.DataFrame(self.get_top_fibers(), columns=['Fiber', 'Count'])
        combo_df = pd.DataFrame([
            {'Combination': ' + '.join(combo), 'Count': count}
            for combo, count in self.get_top_combinations()
        ])
        corr_df = self.get_fiber_pattern_correlation()

        # Save to files
        fiber_df.to_csv(f"{output_path}_fibers.csv")
        combo_df.to_csv(f"{output_path}_combinations.csv")
        corr_df.to_csv(f"{output_path}_correlations.csv")