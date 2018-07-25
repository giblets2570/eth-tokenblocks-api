import random, os, json, arrow
from chalice import Chalice, Response, NotFoundError, ForbiddenError
from database import Database
from truelayer import Truelayer
from passlib.hash import pbkdf2_sha256
import jwt

contract_folder = os.environ.get('CONTRACT_FOLDER', None)
assert contract_folder != None

app = Chalice(app_name='ett-api')

from web3 import Web3, contract

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


def loggedin_middleware(func):
  def wrapper(*args, **kwargs):
    headers = app.current_request.headers
    authorization = headers['authorization'].replace('Bearer ', '')
    try:
      result = jwt.decode(authorization, 'secret', algorithms=['HS256'])
      print(result)
      return func(*args, **kwargs)
    except Exception as e:
      print(e)
      raise e
  return wrapper

@app.route('/truelayer')
def truelayer():
  try:
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
  except Exception as e:
    raise e

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
  try:
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
  except Exception as e:
    print(e)
    raise e

  return result

@app.route('/auth/signup', cors=True, methods=['POST'])
def auth_signup():
  request = app.current_request
  data = request.json_body

  address = data['address']
  name = data['name']
  password = data['password']
  
  user = Database.find_one("User", {
    'name': name,
    'address': Web3.toChecksumAddress(address),
  })
  if not user:
    password_hash = pbkdf2_sha256.hash(password)
    Database.insert("User", {
      'name': name,
      'password': password_hash,
      'address': address
    })
    user = Database.find_one("User", {'address': Web3.toChecksumAddress(address)})
  return {
    'id': user['id'],
    'name': user['name'],
    'address': user['address']
  }

@app.route('/auth/login', cors=True, methods=['POST'])
def auth_login():
  request = app.current_request
  data = request.json_body

  address = data['address']
  name = data['name']
  password = data['password']
  
  user = Database.find_one("User", {
    'name': Web3.toChecksumAddress(name),
    'address': Web3.toChecksumAddress(address),
  })
  if not user: raise NotFoundError('user not found with name {}'.format(name))

  if not pbkdf2_sha256.verify(password, user['password_hash']): raise ForbiddenError('Wrong password')

  token = jwt.encode({
      'id': user['id'],
      'name': user['name'],
      'address': user['address']
    }, 
    'secret', 
    algorithm='HS256'
  )

  return {
    'user': {
      'id': user['id'],
      'name': user['name'],
      'address': user['address']
    },
    'token': token
  }

@app.route('/user/{address}', cors=True, methods=['GET'])
def user_get(address):
  user =  Database.find_one("User", {'address': Web3.toChecksumAddress(address)})
  if not user: raise NotFoundError('user not found with address {}'.format(address))
  return {
    'id': user['id'],
    'kyc': user['kyc'] ,
    'address': user['address'] ,
    'created_at': str(user['created_at']),
    'truelayer_account_id': user['truelayer_account_id']
  }

@app.route('/user/{address}', cors=True, methods=['PUT'])
def user_put(address):
  request = app.current_request
  data = request.json_body

  user = Database.find_one("User", {'address': Web3.toChecksumAddress(address)})
  if not user: raise NotFoundError('user not found with address {}'.format(address))

  Database.update('User', {'id': user['id']}, data)

  return { 'message': 'Done' }

@app.route('/accounts/{address}', cors=True)
def accounts(address):
  user =  Database.find_one("User", {'address': Web3.toChecksumAddress(address)})
  if not user: raise NotFoundError('user not found with address {}'.format(address))

  user = refresh_user_token(user)
  accounts = Truelayer.get_accounts(user)

  return accounts

@app.route('/accounts/{address}/check-kyc')
def checkKyc(address):
  user =  Database.find_one("User", {'address': address})
  if not user: raise NotFoundError('user not found with address {}'.format(address))

  user = refresh_user_token(user)
  accounts = Truelayer.get_accounts(user)

  if not(len(accounts)):
    raise ForbiddenError('Not KYC')
  else:
    return {'message': 'Is KYC', 'status': 200}

@app.route('/accounts/{address}/check-balance')
def checkBalance(address):
  request = app.current_request
  amount = int(request.query_params['amount'])

  user =  Database.find_one("User", {'address': Web3.toChecksumAddress(address)})
  if not user: raise NotFoundError('user not found with address {}'.format(address))

  user = refresh_user_token(user)
  balance = Truelayer.get_balance(user)
  
  balance_small = int(balance['available'] * 100)

  if(balance_small < amount):
    raise ForbiddenError('Not enough funds')
  else:
    return {'message': 'Has funds', 'status': 200}
