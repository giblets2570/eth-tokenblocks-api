from database import Database
from datetime import datetime
from chalice import NotFoundError, ForbiddenError
from web3 import Web3
import jwt, os, json
from utilities import loggedin_middleware, to_object, print_error

contract_folder = os.environ.get('CONTRACT_FOLDER', None)
assert contract_folder != None
web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

with open(contract_folder + "ETT.json") as file:
  ett_contract_abi = json.loads(file.read())["abi"]

def Token(app):
  @app.route('/tokens', cors=True, methods=['POST'])
  @print_error
  def tokens_post():
    request = app.current_request
    data = request.json_body
    token_data = {
      'name': data['name'],
      'symbol': data['symbol'],
      'decimals': data['decimals'],
      'cutoffTime': int(data['cutoffTime']),
      'address': data['tokenAddress']
    }
    token = Database.find_one("Token", token_data, insert=True)
    investors = Database.find("User", {"role": "investor"})
    for investor in investors:
      balance = Database.find_one("TokenBalance", {"investorId": investor["id"], 'tokenId': token['id']}, insert=True)
    token = to_object(token)
    return token

  @app.route('/tokens', cors=True, methods=['GET'])
  @print_error
  def tokens_get():
    request = app.current_request
    tokens = Database.find("Token")
    tokens = [to_object(u) for u in tokens]
    return tokens

  @app.route('/tokens/{tokenId}', cors=True, methods=['GET'])
  @print_error
  def token_get(tokenId):
    request = app.current_request
    token = Database.find_one('Token', {'id': int(tokenId)})
    if not token: raise NotFoundError('token not found with id {}'.format(tokenId))
    token = to_object(token)
    return token

  @app.route('/tokens/{tokenId}/balance', cors=True, methods=['GET'])
  @loggedin_middleware(app)
  @print_error
  def token_get_holdings(tokenId):
    request = app.current_request
    tokenBalance = Database.find_one('TokenBalance', {'tokenId': int(tokenId), 'investorId': request.user['id']})
    if not tokenBalance: raise NotFoundError('tokenBalance not found with token id {}'.format(tokenId))
    return to_object(tokenBalance)

  @app.route('/tokens/{tokenId}/holdings', cors=True, methods=['GET'])
  @print_error
  def token_get_holdings(tokenId):
    request = app.current_request
    token = Database.find_one('Token', {'id': int(tokenId)})
    if not token: raise NotFoundError('token not found with id {}'.format(tokenId))
    token_holdings = Database.find('TokenHoldings', {'tokenId': token['id']})
    token_holdings = [to_object(t) for t in token_holdings]
    return token_holdings


  @app.route('/tokens/{tokenId}/balances', cors=True, methods=['GET'])
  @print_error
  def token_get_balances(tokenId):
    request = app.current_request
    token = Database.find_one('Token', {'id': int(tokenId)})
    if not token: raise NotFoundError('token not found with id {}'.format(tokenId))
    token_balances = Database.find('TokenBalance', {'tokenId': token['id']})

    for token_balance in token_balances:
      investor = Database.find_one("User", {"id": token_balance["investorId"]}, ['id', 'name', 'address'])
      token_balance["investor"] = investor

    token_balances = [to_object(t) for t in token_balances]
    return token_balances


  @app.route('/tokens/{tokenId}/holdings', cors=True, methods=['POST'])
  @loggedin_middleware(app, 'admin')
  @print_error
  def token_post_holdings(tokenId):
    request = app.current_request
    data = request.json_body
    token = Database.find_one('Token', {'id': int(tokenId)})
    if not token: raise NotFoundError('token not found with id {}'.format(tokenId))

    # Generate the data for hashing
    holdings = data['holdings']
    holdings_dict = {}
    for h in holdings: holdings_dict[h['ticker']] = h['stock']

    # need tickers to be sorted
    tickers = sorted(list(holdings_dict.keys()))

    holdings_dict_str = json.dumps([{'ticker': key, 'stock': holdings_dict[key]} for key in tickers], separators=(',', ':'))
    holdings_hash = Web3.sha3(text=holdings_dict_str).hex()
    signature = web3.eth.sign(web3.eth.accounts[0], hexstr=holdings_hash).hex()
    r = signature[2:][0:64]
    s = signature[2:][64:128]
    v = int(signature[2:][128:130]) + 27

    # Set the signature on the contract
    ett_contract = web3.eth.contract(
      address=Web3.toChecksumAddress(token["address"]),
      abi=ett_contract_abi
    )
    transaction = ett_contract.functions.updateHoldings(v, r, s).transact({"from": web3.eth.accounts[0]})

    # Save the holdings to the database
    Database.remove('TokenHolding', {'tokenId': token['id']})
    
    for holding in holdings:
      Database.insert('TokenHolding', {
        'tokenId': token['id'], 
        'ticker': holding['ticker'],
        'stock': holding['stock']
      })

    token_holdings = Database.find('TokenHolding', {'tokenId': token['id']})
    token_holdings = [to_object(t) for t in token_holdings]
    return token_holdings