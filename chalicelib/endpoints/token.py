from chalicelib.database import Database
from datetime import datetime
from chalice import NotFoundError, ForbiddenError
from chalicelib.web3helper import Web3Helper
from chalicelib.cryptor import Cryptor
from chalicelib.utilities import *
import jwt, os, json, arrow, math, hashlib

# Set the signature on the contract
token_factory_contract = Web3Helper.getContract("TokenFactory.json")

def createHoldingsString(_holdings):
  holdings = [{'securityId': h['securityId'], 'securityAmount': h['securityAmount']} for h in _holdings]
  holdings = sorted(holdings, key=lambda x: x['securityId'])
  holdingsString = json.dumps(holdings, separators=(',', ':'))
  # print(holdingsString)
  return holdingsString

def Token(app):

  @app.route("/tokens", cors=True, methods=["POST"])
  @loggedinMiddleware(app)
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

    # Check if a token with the same symbol already exists
    symbolToken = Database.find_one("Token", {"symbol": token_data["symbol"]})
    if(symbolToken): raise ForbiddenError("Already a token with this address")

    token = Database.find_one("Token", token_data, insert=True)
    
    tokenHoldings = Database.find_one("TokenHoldings",{
      "tokenId": token['id'], 
      "executionDate": str(datetime.today().date())
    }, insert=True)
    
    holdings = []
    for holding in data['holdings']:
      # get the correct security
      security = Database.find_one("Security",{"symbol": holding["symbol"]})
      if(security):
        Database.update("Security", {"id": security["id"]}, {
          "name": holding["name"],
          "currency": holding["currency"],
          "country": holding["country"],
          "sector": holding["sector"],
          "class": holding["class"]
        })
      else:
        security = Database.find_one("Security",{
          "symbol": holding["symbol"],
          "name": holding["name"],
          "currency": holding["currency"],
          "country": holding["country"],
          "sector": holding["sector"],
          "class": holding["class"]
        }, insert=True)

      price = holding['price'] if 'price' in holding else '0'
      securityTimestamp = Database.find_one('SecurityTimestamp', {'securityId': security["id"], 'price': price}, order_by='-createdAt', insert=True)
      tokenHolding = Database.find_one("TokenHolding",{
        "securityId": security["id"], 
        "securityAmount": holding["amount"],
        "tokenHoldingsId": tokenHoldings["id"]
      }, insert=True)
      holdings.append(tokenHolding)

    holdingsString = createHoldingsString(holdings)
    
    try:
      tx = Web3Helper.transact(
        token_factory_contract,
        'createETT',
        token_data["name"],
        token_data["decimals"],
        token_data["symbol"],
        int(data["initialAmount"]),
        holdingsString,
        token_data["cutoffTime"],
        token_data["fee"],
        Web3Helper.toChecksumAddress(owner['address']),
      )
      print(tx.hex())
    except Exception as e:
      print(e)
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
      tokenHolding['securityTimestamp'] = toObject(Database.find_one('SecurityTimestamp', {'securityId': tokenHolding["securityId"]}, order_by='-createdAt'))
    token['holdings'] = toObject(tokenHoldingsList)
    return toObject(token)

  @app.route("/tokens/{tokenId}/balance", cors=True, methods=["GET"])
  @loggedinMiddleware(app)
  @printError
  def token_get_balance(tokenId):
    request = app.current_request
    token = Database.find_one("Token", {"id": int(tokenId)})
    if not token: raise NotFoundError("token not found with id {}".format(tokenId))
    tokenBalance = Database.find_one("TokenBalance", {"tokenId": int(tokenId), "userId": request.user["id"]}, insert=True)
    tokenBalance['token'] = toObject(token)
    return toObject(tokenBalance)

  @app.route("/tokens/{tokenId}/balances", cors=True, methods=["GET"])
  @printError
  def token_get_balances(tokenId):
    request = app.current_request
    token = Database.find_one("Token", {"id": int(tokenId)})
    if not token: raise NotFoundError("token not found with id {}".format(tokenId))
    tokenBalances = Database.find("TokenBalance", {"tokenId": token["id"]})
    for tokenBalance in tokenBalances:
      investor = Database.find_one("User", {"id": tokenBalance["userId"]}, ["id", "name", "address"])
      tokenBalance["investor"] = investor
      tokenBalance["token"] = toObject(token)
    return toObject(tokenBalances)

  @app.route("/tokens/{tokenId}/holdings", cors=True, methods=["GET"])
  @printError
  def token_get_holdings(tokenId):
    request = app.current_request
    token = Database.find_one("Token", {"id": int(tokenId)})
    if not token: raise NotFoundError("token not found with id {}".format(tokenId))
    tokenHoldings = Database.find_one("TokenHoldings", {"tokenId": token["id"]}, order_by='-createdAt')
    tokenHoldingsList = Database.find("TokenHolding", {"tokenHoldingsId": tokenHoldings["id"]})
    for tokenHolding in tokenHoldingsList:
      tokenHolding['security'] = toObject(Database.find_one('Security', {'id': tokenHolding["securityId"]}))
      tokenHolding['securityTimestamp'] = toObject(Database.find_one('SecurityTimestamp', {'securityId': tokenHolding["securityId"]}, order_by='-createdAt'))
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
    owner = Database.find_one("User",{"address": Web3Helper.toChecksumAddress(data["owner"])})
    tokenBalance = Database.find_one("TokenBalance", {"tokenId": token['id'], "userId": owner["id"]})
    if not tokenBalance:
      tokenBalance = Database.find_one("TokenBalance", {"tokenId": token['id'], "userId": owner["id"], "balance": data['initialAmount']}, insert=True)
      print(tokenBalance)
    return toObject(token)

  @app.route("/tokens/contract/end-of-day", cors=True, methods=["PUT"])
  @printError
  def tokens_contract_end_of_day():
    request = app.current_request
    data = request.json_body
    totalSupply = data["totalSupply"]
    time = data["time"]
    executionDate = arrow.get(time).format('YYYY-MM-DD')

    token = Database.find_one("Token",{"address": data["token"]})
    print("Token {}".format(token['symbol']))
    print("Total Supplys")
    print("Old {}, New {}".format(float(token['totalSupply']), totalSupply))
    print("Increase: {}".format(360 * (totalSupply/float(token['totalSupply']))))
    tokenHoldings = Database.find_one("TokenHoldings",{"tokenId": token["id"]}, order_by='-createdAt')
    allTokenHoldings = Database.find("TokenHolding",{"tokenHoldingsId": tokenHoldings["id"]})

    AUM = 0
    for holding in allTokenHoldings:
      securityTimestamp = Database.find_one('SecurityTimestamp', {'securityId': holding["securityId"]}, order_by='-createdAt')
      AUM += securityTimestamp['price'] * holding['securityAmount']


    # create the new token holdings
    Database.insert("TokenHoldings",{"tokenId": token['id'], "executionDate": executionDate})
    newTokenHoldings = Database.find_one("TokenHoldings",{"tokenId": token['id'], "executionDate": executionDate}, order_by='-createdAt')
    newAllTokenHoldings = []
    print("Token Holdings Length: {}".format(len(allTokenHoldings)))
    for tokenHolding in allTokenHoldings:
      newAllTokenHoldings.append({
        "securityId": tokenHolding['securityId'],
        "securityAmount": tokenHolding['securityAmount'],
        "tokenHoldingsId": newTokenHoldings['id']
      })

    # calculate the new NAV
    NAV = AUM / totalSupply

    print(NAV * math.pow(10, token['decimals']), AUM * math.pow(10, token['decimals']) / float(token['totalSupply']))

    # Create the new tokens at this NAV
    # First need to collect the orders 
    verifiedOrders = Database.find("Order", {"state": 1, "executionDate": executionDate, "tokenId": token["id"]})
    print("Verified orders length: {}".format(len(verifiedOrders)))
    # Then the trades
    allOrderTrades = []
    for order in verifiedOrders:
      # update the token holdings
      orderHoldings = Database.find("OrderHolding", {"orderId": order["id"]})
      orderHoldingsHash = {orderHolding['securityId']: orderHolding for orderHolding in orderHoldings}
      for tokenHolding in newAllTokenHoldings:
        tokenHolding['securityAmount'] += orderHoldingsHash[tokenHolding['securityId']]['amount']

      # Gather the trades
      orderTrades = Database.find("OrderTrade", {"orderId": order["id"]})
      tradeIds = [o['tradeId'] for o in orderTrades]
      tradeQuery = [[('id','=',tradeId)] for tradeId in tradeIds]
      trades = Database.find("Trade", tradeQuery)
      allOrderTrades += trades

    for tokenHolding in newAllTokenHoldings:
      print(tokenHolding)
      Database.insert("TokenHolding", tokenHolding)
    # Create the holdings string
    print('newAllTokenHoldings length: {}'.format(len(newAllTokenHoldings)))
    holdingsString = createHoldingsString(newAllTokenHoldings)

    # and set all orders to completed
    orderQuery = [[('id','=',o['id'])] for o in verifiedOrders]
    Database.update('Order', orderQuery, {'state': 2})

    # Need to go through each trade and get the NAV+price
    supplyUpdate = 0
    for trade in allOrderTrades:
      decryptedNominalAmount = Cryptor.decryptInput(trade['nominalAmount'], trade['sk'])
      amountInvested = int(decryptedNominalAmount.split(':')[1])
      decryptedPrice = Cryptor.decryptInput(trade['price'], trade['sk'])
      decryptedPrice = float(decryptedPrice)
      effectiveNAV = NAV*(100.0+decryptedPrice)/100.0
      print(amountInvested, NAV)
      supplyUpdate += int(amountInvested * 1.0 / NAV)

    tokenContract = Web3Helper.getContract("ETT.json", token['address'])

    newAUM = 0
    for holding in newAllTokenHoldings:
      securityTimestamp = Database.find_one('SecurityTimestamp', {'securityId': holding["securityId"]}, order_by='-createdAt')
      newAUM += securityTimestamp['price'] * holding['securityAmount']

    print("supplyUpdate", supplyUpdate)
    print("oldSupply", totalSupply)
    print("newSupply", supplyUpdate + totalSupply)
    print("oldAUM", AUM)
    print("newAUM", newAUM)

    print("\n===================\n")
    print("New NAV", newAUM / (supplyUpdate + totalSupply))


    # Update trades to be ready for claiming
    tradeIds = [o['tradeId'] for o in allOrderTrades]
    tradeQuery = [[('id','=',tradeId)] for tradeId in tradeIds]
    Database.update("Trade", tradeQuery, {'state': 5})

    tx = Web3Helper.transact(
      tokenContract,
      'updateTotalSupply',
      supplyUpdate,
      holdingsString,
      executionDate
    )
    # tx = b''
    print(tx.hex())

    return toObject(token)

