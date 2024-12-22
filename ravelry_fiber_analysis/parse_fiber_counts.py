import json
import numpy as np
import matplotlib.pylab as plt
import pickle

from ravelry_fiber_analysis import ravelry_api_common as rc

def parse_fiber_counts():
    yarn_names = json.load(rc.YARN_NAMES,'rb')['yarns']
    stored_json_projects = json.load(rc.STORED_PROJECTS,'rb')

    yarn_data_matrix = np.identity(len(yarn_names))
    yarn_name_to_matrix_id_dict = {}

    index = 0
    for yarn_name in yarn_names:
        yarn_name_to_matrix_id_dict[yarn_name[2]] = index
        index += 1

    json.dump(yarn_name_to_matrix_id_dict,open(rc.YARN_NAME_TO_MATRIX_DICT,'wb'))

    for pattern_group in stored_json_projects['projects']:
        key = pattern_group.keys()[0]
        fibers_for_pattern = json.load(open(rc.STORED_PATTERNS + key,'rb'))

        yarns = []
        for project in fibers_for_pattern[key]:
            for yarn in project['yarn_data']:
                if yarn['yarn_id'] is None or yarn in yarns:
                    continue
                else:
                    yarns.append(yarn)

        for i in yarns:
            for j in yarns:
                if i != j:
                    yarn_data_matrix[yarn_name_to_matrix_id_dict[str(i['yarn_id'])]][yarn_name_to_matrix_id_dict[str(j['yarn_id'])]] += 1

        print (key)

    plt.spy(yarn_data_matrix, precision=0.01, markersize=1)
    plt.show()

    return pickle.dump(yarn_data_matrix, open(rc.YARN_DATA_MATRIX, 'wb'))