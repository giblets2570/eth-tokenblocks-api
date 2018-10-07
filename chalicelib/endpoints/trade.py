import jwt, os, json, requests, math, arrow
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

    # Socket
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
      query['state'] = ('>=', 1)
      del query['confirmed']

    if request.user["role"] == "investor":
      query["investorId"] = request.user["id"]
      dbRes = Database.find("Trade", query, page=page, page_count=page_count)
      trades = dbRes['data']
      total = dbRes['total']

    elif request.user["role"] == "broker":
      dbRes = Database.find("TradeBroker", {"brokerId": request.user["id"]}, page=page, page_count=page_count)
      tradeBrokers = dbRes['data']
      total = dbRes["total"]
      tradeIds = [tradeBroker["tradeId"] for tradeBroker in tradeBrokers]
      for i, tradeId in enumerate(tradeIds):
        query["id"] = tradeId
        trade = Database.find_one("Trade", query)
        if trade:
          if trade["brokerId"] and trade["brokerId"] != request.user["id"]: continue          
          trade["tradeBrokers"] = [tradeBrokers[i]]
          trades += [trade]

    tokenIds = list(set([o["tokenId"] for o in trades]))
    tokens = [Database.find_one("Token", {"id": t}) for t in tokenIds]
    tokens = [toObject(t, ["id","address","cutoffTime","symbol","name","decimals"]) for t in tokens]
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
    
    token = Database.find_one("Token", {"id": trade["tokenId"]}, ["id","address","cutoffTime","symbol","name","decimals"])
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
    # Socket
    r = passWithoutError(requests.post)(socket_uri + "trade-update", data={"id": trade["id"]})
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
    # Socket
    r = passWithoutError(requests.post)(socket_uri + "trade-update", data={"id": trade["id"]})
    return toObject(trade)


  @app.route("/trades/{tradeId}/set-price", cors=True, methods=["PUT"])
  @loggedinMiddleware(app)
  @printError
  def trades_show(tradeId):
    request = app.current_request
    data = request.json_body
    trade = Database.find_one("Trade", {"id": int(tradeId)})
    if not trade: raise NotFoundError("trade not found with id {}".format(tradeId))
    tradeBroker = Database.find_one("TradeBroker", {"tradeId": trade["id"], "brokerId": request.user["id"]})
    if not tradeBroker: raise NotFoundError("tradeBroker not found with trade id {}".format(tradeId))
    Database.update("TradeBroker", {"id": tradeBroker["id"]}, {"price": data["price"]})
    # Socket
    r = passWithoutError(requests.post)(socket_uri + "trade-update", data={"id": trade["id"]})
    return toObject(trade)

  @app.route("/trades/{tradeId}/claim", cors=True, methods=["PUT"])
  @printError
  def trades_claim(tradeId):
    trade = Database.find_one("Trade", {"id": int(tradeId)})
    decrypted = Cryptor.decryptInput(trade['nominalAmount'], trade['sk'])
    # Ill need to include the currency here
    amountInvested = int(float(decrypted.split(':')[1])*100)
    if trade['state'] != 2:
      return {'message': 'Trade is in state {}, requires state 2'.format(trade['state'])}

    # First move the funds from the investors bank account to the brokers account
    moved = TL.move_funds(trade['brokerId'], trade['investorId'])

    if not moved:
      # Need to alert the smart contract that this trade hasn't worked
      return {'message': "Funds have not been moved, tokens not distributed"}
    
    # get todays nav and totalSupply
    token = Database.find_one('Token', {'id': trade['tokenId']})
    navTimestamp = Database.find_one('NavTimestamp', {"executionDate": trade['executionDate'], "tokenId": trade["tokenId"]})
    tokenContract = Web3Helper.getContract("ETT.json", token['address'])
    totalSupply = Web3Helper.call(tokenContract,'dateTotalSupply',arrow.get(trade['executionDate']).format('YYYY-MM-DD'),)

    # find number of tokens user allocated
    numberTokens = 0 if not navTimestamp['value'] else math.floor(amountInvested * totalSupply / navTimestamp['value'])

    # now ask the contract to distribute the tokens (maybe should be the investor that does this)
    investor = Database.find_one("User", {"id": trade["investorId"]})
    tradeKernelContract = Web3Helper.getContract("TradeKernel.json")
    Web3Helper.transact(
      tradeKernelContract,
      'distributeTokens',
      trade['hash'], 
      Web3Helper.toChecksumAddress(investor['address']), 
      Web3Helper.toChecksumAddress(token['address']), 
      numberTokens,
    )

    Database.update("Trade", {"id": trade["id"]}, {"state": 5, "numberTokens": numberTokens})
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

    # Socket
    r = passWithoutError(requests.post)(socket_uri + "trade-update", data={"id": trade["id"]})
    trade["state"] = 1
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

    # Socket
    r = passWithoutError(requests.post)(socket_uri + "trade-update", data={"id": trade["id"]})
    trade["state"] = state
    return toObject(trade) 
