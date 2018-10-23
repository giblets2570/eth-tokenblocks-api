from chalicelib.database import Database
from datetime import datetime
from chalice import NotFoundError, ForbiddenError
from chalicelib.utilities import *
from chalicelib.web3helper import Web3Helper
from chalicelib.endpoints.token import createToken, getBalances
import jwt, os, json, arrow, math, hashlib

def Fund(app):

  @app.route("/funds", cors=True, methods=["POST"])
  @loggedinMiddleware(app)
  @printError
  def funds_post():
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

    fund_data = {
      "name": data["name"]
    }

    fund = Database.find_one('Fund', fund_data, insert=True)

    for token in data["tokens"]:
      token_data = {
        "name": data["name"],
        "fundId": fund["id"],
        "decimals": token["decimals"],
        "symbol": token["symbol"],
        "cutoffTime": int(token["cutoffTime"]),
        "fee": int(token["fee"]),
        "ownerId": ownerId,
        "currency": token["currency"],
        "initialAmount": token["initialAmount"],
        "incomeCategory": token["incomeCategory"],
        "minimumOrder": token["minimumOrder"]
      }
      if "holdings" in token: token_data["holdings"] = token["holdings"]
      token = createToken(token_data)
      print(token)

    return toObject(fund)

  @app.route("/funds", cors=True, methods=["GET"])
  @printError
  def funds_get():
    request = app.current_request
    funds = Database.find("Fund")
    funds = [toObject(u) for u in funds]
    return funds

  @app.route("/funds/{fundId}", cors=True, methods=["GET"])
  @printError
  def token_get(fundId):
    request = app.current_request
    fund = Database.find_one("Fund", {"id": int(fundId)})
    if not fund: raise NotFoundError("fund not found with id {}".format(fundId))
    tokens = Database.find("Token", {"fundId": fund["id"]})
    fund["tokens"] = toObject(tokens)
    for token in fund["tokens"]:
      tokenHoldings = Database.find_one("TokenHoldings", {"tokenId": token["id"]})
      tokenHoldingsList = Database.find("TokenHolding", {"tokenHoldingsId": tokenHoldings["id"]})
      for tokenHolding in tokenHoldingsList:
        tokenHolding['security'] = toObject(Database.find_one('Security', {'id': tokenHolding["securityId"]}))
        tokenHolding['securityTimestamp'] = toObject(Database.find_one('SecurityTimestamp', {'securityId': tokenHolding["securityId"]}, order_by='-createdAt'))
      token['holdings'] = toObject(tokenHoldingsList)
    return toObject(fund)

  @app.route("/funds/{fundId}/balances", cors=True, methods=["GET"])
  @printError
  def fund_balances(fundId):
    request = app.current_request
    fund = Database.find_one("Fund", {"id": int(fundId)})
    if not fund: raise NotFoundError("fund not found with id {}".format(fundId))
    tokens = Database.find("Token", {"fundId": fund["id"]})
    token_balances = []
    for token in tokens:
      token_balances += getBalances(token["id"])
    user_hash = {}
    total_balance = []
    for token_balance in token_balances:
      if not token_balance['balance']: continue
      id = token_balance['investor']['id']
      if id in user_hash:
        print(total_balance[user_hash[id]]['balance'], token_balance['balance'])
        total_balance[user_hash[id]]['balance'] = int(total_balance[user_hash[id]]['balance'])
        total_balance[user_hash[id]]['balance'] += int(token_balance['balance'])
        total_balance[user_hash[id]]['balance'] = str(total_balance[user_hash[id]]['balance'])
        print(total_balance[user_hash[id]]['balance'])
      else:
        index = len(total_balance)
        user_hash[id] = index
        total_balance.append(token_balance)

    return toObject(total_balance)
