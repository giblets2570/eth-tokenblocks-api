from chalice import Chalice
app = Chalice(app_name='ett-api')

from endpoints.auth import Auth
from endpoints.user import User
from endpoints.order import Order
from endpoints.token import Token
from endpoints.trade import Trade
from endpoints.truelayer import Truelayer
Auth(app)
User(app)
Token(app)
Trade(app)
Order(app)
Truelayer(app)
from database import Database
from web3 import Web3
from passlib.hash import pbkdf2_sha256

web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

def seedData():
  user = Database.find_one("User", {'name': 'admin'})
  if not user:
    password_hash = pbkdf2_sha256.hash('admin')
    Database.insert("User", {
      'name': 'admin',
      'password': password_hash,
      'address': web3.eth.accounts[0],
      'role': 'admin'
    })
  user = Database.find_one("User", {'name': 'broker1'})
  if not user:
    password_hash = pbkdf2_sha256.hash('broker1')
    Database.insert("User", {
      'name': 'broker1',
      'password': password_hash,
      'address': web3.eth.accounts[1],
      'role': 'broker'
    })
  user = Database.find_one("User", {'name': 'broker2'})
  if not user:
    password_hash = pbkdf2_sha256.hash('broker2')
    Database.insert("User", {
      'name': 'broker2',
      'password': password_hash,
      'address': web3.eth.accounts[3],
      'role': 'broker'
    })
  user = Database.find_one("User", {'name': 'investor'})
  if not user:
    password_hash = pbkdf2_sha256.hash('investor')
    Database.insert("User", {
      'name': 'investor',
      'password': password_hash,
      'address': web3.eth.accounts[2],
      'role': 'investor'
    })

# Database.clean_table('TokenHolding')
# Database.clean_table('TokenBalance')
# Database.clean_table('Token')
# Database.clean_table('OrderBroker')
# Database.clean_table('`Order`')
# Database.clean_table('User')
seedData()