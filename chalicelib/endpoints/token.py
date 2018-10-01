from chalicelib.database import Database
from datetime import datetime
from chalice import NotFoundError, ForbiddenError
from chalicelib.web3helper import Web3Helper
import jwt, os, json
from chalicelib.utilities import *

# Set the signature on the contract
token_factory_contract = Web3Helper.getContract("TokenFactory.json")

def Token(app):
  @app.route("/tokens", cors=True, methods=["POST"])
  @loggedinMiddleware(app, "admin")
  @printError
  def tokens_post():
    request = app.current_request
    data = request.json_body

    owner = None
    ownerId = data["ownerId"] if "ownerId" in data else None
    if not ownerId:
      owner = Database.find_one("User", {"address": Web3Helper.account()})
      ownerId = owner["id"]
    else:
      owner = Database.find_one("User", {"id": ownerId})
    
    if not owner: raise NotFoundError('No user found')
    
    token_data = {
      "name": data["name"],
      "symbol": data["symbol"],
      "decimals": data["decimals"],
      "cutoffTime": int(data["cutoffTime"]),
      "fee": int(data["fee"]),
      "ownerId": ownerId
    }
    try:
      tx = Web3Helper.transact(
        token_factory_contract,
        'createETT',
        token_data["name"],
        token_data["decimals"],
        token_data["symbol"],
        token_data["cutoffTime"],
        token_data["fee"],
        Web3Helper.toChecksumAddress(owner['address']),
      )
      print(tx)
    except Exception as e:
      # Token has already been put on blockchain
      print(e)
      pass

    tokenAddress = Web3Helper.call(token_factory_contract,'tokenFromSymbol',token_data["symbol"],)
    token_contract = Web3Helper.getContract("ETT.json", address=tokenAddress)
    tokenOwner = Web3Helper.call(token_contract,'owner',)
    token_data['address'] = Web3Helper.toChecksumAddress(tokenAddress)
    token = Database.find_one("Token", token_data, insert=True)
    return toObject(token)

  @app.route("/tokens", cors=True, methods=["GET"])
  @printError
  def tokens_get():
    request = app.current_request
    tokens = Database.find("Token")
    tokens = [toObject(u) for u in tokens]
    return tokens

  @app.route("/tokens/{tokenId}", cors=True, methods=["GET"])
  @printError
  def token_get(tokenId):
    request = app.current_request
    token = Database.find_one("Token", {"id": int(tokenId)})
    if not token: raise NotFoundError("token not found with id {}".format(tokenId))
    tokenHoldings = Database.find_one("TokenHoldings", {"tokenId": token["id"]})
    tokenHoldingsList = Database.find("TokenHolding", {"tokenHoldingsId": tokenHoldings["id"]})
    for tokenHolding in tokenHoldingsList:
      tokenHolding['security'] = toObject(Database.find_one('Security', {'id': tokenHolding["securityId"]}))
      tokenHolding['securityTimestamp'] = toObject(Database.find_one('SecurityTimestamp', {'securityId': tokenHolding["securityId"]}, order_by='createdAt'))
    token['holdings'] = toObject(tokenHoldingsList)
    return toObject(token)

  @app.route("/tokens/{tokenId}/balance", cors=True, methods=["GET"])
  @loggedinMiddleware(app, "investor")
  @printError
  def token_get_balance(tokenId):
    request = app.current_request
    print({"tokenId": int(tokenId), "investorId": request.user["id"]})
    tokenBalance = Database.find_one("TokenBalance", {"tokenId": int(tokenId), "investorId": request.user["id"]}, insert=True)
    return toObject(tokenBalance)

  @app.route("/tokens/{tokenId}/balances", cors=True, methods=["GET"])
  @printError
  def token_get_balances(tokenId):
    request = app.current_request
    token = Database.find_one("Token", {"id": int(tokenId)})
    if not token: raise NotFoundError("token not found with id {}".format(tokenId))
    token_balances = Database.find("TokenBalance", {"tokenId": token["id"]})
    for token_balance in token_balances:
      investor = Database.find_one("User", {"id": token_balance["investorId"]}, ["id", "name", "address"])
      token_balance["investor"] = investor
    return toObject(token_balances)

  @app.route("/tokens/{tokenId}/holdings", cors=True, methods=["GET"])
  @printError
  def token_get_holdings(tokenId):
    request = app.current_request
    token = Database.find_one("Token", {"id": int(tokenId)})
    if not token: raise NotFoundError("token not found with id {}".format(tokenId))
    tokenHoldings = Database.find_one("TokenHoldings", {"tokenId": token["id"]})
    tokenHoldingsList = Database.find("TokenHolding", {"tokenHoldingsId": tokenHoldings["id"]})
    for tokenHolding in tokenHoldingsList:
      tokenHolding['security'] = toObject(Database.find_one('Security', {'id': tokenHolding["securityId"]}))
      tokenHolding['securityTimestamp'] = toObject(Database.find_one('SecurityTimestamp', {'securityId': tokenHolding["securityId"]}, order_by='createdAt'))
    return toObject(tokenHoldingsList)

  @app.route("/tokens/{tokenId}/holdings", cors=True, methods=["POST"])
  @loggedinMiddleware(app, "admin")
  @printError
  def token_post_holdings(tokenId):
    request = app.current_request
    data = request.json_body
    token = Database.find_one("Token", {"id": int(tokenId)})
    if not token: raise NotFoundError("token not found with id {}".format(tokenId))

    tokenHoldings = Database.find_one("TokenHoldings",{
      "tokenId": token['id'], 
      "executionDate": str(datetime.today().date())
    }, insert=True)

    for holding in data:
      security = Database.find_one("Security",{"symbol": holding["symbol"]}, insert=True)
      tokenHolding = Database.find_one("TokenHolding",{
        "securityId": security["id"], 
        "securityAmount": holding["amount"],
        "tokenHoldingsId": tokenHoldings["id"]
      }, insert=True)


    return toObject(tokenHoldings)