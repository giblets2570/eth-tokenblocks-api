from .auth import Auth
from .user import User
from .order import Order
from .token import Token
from .trade import Trade
from .truelayer import Truelayer

def createEndpoints(app):
	Auth(app)
	User(app)
	Token(app)
	Trade(app)
	Order(app)
	Truelayer(app)