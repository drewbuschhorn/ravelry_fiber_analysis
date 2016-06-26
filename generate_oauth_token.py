# Taken from https://github.com/requests/requests-oauthlib
import os
from requests_oauthlib import OAuth1Session
client_key = os.environ.get('RAVELRY_CLIENT_KEY')  # Replace with: client_key = "CLIENT_KEY_HERE" , if no env vars
client_secret = os.environ.get('RAVELRY_CLIENT_SECRET') # Replace with: client_secret = "CLIENT_SECRET_HERE" , if no env vars

request_token_url = 'https://www.ravelry.com/oauth/request_token'
# Note Ravelry requires the callback_uri param but doesn't accept OOB
oauth = OAuth1Session(client_key, client_secret=client_secret, callback_uri='https://127.0.0.1/test')
fetch_response = oauth.fetch_request_token(request_token_url)
resource_owner_key = fetch_response.get('oauth_token')
resource_owner_secret = fetch_response.get('oauth_token_secret')

base_authorization_url = 'https://www.ravelry.com/oauth/authorize'
authorization_url = oauth.authorization_url(base_authorization_url)
print 'Please go here and authorize,', authorization_url

redirect_response = raw_input('Paste the full redirect URL here: ')

oauth_response = oauth.parse_authorization_response(redirect_response)
verifier = oauth_response.get('oauth_verifier')

access_token_url = 'https://www.ravelry.com/oauth/access_token'
oauth = OAuth1Session(client_key,
                           client_secret=client_secret,
                           resource_owner_key=resource_owner_key,
                           resource_owner_secret=resource_owner_secret,
                           verifier=verifier)
oauth_tokens = oauth.fetch_access_token(access_token_url)

print oauth_tokens
resource_owner_key = oauth_tokens.get('oauth_token')
resource_owner_secret = oauth_tokens.get('oauth_token_secret')
oauth = OAuth1Session(client_key,
                           client_secret=client_secret,
                           resource_owner_key=resource_owner_key,
                           resource_owner_secret=resource_owner_secret)
r = oauth.get('https://api.ravelry.com/current_user.json')

print r.text
