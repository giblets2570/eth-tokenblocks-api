from chalice import Chalice, Rate
from chalicelib import Database

def Security(app):

  # Automatically runs every 5 minutes
  # @app.schedule(Rate(100, unit=Rate.MINUTES))
  def periodic_task():

      return {"hello": "world"}
  pass
