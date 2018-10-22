from .auth import Auth
from .user import User
from .fund import Fund
from .order import Order
from .token import Token
from .trade import Trade
from .error import Error
from .security import Security
from .truelayer import Truelayer

def createEndpoints(app):
	Auth(app)
	User(app)
	Fund(app)
	Token(app)
	Trade(app)
	Order(app)
	Error(app)
	Security(app)
	Truelayer(app)
