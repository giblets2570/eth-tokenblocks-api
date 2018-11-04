from datetime import datetime, date
from chalice import ForbiddenError
import jwt, os, json

env = os.environ.get('ENV', None)

def loggedinMiddleware(app, role=None):
  def outer(func):
    def inner(*args, **kwargs):
      if env == 'demo':
        fake_user = {}
        if 'referer' in app.current_request.headers:
          if 'broker' in app.current_request.headers['referer']:
            fake_user['role'] = 'broker'
            fake_user['id'] = 3
          if 'issuer' in app.current_request.headers['referer']:
            fake_user['role'] = 'issuer'
            fake_user['id'] = 6
          if 'investor' in app.current_request.headers['referer']:
            fake_user['role'] = 'investor'
            fake_user['id'] = 4
          if 'custodian' in app.current_request.headers['referer']:
            fake_user['role'] = 'custodian'
            fake_user['id'] = 5
        setattr(app.current_request, 'user', fake_user)
        return func(*args, **kwargs)
      headers = app.current_request.headers
      if 'authorization' not in headers: raise ForbiddenError("You aren't authenticated")
      authorization = headers['authorization'].replace('Bearer ', '')
      try:
        secret = os.getenv('SECRET', None)
        assert secret != None
        user = jwt.decode(authorization, secret, algorithms=['HS256'])
        if role and user['role'] != role: raise ForbiddenError("You aren't authenticated")
        setattr(app.current_request, 'user', user)
      except Exception as e:
        print(e)
        raise e
      return func(*args, **kwargs)
    return inner
  return outer

def printError(func):
  def inner(*args, **kwargs):
    try:
      return func(*args, **kwargs)
    except Exception as e:
      print(e)
      raise e
  return inner

def toObject(model, keys=None):
  if model == None: return None
  if type(model) == list:
    return [toObject(m, keys) for m in model]
  if type(model) == tuple:
    return toObject(list(model))
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


def passWithoutError(func):
  def inner(*args, **kwargs):
    try:
      func(*args,**kwargs)
    except Exception as e:
      pass
  return inner

def decode(s):
  return "".join("%02x" % ord(c) for c in str(s))
