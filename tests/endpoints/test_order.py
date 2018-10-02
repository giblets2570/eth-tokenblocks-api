import json
import unittest
from unittest.mock import patch

env = {"MYSQL_HOST":"127.0.0.1","MYSQL_DB":"etttest","MYSQL_USER":"root" }

class TestApiSchema(unittest.TestCase):

    def setUp(self):
        self.order = Order(app)
        print(self.order)
        with patch.dict('os.environ', env):
            Database.clean_tables()

    @staticmethod
    def create_event(uri, method, path, content_type='application/json'):
        return {
            'requestContext': {
                'httpMethod': method,
                'resourcePath': uri,
            },
            'headers': {
                'Content-Type': content_type,
            },
            'pathParameters': path,
            'queryStringParameters': {},
            'body': "",
            'stageVariables': {},
        }

    @classmethod
    def get_app_response(cls, _app, uri, method, path, content_type='application/json', context=None):
        context = context or {}
        response = _app(cls.create_event(uri, method, path, content_type), context)
        response['body'] = json.loads(response['body'])
        return response


if __name__ == '__main__':
    unittest.main()