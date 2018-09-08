from chalicelib.database import Database
from datetime import datetime
from chalice import NotFoundError, ForbiddenError
from web3 import Web3
from utilities import loggedin_middleware, to_object, print_error

def Order(app):

  @app.route('/orders', cors=True, methods=['GET'])
  # @loggedin_middleware
  @print_error
  def orders_get():
    request = app.current_request
    query = request.query_params or {}
    single = False
    orders = []
    if 'single' in query:
      del query['single']
      single = True
      orders = [Database.find_one("Order", query)]
    else:
      orders = Database.find("Order", query)
    for order in orders:
      order["token"] = to_object(Database.find_one("Token", {"id": order["tokenId"]}))
      order["orderHoldings"] = Database.find("OrderHolding", {"orderId": order["id"]})

      for orderHolding in order["orderHoldings"]:
        orderHolding["security"] = to_object(Database.find_one("Security", {"id": orderHolding["securityId"]}))

      order["orderTrades"] = Database.find("OrderTrade", {"orderId": order["id"]})
      for orderTrade in order["orderTrades"]:
        orderTrade["trade"] = to_object(Database.find_one("Trade", {"id": orderTrade["tradeId"]}))

    if single: return to_object(orders[0])
    return [to_object(t) for t in orders]

  @app.route('/orders', cors=True, methods=['POST'])
  @loggedin_middleware(app, 'broker')
  @print_error
  def orders_post():
    request = app.current_request
    data = request.json_body
    executions = data['executions']
    trades = data['trades']
    order = {
      "brokerId": request.user["id"],
      "signature": data["signature"],
      "tokenId": data["token"],
      "executionDate": data["executionDate"],
      "verified": False
    }

    order = Database.insert("Order", order)
    for execution in executions:
      security = Database.find_one("Security", {"symbol": execution["symbol"]}, insert=True)
      amount = 1 if execution["direction"] == "Buy" else -1
      amount *= int(execution["amount"])
      orderHolding = {
        "securityId": security["id"],
        "orderId": order["id"],
        "amount": amount,
        "cost": int(execution["cost"])
      }
      orderHolding = Database.insert("OrderHolding", orderHolding)

    for trade in trades:
      orderTrade = {
        "orderId": order["id"],
        "tradeId": trade["id"]
      }
      orderTrade = Database.insert("OrderTrade", orderTrade)

    return to_object(order)
