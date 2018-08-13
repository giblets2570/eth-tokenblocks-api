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
        'address': data['tokenAddress'],
        'decimals': data['decimals'],
        'cutoff_time': data['cutoffTime']
      }
      token = Database.find_one("Token", token_data)
      if not token:
        Database.insert("Token", token_data)
        token = Database.find_one("Token", token_data)
      token = to_object(token, ['name','symbol','address','decimals','cutoff_time'])
      return token
    except Exception as e:
      print(e)
      raise e

  @app.route('/tokens', cors=True, methods=['GET'])
  def tokens_get():
    request = app.current_request
    tokens = Database.find("Token", {})
    print(tokens)
    tokens = [to_object(u, ['name','symbol','address','decimals','cutoff_time']) for u in tokens]
    return tokens