from chalice import Chalice, Rate
app = Chalice(app_name='ett-api')
app.debug = True

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