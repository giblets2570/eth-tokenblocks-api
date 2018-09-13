from chalicelib.truelayer import Truelayer as TL
from chalicelib.database import Database
from chalicelib.web3helper import Web3Helper
from chalice import Response, NotFoundError
import os, json, random

front_end_url = os.environ.get('FRONT_END','http://localhost:3001/#/')

permissions = Web3Helper.getContract("Permissions.json")
permissions_contract_abi = permissions["abi"]
network = list(permissions["networks"].keys())[0]
permissions_contract_address = permissions["networks"][network]["address"]
permissions_contract = permissions_contract = Web3Helper.contract(
  address=Web3Helper.toChecksumAddress(permissions_contract_address),
  abi=permissions_contract_abi
)

def refresh_user_token(user):
  Database.update(
    'User', 
    {"id": user["id"]},
    TL.get_refresh_token(user)
  )
  return Database.find_one("User", {'id': user["id"]})

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
    return Response(
      body=None,
      status_code=302,
      headers={
        "Location" : TL.get_auth_url(nonce)
      }
    )

  @app.route('/truelayer-callback')
  def truelayer_callback():
    request = app.current_request
    code = request.query_params['code']
    nonce = request.query_params['state']
    user =  Database.find_one("User", {'nonce': nonce})
    if not user: raise NotFoundError('user not found with id {}'.format(user_id))
    user = Database.update(
      'User',
      {"id": user["id"]},
      TL.get_access_token(user, code),
      return_updated = True
    )
    accounts = TL.get_accounts(user)
    if not len(accounts): raise NotFoundError('No accounts found for user')

    # update the permissions contract
    # Web3Helper.transact(permissions_contract,'setAuthorized',Web3Helper.toChecksumAddress(user['address']),1)

    return Response(
      body=None,
      status_code=302,
      headers={
        "Location" : "{}dashboard/profile/setup".format(front_end_url)
      }
    )
