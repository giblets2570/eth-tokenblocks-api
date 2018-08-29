from database import Database
from datetime import datetime, date
from chalice import NotFoundError, ForbiddenError
from web3 import Web3
import jwt, os, json, requests
from utilities import loggedin_middleware, to_object, print_error

contract_folder = os.environ.get("CONTRACT_FOLDER", None)
assert contract_folder != None
socket_uri = os.environ.get("SOCKET_URI", None)
assert socket_uri != None
web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

with open(contract_folder + "CreateOrder.json") as file:
  createOrder_contractAbi = json.loads(file.read())["abi"]

def Order(app):
  @app.route("/orders", cors=True, methods=["POST"])
  @print_error
  def orders_post():

    request = app.current_request
    data = request.json_body
    orderData = {
      "investorId": data["investorId"],
      "tokenId": data["tokenId"],
      "executionDate": data["executionDate"],
      "expirationTimestampInSec": data["expirationTimestampInSec"],
      "salt": data["salt"]
    }
    order = Database.find_one("Order", orderData)

    if order:
      return to_object(order, [
        "id""investorId","brokerId","tokenId",
        "ik","ek","nominalAmount","price","executionDate",
        "expirationTimestampInSec","salt","state"
      ])
    
    orderData['state'] = 0
    Database.insert("Order", orderData)
    order = Database.find_one("Order", orderData)

    data['id'] = order['id']

    r = requests.post(socket_uri + "order-created", data=data)

    for brokerId, ik, ek, nominalAmount in zip(data['brokers'],data['iks'],data['eks'],data['nominalAmounts']):
      orderBrokerData = {"orderId": order['id'],"brokerId": brokerId, "ik": ik, "ek": ek, "nominalAmount": nominalAmount}
      orderBroker = Database.find_one("OrderBroker", orderBrokerData)
      if orderBroker: continue
      orderBrokerData['state'] = 0
      Database.insert("OrderBroker", orderBrokerData)
      orderBroker = Database.find_one("OrderBroker", orderBrokerData)
    return to_object(order, [
      "id","investorId","brokerId","tokenId",
      "ik","ek","nominalAmount","price","executionDate",
      "expirationTimestampInSec","salt","state"
    ])

  @app.route("/orders", cors=True, methods=["GET"])
  @loggedin_middleware(app)
  @print_error
  def orders_get():
    request = app.current_request
    orders = []
    orderBrokers = []
    query = request.query_params or {}
    if request.user["role"] == "investor":
      query["investorId"] = request.user["id"]
      orders = Database.find("Order", query)
    elif request.user["role"] == "broker":
      orderBrokers = Database.find("OrderBroker", {"brokerId": request.user["id"]})
      orderIds = [orderBroker["orderId"] for orderBroker in orderBrokers]
      for i, orderId in enumerate(orderIds):
        query["id"] = orderId
        order = Database.find_one("Order", query)
        if order:
          if order["brokerId"] and order["brokerId"] != request.user["id"]: continue          
          order["orderBrokers"] = [orderBrokers[i]]
          orders += [order]

    tokenIds = list(set([o["tokenId"] for o in orders]))
    tokens = [Database.find_one("Token", {"id": t}) for t in tokenIds]
    tokens = [to_object(t, ["id","address","cutoffTime","symbol","name","decimals"]) for t in tokens]
    tokens_hash = {token["id"]: token for token in tokens}
    for order in orders:
      investor = Database.find_one("User", {"id": order["investorId"]}, ["address", "id","name"])
      order["investor"] = investor
      order["token"] = tokens_hash[order["tokenId"]]
      if request.user["role"] == "investor":
        orderBrokers = Database.find("OrderBroker", {"orderId": order["id"]})
        for orderBroker in orderBrokers:
          orderBroker["broker"] = Database.find_one("User", {"id": orderBroker["brokerId"]}, ["address", "id","name"])
        order["orderBrokers"] = orderBrokers

    orders = [to_object(u, ["id","investorId","createdAt","token","orderBrokers","investor","executionDate","expirationTimestampInSec","salt","state"]) for u in orders]
    return orders

  @app.route("/orders/{orderId}", cors=True, methods=["GET"])
  @loggedin_middleware(app)
  @print_error
  def orders_show(orderId):
    request = app.current_request
    data = request.json_body
    order = Database.find_one("Order", {"id": int(orderId)})
    if not order: raise NotFoundError("order not found with id {}".format(orderId))
    investor = Database.find_one("User", {"id": order["investorId"]}, ["address", "id","name"])
    order["investor"] = investor
    
    token = Database.find_one("Token", {"id": order["tokenId"]}, ["id","address","cutoffTime","symbol","name","decimals"])
    order["token"] = token

    orderBrokers = Database.find("OrderBroker", {"orderId": order["id"]})
    for ob in orderBrokers: ob["broker"] = Database.find_one("User", {"id": ob["brokerId"]}, ["address", "id","name"])
    order["orderBrokers"] = orderBrokers
    order = to_object(order, ["id","investorId","createdAt","token","orderBrokers","investor","executionDate","expirationTimestampInSec","salt","state"])
    return order

  @app.route("/orders/{orderId}/set-price", cors=True, methods=["PUT"])
  @loggedin_middleware(app)
  @print_error
  def orders_show(orderId):
    request = app.current_request
    data = request.json_body
    order = Database.find_one("Order", {"id": int(orderId)})
    if not order: raise NotFoundError("order not found with id {}".format(orderId))
    orderBroker = Database.find_one("OrderBroker", {"orderId": order["id"], "brokerId": request.user["id"]})
    if not orderBroker: raise NotFoundError("orderBroker not found with order id {}".format(orderId))
    Database.update("OrderBroker", {"id": orderBroker["id"]}, {"price": data["price"]})
    order = to_object(order, ["id","investorId","createdAt","tokenId","investorId","executionDate","expirationTimestampInSec","salt","state"])
    return order
