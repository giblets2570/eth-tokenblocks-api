from database import Database
from datetime import datetime
from chalice import NotFoundError, ForbiddenError
from web3 import Web3
from utilities import loggedin_middleware, to_object, print_error

def Trade(app):

  @app.route('/trades', cors=True, methods=['GET'])
  # @loggedin_middleware
  @print_error
  def trades_get():
    request = app.current_request
    query = request.query_params or {}
    trades = Database.find("Trade", query)
    for trade in trades:
      trade["token"] = to_object(Database.find_one("Token", {"id": trade["tokenId"]}))
      trade["tradeHoldings"] = Database.find("TradeHolding", {"tradeId": trade["id"]})
      for tradeHolding in trade["tradeHoldings"]:
        tradeHolding["security"] = to_object(Database.find_one("Security", {"id": tradeHolding["securityId"]}))
      trade["tradeOrders"] = Database.find("TradeOrder", {"tradeId": trade["id"]})
      for tradeOrder in trade["tradeOrders"]:
        tradeOrder["order"] = to_object(Database.find_one("Order", {"id": tradeOrder["orderId"]}))

    return [to_object(t) for t in trades]

  @app.route('/trades', cors=True, methods=['POST'])
  @loggedin_middleware(app, 'broker')
  @print_error
  def trades_post():
    request = app.current_request
    data = request.json_body
    executions = data['executions']
    orders = data['orders']
    trade = {
      "brokerId": request.user["id"],
      "signature": data["signature"],
      "tokenId": data["token"],
      "executionDate": data["executionDate"],
      "verified": False
    }

    trade = Database.insert("Trade", trade)
    for execution in executions:
      security = Database.find_one("Security", {"symbol": execution["symbol"]}, insert=True)
      amount = 1 if execution["direction"] == "Buy" else -1
      amount *= int(execution["amount"])
      tradeHolding = {
        "securityId": security["id"],
        "tradeId": trade["id"],
        "amount": amount,
        "cost": int(execution["cost"])
      }
      tradeHolding = Database.insert("TradeHolding", tradeHolding)

    for order in orders:
      tradeOrder = {
        "orderId": order["id"],
        "tradeId": trade["id"]
      }
      tradeOrder = Database.insert("TradeOrder", tradeOrder)

    return to_object(trade)
