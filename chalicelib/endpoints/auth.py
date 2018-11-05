from passlib.hash import pbkdf2_sha256
from chalicelib.truelayer import Truelayer
from chalicelib.database import Database
from datetime import datetime
from chalice import Response, NotFoundError
from chalicelib.utilities import *
from web3 import Web3
import jwt, os

secret = os.getenv('SECRET', None)
assert secret != None

def Auth(app):
  @app.route('/auth/signup', cors=True, methods=['POST'])
  @printError
  def auth_signup():
    request = app.current_request
    data = request.json_body
    email = data['email']
    name = data['name']
    password = data['password']

    # addressLine1 = data['addressLine1']
    # addressLine2 = data['addressLine2']
    # city = data['city']
    # postcode = data['postcode']
    # country = data['country']
    # juristiction = data['juristiction']
    print(data)

    role = data['role'] if 'role' in data else 'investor'
    user = Database.find_one("User", {
      'email': email
    })
    if not user:
      password_hash = pbkdf2_sha256.hash(password)
      user = Database.insert("User", {
        'name': name,
        'email': email,
        'password': password_hash,
        'role': role,
        # 'addressLine1': addressLine1,
        # 'addressLine2': addressLine2,
        # 'city': city,
        # 'postcode': postcode,
        # 'country': country,
        # 'juristiction': juristiction,
        'type': 'institutional',
      }, return_inserted=True)
    return toObject(user, ['id', 'name', 'address', 'role', 'ik', 'spk', 'signature', 'truelayerAccountId'])

  @app.route('/auth/login', cors=True, methods=['POST'])
  @printError
  def auth_login():
    request = app.current_request
    data = request.json_body
    email = data['email']
    password = data['password']

    user = Database.find_one("User", {
      'email': email
    })
    if not user: raise NotFoundError('user not found with email {}'.format(email))
    if not pbkdf2_sha256.verify(password, user['password']): raise ForbiddenError('Wrong password')
    token = jwt.encode(toObject(user, ['id', 'name', 'email', 'address', 'role', 'ik', 'spk', 'signature', 'truelayerAccountId']),
      secret,
      algorithm='HS256'
    )
    return {
      'user': toObject(user, ['id', 'name', 'email', 'address', 'role', 'ik', 'spk', 'signature', 'truelayerAccountId']),
      'token': token.decode("utf-8")
    }
