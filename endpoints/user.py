from database import Database
from chalice import NotFoundError, ForbiddenError
from web3 import Web3

def to_object(model, keys):
  output = dict()
  for key in keys:
    output[key] = model[key]
  return output

def User(app):
  @app.route('/users/{user_id}', cors=True, methods=['PUT'])
  def user_put(user_id):
    request = app.current_request
    data = request.json_body
    user = Database.find_one("User", {'id': int(user_id)})
    if not user: raise NotFoundError('user not found with id {}'.format(user_id))
    Database.update('User', {'id': user['id']}, data)
    return { 'message': 'Done' }

  @app.route('/users/{address}/bundle', cors=True)
  def accounts(address):
    user =  Database.find_one("User", {'address': Web3.toChecksumAddress(address)})
    if not user: raise NotFoundError('user not found with address {}'.format(address))
    return to_object(user, ['ik', 'spk', 'signature'])

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
