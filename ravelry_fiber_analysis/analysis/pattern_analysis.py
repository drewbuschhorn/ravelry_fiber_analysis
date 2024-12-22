from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import logging
import pandas as pd
import numpy as np
from tqdm import tqdm

from ..api.models import Pattern, Project

logger = logging.getLogger(__name__)

class PatternAnalyzer:
    """Analyzes patterns and their relationships with projects."""

    def __init__(self):
        self.pattern_stats = {}
        self.pattern_tags = defaultdict(list)
        self.pattern_popularity = defaultdict(int)

    def analyze_patterns(self, patterns: List[Pattern], projects: Optional[List[Project]] = None) -> None:
        """Analyze patterns and their associated projects."""
        logger.info(f"Analyzing {len(patterns)} patterns")

        for pattern in tqdm(patterns, desc="Analyzing patterns"):
            self.pattern_stats[pattern.id] = {
                'name': pattern.name,
                'favorites': pattern.favorites_count or 0,
                'difficulty': pattern.difficulty_average or 0,
                'rating': pattern.rating_average or 0,
                'projects_count': pattern.projects_count or 0
            }

        if projects:
            logger.info(f"Analyzing {len(projects)} projects for pattern relationships")
            for project in tqdm(projects, desc="Processing projects"):
                if project.pattern_id:
                    self.pattern_popularity[project.pattern_id] += 1
                    if project.tags:
                        self.pattern_tags[project.pattern_id].extend(project.tags)

    def get_popular_patterns(self, n: int = 10) -> List[Dict]:
        """Get the most popular patterns based on favorites and projects."""
        patterns = []
        for pattern_id, stats in self.pattern_stats.items():
            score = (stats['favorites'] * 0.7 + 
                    stats['projects_count'] * 0.3)
            patterns.append({
                'pattern_id': pattern_id,
                'name': stats['name'],
                'popularity_score': score,
                'favorites': stats['favorites'],
                'projects': stats['projects_count']
            })
        
        return sorted(patterns, key=lambda x: x['popularity_score'], reverse=True)[:n]

    def get_pattern_difficulty_distribution(self) -> pd.DataFrame:
        """Get distribution of pattern difficulties."""
        difficulties = [stats['difficulty'] for stats in self.pattern_stats.values()]
        return pd.DataFrame({
            'difficulty': difficulties
        }).describe()

    def get_common_pattern_tags(self, n: int = 20) -> List[Tuple[str, int]]:
        """Get most common tags associated with patterns."""
        tag_counts = defaultdict(int)
        for tags in self.pattern_tags.values():
            for tag in tags:
                tag_counts[tag] += 1
                
        return sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:n]

    def get_pattern_correlations(self) -> pd.DataFrame:
        """Get correlations between pattern metrics."""
        df = pd.DataFrame([{
            'difficulty': stats['difficulty'],
            'rating': stats['rating'],
            'favorites': stats['favorites'],
            'projects': stats['projects_count']
        } for stats in self.pattern_stats.values()])
        
        return df.corr()

    def export_analysis(self, output_path: str) -> None:
        """Export analysis results to files."""
        # Popular patterns
        popular_df = pd.DataFrame(self.get_popular_patterns())
        if not popular_df.empty:
            popular_df.to_csv(f"{output_path}_popular_patterns.csv")

        # Difficulty distribution
        diff_dist = self.get_pattern_difficulty_distribution()
        diff_dist.to_csv(f"{output_path}_difficulty_distribution.csv")

        # Tags
        tags_df = pd.DataFrame(self.get_common_pattern_tags(), 
                             columns=['Tag', 'Count'])
        tags_df.to_csv(f"{output_path}_common_tags.csv")

        # Correlations
        corr_df = self.get_pattern_correlations()
        corr_df.to_csv(f"{output_path}_metric_correlations.csv")