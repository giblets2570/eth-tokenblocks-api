from chalicelib.database import Database
from datetime import datetime
from chalice import NotFoundError, ForbiddenError
from chalicelib.web3helper import Web3Helper
from chalicelib.cryptor import Cryptor
from chalicelib.utilities import *
import jwt, os, json, arrow, math

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
      "decimals": data["decimals"],
      "symbol": data["symbol"],
      "cutoffTime": int(data["cutoffTime"]),
      "fee": int(data["fee"]),
      "ownerId": ownerId,
      "totalSupply": data["initialAmount"]
    }

    token = Database.find_one("Token", token_data, insert=True)
    
    tokenHoldings = Database.find_one("TokenHoldings",{
      "tokenId": token['id'], 
      "executionDate": str(datetime.today().date())
    }, insert=True)
    
    initialAUM = 0
    for holding in data['holdings']:
      # get the correct security
      security = Database.find_one("Security",{"symbol": holding["symbol"]}, insert=True)
      tokenHolding = Database.find_one("TokenHolding",{
        "securityId": security["id"], 
        "securityAmount": holding["amount"],
        "tokenHoldingsId": tokenHoldings["id"]
      }, insert=True)
      securityTimestamp = Database.find_one('SecurityTimestamp', {'securityId': security["id"]}, order_by='createdAt')
      initialAUM += securityTimestamp['price'] * holding['amount']

    try:
      tx = Web3Helper.transact(
        token_factory_contract,
        'createETT',
        token_data["name"],
        token_data["decimals"],
        token_data["symbol"],
        int(data["initialAmount"]),
        initialAUM,
        token_data["cutoffTime"],
        token_data["fee"],
        Web3Helper.toChecksumAddress(owner['address']),
      )
      print(tx.hex())
    except Exception as e:
      pass

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
  @loggedinMiddleware(app)
  @printError
  def token_get_balance(tokenId):
    request = app.current_request
    print({"tokenId": int(tokenId), "userId": request.user["id"]})
    tokenBalance = Database.find_one("TokenBalance", {"tokenId": int(tokenId), "userId": request.user["id"]}, insert=True)
    return toObject(tokenBalance)

  @app.route("/tokens/{tokenId}/balances", cors=True, methods=["GET"])
  @printError
  def token_get_balances(tokenId):
    request = app.current_request
    token = Database.find_one("Token", {"id": int(tokenId)})
    if not token: raise NotFoundError("token not found with id {}".format(tokenId))
    token_balances = Database.find("TokenBalance", {"tokenId": token["id"]})
    for token_balance in token_balances:
      investor = Database.find_one("User", {"id": token_balance["userId"]}, ["id", "name", "address"])
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

  @app.route("/tokens/{tokenId}/invested", cors=True, methods=["GET"])
  @loggedinMiddleware(app)
  @printError
  def token_invested(tokenId):
    request = app.current_request
    data = request.json_body
    token = Database.find_one("Token", {"id": int(tokenId)})
    if not token: raise NotFoundError("token not found with id {}".format(tokenId))

    # Need to find all the trades this investor invested in
    claimedTrades = Database.find("Trade", {"tokenId": token["id"], "investorId": request.user["id"], "state": 5})

    totalAmount = 0
    for trade in claimedTrades:
      decrypted = Cryptor.decryptInput(trade['nominalAmount'], trade['sk'])
      # I'll need to include the currency here
      amountInvested = int(decrypted.split(':')[1])
      print(amountInvested)
      totalAmount += amountInvested

    return toObject({"totalAmount": totalAmount})

  @app.route("/tokens/contract/update", cors=True, methods=["PUT"])
  @printError
  def tokens_contract_update():
    request = app.current_request
    data = request.json_body
    Database.update("Token", {"symbol": data["symbol"]},{
      "address": Web3Helper.toChecksumAddress(data["tokenAddress"]),
    })
    token = Database.find_one("Token",{"symbol": data["symbol"]})
    return toObject(token)

  @app.route("/tokens/contract/aum", cors=True, methods=["PUT"])
  @printError
  def tokens_contract_aum():
    request = app.current_request
    data = request.json_body
    token = Database.find_one("Token",{"address": data["token"]})
    print(token)
    AUM = data["AUM"]
    totalSupply = data["totalSupply"]
    time = data["time"]
    print(AUM, totalSupply)
    # calculate the new NAV
    NAV = AUM / totalSupply

    # Create the new tokens at this NAV
    # First need to collect the orders 
    executionDate = arrow.get(time).format('YYYY-MM-DD')
    completedOrders = Database.find("Order", {"state": 1, "executionDate": executionDate, "tokenId": token["id"]})
    # Then the trades
    allOrderTrades = []
    for order in completedOrders:
      orderTrades = Database.find("OrderTrade", {"orderId": order["id"]})
      tradeIds = [o['tradeId'] for o in orderTrades]
      tradeQuery = [[('id','=',tradeId)] for tradeId in tradeIds]
      trades = Database.find("Trade", tradeQuery)
      allOrderTrades += trades

    # Need to go through each trade and get the NAV+price
    supplyUpdate = 0
    for trade in allOrderTrades:
      decryptedNominalAmount = Cryptor.decryptInput(trade['nominalAmount'], trade['sk'])
      amountInvested = int(decryptedNominalAmount.split(':')[1])/100.0
      decryptedPrice = Cryptor.decryptInput(trade['price'], trade['sk'])
      decryptedPrice = float(decryptedPrice)
      effectiveNAV = NAV*(100.0+decryptedPrice)/100.0
      print(amountInvested, NAV)
      supplyUpdate += int(amountInvested / NAV)

    print(supplyUpdate)
    tokenContract = Web3Helper.getContract("ETT.json", token['address'])

    tx = Web3Helper.transact(
      tokenContract,
      'updateTotalSupply',
      supplyUpdate,
      executionDate
    )
    # tx = b''
    print(tx.hex())

    return toObject(token)

