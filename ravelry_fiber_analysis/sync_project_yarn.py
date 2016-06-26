import json
import pickle

from ravelry_fiber_analysis import ravelry_api_common as rc


def sync_project_yarn():
    yarn_name_to_matrix_id_dict = json.load(open(rc.YARN_NAME_TO_MATRIX_DICT,'rb'))
    yarn_names = json.load(open(rc.YARN_NAMES,'rb'))['yarns']

    translation_dict = {}

    for join_record in yarn_names:
        yarn_id = join_record[2]
        yarn_name = join_record[1]
        matrix_id = yarn_name_to_matrix_id_dict[yarn_id]

        translation_dict[matrix_id] = yarn_name

    return pickle.dump(translation_dict,open(rc.YARN_TRANSLATION_DATA,'wb'))