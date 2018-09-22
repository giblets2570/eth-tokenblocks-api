from chalicelib.database import Database
from datetime import datetime
from chalice import NotFoundError, ForbiddenError
from chalicelib.utilities import *

def Security(app):

  @app.route('/securities', cors=True, methods=['POST'])
  @loggedinMiddleware(app, 'admin')
  @printError
  def securities_post():
    request = app.current_request
    data = request.json_body
    security = Database.find_one('Security', data, insert=True)
    return toObject(security)