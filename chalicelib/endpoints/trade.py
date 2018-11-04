import jwt, os, json, requests, math, arrow, copy
from chalicelib.database import Database
from chalicelib.truelayer import Truelayer as TL
from datetime import datetime, date
from chalice import NotFoundError, ForbiddenError
from chalicelib.web3helper import Web3Helper
from chalicelib.cryptor import Cryptor
from chalicelib.utilities import *

socket_uri = os.environ.get("SOCKET_URI", None)
assert socket_uri != None

tradeKernelContract = Web3Helper.getContract("TradeKernel.json")

def takeFunds(trade):
  print("Taking funds", trade['state'])
  decrypted = Cryptor.decryptInput(trade['nominalAmount'], trade['sk'])
  price = Cryptor.decryptInput(trade['price'], trade['sk'])

  # Ill need to include the currency here
  amountInvested = int(decrypted.split(':')[1])
  if trade['state'] != 4:
    return {'message': 'Trade is in state {}, requires state 4'.format(trade['state'])}

  # if amountInvested > 0:
  #   # First move the funds from the investors bank account to the brokers account
  #   moved = TL.move_funds(trade['brokerId'], trade['investorId'])
  #   if not moved:
  #     # Need to alert the smart contract that this trade hasn't worked
  #     return {'message': "Funds have not been moved, tokens not distributed"}
  # else:
  #   # Selling the tokens
  #   # First move the funds from the investors bank account to the brokers account
  #   moved = TL.move_funds(trade['investorId'], trade['brokerId'])
  #   if not moved:
  #     # Need to alert the smart contract that this trade hasn't worked
  #     return {'message': "Funds have not been moved, tokens not sold"}

  tx = Web3Helper.transact(
    tradeKernelContract,
    'transferFunds',
    trade['hash'],
  )
  print(tx.hex())

def Trade(app):
  @app.route("/trades", cors=True, methods=["POST"])
  @loggedinMiddleware(app)
  @printError
  def trades_post():

    request = app.current_request
    data = request.json_body

    tradeData = {
      "investorId": data["investorId"],
      "tokenId": data["tokenId"],
      "executionDate": data["executionDate"],
      "expirationTimestampInSec": data["expirationTimestampInSec"],
      "salt": data["salt"]
    }
    trade = Database.find_one("Trade", tradeData)

    if trade: return toObject(trade)

    tradeData['state'] = 0
    Database.insert("Trade", tradeData)
    trade = Database.find_one("Trade", tradeData)
    data['id'] = trade['id']

    for brokerId, ik, ek, nominalAmount in zip(data['brokers'],data['iks'],data['eks'],data['nominalAmounts']):
      tradeBrokerData = {"tradeId": trade['id'],"brokerId": brokerId, "ik": ik, "ek": ek, "nominalAmount": nominalAmount}
      tradeBroker = Database.find_one("TradeBroker", tradeBrokerData)
      if tradeBroker: continue
      tradeBrokerData['state'] = 0
      Database.insert("TradeBroker", tradeBrokerData)
      tradeBroker = Database.find_one("TradeBroker", tradeBrokerData)
    # Socket, should be pushing to a message queue of some kind
    r = passWithoutError(requests.post)(socket_uri + "trade-created", data=data)
    return toObject(trade)

  @app.route("/trades", cors=True, methods=["GET"])
  @loggedinMiddleware(app)
  @printError
  def trades_get():
    request = app.current_request
    trades = []
    tradeBrokers = []
    query = request.query_params or {}
    if 'state' in query:
      query['state'] = int(query['state'])

    page = 0
    page_count = None
    total = None

    if 'page' in query:
      page = int(query['page'])
      del query['page']
    if 'page_count' in query:
      page_count = int(query['page_count'])
      del query['page_count']

    if 'confirmed' in query:
      query['state'] = ('>', 0)
      del query['confirmed']

    if request.user["role"] == "investor":
      query["investorId"] = request.user["id"]
      dbRes = Database.find("Trade", query, page=page, page_count=page_count)
      trades = dbRes['data']
      total = dbRes['total']

    elif request.user["role"] == "broker":
      dbRes = Database.find("TradeBroker", {"brokerId": request.user["id"]}, page=0, page_count=500000000000)
      tradeBrokers = dbRes['data']
      total = dbRes["total"]
      tradeIds = [tradeBroker["tradeId"] for tradeBroker in tradeBrokers]
      for i, tradeId in enumerate(tradeIds):
        _query = copy.copy(query)
        _query["id"] = tradeId
        trade = Database.find_one("Trade", _query)
        if trade:
          if trade["brokerId"] and trade["brokerId"] != request.user["id"]: continue
          trade["tradeBrokers"] = [tradeBrokers[i]]
          trades += [trade]
      if page_count:
        trades = trades[page*page_count: (page+1)*page_count]

    elif request.user["role"] == "issuer":
      # first find all the funds the issuer owns
      funds = Database.find("Fund")
      fundIds = [o['id'] for o in funds]
      tokenQuery = [[('fundId','=',fundId)] for fundId in fundIds]
      tokens = Database.find("Token", tokenQuery)
      tokenIds = [o['id'] for o in tokens]
      tradeQuery = []
      if 'tokenId' in query:
        tokenIds = [t for t in tokenIds if t == int(query['tokenId'])]
      if 'investorId' in query:
        tradeQuery = [[
          ('tokenId','=',tokenId),
          ('investorId','=',query['investorId'])
        ] for tokenId in tokenIds]
      else:
        tradeQuery = [[('tokenId','=',tokenId)] for tokenId in tokenIds]
      print(tradeQuery)
      trades = None

      if page_count:
        dbRes = Database.find("Trade", tradeQuery, page=page, page_count=page_count)
        trades = dbRes['data']
        total = dbRes['total']
      else:
        trades = Database.find("Trade", tradeQuery)

      for trade in trades:
        tradeBrokers = Database.find("TradeBroker", {"tradeId": trade["id"]})
        trade['tradeBrokers'] = tradeBrokers

    tokenIds = list(set([o["tokenId"] for o in trades]))
    tokens = [Database.find_one("Token", {"id": t}) for t in tokenIds]
    tokens = [toObject(t, ["id","address","cutoffTime","symbol","decimals"]) for t in tokens]
    tokens_hash = {token["id"]: token for token in tokens}
    for trade in trades:
      investor = Database.find_one("User", {"id": trade["investorId"]}, ["address", "id","name"])
      trade["investor"] = investor
      trade["token"] = tokens_hash[trade["tokenId"]]
      if request.user["role"] == "investor":
        tradeBrokers = Database.find("TradeBroker", {"tradeId": trade["id"]})
        for tradeBroker in tradeBrokers:
          tradeBroker["broker"] = Database.find_one("User", {"id": tradeBroker["brokerId"]}, ["address", "id","name"])
        trade["tradeBrokers"] = tradeBrokers

    return {"total": total, "data": toObject(trades), "page": page, "page_count": page_count}

  @app.route("/trades/{tradeId}", cors=True, methods=["GET"])
  @loggedinMiddleware(app)
  @printError
  def trades_show(tradeId):
    request = app.current_request
    trade = Database.find_one("Trade", {"id": int(tradeId)})
    if not trade: raise NotFoundError("trade not found with id {}".format(tradeId))
    investor = Database.find_one("User", {"id": trade["investorId"]}, ["address", "id","name"])
    trade["investor"] = investor
    if trade['brokerId']:
      broker = Database.find_one("User", {"id": trade["brokerId"]}, ["address", "id","name"])
      trade["broker"] = broker

    token = Database.find_one("Token", {"id": trade["tokenId"]}, ["id","address","cutoffTime","symbol","decimals"])
    trade["token"] = token

    tradeBrokers = Database.find("TradeBroker", {"tradeId": trade["id"]})
    for ob in tradeBrokers: ob["broker"] = Database.find_one("User", {"id": ob["brokerId"]}, ["address", "id","name"])
    trade["tradeBrokers"] = tradeBrokers
    return toObject(trade)

  @app.route("/trades/{tradeId}", cors=True, methods=["PUT"])
  @loggedinMiddleware(app)
  @printError
  def trades_update(tradeId):
    request = app.current_request
    data = request.json_body
    trade = Database.find_one("Trade", {"id": int(tradeId)})
    if not trade: raise NotFoundError("trade not found with id {}".format(tradeId))

    trade = Database.update("Trade", {"id": int(tradeId)}, data, return_updated=True)[0]
    # Socket, should be pushing to a message queue of some kind
    r = passWithoutError(requests.post)(socket_uri + "trade-update", data=toObject(trade))
    return toObject(trade)

  @app.route("/trades/{tradeId}", cors=True, methods=["DELETE"])
  @loggedinMiddleware(app)
  @printError
  def trades_delete(tradeId):
    request = app.current_request
    data = request.json_body
    trade = Database.find_one("Trade", {"id": int(tradeId)})
    if not trade: raise NotFoundError("trade not found with id {}".format(tradeId))

    trade = Database.update("Trade", {"id": int(tradeId)}, {'state': 3}, return_updated=True)[0]
    # Socket, should be pushing to a message queue of some kind
    r = passWithoutError(requests.post)(socket_uri + "trade-update", data=toObject(trade))
    return toObject(trade)


  @app.route("/trades/{tradeId}/set-price", cors=True, methods=["PUT"])
  @loggedinMiddleware(app)
  @printError
  def trades_show(tradeId):
    request = app.current_request
    data = request.json_body
    trade = Database.find_one("Trade", {"id": int(tradeId)})
    if not trade: raise NotFoundError("trade not found with id {}".format(tradeId))

    tradeBroker = Database.find_one("TradeBroker", {
      "tradeId": trade["id"],
      "brokerId": request.user["id"]
    })
    if not tradeBroker: raise NotFoundError("tradeBroker not found with trade id {}".format(tradeId))
    Database.update("TradeBroker", {"id": tradeBroker["id"]}, {"price": data["price"]})
    # Socket, should be pushing to a message queue of some kind
    r = passWithoutError(requests.post)(socket_uri + "trade-update", data=toObject(trade))
    return toObject(trade)

  @app.route("/trades/{tradeId}/claim", cors=True, methods=["PUT"])
  @loggedinMiddleware(app)
  @printError
  def trades_claim(tradeId):
    trade = Database.find_one("Trade", {"id": int(tradeId)})
    decrypted = Cryptor.decryptInput(trade['nominalAmount'], trade['sk'])
    price = Cryptor.decryptInput(trade['price'], trade['sk'])

    # Ill need to include the currency here
    amountInvested = int(decrypted.split(':')[1])
    if trade['state'] != 5:
      return {'message': 'Trade is in state {}, requires state 5'.format(trade['state'])}

    # get trade dates nav
    nav = Database.find_one("NAVTimestamp", {"tokenId": trade["tokenId"]}, order_by='-createdAt')
    # get todays nav and totalSupply
    token = Database.find_one('Token', {'id': trade['tokenId']})

    totalTokens = int(amountInvested / nav['price'])

    investorTokens = None
    if amountInvested > 0:
      effectiveNAV = (1.0+float(price)/100)*nav['price']
      investorTokens = amountInvested / effectiveNAV
    else:
      investorTokenBalance = Database.find_one("TokenBalance", {"tokenId": token["id"], "userId": investor["id"]})
      if not investorTokenBalance['balance']: investorTokenBalance['balance'] = '0'
      effectiveNAV = (1-float(price)/100)*nav['price']
      investorTokens =  min(int(amountInvested / effectiveNAV), -1 * int(investorTokenBalance['balance']))

    tokenContract = Web3Helper.getContract("ETT.json", token['address'])
    totalSupply = Web3Helper.call(tokenContract,'dateTotalSupply',arrow.get(trade['executionDate']).format('YYYY-MM-DD'),)

    # find number of tokens user allocated
    numberTokens = 0 if not nav['price'] else math.floor(amountInvested * totalSupply / nav['price'])
    investorTokens = int(investorTokens * math.pow(10, token['decimals']))

    # now ask the contract to distribute the tokens (maybe should be the investor that does this)
    investor = Database.find_one("User", {"id": trade["investorId"]})
    tradeKernelContract = Web3Helper.getContract("TradeKernel.json")
    tx = Web3Helper.transact(
      tradeKernelContract,
      'distributeTokens',
      trade['hash'],
      [
        Web3Helper.toChecksumAddress(token['address']),
        Web3Helper.toChecksumAddress(investor['address']),
      ],
      [
        investorTokens
      ]
    )
    print(tx.hex())
    Database.update("Trade", {"id": trade["id"]}, {"state": 6, "numberTokens": numberTokens})
    return {"message": "Tokens distributed"}

  @app.route("/trades/confirmed", cors=True, methods=["PUT"])
  @printError
  def trades_confirmed():
    request = app.current_request
    data = request.json_body
    tradeHash = data['tradeHash']
    broker = Database.find_one("User", {"address": data["broker"]})
    trade = Database.find_one("Trade", {"hash": tradeHash})
    if not trade: raise NotFoundError("trade not found with hash {}".format(tradeHash))

    Database.update("Trade", {"id": trade["id"]}, {"state": 1})
    Database.update("TradeBroker", {"tradeId": trade["id"], "brokerId": broker["id"]}, {"state": 1})

    trade["state"] = 1
    # Socket, should be pushing to a message queue of some kind
    r = passWithoutError(requests.post)(socket_uri + "trade-update", data=toObject(trade))
    return toObject(trade)

  @app.route("/trades/cancel", cors=True, methods=["PUT"])
  @printError
  def trades_cancel():
    request = app.current_request
    data = request.json_body
    tradeHash = data['tradeHash']
    broker = Database.find_one("User", {"address": data["broker"]})
    trade = Database.find_one("Trade", {"hash": tradeHash})
    if not trade: raise NotFoundError("trade not found with hash {}".format(tradeHash))
    state = 3 if data["investor"] == data["canceller"] else 4

    Database.update("Trade", {"id": trade["id"]}, {"state": state})
    Database.update("TradeBroker", {"tradeId": trade["id"], "brokerId": broker["id"]}, {"state": state})

    trade["state"] = state
    # Socket, should be pushing to a message queue of some kind
    r = passWithoutError(requests.post)(socket_uri + "trade-update", data=toObject(trade))
    return toObject(trade)

  @app.route("/trades/funds-transfered", cors=True, methods=["PUT"])
  @printError
  def trades_funds_transfered():
    request = app.current_request
    data = request.json_body
    tradeHash = data['tradeHash']
    trade = Database.update("Trade", {"hash": tradeHash}, {'state': 5})
    return toObject(trade)
