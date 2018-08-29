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


  @app.route('/trades', cors=True, methods=['POST'])
  @loggedin_middleware(app, 'broker')
  @print_error
  def trades_post():
    request = app.current_request
    data = request.json_body

    print(data)

    return data
