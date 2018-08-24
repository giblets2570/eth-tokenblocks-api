from database import Database
from datetime import datetime, date
from chalice import NotFoundError, ForbiddenError
from web3 import Web3
import jwt, os, json
from utilities import loggedin_middleware, to_object

contract_folder = os.environ.get("CONTRACT_FOLDER", None)
assert contract_folder != None
web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

with open(contract_folder + "CreateOrder.json") as file:
  create_order_contract_abi = json.loads(file.read())["abi"]

def Order(app):
  @app.route("/orders", cors=True, methods=["POST"])
  def orders_post():
    request = app.current_request
    data = request.json_body
    investor = Database.find_one("User", {"address": Web3.toChecksumAddress(data["investor"])})
    token = Database.find_one("Token", {"create_order_address": Web3.toChecksumAddress(data["createOrderAddress"])})
    print(data)
    print(date.fromtimestamp(int(data["executionDate"])))
    order_data = {
      "create_order_address": Web3.toChecksumAddress(data["createOrderAddress"]),
      "execution_date": date.fromtimestamp(int(data["executionDate"])),
      "order_index": int(data["index"]), "investor_id": investor["id"],
      "token_id": token["id"], "state": 0
    }
    order = Database.find_one("Order", order_data)
    if not order:
      Database.insert("Order", order_data)
      order = Database.find_one("Order", order_data)

    create_order_contract = web3.eth.contract(
      address=Web3.toChecksumAddress(order["create_order_address"]),
      abi=create_order_contract_abi
    )

    order_brokers = []
    for _broker in data["brokers"]:
      broker = Database.find_one("User", {"address": Web3.toChecksumAddress(_broker)})
      order_brokers.append(broker["id"])
      order_broker_data = {
        "order_id": order["id"],
        "broker_id": broker["id"]
      }
      order_broker = Database.find_one("OrderBroker", order_broker_data)
      if not order_broker:
        Database.insert("OrderBroker", order_broker_data)
        order_broker = Database.find_one("OrderBroker", order_broker_data)
      
      order_broker_contract = create_order_contract.functions.getOrderBrokers(
        order["order_index"],
        Web3.toChecksumAddress(_broker)
      ).call({
        "from": web3.eth.accounts[0]
      })
      
      order_broker_contract = {
        "amount": order_broker_contract[3].hex(),
        "ik": "04"+order_broker_contract[4].hex()+order_broker_contract[5].hex(),
        "ek": "04"+order_broker_contract[6].hex()+order_broker_contract[7].hex(),
        "price": order_broker_contract[8].hex(),
        "state": order_broker_contract[9]
      }
      
      Database.update("OrderBroker", {"id": order_broker["id"]}, order_broker_contract)

    order = to_object(order, ["id","create_order_address","token_id","order_index","investor_id","created_at","state"])
    order["brokers"] = order_brokers
    return order

  @app.route("/orders", cors=True, methods=["GET"])
  @loggedin_middleware(app)
  def orders_get():
    request = app.current_request
    orders = []
    order_brokers = []
    query = request.query_params or {}
    if request.user["role"] == "investor":
      query["investor_id"] = request.user["id"]
      orders = Database.find("Order", query)
    elif request.user["role"] == "broker":
      order_brokers = Database.find("OrderBroker", {"broker_id": request.user["id"]})
      order_ids = [order_broker["order_id"] for order_broker in order_brokers]
      for i, order_id in enumerate(order_ids):
        query["id"] = order_id
        order = Database.find_one("Order", query)
        if order:
          if order["broker_id"] and order["broker_id"] != request.user["id"]: continue          
          order["order_brokers"] = [order_brokers[i]]
          orders += [order]

    token_ids = list(set([o["token_id"] for o in orders]))
    tokens = [Database.find_one("Token", {"id": t}) for t in token_ids]
    tokens = [to_object(t, ["id","create_order_address","address","cutoff_time","symbol","name","decimals"]) for t in tokens]
    tokens_hash = {token["id"]: token for token in tokens}
    for order in orders:
      investor = Database.find_one("User", {"id": order["investor_id"]}, ["address", "id","name"])
      order["investor"] = investor
      order["token"] = tokens_hash[order["token_id"]]
      if request.user["role"] == "investor":
        order_brokers = Database.find("OrderBroker", {"order_id": order["id"]})
        for order_broker in order_brokers:
          order_broker["broker"] = Database.find_one("User", {"id": order_broker["broker_id"]}, ["address", "id","name"])
        order["order_brokers"] = order_brokers

    orders = [to_object(u, ["id","create_order_address","order_index","investor_id","created_at","state","token","order_brokers","investor","execution_date"]) for u in orders]
    return orders

  @app.route("/orders/{order_id}", cors=True, methods=["GET"])
  @loggedin_middleware(app)
  def orders_show(order_id):
    request = app.current_request
    data = request.json_body
    order = Database.find_one("Order", {"id": int(order_id)})
    if not order: raise NotFoundError("order not found with id {}".format(order_id))
    investor = Database.find_one("User", {"id": order["investor_id"]}, ["address", "id","name"])
    order["investor"] = investor
    
    token = Database.find_one("Token", {"id": order["token_id"]}, ["id","create_order_address","address","cutoff_time","symbol","name","decimals"])
    order["token"] = token

    order_brokers = Database.find("OrderBroker", {"order_id": order["id"]})
    for ob in order_brokers: ob["broker"] = Database.find_one("User", {"id": ob["broker_id"]}, ["address", "id","name"])
    order["order_brokers"] = order_brokers
    order = to_object(order, ["id","create_order_address","order_index","investor_id","created_at","state","token","order_brokers","investor","execution_date"])
    return order

  @app.route("/orders/{order_index}/set-price", cors=True, methods=["PUT"])
  def orders_update_state(order_index):
    request = app.current_request
    data = request.json_body
    token = Database.find_one(
      "Token", 
      {"create_order_address": Web3.toChecksumAddress(data["createOrderAddress"])}
    )
    order = Database.find_one(
      "Order", 
      {"order_index": int(order_index), "token_id": token["id"]}
    )
    broker = Database.find_one(
      "User",
      {"address": Web3.toChecksumAddress(data["broker"])}
    )
    Database.update(
      "OrderBroker", 
      {"order_id": order["id"], "broker_id": broker["id"]},
      {"price": data["price"][2:], "state": 1}
    )
    order = to_object(order, ["id","create_order_address","order_index","investor_id","created_at","state"])
    return order

  @app.route("/orders/{order_index}/investor-confirm", cors=True, methods=["PUT"])
  def orders_update_state(order_index):
    request = app.current_request
    data = request.json_body
    token = Database.find_one(
      "Token", 
      {"create_order_address": Web3.toChecksumAddress(data["createOrderAddress"])}
    )
    order = Database.find_one(
      "Order", 
      {"order_index": int(order_index), "token_id": token["id"]}
    )
    broker = Database.find_one(
      "User", 
      {"address": Web3.toChecksumAddress(data["broker"])}
    )
    Database.update(
      "Order", 
      {"id": order["id"]},
      {"broker_id": broker['id']}
    )
    Database.update(
      "OrderBroker", 
      {"order_id": order["id"], "broker_id": broker['id']},
      {"state": 2}
    )
    order['broker_id'] = broker['id']
    order = to_object(order, ["id","create_order_address","order_index","investor_id","created_at","state","broker_id"])
    return order

  @app.route("/orders/{order_index}/broker-confirm", cors=True, methods=["PUT"])
  def orders_update_state(order_index):
    request = app.current_request
    data = request.json_body
    token = Database.find_one(
      "Token", 
      {"create_order_address": Web3.toChecksumAddress(data["createOrderAddress"])}
    )
    order = Database.find_one(
      "Order", 
      {"order_index": int(order_index), "token_id": token["id"]}
    )
    broker = Database.find_one(
      "User",
      {"address": Web3.toChecksumAddress(data["broker"])}
    )
    Database.update(
      "OrderBroker", 
      {"order_id": order["id"], "broker_id": broker["id"]},
      {"state": 3}
    )
    order = to_object(order, ["id","create_order_address","order_index","investor_id","created_at","state","broker_id"])
    return order
