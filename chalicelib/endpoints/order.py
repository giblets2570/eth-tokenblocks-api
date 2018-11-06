import arrow, math, random
from chalicelib.database import Database
from datetime import datetime
from chalice import NotFoundError, ForbiddenError
from chalicelib.utilities import *
from chalicelib.web3helper import Web3Helper

trade_kernel_contract = Web3Helper.getContract("TradeKernel.json")

def Order(app):

  @app.route('/orders', cors=True, methods=['GET'])
  @loggedinMiddleware(app)
  @printError
  def orders_get():
    request = app.current_request
    query = request.query_params or {}
    single = False
    orders = []
    total = None

    if 'page' in query:
      page = int(query['page'])
      del query['page']
    if 'page_count' in query:
      page_count = int(query['page_count'])
      del query['page_count']

    if 'single' in query:
      del query['single']
      single = True
      order = Database.find_one("Order", query)
      if not order: raise NotFoundError("No order found")
      orders = [order]
    else:
      dbRes = Database.find("Order", query, page=page, page_count=page_count)
      orders = dbRes['data']
      total = dbRes['total']


    for order in orders:
      order["broker"] = Database.find_one("User", {"id": order["brokerId"]}, ['id','name','email','address'])
      order["token"] = toObject(Database.find_one("Token", {"id": order["tokenId"]}))
      order["orderHoldings"] = Database.find("OrderHolding", {"orderId": order["id"]})

      for orderHolding in order["orderHoldings"]:
        orderHolding["security"] = toObject(Database.find_one("Security", {"id": orderHolding["securityId"]}))

      order["orderTrades"] = Database.find("OrderTrade", {"orderId": order["id"]})
      for orderTrade in order["orderTrades"]:
        orderTrade["trade"] = toObject(Database.find_one("Trade", {"id": orderTrade["tradeId"]}))

    if single:
      return toObject(orders[0])

    return {"data": toObject(orders), "total": total}

  @app.route('/orders', cors=True, methods=['POST'])
  @loggedinMiddleware(app, 'broker')
  @printError
  def orders_post():
    request = app.current_request
    data = request.json_body
    trades = data['trades']
    order = {
      "brokerId": request.user["id"],
      "signature": data["signature"],
      "tokenId": data["token"],
      "salt": data["salt"],
      "amount": data["amount"],
      "executionDate": data["executionDate"],
      "hash": data["hash"],
      "state": 0
    }

    order = Database.insert("Order", order)
    for orderHolding in data['orderHoldings']:
      security = Database.find_one("Security", {"id": orderHolding["securityId"]}, insert=True)
      amount = 1 if orderHolding["direction"] == "Buy" else -1
      amount *= int(orderHolding["amount"])
      orderHolding = {
        "securityId": security["id"],
        "orderId": order["id"],
        "amount": amount,
        "cost": int(orderHolding["cost"]) if "cost" in orderHolding else 0
      }
      orderHolding = Database.insert("OrderHolding", orderHolding, return_inserted=True)

    for trade in trades:
      Database.update("Trade", {"id": trade["id"]},{"sk": trade["sk"]})
      orderTrade = {
        "orderId": order["id"],
        "tradeId": trade["id"]
      }
      orderTrade = Database.insert("OrderTrade", orderTrade, return_inserted=True)

    return toObject(order)

  @app.route('/orders/{orderId}', cors=True, methods=['GET'])
  @loggedinMiddleware(app)
  @printError
  def orders_show(orderId):
    order = Database.find_one("Order", {"id": orderId})

    order["broker"] = Database.find_one("User", {"id": order["brokerId"]}, ['id','name','email','address'])
    order["token"] = toObject(Database.find_one("Token", {"id": order["tokenId"]}))
    order["orderHoldings"] = Database.find("OrderHolding", {"orderId": order["id"]})

    for orderHolding in order["orderHoldings"]:
      orderHolding["security"] = toObject(Database.find_one("Security", {"id": orderHolding["securityId"]}))

    order["orderTrades"] = Database.find("OrderTrade", {"orderId": order["id"]})
    for orderTrade in order["orderTrades"]:
      orderTrade["trade"] = toObject(Database.find_one("Trade", {"id": orderTrade["tradeId"]}))

    return toObject(order)


  @app.route('/orders/complete', cors=True, methods=['PUT'])
  @printError
  def orders_complete():
    request = app.current_request
    data = request.json_body
    order = Database.find_one("Order", {"hash": data["orderHash"]})

    # set order state to complete
    Database.update("Order", {"id": order["id"]}, {"state": 1})

    # set state to all trade as verified
    orderTrades = Database.find("OrderTrade", {"orderId": order["id"]})
    tradeIds = [o['tradeId'] for o in orderTrades]
    tradeQuery = [[('id','=',tradeId)] for tradeId in tradeIds]
    Database.update("Trade", tradeQuery, {'state': 2})

    # Here I need to check if all orders are complete for the day
    executionDate = order["executionDate"]
    incompleteOrders = Database.find("Order", {"state": 0, "executionDate": executionDate, "tokenId": order["tokenId"]})
    if len(incompleteOrders):
      # There are still orders waiting to complete
      print("There are still orders waiting to complete")
      return {"message": "Order completed"}

    # Here I need to calculate the AUM
    # find the token
    token = Database.find_one("Token", {"id": order["tokenId"]})
    print(token['address'])
    tokenContract = Web3Helper.getContract("ETT.json", token['address'])

    tokenHoldingsObject = Database.find_one("TokenHoldings", {"tokenId": token["id"]})
    tokenHoldings = Database.find("TokenHolding", {"tokenHoldingsId": tokenHoldingsObject["id"]})

    newAUM = 0
    for tokenHolding in tokenHoldings:
      securityTimestamp = Database.find_one('SecurityTimestamp', {'securityId': tokenHolding["securityId"]}, order_by='-createdAt')
      newAUM += securityTimestamp['price'] * tokenHolding['securityAmount']

    executionDateString = arrow.get(executionDate).format('YYYY-MM-DD')

    tx = Web3Helper.transact(tokenContract, 'endOfDay', executionDateString)
    # tx = b''
    print({"message": "AUM updated", "AUM": newAUM, "hash": tx.hex()})
    return {"message": "AUM updated", "AUM": newAUM, "hash": tx.hex()}
