# Taken from https://github.com/requests/requests-oauthlib
import os
from requests_oauthlib import OAuth1Session
client_key = os.environ.get('RAVELRY_CLIENT_KEY')  # Replace with: client_key = "CLIENT_KEY_HERE" , if no env vars
client_secret = os.environ.get('RAVELRY_CLIENT_SECRET') # Replace with: client_secret = "CLIENT_SECRET_HERE" , if no env vars
resource_owner_key = os.environ.get('RAVELRY_OAUTH_TOKEN') # Replace with: resource_owner_key = "OAUTH_TOKEN_HERE" , if no env vars
resource_owner_secret = os.environ.get('RAVELRY_OAUTH_SECRET') # Replace with: resource_owner_secret = "OAUTH_SECRET_HERE" , if no env vars

oauth = OAuth1Session(client_key,
                           client_secret=client_secret,
                           resource_owner_key=resource_owner_key,
                           resource_owner_secret=resource_owner_secret)
r = oauth.get('https://api.ravelry.com/current_user.json')

print r,r.text