from datetime import datetime, date
from chalice import ForbiddenError
import jwt, os

secret = os.getenv('SECRET', None)
assert secret != None

def loggedin_middleware(app, role=None):
  def outer(func):
    def inner(*args, **kwargs):
      headers = app.current_request.headers
      try:
        authorization = headers['authorization'].replace('Bearer ', '')
        user = jwt.decode(authorization, secret, algorithms=['HS256'])
        if role and user['role'] != role: raise ForbiddenError("You aren't authenticated")
        setattr(app.current_request, 'user', user)
        return func(*args, **kwargs)
      except Exception as e:
        print(e)
        raise e
    return inner
  return outer

def print_error(func):
  def inner(*args, **kwargs):
    try:
      return func(*args, **kwargs)
    except Exception as e:
      print(e)
      raise e
  return inner

def to_object(model, keys=None):
  print(model)
  output = dict()
  if not keys: keys = list(model.keys())
  for key in keys:
    if key not in model: continue
    output[key] = model[key]
    if(type(output[key]) == datetime):
      output[key] = output[key].timestamp()
    elif(type(output[key]) == date):
      output[key] = output[key].isoformat()
  return output


def decode(s):
  return "".join("%02x" % ord(c) for c in str(s))