import json
import time

from ravelry_fiber_analysis import ravelry_api_common as rc


def pull_project_data():

    oauth = rc.generate_oauth_request_object()
    stored_json_projects = json.load(open(rc.STORED_PROJECTS,'rb'))

    for pattern_group in stored_json_projects['projects']:
        key = pattern_group.keys()[0]
        pattern_group_project_yarns = {key: []}

        for project in pattern_group[key]:
            url = rc.PROJECT_DETAIL_URL % (project['username'], project['id'])
            full_project_data = oauth.get(url)
            full_project_data.raise_for_status()  #Throw exception if we start overloading the server

            json_parsed = json.loads(full_project_data.text)['project']
            project_yarn_data = {
                'pattern_id': json_parsed['pattern_id'],
                'project_id': json_parsed['id'],
                'project_favorites': json_parsed['favorites_count'],
                'yarn_data': []
            }
            for yarn_data in json_parsed['packs']:
                if yarn_data['id'] is None:
                    break
                else:
                    project_yarn_data['yarn_data'].append({
                        'package_id': yarn_data['id'],
                        'yarn_id': yarn_data['yarn_id'],
                        'yarn_name': yarn_data['yarn_name'],
                        'yarn_permalink': None if yarn_data['yarn'] is None else yarn_data['yarn']['permalink']
                    })
            pattern_group_project_yarns[key].append(project_yarn_data)
            time.sleep(0.1)

        json.dump(pattern_group_project_yarns, open(rc.STORED_PROJECTS + key))
        time.sleep(5)

    return True
