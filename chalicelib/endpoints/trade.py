from chalicelib.database import Database
from datetime import datetime, date
from chalice import NotFoundError, ForbiddenError
import jwt, os, json, requests
from chalicelib.utilities import loggedin_middleware, to_object, print_error

socket_uri = os.environ.get("SOCKET_URI", None)
assert socket_uri != None

def passWithoutError(func):
  def inner(*args, **kwargs):
    try:
      func(*args,**kwargs)
    except Exception as e:
      pass
  return inner

def Trade(app):
  @app.route("/trades", cors=True, methods=["POST"])
  @print_error
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

    if trade: return to_object(trade)
    
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
    return to_object(trade)

  @app.route("/trades", cors=True, methods=["GET"])
  @loggedin_middleware(app)
  @print_error
  def trades_get():
    request = app.current_request
    trades = []
    tradeBrokers = []
    query = request.query_params or {}
    page = 0
    page_count = None
    
    if 'page' in query:
      page = query['page']
      del query['page']
    if 'page_count' in query:
      page_count = query['page_count']
      del query['page_count']

    if request.user["role"] == "investor":
      query["investorId"] = request.user["id"]
      trades = Database.find("Trade", query, page=page, page_count=page_count)
    elif request.user["role"] == "broker":
      tradeBrokers = Database.find("TradeBroker", {"brokerId": request.user["id"]}, page=page, page_count=page_count)
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
    tokens = [to_object(t, ["id","address","cutoffTime","symbol","name","decimals"]) for t in tokens]
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

    return to_object(trades)

  @app.route("/trades/{tradeId}", cors=True, methods=["GET"])
  @loggedin_middleware(app)
  @print_error
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
    return to_object(trade)

  @app.route("/trades/{tradeId}", cors=True, methods=["PUT"])
  @loggedin_middleware(app)
  @print_error
  def trades_update(tradeId):
    request = app.current_request
    data = request.json_body
    trade = Database.find_one("Trade", {"id": int(tradeId)})
    if not trade: raise NotFoundError("trade not found with id {}".format(tradeId))

    Database.update("Trade", {"id": int(tradeId)}, data)
    trade = Database.find_one("Trade", {"id": int(tradeId)})
    # Socket
    r = passWithoutError(requests.post)(socket_uri + "trade-update", data={"id": trade["id"]})
    return to_object(trade)


  @app.route("/trades/{tradeId}/set-price", cors=True, methods=["PUT"])
  @loggedin_middleware(app)
  @print_error
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
    return to_object(trade)

  @app.route("/trades/confirmed", cors=True, methods=["PUT"])
  @print_error
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
    return to_object(trade)


