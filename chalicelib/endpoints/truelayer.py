from chalicelib.truelayer import Truelayer as TL
from chalicelib.database import Database
from chalicelib.web3helper import Web3Helper
from chalice import Response, NotFoundError
from chalicelib.web3helper import Web3Helper
import os, json, random

front_end_url = os.environ.get('FRONT_END','http://localhost:3000/')

permissions_contract = Web3Helper.getContract("Permissions.json")

def refresh_user_token(user):
  return Database.update(
    'User',
    {"id": user["id"]},
    TL.get_refresh_token(user),
    return_updated=True
  )[0]

def Truelayer(app):
  @app.route('/truelayer')
  def truelayer():
    request = app.current_request
    if 'id' not in request.query_params: raise NotFoundError('id')
    user_id = request.query_params['id']
    user = Database.find_one('User', {'id': user_id})
    nonce = ''.join(random.choice("qwertyuioplkjhgfdsazxvbnm") for _ in range(10))
    Database.update(
      'User',
      {"id": int(user["id"])},
      {"nonce": nonce}
    )
    url = TL.get_auth_url(nonce)
    return Response(
      body=None,
      status_code=302,
      headers={
        "Location" : url
      }
    )

  @app.route('/truelayer-callback')
  def truelayer_callback():
    request = app.current_request
    code = request.query_params['code']
    nonce = request.query_params['state']
    user =  Database.find_one("User", {'nonce': nonce})
    if not user: raise NotFoundError('user not found')
    user = Database.update(
      'User',
      {"id": user["id"]},
      TL.get_access_token(user, code),
      return_updated = True
    )[0]
    accounts = TL.get_accounts(user)
    if not len(accounts): raise NotFoundError('No accounts found for user')

    # update the permissions contract
    # Web3Helper.transact(permissions_contract,'setAuthorized',Web3Helper.toChecksumAddress(user['address']),1)

    return Response(
      body=None,
      status_code=302,
      headers={
        "Location" : "{}setup".format(front_end_url)
      }
    )
