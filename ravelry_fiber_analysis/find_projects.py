import json
import time
import os
from tqdm import tqdm
from ravelry_fiber_analysis import ravelry_api_common as rc

CHECKPOINT_FILE = 'crawler_checkpoint.json'

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        print("Loading checkpoint from %s" % CHECKPOINT_FILE)
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    else:
        print("No checkpoint file found. Starting from scratch.")
        return {
            'patterns_completed': False,
            'stored_patterns': {'patterns': []},
            'stored_projects': {'projects': []},
            'last_pattern_index': -1
        }

def save_checkpoint(checkpoint_data):
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint_data, f)

def find_projects():
    oauth = rc.generate_oauth_request_object()
    checkpoint = load_checkpoint()

    # Pattern collection
    if not checkpoint['patterns_completed']:
        patterns_url = rc.PATTERNS_SEARCH_URL + \
                      '?craft=knitting&pc=sweater&sort=popularity&page_size=100&page=1'
        
        try:
            patterns_json = json.loads(oauth.get(patterns_url).text)
            
            print("Collecting patterns...")
            for item in tqdm(patterns_json['patterns']):
                checkpoint['stored_patterns']['patterns'].append({
                    'id': item['id'],
                    'name': item['name'],
                    'permalink': item['permalink']
                })
            
            checkpoint['patterns_completed'] = True
            print("Patterns collected.")
            save_checkpoint(checkpoint)
            print("Checkpoint saved to %s" % CHECKPOINT_FILE)
            
        except Exception as e:
            print(f"Error collecting patterns: {str(e)}")
            save_checkpoint(checkpoint)
            raise

    # Project collection
    projects_url = rc.PROJECTS_SEARCH_URL + \
                   '?pattern-link=%s&craft=knitting&pc=sweater&status=finished&sort=popularity&page_size=100&page=1'

    start_idx = checkpoint['last_pattern_index'] + 1
    patterns = checkpoint['stored_patterns']['patterns'][start_idx:]
    
    print(f"\nCollecting projects (resuming from pattern {start_idx})...")
    for idx, item in enumerate(tqdm(patterns, initial=start_idx, total=len(checkpoint['stored_patterns']['patterns']))):
        try:
            projects_json = json.loads(
                oauth.get(projects_url % (item['permalink'],)).text
            )

            stored_json_this_pattern_projects = {item['permalink']: []}
            
            for project in projects_json['projects']:
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

            checkpoint['stored_projects']['projects'].append(stored_json_this_pattern_projects)
            checkpoint['last_pattern_index'] = start_idx + idx
            save_checkpoint(checkpoint)
            
            time.sleep(0.1)  # Rate limiting
            
        except Exception as e:
            print(f"\nError collecting projects for pattern {item['permalink']}: {str(e)}")
            save_checkpoint(checkpoint)
            raise

    # Store final results
    print("\nSaving final results...")
    with open(rc.STORED_PROJECTS, 'w') as f:
        json.dump(checkpoint['stored_projects'], f)
    
    # Clean up checkpoint file
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        
    return checkpoint['stored_projects']