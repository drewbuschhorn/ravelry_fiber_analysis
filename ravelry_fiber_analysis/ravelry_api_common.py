import os
import requests
import requests_cache
from requests_oauthlib import OAuth1Session

# start Ravelry constants
RAVELRY_API = 'https://api.ravelry.com'
PROJECT_DETAIL_URL = RAVELRY_API + '/projects/%s/%s.json' # projects/username/project_id.json
PATTERNS_SEARCH_URL = RAVELRY_API + '/patterns/search.json'
PROJECTS_SEARCH_URL = RAVELRY_API + '/projects/search.json'
# end Ravelry constants

# start Project constants
DATA_PATH = 'data' + os.sep
REQUEST_CACHE = DATA_PATH + 'ravelry_cache'
STORED_PROJECTS = DATA_PATH + 'projects'
STORED_PATTERNS = DATA_PATH + 'patterns' + os.sep
YARN_NAMES = DATA_PATH + 'yarn_names'
YARN_NAME_TO_MATRIX_DICT = DATA_PATH + 'yarn_name_to_matrix_id_dict'
YARN_DATA_MATRIX = DATA_PATH + 'yarn_data_matrix.pickle'
YARN_TRANSLATION_DATA = DATA_PATH + 'translation_dict.pickle'
RECOMMENDER_TRAINING = DATA_PATH + 'computed_training.pickle'
RECOMMENDER_MODEL = DATA_PATH + 'model.pickle'
# end Project Constants


def generate_oauth_request_object():
    requests_cache.install_cache(REQUEST_CACHE)

    client_key = os.environ.get('RAVELRY_CLIENT_KEY')  # Replace with: client_key = "CLIENT_KEY_HERE" , if no env vars
    client_secret = os.environ.get(
        'RAVELRY_CLIENT_SECRET')  # Replace with: client_secret = "CLIENT_SECRET_HERE" , if no env vars
    resource_owner_key = os.environ.get(
        'RAVELRY_OAUTH_TOKEN')  # Replace with: resource_owner_key = "OAUTH_TOKEN_HERE" , if no env vars
    resource_owner_secret = os.environ.get(
        'RAVELRY_OAUTH_SECRET')  # Replace with: resource_owner_secret = "OAUTH_SECRET_HERE" , if no env vars

    return OAuth1Session(client_key,
                          client_secret=client_secret,
                          resource_owner_key=resource_owner_key,
                          resource_owner_secret=resource_owner_secret)