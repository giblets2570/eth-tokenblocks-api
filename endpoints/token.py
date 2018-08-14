from database import Database
from datetime import datetime
from chalice import NotFoundError, ForbiddenError
from web3 import Web3
import jwt, os, json

contract_folder = os.environ.get('CONTRACT_FOLDER', None)
assert contract_folder != None
web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

def to_object(model, keys):
  output = dict()
  for key in keys:
    output[key] = model[key]
    if(type(output[key]) == datetime):
      output[key] = output[key].timestamp()
  return output

def Token(app):
  def loggedin_middleware(func):
    def wrapper(*args, **kwargs):
      headers = app.current_request.headers
      if 'authorization' not in headers: raise ForbiddenError('Not authorized')
      authorization = headers['authorization'].replace('Bearer ', '')
      try:
        result = jwt.decode(authorization, 'secret', algorithms=['HS256'])
        setattr(app.current_request, 'user', result)
        return func(*args, **kwargs)
      except Exception as e:
        print(e)
        raise e
    return wrapper

  @app.route('/tokens', cors=True, methods=['POST'])
  def tokens_post():
    try:
      request = app.current_request
      data = request.json_body
      token_data = {
        'name': data['name'],
        'symbol': data['symbol'],
        'decimals': data['decimals'],
        'cutoff_time': data['cutoffTime']
      }
      token = Database.find_one("Token", token_data)
      token_data['address'] = data['tokenAddress']
      
      if token:
        Database.update("Token", {'id': token['id']}, token_data)
      else:
        Database.insert("Token", token_data)

      token = Database.find_one("Token", token_data)

      with open(contract_folder + 'TokenFactory.json') as file:
        data = json.loads(file.read())
        network = list(data['networks'].keys())[0]
        token_factory_contract = web3.eth.contract(
          address=Web3.toChecksumAddress(data['networks'][network]['address']),
          abi=data['abi']
        )
        create_order_address = token_factory_contract.functions.tokenToCreateOrder(Web3.toChecksumAddress(token['address'])).call()
        Database.update("Token", {'id': token['id']}, {'create_order_address': Web3.toChecksumAddress(create_order_address)})

      token = to_object(token, ['name','symbol','address','create_order_address','decimals','cutoff_time'])
      return token
    except Exception as e:
      print(e)
      raise e

  @app.route('/tokens', cors=True, methods=['GET'])
  def tokens_get():
    request = app.current_request
    tokens = Database.find("Token", {})
    print(tokens)
    tokens = [to_object(u, ['name','symbol','address','create_order_address','decimals','cutoff_time']) for u in tokens]
    return tokens