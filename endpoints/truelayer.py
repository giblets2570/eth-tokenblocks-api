from truelayer import Truelayer
from database import Database
from chalice import Response, NotFoundError
from web3 import Web3
import os, json

contract_folder = os.environ.get('CONTRACT_FOLDER', None)
assert contract_folder != None

web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

with open(contract_folder + 'Registry.json') as file:
  data = json.loads(file.read())
  network = list(data['networks'].keys())[0]
  registry_contract = web3.eth.contract(
    address=Web3.toChecksumAddress(data['networks'][network]['address']),
    abi=data['abi']
  )

def refresh_user_token(user):
  Database.update(
    'User', 
    {"id": user["id"]},
    Truelayer.get_refresh_token(user)
  )
  return Database.find_one("User", {'id': user["id"]})

def Truelayer(app):
  @app.route('/truelayer')
  def truelayer():
    request = app.current_request
    if 'address' not in request.query_params: raise NotFoundError('address')
    user_address = Web3.toChecksumAddress(request.query_params['address'])
    user = Database.find_one('User', {'address': user_address})
    if not user: 
      Database.insert('User', {"address": user_address})
      user = Database.find_one('User', {'address': user_address})
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
        "Location" : Truelayer.get_auth_url(nonce)
      }
    )
  @app.route('/truelayer-callback')
  def truelayer_callback():
    request = app.current_request
    code = request.query_params['code']
    nonce = request.query_params['state']
    user =  Database.find_one("User", {'nonce': nonce})
    if not user: raise NotFoundError('user not found with id {}'.format(user_id))
    Database.update(
      'User',
      {"id": user["id"]},
      Truelayer.get_access_token(user, code)
    )
    user =  Database.find_one("User", {"id": user["id"]})
    accounts = Truelayer.get_accounts(user)
    if not len(accounts): raise NotFoundError('No accounts found for user')

    # update the registry contract
    registry_contract.functions.registerInvestor(Web3.toChecksumAddress(user['address'])).transact({'from': web3.eth.accounts[0]})

    return result
