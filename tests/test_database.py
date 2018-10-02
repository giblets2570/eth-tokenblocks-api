import unittest, os, json
from unittest.mock import patch
from chalicelib.database import Database

env = {"MYSQL_HOST":"127.0.0.1","MYSQL_DB":"etttest","MYSQL_USER":"root" }

class TestDatabase(unittest.TestCase):

    def setUp(self):
        with patch.dict('os.environ', env):
            Database.clean_table('User')

    def tearDown(self):
        with patch.dict('os.environ', env):
            Database.clean_table('User')

    def test_insert(self):
        with patch.dict('os.environ', env):
            user = Database.insert("User", {'name': 'tom'}, return_inserted = True)
            self.assertEqual(user['name'], 'tom')

    def test_find(self):
        with patch.dict('os.environ', env):
            Database.insert("User", {'name': 'tom'})

            users = Database.find("User", {'name': 'tom'})
            
            self.assertEqual(len(users), 1)
            self.assertEqual(users[0]['name'], 'tom')

    def test_find_one(self):
        with patch.dict('os.environ', env):
            Database.insert("User", {'name': 'tom'})
            user = Database.find_one("User", {'name': 'tom'})
            self.assertEqual(user['name'], 'tom')

    def test_update(self):
        with patch.dict('os.environ', env):
            Database.insert("User", {'name': 'tom'})
            Database.update("User", [[('name','=','tom')]], {'name': 'tom2'})

            user = Database.find_one("User", {'name': 'tom'})
            self.assertEqual(user, None)

            user = Database.find_one("User", {'name': 'tom2'})
            self.assertEqual(user['name'], 'tom2')


    def test_update_multiple(self):
        with patch.dict('os.environ', env):
            Database.insert("User", {'name': 'tom'})
            Database.insert("User", {'name': 'tom'})

            Database.update("User", [[('name','=','tom')]], {'name': 'tom2'})

            user = Database.find_one("User", {'name': 'tom'})
            self.assertEqual(user, None)

            users = Database.find("User", {'name': 'tom2'})
            self.assertEqual(len(users), 2)
            self.assertEqual(users[0]['name'], 'tom2')
            self.assertEqual(users[1]['name'], 'tom2')

    def test_update_multiple_with_or(self):
        with patch.dict('os.environ', env):
            Database.insert("User", {'name': 'tom'})
            Database.insert("User", {'name': 'tom2'})

            Database.update("User", [[('name','=','tom')],[('name','=','tom2')]], {'name': 'tom3'})

            user = Database.find_one("User", {'name': 'tom'})
            self.assertEqual(user, None)
            user = Database.find_one("User", {'name': 'tom2'})
            self.assertEqual(user, None)

            users = Database.find("User", {'name': 'tom3'})
            self.assertEqual(len(users), 2)
            self.assertEqual(users[0]['name'], 'tom3')
            self.assertEqual(users[1]['name'], 'tom3')


if __name__ == '__main__':
    unittest.main()