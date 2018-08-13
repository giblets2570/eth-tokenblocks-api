from database import Database
from datetime import datetime
from chalice import NotFoundError, ForbiddenError
from web3 import Web3
import jwt, os, json

contract_folder = os.environ.get('CONTRACT_FOLDER', None)
assert contract_folder != None
web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

with open(contract_folder + 'CreateOrder.json') as file:
  create_order_contract_abi = json.loads(file.read())['abi']

def to_object(model, keys):
  output = dict()
  for key in keys:
    output[key] = model[key]
    if(type(output[key]) == datetime):
      output[key] = output[key].timestamp()
  return output

def Order(app):
  def loggedin_middleware(func):
    def wrapper(*args, **kwargs):
      headers = app.current_request.headers
      if 'authorization' not in headers: raise ForbiddenError('Not authorized')
      authorization = headers['authorization'].replace('Bearer ', '')
      try:
        result = jwt.decode(authorization, 'secret', algorithms=['HS256'])
        setattr(app.current_request, 'user', result)
        return func(*args, **kwargs)
      except Exception as e:
        print(e)
        raise e
    return wrapper

  @app.route('/orders', cors=True, methods=['POST'])
  def orders_post():
    request = app.current_request
    data = request.json_body
    investor = Database.find_one("User", {'address': Web3.toChecksumAddress(data['investor'])})

    order_data = {
      'create_order_address': data['createOrderAddress'],
      'order_index': int(data['index']),
      'investor_id': investor['id'],
      'created_at': datetime.fromtimestamp(int(data['date'])),
      'state': 0
    }
    order = Database.find_one("Order", order_data)
    if not order:
      Database.insert("Order", order_data)
      order = Database.find_one("Order", order_data)

    order_brokers = []
    for _broker in data['brokers']:
      broker = Database.find_one("User", {'address': Web3.toChecksumAddress(_broker)})
      order_broker_data = {
        'order_id': order['id'],
        'broker_id': broker['id']
      }
      order_broker = Database.find_one("OrderBroker", order_broker_data)
      if not order_broker:
        Database.insert("OrderBroker", order_broker_data)
        order_broker = Database.find_one("OrderBroker", order_broker_data)
      order_brokers.append(order_broker['broker_id'])

    create_order_contract = web3.eth.contract(
      address=Web3.toChecksumAddress(order['create_order_address']),
      abi=create_order_contract_abi
    )

    data = create_order_contract.functions.getOrderBrokers(
      order['order_index'], 
      Web3.toChecksumAddress(data['investor'])
    ).call()

    print(data)

    order = to_object(order, ['id','create_order_address','order_index','investor_id','created_at','state'])
    order['brokers'] = order_brokers
    return order

  @app.route('/orders', cors=True, methods=['GET'])
  @loggedin_middleware
  def orders_get():
    request = app.current_request
    orders = None
    query = request.query_params or {}
    query['investor_id'] = request.user['id']
    orders = Database.find("Order", query)
    orders = [to_object(u, ['id','create_order_address','order_index','investor_id','created_at','state']) for u in orders]
    return orders

  @app.route('/orders/{order_id}', cors=True, methods=['GET'])
  @loggedin_middleware
  def orders_show(order_id):
    request = app.current_request
    data = request.json_body
    order = Database.find_one('Order', {'id': int(order_id)})
    if not order: raise NotFoundError('order not found with id {}'.format(order_id))
    order['brokers'] = []
    order_brokers = Database.find('OrderBroker', {'order_id': order['id']})
    for order_broker in order_brokers:
      broker = Database.find_one('User', {'id': order_broker['broker_id']})
      order['brokers'].append(to_object(broker, ['id', 'name', 'address', 'role']))
    order = to_object(order, ['id','create_order_address','order_index','investor_id','created_at','state','brokers'])
    return order


  @app.route('/orders/{order_index}/state', cors=True, methods=['PUT'])
  def orders_update_state(order_index):
    request = app.current_request
    data = request.json_body
    order = Database.find_one(
      'Order', 
      {'order_index': int(order_index)}
    )
    if(order['state'] < data['state']):
      Database.find_one(
        'Order', 
        {'order_index': int(order_index)},
        {'state': data['state']}
      )
      return {'message':'Done'}
    return {'message':'Not updated'}
