import json
import time
import os
from tqdm import tqdm
from ravelry_fiber_analysis import ravelry_api_common as rc
from dotenv import load_dotenv

load_dotenv()


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
            'stored_patterns': {'patterns': []},
            'stored_projects': {'projects': []},
            'last_pattern_index': -1,
            'yarn_collection': {
                'completed_patterns': [],
                'completed_projects': set(),  # Track completed projects by unique ID
                'current_pattern': None,
                'current_project_index': 0
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

    # Pattern collection phase
    if not checkpoint['patterns_completed']:
        patterns_url = rc.PATTERNS_SEARCH_URL + \
                      '?craft=knitting&pc=sweater&sort=popularity&page_size=100&page=1'
        
        try:
            patterns_json = json.loads(oauth.get(patterns_url).text)
            
            print("Collecting patterns...")
            for item in tqdm(patterns_json['patterns'], desc="Collecting patterns"):
                checkpoint['stored_patterns']['patterns'].append({
                    'id': item['id'],
                    'name': item['name'],
                    'permalink': item['permalink']
                })
            
            checkpoint['patterns_completed'] = True
            save_checkpoint(checkpoint, CHECKPOINT_FILE)
            
        except Exception as e:
            print(f"Error collecting patterns: {str(e)}")
            save_checkpoint(checkpoint, CHECKPOINT_FILE)
            raise

    # Project and yarn collection phase
    projects_url = rc.PROJECTS_SEARCH_URL + \
                   '?pattern-link=%s&craft=knitting&pc=sweater&status=finished&sort=popularity&page_size=100&page=1'

    start_idx = checkpoint['last_pattern_index'] + 1
    patterns = checkpoint['stored_patterns']['patterns'][start_idx:]
    
    print(f"\nCollecting projects and yarn data (resuming from pattern {start_idx})...")
    
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
            
            # Get projects for this pattern
            projects_json = json.loads(
                oauth.get(projects_url % (item['permalink'],)).text
            )
            
            # Track existing project IDs in yarn data
            existing_project_ids = {
                p['project_id'] for p in pattern_group_project_yarns[item['permalink']]
            }
            
            # Collect projects and their yarn data
            for project_idx, project in enumerate(tqdm(projects_json['projects'], 
                                                     desc=f"Processing projects for {item['permalink']}", 
                                                     leave=False)):
                project_unique_id = f"{project['name']}_{project['id']}"
                
                # Skip if we've already processed this project
                if (project_unique_id in yarn_checkpoint['yarn_collection']['completed_projects'] or
                    project['id'] in existing_project_ids):
                    continue
                    
                # Store basic project info
                stored_json_this_pattern_projects[item['permalink']].append({
                    'id': project['id'],
                    'name': project['name'],
                    'permalink': project['permalink'],
                    'pattern_id': project['pattern_id'],
                    'user_id': project['user_id'],
                    'username': project['user']['username'],
                    'status': project['status_name'],
                    'tag_names': project['tag_names']
                })
                
                # Collect yarn data
                try:
                    yarn_data = collect_yarn_data(oauth, project, item['permalink'])
                    pattern_group_project_yarns[item['permalink']].append(yarn_data)
                    
                    # Update yarn checkpoint
                    yarn_checkpoint['yarn_collection']['current_pattern'] = item['permalink']
                    yarn_checkpoint['yarn_collection']['current_project_index'] = project_idx + 1
                    yarn_checkpoint['yarn_collection']['completed_projects'] = set(yarn_checkpoint['yarn_collection']['completed_projects'])
                    yarn_checkpoint['yarn_collection']['completed_projects'].add(project_unique_id)
                    
                    # Save yarn data after each project
                    json.dump(pattern_group_project_yarns, 
                            open(os.path.join(rc.STORED_PATTERNS, f"{item['permalink']}.json"), 'w'))
                    save_checkpoint(yarn_checkpoint, YARN_CHECKPOINT_FILE)
                    
                    time.sleep(0.1)  # Rate limiting for yarn API calls
                    
                except Exception as e:
                    print(f"\nError collecting yarn data for project {project['id']}: {str(e)}")
                    continue

            # Only append to stored_projects if we processed any new projects
            if stored_json_this_pattern_projects[item['permalink']]:
                checkpoint['stored_projects']['projects'].append(stored_json_this_pattern_projects)
            
            # Update checkpoints
            checkpoint['last_pattern_index'] = start_idx + idx
            yarn_checkpoint['yarn_collection']['completed_patterns'].append(item['permalink'])
            yarn_checkpoint['yarn_collection']['current_pattern'] = None
            yarn_checkpoint['yarn_collection']['current_project_index'] = 0
            
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