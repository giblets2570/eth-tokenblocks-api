from chalicelib.utilities import *

def Error(app):
  @app.route('/errors', cors=True, methods=['POST'])
  @printError
  def errors():
    request = app.current_request
    data = request.json_body
    
    print(data)

    return data