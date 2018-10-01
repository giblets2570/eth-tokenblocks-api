from .auth import Auth
from .user import User
from .order import Order
from .token import Token
from .trade import Trade
from .security import Security
from .truelayer import Truelayer
from .error import Error

def createEndpoints(app):
	Auth(app)
	User(app)
	Token(app)
	Trade(app)
	Order(app)
	Error(app)
	Security(app)
	Truelayer(app)