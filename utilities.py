from datetime import datetime, date
import jwt

def loggedin_middleware(app):
  def outer(func):
    def inner(*args, **kwargs):
      headers = app.current_request.headers
      authorization = headers['authorization'].replace('Bearer ', '')
      try:
        result = jwt.decode(authorization, 'secret', algorithms=['HS256'])
        setattr(app.current_request, 'user', result)
        return func(*args, **kwargs)
      except Exception as e:
        print(e)
        raise e
    return inner
  return outer

def to_object(model, keys):
  output = dict()
  for key in keys:
    output[key] = model[key]
    if(type(output[key]) == datetime):
      output[key] = output[key].timestamp()
    elif(type(output[key]) == date):
      output[key] = output[key].isoformat()
  return output


def decode(s):
  return "".join("%02x" % ord(c) for c in str(s))