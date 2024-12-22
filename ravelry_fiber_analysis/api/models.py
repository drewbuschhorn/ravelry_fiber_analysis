from typing import Optional, List, Dict, Any
from datetime import datetime
import attr

@attr.s(auto_attribs=True)
class Pattern:
    """Represents a Ravelry pattern."""
    id: int
    name: str
    permalink: str
    favorites_count: Optional[int] = None
    difficulty_average: Optional[float] = None
    rating_average: Optional[float] = None
    projects_count: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Pattern':
        """Create a Pattern instance from API response data."""
        return cls(
            id=data['id'],
            name=data['name'],
            permalink=data['permalink'],
            favorites_count=data.get('favorites_count'),
            difficulty_average=data.get('difficulty_average'),
            rating_average=data.get('rating_average'),
            projects_count=data.get('projects_count')
        )

@attr.s(auto_attribs=True)
class FiberContent:
    """Represents fiber content information."""
    fiber_type: str
    percentage: Optional[float] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FiberContent':
        """Create a FiberContent instance from API response data."""
        return cls(
            fiber_type=data['fiber_type'],
            percentage=data.get('percentage')
        )

@attr.s(auto_attribs=True)
class Yarn:
    """Represents yarn information in a project."""
    id: Optional[int]
    name: str
    permalink: Optional[str] = None
    fiber_content: Optional[List[FiberContent]] = attr.ib(factory=list)
    weight: Optional[str] = None
    grams: Optional[float] = None
    meters: Optional[float] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Yarn':
        """Create a Yarn instance from API response data."""
        fiber_content = []
        if 'fiber_content' in data:
            fiber_content = [FiberContent.from_dict(f) for f in data['fiber_content']]
            
        return cls(
            id=data.get('id'),
            name=data['name'],
            permalink=data.get('permalink'),
            fiber_content=fiber_content,
            weight=data.get('weight'),
            grams=data.get('grams'),
            meters=data.get('meters')
        )

@attr.s(auto_attribs=True)
class Project:
    """Represents a Ravelry project."""
    id: int
    name: str
    pattern_id: Optional[int]
    user_id: int
    username: str
    status: str
    started: Optional[datetime] = None
    completed: Optional[datetime] = None
    favorites_count: Optional[int] = None
    yarns: List[Yarn] = attr.ib(factory=list)
    tags: List[str] = attr.ib(factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Create a Project instance from API response data."""
        # Parse dates if available
        started = None
        completed = None
        if 'started' in data:
            try:
                started = datetime.fromisoformat(data['started'])
            except (ValueError, TypeError):
                pass
        if 'completed' in data:
            try:
                completed = datetime.fromisoformat(data['completed'])
            except (ValueError, TypeError):
                pass

        # Parse yarns if available
        yarns = []
        if 'packs' in data:
            for pack in data['packs']:
                if pack.get('yarn'):
                    yarns.append(Yarn.from_dict(pack['yarn']))

        return cls(
            id=data['id'],
            name=data['name'],
            pattern_id=data.get('pattern_id'),
            user_id=data['user_id'],
            username=data['user']['username'],
            status=data['status_name'],
            started=started,
            completed=completed,
            favorites_count=data.get('favorites_count'),
            yarns=yarns,
            tags=data.get('tag_names', [])
        )