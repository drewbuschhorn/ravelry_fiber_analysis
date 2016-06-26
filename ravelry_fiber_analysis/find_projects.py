# Taken from https://github.com/requests/requests-oauthlib
import json
import time

from ravelry_fiber_analysis import ravelry_api_common as rc


def find_projects():
    oauth = rc.generate_oauth_request_object()

    # let's get some patterns and their projects
    patterns_url = rc.PATTERNS_SEARCH_URL + \
                   '?craft=knitting&pc=sweater&sort=popularity&page_size=100&page=1'
    projects_url = rc.PROJECTS_SEARCH_URL + \
                   '?pattern-link=%s&craft=knitting&pc=sweater&status=finished&sort=popularity&page_size=100&page=1'

    patterns_json = json.loads(oauth.get(patterns_url).text)

    stored_json_patterns = {'patterns': []}
    for item in patterns_json['patterns']:
        print '[%s] [%s] [%s]' % (item['id'], item['name'], item['permalink'])
        stored_json_patterns['patterns'].append(
            {'id': item['id'], 'name': item['name'], 'permalink': item['permalink']})

    stored_json_projects = {'projects': []}
    for item in stored_json_patterns['patterns']:
        projects_json = json.loads(
                            oauth.get(projects_url % (item['permalink'],)).text
                        )

        stored_json_this_pattern_projects = {item['permalink']: []}
        for project in projects_json['projects']:
            stored_json_this_pattern_projects[item['permalink']].append(
                {'id': project['id'], 'name': project['name'], 'permalink': project['permalink'],
                 'pattern_id': project['pattern_id'], 'user_id': project['user_id'],
                 'username': project['user']['username'],
                 'status': project['status_name'], 'tag_names': project['tag_names']
                 }
            )
        stored_json_projects['projects'].append(stored_json_this_pattern_projects)
        time.sleep(0.1)

    # Store cached ravelery projects
    return json.dump(stored_json_projects, open(rc.STORED_PROJECTS, 'wb'))