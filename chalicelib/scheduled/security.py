from chalice import Chalice, Rate

def Security(app):

    # Automatically runs every 5 minutes
    # @app.schedule(Rate(100, unit=Rate.MINUTES))
    # def periodic_task():
    #     print("What")
    #     return {"hello": "world"}
    pass