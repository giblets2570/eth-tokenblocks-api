from passlib.hash import pbkdf2_sha256
from truelayer import Truelayer
from database import Database
from datetime import datetime
from chalice import Response, NotFoundError
from web3 import Web3
from utilities import loggedin_middleware, to_object, print_error
import jwt, os

secret = os.getenv('SECRET', None)
assert secret != None

web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

def Auth(app):
  @app.route('/auth/signup', cors=True, methods=['POST'])
  @print_error
  def auth_signup():
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

  @app.route('/auth/login', cors=True, methods=['POST'])
  @print_error
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
      secret, 
      algorithm='HS256'
    )
    return {
      'user': to_object(user, ['id', 'name', 'address', 'role', 'ik', 'spk', 'signature']),
      'token': token.decode("utf-8")
    }