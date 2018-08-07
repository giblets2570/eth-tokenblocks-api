from truelayer import Truelayer
from database import Database
from chalice import Response, NotFoundError
from passlib.hash import pbkdf2_sha256
import jwt
from web3 import Web3



def seedData():
  user = Database.find_one("User", {'role': 'broker'})
  if not user:
    password_hash = pbkdf2_sha256.hash('broker')
    Database.insert("User", {
      'name': 'broker',
      'password': password_hash,
      'address': '0x1bbf9F9429202f6C95B1890abfeF0e09595D3c2F',
      'role': 'broker'
    })
# Database.clean_table('User')
seedData()

def to_object(model, keys):
  output = dict()
  for key in keys:
    output[key] = model[key]
  return output

def Auth(app):
  @app.route('/auth/signup', cors=True, methods=['POST'])
  def auth_signup():
    try:
      request = app.current_request
      data = request.json_body

      address = data['address']
      name = data['name']
      password = data['password']
      role = data['role'] if 'role' in data else 'investor'
      
      user = Database.find_one("User", {
        'name': name,
        'address': Web3.toChecksumAddress(address),
      })
      if not user:
        password_hash = pbkdf2_sha256.hash(password)
        Database.insert("User", {
          'name': name,
          'password': password_hash,
          'address': address,
          'role': role
        })
        user = Database.find_one("User", {'address': Web3.toChecksumAddress(address)})
      return to_object(user, ['id', 'name', 'address', 'role', 'ik', 'spk', 'signature'])
    except Exception as e:
      print(e)
      raise e

  @app.route('/auth/login', cors=True, methods=['POST'])
  def auth_login():
    request = app.current_request
    data = request.json_body
    address = data['address']
    name = data['name']
    password = data['password']
    
    user = Database.find_one("User", {
      'name': name,
      'address': Web3.toChecksumAddress(address),
    })
    if not user: raise NotFoundError('user not found with name {}'.format(name))

    if not pbkdf2_sha256.verify(password, user['password']): raise ForbiddenError('Wrong password')

    token = jwt.encode(to_object(user, ['id', 'name', 'address', 'role', 'ik', 'spk', 'signature']), 
      'secret', 
      algorithm='HS256'
    )
    return {
      'user': to_object(user, ['id', 'name', 'address', 'role', 'ik', 'spk', 'signature']),
      'token': token.decode("utf-8")
    }
