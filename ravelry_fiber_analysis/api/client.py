import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any, Generator, Union
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin
from contextlib import contextmanager

import attr
import requests
import requests_cache
from requests_oauthlib import OAuth1Session
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from tqdm import tqdm

from .models import Pattern, Project, Yarn
from ..config import settings

logger = logging.getLogger(__name__)

@attr.s(auto_attribs=True)
class RavelryClient:
    """Main client for interacting with the Ravelry API with advanced features.
    
    Features:
    - Automatic pagination
    - Request caching with configurable TTL
    - Rate limiting
    - Retry logic with exponential backoff
    - Progress tracking
    - Checkpointing for long operations
    """
    
    client_key: str
    client_secret: str
    oauth_token: str
    oauth_secret: str
    cache_dir: Path = attr.ib(factory=lambda: Path("data"))
    cache_ttl: int = attr.ib(default=3600)  # Cache TTL in seconds
    rate_limit_calls: int = attr.ib(default=100)  # Calls per minute
    rate_limit_period: int = attr.ib(default=60)  # Period in seconds
    _session: Optional[OAuth1Session] = attr.ib(default=None, init=False)
    _last_calls: List[float] = attr.ib(factory=list, init=False)

    # API Endpoints
    RAVELRY_API = 'https://api.ravelry.com'
    PATTERNS_SEARCH = '/patterns/search.json'
    PROJECTS_SEARCH = '/projects/search.json'
    PROJECT_DETAIL = '/projects/{username}/{project_id}.json'
    PATTERN_DETAIL = '/patterns/{pattern_id}.json'
    YARN_DETAIL = '/yarns/{yarn_id}.json'
    
    def __attrs_post_init__(self):
        """Initialize the client after creation."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._setup_cache()
        self._setup_session()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Context manager exit with cleanup."""
        if self._session:
            self._session.close()

    def _setup_cache(self):
        """Setup request caching with TTL."""
        cache_path = self.cache_dir / 'ravelry_cache'
        requests_cache.install_cache(
            str(cache_path),
            backend='sqlite',
            expire_after=timedelta(seconds=self.cache_ttl)
        )

    def _setup_session(self):
        """Initialize OAuth session with custom user agent."""
        self._session = OAuth1Session(
            self.client_key,
            client_secret=self.client_secret,
            resource_owner_key=self.oauth_token,
            resource_owner_secret=self.oauth_secret
        )
        self._session.headers.update({
            'User-Agent': 'RavelryFiberAnalysis/1.0',
            'Accept': 'application/json',
        })

    def _check_rate_limit(self):
        """Implement rate limiting."""
        now = time.time()
        # Remove calls outside the window
        self._last_calls = [t for t in self._last_calls 
                           if now - t < self.rate_limit_period]
        
        if len(self._last_calls) >= self.rate_limit_calls:
            # Wait until we can make another call
            sleep_time = self.rate_limit_period - (now - self._last_calls[0])
            if sleep_time > 0:
                logger.debug(f"Rate limit reached, waiting {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
            self._last_calls = self._last_calls[1:]
        
        self._last_calls.append(now)

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(
            (requests.exceptions.RequestException, json.JSONDecodeError)
        )
    )
    def _make_request(
        self, 
        endpoint: str, 
        method: str = 'GET',
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict:
        """Make a request to the Ravelry API with retries and error handling.
        
        Args:
            endpoint: API endpoint to call
            method: HTTP method to use
            params: Query parameters
            json_data: JSON data for POST/PUT requests
            headers: Additional headers
            
        Returns:
            JSON response from the API
            
        Raises:
            requests.exceptions.RequestException: On request failure
            json.JSONDecodeError: On invalid JSON response
        """
        url = urljoin(self.RAVELRY_API, endpoint)
        self._check_rate_limit()
        
        try:
            response = self._session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making {method} request to {url}: {str(e)}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from {url}: {str(e)}")
            raise

    def paginate(
        self,
        endpoint: str,
        params: Dict[str, Any],
        data_key: str,
        model_class: Any,
        page_size: int = 100,
        max_pages: Optional[int] = None,
        show_progress: bool = True
    ) -> Generator[Any, None, None]:
        """Generic pagination helper for Ravelry API endpoints.
        
        Args:
            endpoint: API endpoint to call
            params: Base query parameters
            data_key: Key in response containing items
            model_class: Class to instantiate for each item
            page_size: Number of items per page
            max_pages: Maximum number of pages to fetch (None for all)
            show_progress: Whether to show progress bar
            
        Yields:
            Instantiated model objects
        """
        params = params.copy()
        params['page_size'] = page_size
        page = 1
        total_pages = None
        
        pbar = None
        try:
            while max_pages is None or page <= max_pages:
                params['page'] = page
                response = self._make_request(endpoint, params=params)
                
                if total_pages is None:
                    total_pages = response.get('paginator', {}).get('page_count', 1)
                    if max_pages:
                        total_pages = min(total_pages, max_pages)
                    if show_progress:
                        pbar = tqdm(total=total_pages, desc=f"Fetching {data_key}")

                for item in response.get(data_key, []):
                    yield model_class.from_dict(item)

                if page >= total_pages:
                    break

                page += 1
                if pbar:
                    pbar.update(1)

        finally:
            if pbar:
                pbar.close()

    def search_patterns(
        self,
        craft: str = "knitting",
        pattern_type: str = "sweater",
        sort: str = "popularity",
        page_size: int = 100,
        max_pages: Optional[int] = None,
        show_progress: bool = True,
        **extra_params
    ) -> Generator[Pattern, None, None]:
        """Search for patterns with given criteria.
        
        Args:
            craft: Type of craft (knitting, crochet, etc.)
            pattern_type: Type of pattern
            sort: Sort order
            page_size: Items per page
            max_pages: Maximum pages to fetch (None for all)
            show_progress: Whether to show progress bar
            **extra_params: Additional search parameters
            
        Yields:
            Pattern objects matching the criteria
        """
        params = {
            "craft": craft,
            "pc": pattern_type,
            "sort": sort,
            **extra_params
        }

        logger.info(f"Searching for patterns with params: {params}")
        return self.paginate(
            self.PATTERNS_SEARCH,
            params,
            'patterns',
            Pattern,
            page_size,
            max_pages,
            show_progress
        )

    def get_pattern(self, pattern_id: Union[int, str]) -> Pattern:
        """Get detailed information about a specific pattern."""
        endpoint = self.PATTERN_DETAIL.format(pattern_id=pattern_id)
        response = self._make_request(endpoint)
        return Pattern.from_dict(response["pattern"])

    def get_project(self, username: str, project_id: Union[int, str]) -> Project:
        """Get detailed information about a specific project."""
        endpoint = self.PROJECT_DETAIL.format(username=username, project_id=project_id)
        response = self._make_request(endpoint)
        return Project.from_dict(response["project"])

    def get_yarn(self, yarn_id: Union[int, str]) -> Yarn:
        """Get detailed information about a specific yarn."""
        endpoint = self.YARN_DETAIL.format(yarn_id=yarn_id)
        response = self._make_request(endpoint)
        return Yarn.from_dict(response["yarn"])

    def search_projects(
        self,
        pattern_permalink: Optional[str] = None,
        craft: str = "knitting",
        status: str = "finished",
        sort: str = "popularity",
        page_size: int = 100,
        max_pages: Optional[int] = None,
        show_progress: bool = True,
        **extra_params
    ) -> Generator[Project, None, None]:
        """Search for projects with given criteria.
        
        Args:
            pattern_permalink: Filter by pattern
            craft: Type of craft
            status: Project status
            sort: Sort order
            page_size: Items per page
            max_pages: Maximum pages to fetch (None for all)
            show_progress: Whether to show progress bar
            **extra_params: Additional search parameters
            
        Yields:
            Project objects matching the criteria
        """
        params = {
            "craft": craft,
            "status": status,
            "sort": sort,
            **extra_params
        }
        if pattern_permalink:
            params["pattern-link"] = pattern_permalink

        logger.info(f"Searching for projects with params: {params}")
        return self.paginate(
            self.PROJECTS_SEARCH,
            params,
            'projects',
            Project,
            page_size,
            max_pages,
            show_progress
        )

    def download_pattern_projects(
        self,
        patterns: List[Pattern],
        checkpoint_file: Optional[Path] = None,
        max_projects_per_pattern: Optional[int] = None,
        show_progress: bool = True
    ) -> Dict[str, List[Project]]:
        """Download all projects for a list of patterns with progress tracking and checkpointing.
        
        Args:
            patterns: List of patterns to get projects for
            checkpoint_file: File to store progress (optional)
            max_projects_per_pattern: Maximum projects to fetch per pattern
            show_progress: Whether to show progress bars
            
        Returns:
            Dictionary mapping pattern permalinks to lists of projects
            
        The function implements smart checkpointing and will resume from the last
        successful pattern if interrupted.
        """
        # Load checkpoint if exists
        checkpoint_data = self._load_checkpoint(checkpoint_file) if checkpoint_file else {
            "last_pattern_idx": -1,
            "results": {}
        }
        
        start_idx = checkpoint_data.get("last_pattern_idx", -1) + 1
        results = checkpoint_data.get("results", {})
        
        # Skip already processed patterns
        remaining_patterns = patterns[start_idx:]
        if not remaining_patterns:
            logger.info("No remaining patterns to process")
            return results

        # Setup progress tracking
        if show_progress:
            pattern_pbar = tqdm(
                remaining_patterns,
                initial=start_idx,
                total=len(patterns),
                desc="Processing patterns"
            )
        else:
            pattern_pbar = remaining_patterns

        try:
            for idx, pattern in enumerate(pattern_pbar, start=start_idx):
                logger.info(f"Processing pattern: {pattern.name} ({pattern.permalink})")
                
                try:
                    # Calculate max pages if max_projects_per_pattern is set
                    max_pages = None
                    if max_projects_per_pattern:
                        max_pages = -(-max_projects_per_pattern // 100)  # Ceiling division
                    
                    # Fetch projects with pagination
                    projects = list(self.search_projects(
                        pattern_permalink=pattern.permalink,
                        max_pages=max_pages,
                        show_progress=show_progress
                    ))
                    
                    # Store results
                    results[pattern.permalink] = projects
                    logger.info(f"Found {len(projects)} projects for pattern {pattern.permalink}")

                    # Save checkpoint
                    if checkpoint_file:
                        self._save_checkpoint(checkpoint_file, {
                            "last_pattern_idx": idx,
                            "results": results
                        })

                except Exception as e:
                    logger.error(f"Error processing pattern {pattern.permalink}: {str(e)}")
                    if checkpoint_file:
                        self._save_checkpoint(checkpoint_file, {
                            "last_pattern_idx": idx - 1,  # Save last successful
                            "results": results
                        })
                    raise

        finally:
            if show_progress and hasattr(pattern_pbar, 'close'):
                pattern_pbar.close()

            # Clean up checkpoint file if all patterns were processed
            if checkpoint_file and len(results) == len(patterns):
                logger.info("All patterns processed, removing checkpoint file")
                try:
                    checkpoint_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to remove checkpoint file: {str(e)}")

        return results

    def _load_checkpoint(self, checkpoint_file: Path) -> Dict[str, Any]:
        """Load checkpoint data if it exists.
        
        Args:
            checkpoint_file: Path to checkpoint file
            
        Returns:
            Dictionary with checkpoint data or empty dict if no checkpoint exists
        """
        if checkpoint_file and checkpoint_file.exists():
            try:
                logger.info(f"Loading checkpoint from {checkpoint_file}")
                data = json.loads(checkpoint_file.read_text())
                logger.info(f"Resuming from pattern index {data.get('last_pattern_idx', -1)}")
                return data
            except Exception as e:
                logger.error(f"Error loading checkpoint file: {str(e)}")
                logger.info("Starting from beginning")
        return {}

    def _save_checkpoint(self, checkpoint_file: Path, data: Dict[str, Any]):
        """Save checkpoint data.
        
        Args:
            checkpoint_file: Path to checkpoint file
            data: Data to save
            
        The function implements atomic writes to prevent corruption
        of the checkpoint file if interrupted.
        """
        # Create parent directories if they don't exist
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to temporary file first
        temp_file = checkpoint_file.with_suffix('.tmp')
        try:
            temp_file.write_text(json.dumps(data, indent=2))
            temp_file.replace(checkpoint_file)  # Atomic replace
        except Exception as e:
            logger.error(f"Error saving checkpoint: {str(e)}")
            if temp_file.exists():
                temp_file.unlink()
            raise