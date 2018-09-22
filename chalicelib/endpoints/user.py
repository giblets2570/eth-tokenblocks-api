from chalicelib.database import Database
from datetime import datetime
from chalice import NotFoundError, ForbiddenError
from chalicelib.utilities import *
from chalicelib.web3helper import Web3Helper

permissions_contract = Web3Helper.getContract("Permissions.json")

def User(app):

  @app.route('/users', cors=True, methods=['GET'])
  @printError
  # @loggedinMiddleware
  def users_get():
    request = app.current_request
    users = None
    if 'role' in request.query_params:
      role = request.query_params['role']
      users = Database.find("User", {'role': role})
      users = [u for u in users if u['ik']]
    else:
      users = Database.find("User")
    users = [toObject(u, ['id', 'name', 'address', 'role', 'ik', 'spk', 'signature']) for u in users]
    return users

  @app.route('/users/{userId}', cors=True, methods=['GET'])
  @printError
  def user_get(userId):
    request = app.current_request
    user = Database.find_one("User", {'id': int(userId)})
    if not user: raise NotFoundError('user not found with id {}'.format(userId))
    user['bankConnected'] = not not user['truelayerAccessToken']
    return toObject(user, ['id', 'name', 'address', 'role', 'ik', 'spk', 'signature', 'bankConnected'])

  @app.route('/users/{userId}', cors=True, methods=['PUT'])
  @printError
  def user_put(userId):
    request = app.current_request
    data = request.json_body
    if 'address' in data:
      data['address'] = Web3Helper.toChecksumAddress(data['address'])
      tx = Web3Helper.transact(
        permissions_contract,
        'setAuthorized',
        data['address'],
        1
      )

    user = Database.find_one("User", {'id': int(userId)})
    if not user: raise NotFoundError('user not found with id {}'.format(userId))
    user = Database.update('User', {'id': user['id']}, data, return_updated=True)
    return toObject(user, ['id', 'name', 'address', 'role', 'ik', 'spk', 'signature'])

  @app.route('/users/{userId}/bundle', cors=True, methods=['GET'])
  @printError
  def bundle(userId):
    user =  Database.find_one("User", {'id': int(userId)})
    if not user: raise NotFoundError('user not found with id {}'.format(userId))
    return toObject(user, ['ik', 'spk', 'signature'])

  @app.route('/users/balance/total-supply', cors=True, methods=['PUT'])
  @printError
  def balanceTotalSupply():
    request = app.current_request
    data = request.json_body
    user = Database.find_one("User", {'address': data["owner"]})
    if not user: raise NotFoundError('user not found with address {}'.format(data["owner"]))
    userBalance = Database.find_one("TokenBalance", {'address': data["owner"]})







  @app.route('/accounts/{address}/check-kyc')
  @printError
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
  @printError
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
