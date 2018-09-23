import arrow, math
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
    if 'single' in query:
      del query['single']
      single = True
      order = Database.find_one("Order", query)
      if not order: raise NotFoundError("No order found")
      orders = [order]
    else:
      orders = Database.find("Order", query)

    for order in orders:
      order["broker"] = Database.find_one("User", {"id": order["brokerId"]}, ['id','name','email','address'])
      order["token"] = toObject(Database.find_one("Token", {"id": order["tokenId"]}))
      order["orderHoldings"] = Database.find("OrderHolding", {"orderId": order["id"]})

      for orderHolding in order["orderHoldings"]:
        orderHolding["security"] = toObject(Database.find_one("Security", {"id": orderHolding["securityId"]}))

      order["orderTrades"] = Database.find("OrderTrade", {"orderId": order["id"]})
      for orderTrade in order["orderTrades"]:
        orderTrade["trade"] = toObject(Database.find_one("Trade", {"id": orderTrade["tradeId"]}))

    if single: return toObject(orders[0])
    return [toObject(t) for t in orders]

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
      orderHolding = Database.insert("OrderHolding", orderHolding)

    for trade in trades:
      Database.update("Trade", {"id": trade["id"]},{"sk": trade["sk"]})
      orderTrade = {
        "orderId": order["id"],
        "tradeId": trade["id"]
      }
      orderTrade = Database.insert("OrderTrade", orderTrade)

    return toObject(order)

  @app.route('/orders/complete', cors=True, methods=['PUT'])
  @printError
  def orders_complete():
    request = app.current_request
    data = request.json_body
    order = Database.find_one("Order", {"hash": data["orderHash"]})

    # set state to complete
    Database.update("Order", {"id": order["id"]}, {"state": 1})

    # Here I need to check if all orders are complete for the day
    incompleteOrders = Database.find("Order", {"state": 0})
    if len(incompleteOrders): 
      # There are still orders waiting to complete
      print("There are still orders waiting to complete")
      return {"message": "Order completed"}

    executionDate = order["executionDate"]
    # find the token
    token = Database.find_one("Token", {"id": order["tokenId"]})
    # Here I need to calculate the NAV of the fund
    navTimestamp = Database.find_one('NavTimestamp', {"executionDate": executionDate})

    # if nav already calculated today
    if navTimestamp: 
      print("Already calculated")
      return {"message": "Already calculated"}

    # get yesterdays nav and totalSupply
    yesterdaysExecutionDate = arrow.get(executionDate).shift(days=-1).format('YYYY-MM-DD')
    yesterdaysNavTimestamp = Database.find_one('NavTimestamp', {"executionDate": yesterdaysExecutionDate, "tokenId": order["tokenId"]}, insert=True)
    yesterdaysValue = yesterdaysNavTimestamp['value']

    ######################################################
    # lets just set this to £1,000,000 for now
    ######################################################
    valueWithoutHoldingsUpdate = 100000000
    valueOfNewHoldings = 25000
    newNav = valueWithoutHoldingsUpdate + valueOfNewHoldings
    Database.insert('NavTimestamp', {"executionDate": executionDate, "tokenId": order["tokenId"], "value": newNav})

    # create the new tokens
    executionDateString = arrow.get(executionDate).format('YYYY-MM-DD')
    token_contract = Web3Helper.getContract("ETT.json", token['address'])
    totalSupply = Web3Helper.call(token_contract,'totalSupply',)
    tokensSupplyChange = math.floor(totalSupply * valueOfNewHoldings / valueWithoutHoldingsUpdate)
    tx = Web3Helper.transact(token_contract, 'updateTotalSupply', tokensSupplyChange, executionDateString)
    tx = Web3Helper.transact(token_contract, 'updateNAV', newNav, executionDateString)

    print("Order completed and created new tokens")
    return {"message": "Order completed and created new tokens"}
