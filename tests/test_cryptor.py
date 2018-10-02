import unittest, os, json
from unittest.mock import patch
from chalicelib.cryptor import Cryptor

env = {"MYSQL_HOST":"127.0.0.1","MYSQL_DB":"etttest","MYSQL_USER":"root" }

class TestCryptor(unittest.TestCase):

    def setUp(self):
        self.key = "01ab38d5e05c92aa098921d9d4626107133c7e2ab0e4849558921ebcc242bcb0"
        self.text = 'i took a pill in ibiza'
        self.encrypted = 'ddb556251a9823823fb1134516af7cdb468c553eee32816d5b1ebb0275afbc88'

    def test_encrypt(self):
        iv, encrypted = Cryptor.encrypt(self.text, self.key)
        self.assertEqual(encrypted.hex(), self.encrypted)

    def test_decrypt(self):
        decrypted = Cryptor.decryptInput(self.encrypted, self.key)
        self.assertEqual(decrypted, self.text)

if __name__ == '__main__':
    unittest.main()