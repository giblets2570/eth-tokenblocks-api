import requests, os, arrow

truelayer_client_id = os.getenv('TRUELAYER_CLIENT_ID', None)
truelayer_client_secret = os.getenv('TRUELAYER_CLIENT_SECRET', None)
truelayer_redirect_uri = os.getenv('TRUELAYER_REDIRECT_URI', None)
assert truelayer_client_id != None
assert truelayer_client_secret != None
assert truelayer_redirect_uri != None

class Truelayer(object):

  @classmethod
  def get_refresh_token(cls, user):
    data = {
      "grant_type": 'refresh_token',
      "client_id": truelayer_client_id,
      "client_secret": truelayer_client_secret,
      "refresh_token": user['truelayerRefreshToken'],
    }
    r = requests.post("https://auth.truelayer.com/connect/token", data=data).json()
    return {
      "truelayerAccessToken": r["access_token"],
      "truelayerRefreshToken": r["refresh_token"]
    }

  @classmethod
  def get_access_token(cls, user, code):
    data = {
      "grant_type": 'authorization_code', #  Required Value authorization_code
      "code": code, #  Required Value from step 2
      "client_id": truelayer_client_id, # Required The client ID you received after registering your application.
      "client_secret": truelayer_client_secret, # Required The client secret you received after registering your application.
      "redirect_uri": truelayer_redirect_uri, #  Required Your application’s redirect URI
    }
    r = requests.post("https://auth.truelayer.com/connect/token", data=data).json()
    return {
      "truelayerAccessToken": r["access_token"],
      "truelayerRefreshToken": r["refresh_token"]
    }

  @classmethod
  def get_accounts(cls, user):
    headers = {'Authorization': 'Bearer {}'.format(user['truelayerAccessToken'])}
    r = requests.get("https://api.truelayer.com/data/v1/accounts", headers=headers)
    accounts = r.json()['results']
    return accounts

  @classmethod
  def get_balance(cls, user):
    headers = {'Authorization': 'Bearer {}'.format(user['truelayerAccessToken'])}
    url = "https://api.truelayer.com/data/v1/accounts/{}/balance".format(user['truelayerAccountId'])
    print(url)
    r = requests.get(url, headers=headers)
    result = r.json()['results'][0]
    return result

  @classmethod
  def move_funds(cls, *args, **kwargs):
    return True

  @classmethod
  def get_auth_url(cls, nonce):
    scope = "info%20accounts%20balance%20transactions%20offline_access"
    auth_url = "https://auth.truelayer.com/?response_type=code&client_id={}&redirect_uri={}&scope={}&nonce=foobar&state={}&enable_mock=true".format(truelayer_client_id,truelayer_redirect_uri,scope,nonce)

    return auth_url

  @classmethod
  def get_transactions(cls, user):
    now = arrow.now()
    previous = now.shift(months=-1)
    url = "https://api.truelayer.com/data/v1/accounts/{}/transactions?from={}".format(user['truelayerAccountId'],previous.format('YYYY-MM-DDTHH:mm:ss'))
    headers = {'Authorization': 'Bearer {}'.format(user['truelayerAccessToken'])}
    print(headers)
    print(url)
    r = requests.get(url, headers=headers)
    transactions = r.json()['results']

    return transactions
