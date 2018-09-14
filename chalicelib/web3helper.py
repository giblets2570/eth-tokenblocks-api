from web3 import Web3
import os, requests, json
provider = os.environ.get("PROVIDER","http://127.0.0.1:8545")
w3 = Web3(Web3.HTTPProvider(provider))

privateKey = os.environ.get("PRIVATE_KEY", None)
account = None
if privateKey: 
	account = w3.eth.account.privateKeyToAccount(privateKey)
	account = account.address
else:
	account = w3.eth.accounts[0]

class Web3Helper():
	@classmethod
	def call(cls,contract,_method,*args):
		print('calling method')
		method = getattr(contract.functions,_method)
		print(args)
		return method(*args).call({'from': account})

	@classmethod
	def transact(cls,contract,_method,*args):
		print('transacting method')
		method = getattr(contract.functions,_method)
		print(args)
		tx = method(*args).buildTransaction({
			"from": account,
			"nonce": w3.eth.getTransactionCount(account),
			"gas": 1728712,
			"chainId": 1,
			"gasPrice": w3.toWei("21", "gwei")
		})
		signedTx = w3.eth.account.signTransaction(tx, private_key=privateKey)
		return w3.eth.sendRawTransaction(signedTx.rawTransaction)


	@classmethod
	def toChecksumAddress(cls, address):
		return Web3.toChecksumAddress(address)

	@classmethod
	def contract(cls, *args, **kwargs):
		return w3.eth.contract(*args, **kwargs)

	@classmethod
	def getContract(cls, filename):
		if os.environ.get('CONTRACT_FOLDER', None):
			folder = os.environ.get('CONTRACT_FOLDER', None)
			with open(folder + filename, 'r') as file:
				return json.loads(file.read())
		else:
			return requests.get("https://s3.eu-west-2.amazonaws.com/tokenblocks-contracts/{}".format(filename)).json()