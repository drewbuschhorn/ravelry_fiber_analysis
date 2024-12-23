import json
import time
import os
from tqdm import tqdm
from ravelry_fiber_analysis import ravelry_api_common as rc
from dotenv import load_dotenv

load_dotenv()

PROJECT_PAGINATION_LIMIT = 5
PATTERN_PAGINATION_LIMIT = 5
CHECKPOINT_FILE = 'data/crawler_checkpoint.json'
YARN_CHECKPOINT_FILE = 'data/yarn_crawler_checkpoint.json'

def ensure_directory_exists(directory):
    """Ensure the data directories exist"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def load_checkpoint(filename):
    if os.path.exists(filename):
        print(f"Loading checkpoint from {filename}")
        with open(filename, 'r') as f:
            return json.load(f)
    else:
        print("No checkpoint file found. Starting from scratch.")
        return {
            'patterns_completed': False,
            'patterns_page': 1,
            'stored_patterns': {'patterns': []},
            'stored_projects': {'projects': []},
            'last_pattern_index': -1,
            'yarn_collection': {
                'completed_patterns': [],
                'completed_projects': set(),  # Track completed projects by unique ID
                'current_pattern': None,
                'current_project_index': 0,
                'current_project_page': 1
            }
        }

def save_checkpoint(checkpoint_data, filename):
    # Convert sets to lists for JSON serialization
    if 'yarn_collection' in checkpoint_data:
        if isinstance(checkpoint_data['yarn_collection']['completed_projects'], set):
            checkpoint_data['yarn_collection']['completed_projects'] = list(
                checkpoint_data['yarn_collection']['completed_projects']
            )
    
    with open(filename, 'w') as f:
        json.dump(checkpoint_data, f)

def load_existing_yarn_data(pattern_key):
    """Load existing yarn data for a pattern if it exists"""
    yarn_file_path = os.path.join(rc.STORED_PATTERNS, f"{pattern_key}.json")
    if os.path.exists(yarn_file_path):
        with open(yarn_file_path, 'r') as f:
            return json.load(f)
    return {pattern_key: []}

def get_paginated_data(oauth, base_url, page, page_size=100):
    """Get paginated data from Ravelry API"""
    url = f"{base_url}&page={page}&page_size={page_size}"
    response = oauth.get(url)
    response.raise_for_status()
    return json.loads(response.text)

def collect_yarn_data(oauth, project, pattern_key):
    """Collect yarn data for a specific project"""
    url = rc.PROJECT_DETAIL_URL % (project['user']['username'], project['id'])
    full_project_data = oauth.get(url)
    full_project_data.raise_for_status()
    
    json_parsed = json.loads(full_project_data.text)['project']
    project_yarn_data = {
        'pattern_id': json_parsed['pattern_id'],
        'project_id': json_parsed['id'],
        'project_favorites': json_parsed['favorites_count'],
        'yarn_data': []
    }
    
    for yarn_data in json_parsed['packs']:
        if yarn_data['id'] is None:
            continue
        project_yarn_data['yarn_data'].append({
            'package_id': yarn_data['id'],
            'yarn_id': yarn_data['yarn_id'],
            'yarn_name': yarn_data['yarn_name'],
            'yarn_permalink': None if yarn_data['yarn'] is None else yarn_data['yarn']['permalink']
        })
    
    return project_yarn_data

def collect_all_patterns(oauth, checkpoint):
    """Collect all patterns with pagination and store full metadata"""
    patterns_base_url = rc.PATTERNS_SEARCH_URL + \
                     '?craft=knitting&pc=sweater&sort=popularity'
    
    # Ensure pattern metadata directory exists
    pattern_metadata_dir = os.path.join(rc.DATA_PATH, 'pattern_metadata')
    ensure_directory_exists(pattern_metadata_dir)
    
    current_page = checkpoint.get('patterns_page', 1)
    patterns_data = get_paginated_data(oauth, patterns_base_url, current_page)
    total_pages = (patterns_data['paginator']['last_page'])
    if PATTERN_PAGINATION_LIMIT is not None:
        total_pages = min(total_pages, PATTERN_PAGINATION_LIMIT)
    
    print(f"Collecting patterns (pages {current_page}-{total_pages})...")
    
    with tqdm(total=total_pages, initial=current_page-1) as pbar:
        while current_page <= total_pages:
            try:
                if current_page > 1:
                    patterns_data = get_paginated_data(oauth, patterns_base_url, current_page)
                
                for item in patterns_data['patterns']:
                    # Store basic info in checkpoint
                    checkpoint['stored_patterns']['patterns'].append({
                        'id': item['id'],
                        'name': item['name'],
                        'permalink': item['permalink']
                    })
                    
                    # Store complete pattern metadata
                    pattern_file = os.path.join(pattern_metadata_dir, f"{item['permalink']}_metadata.json")
                    try:
                        with open(pattern_file, 'w', encoding='utf-8') as f:
                            json.dump(item, f, indent=2, ensure_ascii=False)
                    except Exception as e:
                        print(f"\nWarning: Could not save metadata for pattern {item['permalink']}: {str(e)}")
                
                checkpoint['patterns_page'] = current_page
                save_checkpoint(checkpoint, CHECKPOINT_FILE)
                
                current_page += 1
                pbar.update(1)
                time.sleep(1)  # Rate limiting between pages
                
            except Exception as e:
                print(f"\nError collecting patterns on page {current_page}: {str(e)}")
                save_checkpoint(checkpoint, CHECKPOINT_FILE)
                raise

def collect_projects_for_pattern(oauth, pattern, yarn_checkpoint, stored_json_this_pattern_projects, pattern_group_project_yarns):
    """Collect all projects for a pattern with pagination"""
    projects_base_url = rc.PROJECTS_SEARCH_URL + \
                     f'?pattern-link={pattern["permalink"]}&craft=knitting&pc=sweater&status=finished&sort=popularity'
    
    current_page = yarn_checkpoint['yarn_collection']['current_project_page']
    projects_data = get_paginated_data(oauth, projects_base_url, current_page)
    total_pages = projects_data['paginator']['last_page']
    
    existing_project_ids = {
        p['project_id'] for p in pattern_group_project_yarns[pattern['permalink']]
    }
    
    print(f"\nCollecting projects for {pattern['permalink']} (pages {current_page}-{total_pages})")
    
    with tqdm(total=total_pages, initial=current_page-1) as pbar:
        while current_page <= total_pages:
            try:
                if current_page > 1:
                    projects_data = get_paginated_data(oauth, projects_base_url, current_page)
                    if PROJECT_PAGINATION_LIMIT is not None:
                        total_pages = min(total_pages, PROJECT_PAGINATION_LIMIT)
                    if current_page > total_pages:
                        break
                
                for project in projects_data['projects']:
                    project_unique_id = f"{project['name']}_{project['id']}"
                    
                    if (project_unique_id in yarn_checkpoint['yarn_collection']['completed_projects'] or
                        project['id'] in existing_project_ids):
                        continue
                    
                    stored_json_this_pattern_projects[pattern['permalink']].append({
                        'id': project['id'],
                        'name': project['name'],
                        'permalink': project['permalink'],
                        'pattern_id': project['pattern_id'],
                        'user_id': project['user_id'],
                        'username': project['user']['username'],
                        'status': project['status_name'],
                        'tag_names': project['tag_names']
                    })
                    
                    try:
                        yarn_data = collect_yarn_data(oauth, project, pattern['permalink'])
                        pattern_group_project_yarns[pattern['permalink']].append(yarn_data)
                        
                        yarn_checkpoint['yarn_collection']['current_pattern'] = pattern['permalink']
                        yarn_checkpoint['yarn_collection']['current_project_page'] = current_page
                        yarn_checkpoint['yarn_collection']['completed_projects'] = set(
                            yarn_checkpoint['yarn_collection']['completed_projects']
                        )
                        yarn_checkpoint['yarn_collection']['completed_projects'].add(project_unique_id)
                        
                        json.dump(pattern_group_project_yarns,
                                open(os.path.join(rc.STORED_PATTERNS, f"{pattern['permalink']}.json"), 'w'))
                        save_checkpoint(yarn_checkpoint, YARN_CHECKPOINT_FILE)
                        
                        time.sleep(0.1)  # Rate limiting for yarn API calls
                        
                    except Exception as e:
                        print(f"\nError collecting yarn data for project {project['id']}: {str(e)}")
                        continue
                
                current_page += 1
                pbar.update(1)
                yarn_checkpoint['yarn_collection']['current_project_page'] = current_page
                save_checkpoint(yarn_checkpoint, YARN_CHECKPOINT_FILE)
                
                time.sleep(1)  # Rate limiting between pages
                
            except Exception as e:
                print(f"\nError collecting projects on page {current_page}: {str(e)}")
                save_checkpoint(yarn_checkpoint, YARN_CHECKPOINT_FILE)
                raise
    
    return stored_json_this_pattern_projects, pattern_group_project_yarns

def find_projects_and_yarns():
    # Ensure data directories exist
    ensure_directory_exists(rc.DATA_PATH)
    ensure_directory_exists(rc.STORED_PATTERNS)
    
    oauth = rc.generate_oauth_request_object()
    checkpoint = load_checkpoint(CHECKPOINT_FILE)
    yarn_checkpoint = load_checkpoint(YARN_CHECKPOINT_FILE)
    
    # Convert completed_projects back to set for efficient lookups
    if isinstance(yarn_checkpoint['yarn_collection']['completed_projects'], list):
        yarn_checkpoint['yarn_collection']['completed_projects'] = set(
            yarn_checkpoint['yarn_collection']['completed_projects']
        )

    # Pattern collection phase with pagination
    if not checkpoint['patterns_completed']:
        collect_all_patterns(oauth, checkpoint)
        checkpoint['patterns_completed'] = True
        save_checkpoint(checkpoint, CHECKPOINT_FILE)

    # Project and yarn collection phase
    start_idx = checkpoint['last_pattern_index'] + 1
    patterns = checkpoint['stored_patterns']['patterns'][start_idx:]
    
    print(f"\nProcessing patterns (resuming from index {start_idx})...")
    
    for idx, item in enumerate(tqdm(patterns, initial=start_idx, 
                                  total=len(checkpoint['stored_patterns']['patterns']), 
                                  desc="Processing patterns")):
        try:
            # Skip if pattern is already completed
            if item['permalink'] in yarn_checkpoint['yarn_collection']['completed_patterns']:
                continue
                
            # Load existing project and yarn data
            stored_json_this_pattern_projects = {item['permalink']: []}
            pattern_group_project_yarns = load_existing_yarn_data(item['permalink'])
            
            # Reset project page counter for new pattern
            yarn_checkpoint['yarn_collection']['current_project_page'] = 1
            
            # Collect all projects and yarn data for this pattern
            stored_json_this_pattern_projects, pattern_group_project_yarns = collect_projects_for_pattern(
                oauth, item, yarn_checkpoint, stored_json_this_pattern_projects, pattern_group_project_yarns
            )
            
            # Only append to stored_projects if we processed any new projects
            if stored_json_this_pattern_projects[item['permalink']]:
                checkpoint['stored_projects']['projects'].append(stored_json_this_pattern_projects)
            
            # Update checkpoints
            checkpoint['last_pattern_index'] = start_idx + idx
            yarn_checkpoint['yarn_collection']['completed_patterns'].append(item['permalink'])
            yarn_checkpoint['yarn_collection']['current_pattern'] = None
            yarn_checkpoint['yarn_collection']['current_project_page'] = 1
            
            save_checkpoint(checkpoint, CHECKPOINT_FILE)
            save_checkpoint(yarn_checkpoint, YARN_CHECKPOINT_FILE)
            
            time.sleep(1)  # Rate limiting between patterns
            
        except Exception as e:
            print(f"\nError processing pattern {item['permalink']}: {str(e)}")
            save_checkpoint(checkpoint, CHECKPOINT_FILE)
            save_checkpoint(yarn_checkpoint, YARN_CHECKPOINT_FILE)
            raise

    # Store final results
    print("\nSaving final results...")
    with open(rc.STORED_PROJECTS, 'w') as f:
        json.dump(checkpoint['stored_projects'], f)
    
    # Clean up checkpoint files only if everything completed successfully
    if os.path.exists(CHECKPOINT_FILE) and checkpoint['last_pattern_index'] >= len(checkpoint['stored_patterns']['patterns']) - 1:
        os.remove(CHECKPOINT_FILE)
        os.remove(YARN_CHECKPOINT_FILE)
        
    return checkpoint['stored_projects']

if __name__ == "__main__":
    find_projects_and_yarns()