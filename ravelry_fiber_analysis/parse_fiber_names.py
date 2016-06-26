import json
import numpy as np
from ravelry_fiber_analysis import ravelry_api_common as rc

def parse_fiber_names():
    stored_json_projects = json.load(open(rc.STORED_PROJECTS, 'rb'))

    yarns = []
    for pattern_group in stored_json_projects['projects']:
        key = pattern_group.keys()[0]
        fibers_for_pattern = json.load(open(rc.STORED_PATTERNS + key,'rb'))

        for project in fibers_for_pattern[key]:
            for yarn in project['yarn_data']:
                if yarn['yarn_id'] is None:
                    continue
                yarns.append({
                    'yarn_id': yarn['yarn_id'],
                    'yarn_name': yarn['yarn_name'].encode('ascii', 'ignore'),
                    'yarn_permalink': yarn['yarn_permalink'].encode('ascii', 'ignore')
                })

    yarns = { 'yarns': np.vstack({tuple(row.values()) for row in yarns}).tolist() }

    return json.dump(yarns,open(rc.YARN_NAMES,'wb'))