from chalicelib.database import Database
from datetime import datetime
from chalice import NotFoundError, ForbiddenError
from chalicelib.utilities import loggedin_middleware, to_object, print_error

def Security(app):

  @app.route('/securities', cors=True, methods=['POST'])
  @loggedin_middleware(app, 'admin')
  @print_error
  def securities_post():
    request = app.current_request
    data = request.json_body
    print(data)
    security = Database.find_one('Security', data, insert=True)
    return to_object(security)