from chalice import Chalice, Rate
app = Chalice(app_name='ett-api')
# app.debug = True
from chalicelib.endpoints import init as endpoints
from chalicelib.scheduled import init as scheduled

endpoints.createEndpoints(app)
scheduled.createScheduled(app)