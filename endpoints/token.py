from database import Database
from datetime import datetime
from chalice import NotFoundError, ForbiddenError
from web3 import Web3
import jwt, os, json
from utilities import loggedin_middleware, to_object

contract_folder = os.environ.get('CONTRACT_FOLDER', None)
assert contract_folder != None
web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

def Token(app):
  @app.route('/tokens', cors=True, methods=['POST'])
  def tokens_post():
    request = app.current_request
    data = request.json_body
    token_data = {
      'name': data['name'],
      'symbol': data['symbol'],
      'decimals': data['decimals'],
      'cutoff_time': datetime.fromtimestamp(int(data['cutoffTime']))
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
    token = to_object(token, ['id','name','symbol','address','create_order_address','decimals','cutoff_time'])
    return token

  @app.route('/tokens', cors=True, methods=['GET'])
  def tokens_get():
    request = app.current_request
    tokens = Database.find("Token", {})
    tokens = [to_object(u, ['id','name','symbol','address','create_order_address','decimals','cutoff_time']) for u in tokens]
    return tokens

  @app.route('/tokens/{token_id}', cors=True, methods=['GET'])
  def token_get(token_id):
    request = app.current_request
    token = Database.find_one('Token', {'id': int(token_id)})
    if not token: raise NotFoundError('token not found with id {}'.format(token_id))
    token = to_object(token, ['id','name','symbol','address','create_order_address','decimals','cutoff_time'])
    return token

  @app.route('/tokens/{token_id}/holdings', cors=True, methods=['GET'])
  def token_get_holdings(token_id):
    request = app.current_request
    token = Database.find_one('Token', {'id': int(token_id)})
    if not token: raise NotFoundError('token not found with id {}'.format(token_id))
    token_holdings = Database.find('TokenHolding', {'token_id': token['id']})
    token_holdings = [to_object(t, ['id', 'ticker', 'percent', 'created_at']) for t in token_holdings]
    return token_holdings


  @app.route('/tokens/{token_id}/holdings', cors=True, methods=['POST'])
  def token_get_holdings(token_id):
    request = app.current_request
    data = request.json_body
    token = Database.find_one('Token', {'id': int(token_id)})
    if not token: raise NotFoundError('token not found with id {}'.format(token_id))
    holdings = data['holdings']
    holdings_hash = {}
    for h in holdings:
      holdings_hash[h['ticker']] = h['percent']
    tickers = list(holdings_hash.keys())
    tickers.sort()
    holdings_hash['tickers'] = tickers
    return holdings_hash

    # percent = data['percent']
    # ticker = Web3.toBytes(hexstr=data['ticker']).decode("utf-8")
    # token_holding = Database.find_one('TokenHolding', {'ticker': ticker})
    # if token_holding:
    #   Database.update('TokenHolding', {'id': token_holding['id']}, {'percent': percent})
    # else:
    #   Database.insert('TokenHolding', {'percent': percent, 'ticker': ticker, 'token_id': token['id']})
    # token_holding = Database.find_one('TokenHolding', {'ticker': ticker})
    # return to_object(token_holding, ['id', 'ticker', 'percent', 'created_at'])


