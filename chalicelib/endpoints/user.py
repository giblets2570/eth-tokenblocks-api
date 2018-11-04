from chalicelib.database import Database
from datetime import datetime
from chalice import NotFoundError, ForbiddenError
from chalicelib.utilities import *
from chalicelib.web3helper import Web3Helper
from chalicelib.endpoints.truelayer import refresh_user_token
from chalicelib.truelayer import Truelayer as TL

permissions_contract = Web3Helper.getContract("Permissions.json")

def User(app):

  @app.route('/users', cors=True, methods=['GET'])
  @printError
  # @loggedinMiddleware
  def users_get():
    request = app.current_request
    users = None
    query_params = request.query_params or {}
    if 'role' in query_params:
      role = query_params['role']
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
    return toObject(user, ['id', 'name', 'address', 'role', 'ik', 'spk', 'signature', 'bankConnected', 'truelayerAccountId'])

  @app.route('/users/{userId}', cors=True, methods=['PUT'])
  @loggedinMiddleware(app)
  @printError
  def user_put(userId):
    request = app.current_request
    data = request.json_body

    if 'address' in data:
      # Find if another user
      requestingUser = request.user
      data['address'] = Web3Helper.toChecksumAddress(data['address'])
      user = Database.find_one("User", {'address': data['address']})
      if user and user['id'] != requestingUser['id']:
        raise ForbiddenError('user already exists with address {}'.format(data['address']))

    user = Database.find_one("User", {'id': int(userId)})
    if not user: raise NotFoundError('user not found with id {}'.format(userId))
    user = Database.update('User', {'id': user['id']}, data, return_updated=True)[0]

    if 'address' in data:
      # Set user athorized as investor
      tx = Web3Helper.transact(
        permissions_contract,
        'setAuthorized',
        data['address'],
        1
      )

    return toObject(user, ['id', 'name', 'address', 'role', 'ik', 'spk', 'signature'])

  @app.route('/users/{userId}/bundle', cors=True, methods=['GET'])
  @printError
  def bundle(userId):
    user =  Database.find_one("User", {'id': int(userId)})
    if not user: raise NotFoundError('user not found with id {}'.format(userId))
    return toObject(user, ['ik', 'spk', 'signature'])

  @app.route('/users/{userId}/bank-accounts', cors=True, methods=['GET'])
  @printError
  def user_get(userId):
    request = app.current_request
    user = Database.find_one("User", {'id': int(userId)})
    if not user: raise NotFoundError('user not found with id {}'.format(userId))
    user['bankConnected'] = not not user['truelayerAccessToken']
    user = refresh_user_token(user)
    accounts = TL.get_accounts(user)
    return toObject(accounts)

  @app.route('/users/{userId}/transactions', cors=True, methods=['GET'])
  @printError
  def user_get(userId):
    request = app.current_request
    user = Database.find_one("User", {'id': int(userId)})
    if not user: raise NotFoundError('user not found with id {}'.format(userId))
    user['bankConnected'] = not not user['truelayerAccessToken']
    user = refresh_user_token(user)
    transactions = TL.get_transactions(user)
    return toObject(transactions)

  @app.route('/users/{userId}/balance', cors=True, methods=['GET'])
  @printError
  def user_get(userId):
    request = app.current_request
    user = Database.find_one("User", {'id': int(userId)})
    if not user: raise NotFoundError('user not found with id {}'.format(userId))
    user['bankConnected'] = not not user['truelayerAccessToken']
    user = refresh_user_token(user)
    balance = TL.get_balance(user)
    return toObject(balance)




  @app.route('/users/balance/total-supply', cors=True, methods=['PUT'])
  @printError
  def balanceTotalSupply():
    request = app.current_request
    data = request.json_body
    token = Database.find_one("Token", {"address": data["token"]})
    if not token: raise NotFoundError('token not found with address {}'.format(data["token"]))
    print(data)
    Database.update("Token", {"id": token["id"]}, {"totalSupply": data["newTotalSupply"]})

    user = Database.find_one("User", {'address': data["owner"]})
    if not user: raise NotFoundError('user not found with address {}'.format(data["owner"]))
    userBalance = Database.find_one("TokenBalance", {'userId': user['id'], "tokenId": token["id"]}, insert=True)
    if 'balance' not in userBalance: userBalance['balance'] = '0'
    if not userBalance['balance']: userBalance['balance'] = '0'
    newBalance = int(float(userBalance['balance'])) + int(float(data["newTotalSupply"])) - int(float(data["oldTotalSupply"]))
    userBalance = Database.update("TokenBalance", {"id": userBalance["id"]}, {"balance": newBalance}, return_updated=True)[0]
    return toObject(userBalance)

  @app.route('/users/balance/transfer', cors=True, methods=['PUT'])
  @printError
  def balanceTransfer():
    request = app.current_request
    data = request.json_body
    print("\n\nbalanceTransfer\n\n")
    print(data)
    print("\n\nbalanceTransfer\n\n")
    token = Database.find_one("Token", {"address": data["token"]})
    fromUser = Database.find_one("User", {'address': data["from"]})
    if not fromUser: raise NotFoundError('user not found with address {}'.format(data["from"]))
    toUser = Database.find_one("User", {'address': data["to"]})
    if not toUser: raise NotFoundError('user not found with address {}'.format(data["to"]))
    value = data['value']

    fromBalance = Database.find_one("TokenBalance", {'userId': fromUser['id'], "tokenId": token["id"]}, for_update=True)
    # If there is no from balance this transfer cannot be valid
    if not fromBalance: raise NotFoundError('token balance not found for user {}'.format(fromUser['id']))
    # Check does the user have enough balance
    print("fromBalanceYo: ", fromBalance)
    if (
      'balance' not in fromBalance or
      not fromBalance['balance'] or
      int(fromBalance['balance']) < int(value)
    ): raise NotFoundError('token balance not enough for user {}'.format(fromUser['id']))

    newFromBalance = int(float(fromBalance['balance'])) - int(float(value))
    fromBalance = Database.update("TokenBalance", {"id": fromBalance["id"]}, {"balance": newFromBalance}, return_updated=True)[0]

    toBalance = Database.find_one("TokenBalance", {'userId': toUser['id'], "tokenId": token["id"]}, insert=True, for_update=True)
    if 'balance' not in toBalance: toBalance['balance'] = '0'
    if not toBalance['balance']: toBalance['balance'] = '0'
    newToBalance = int(float(toBalance['balance'])) + int(float(value))
    toBalance = Database.update("TokenBalance", {"id": toBalance["id"]}, {"balance": newToBalance}, return_updated=True)[0]

    return {"message": "Funds transferred"}

  @app.route('/users/balance/fee-taken', cors=True, methods=['PUT'])
  @printError
  def feeTaken():
    request = app.current_request
    data = request.json_body
    print(data)

    token = Database.find_one("Token", {"address": data["token"]})
    ownerUser = Database.find_one("User", {'address': data["owner"]})
    if not ownerUser: raise NotFoundError('user not found with address {}'.format(data["owner"]))

    value = data['value']

    ownerBalance = Database.find_one("TokenBalance", {'userId': ownerUser['id'], "tokenId": token["id"]}, insert=True)
    if 'balance' not in ownerBalance: ownerBalance['balance'] = '0'
    if not ownerBalance['balance']: ownerBalance['balance'] = '0'
    newOwnerBalance = int(float(ownerBalance['balance'])) + int(float(value))
    ownerBalance = Database.update("TokenBalance", {"id": ownerBalance["id"]}, {"balance": newOwnerBalance}, return_updated=True)[0]

    return {"message": "Fee taken"}


  @app.route('/accounts/{address}/check-kyc')
  @printError
  def checkKyc(address):
    user =  Database.find_one("User", {'address': address})
    if not user: raise NotFoundError('user not found with address {}'.format(address))
    user = refresh_user_token(user)
    accounts = TL.get_accounts(user)
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
    balance = TL.get_balance(user)

    balance_small = int(balance['available'] * 100)

    if(balance_small < amount):
      raise ForbiddenError('Not enough funds')
    else:
      return {'message': 'Has funds', 'status': 200}
