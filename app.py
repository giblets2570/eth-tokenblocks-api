from chalice import Chalice

app = Chalice(app_name='ett-api')

# Get the endpoints
from endpoints.auth import Auth
from endpoints.user import User
from endpoints.truelayer import Truelayer
Auth(app)
User(app)
Truelayer(app)