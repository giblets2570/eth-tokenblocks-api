from chalice import Chalice

app = Chalice(app_name='ett-api')

# Get the endpoints
from endpoints.auth import Auth
from endpoints.user import User
from endpoints.truelayer import Truelayer
Auth(app)
User(app)
Truelayer(app)


def loggedin_middleware(func):
  def wrapper(*args, **kwargs):
    headers = app.current_request.headers
    authorization = headers['authorization'].replace('Bearer ', '')
    try:
      result = jwt.decode(authorization, 'secret', algorithms=['HS256'])
      return func(*args, **kwargs)
    except Exception as e:
      print(e)
      raise e
  return wrapper