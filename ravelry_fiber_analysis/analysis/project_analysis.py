from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import pandas as pd
from tqdm import tqdm

from ..api.models import Project

logger = logging.getLogger(__name__)

class ProjectAnalyzer:
    """Analyzes projects and their metadata."""

    def __init__(self):
        self.completion_times = []
        self.status_counts = defaultdict(int)
        self.monthly_starts = defaultdict(int)
        self.user_projects = defaultdict(list)
        self.project_tags = defaultdict(list)

    def analyze_projects(self, projects: List[Project]) -> None:
        """Analyze various aspects of projects."""
        logger.info(f"Analyzing {len(projects)} projects")

        for project in tqdm(projects, desc="Analyzing projects"):
            # Status counts
            self.status_counts[project.status] += 1
            
            # Track completion times
            if project.started and project.completed:
                duration = project.completed - project.started
                if duration > timedelta(0):  # Only count positive durations
                    self.completion_times.append(duration.days)

            # Track monthly starts
            if project.started:
                month_key = project.started.strftime('%Y-%m')
                self.monthly_starts[month_key] += 1

            # Track user projects
            self.user_projects[project.username].append(project)

            # Track tags
            if project.tags:
                self.project_tags[project.id] = project.tags

    def get_completion_time_stats(self) -> Dict:
        """Get statistics about project completion times."""
        if not self.completion_times:
            return {}

        times_df = pd.Series(self.completion_times)
        return {
            'mean_days': times_df.mean(),
            'median_days': times_df.median(),
            'std_days': times_df.std(),
            'min_days': times_df.min(),
            'max_days': times_df.max(),
            'quartiles': times_df.quantile([0.25, 0.5, 0.75]).to_dict()
        }

    def get_status_distribution(self) -> Dict[str, int]:
        """Get distribution of project statuses."""
        return dict(self.status_counts)

    def get_monthly_trend(self, months: int = 12) -> Dict[str, int]:
        """Get trend of project starts over recent months."""
        sorted_months = sorted(self.monthly_starts.items(), reverse=True)
        return dict(sorted_months[:months])

    def get_active_users(self, n: int = 10) -> List[Tuple[str, int]]:
        """Get most active users based on project count."""
        user_counts = [(user, len(projects)) 
                      for user, projects in self.user_projects.items()]
        return sorted(user_counts, key=lambda x: x[1], reverse=True)[:n]

    def get_common_tags(self, n: int = 20) -> List[Tuple[str, int]]:
        """Get most common project tags."""
        tag_counts = defaultdict(int)
        for tags in self.project_tags.values():
            for tag in tags:
                tag_counts[tag] += 1
        return sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:n]

    def get_tag_correlations(self) -> pd.DataFrame:
        """Get correlations between commonly used tags."""
        # Create tag presence matrix
        common_tags = [tag for tag, _ in self.get_common_tags(20)]
        tag_matrix = pd.DataFrame(index=self.project_tags.keys(), 
                                columns=common_tags, 
                                data=0)
        
        for project_id, tags in self.project_tags.items():
            for tag in tags:
                if tag in common_tags:
                    tag_matrix.loc[project_id, tag] = 1
                    
        return tag_matrix.corr()

    def export_analysis(self, output_path: str) -> None:
        """Export analysis results to files."""
        # Completion time stats
        completion_stats = pd.DataFrame([self.get_completion_time_stats()])
        completion_stats.to_csv(f"{output_path}_completion_stats.csv")

        # Status distribution
        status_df = pd.DataFrame([self.get_status_distribution()])
        status_df.to_csv(f"{output_path}_status_distribution.csv")

        # Monthly trends
        trends_df = pd.DataFrame([self.get_monthly_trend()])
        trends_df.to_csv(f"{output_path}_monthly_trends.csv")

        # Active users
        users_df = pd.DataFrame(self.get_active_users(), 
                              columns=['Username', 'Projects'])
        users_df.to_csv(f"{output_path}_active_users.csv")

        # Tags
        tags_df = pd.DataFrame(self.get_common_tags(), 
                             columns=['Tag', 'Count'])
        tags_df.to_csv(f"{output_path}_common_tags.csv")

        # Tag correlations
        corr_df = self.get_tag_correlations()
        corr_df.to_csv(f"{output_path}_tag_correlations.csv")