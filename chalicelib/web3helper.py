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

debug = True

class Web3Helper():
	@classmethod
	def call(cls,contract,_method,*args):
		method = getattr(contract.functions,_method)
		return method(*args).call({'from': account})

	@classmethod
	def transact(cls,contract,_method,*args):
		print("Price ",w3.eth.generateGasPrice())
		method = getattr(contract.functions,_method)
		# return method(*args).transact({'from': account})
		try: 
			tx = method(*args).buildTransaction({
				"from": account,
				"nonce": w3.eth.getTransactionCount(account),
				"gasPrice": 91000000000
			})
			signedTx = w3.eth.account.signTransaction(tx, private_key=privateKey)
			return w3.eth.sendRawTransaction(signedTx.rawTransaction)
		except Exception as e:
			if debug: print(e)
			else: print("Transaction failed")
			return b''
			

	@classmethod
	def account(cls):
		return cls.toChecksumAddress(account)

	@classmethod
	def toChecksumAddress(cls, address):
		return Web3.toChecksumAddress(address)

	@classmethod
	def contract(cls, *args, **kwargs):
		return w3.eth.contract(*args, **kwargs)

	@classmethod
	def getContract(cls, filename, address=None):
		contract_json = None
		if os.environ.get('CONTRACT_FOLDER', None):
			folder = os.environ.get('CONTRACT_FOLDER', None)
			with open(folder + filename, 'r') as file:
				contract_json = json.loads(file.read())
		else:
			contract_json = requests.get("https://s3.eu-west-2.amazonaws.com/tokenblocks-contracts/{}".format(filename)).json()

		abi = contract_json["abi"]
		if not address:
			network = list(contract_json["networks"].keys())[0]
			address = Web3Helper.toChecksumAddress(contract_json["networks"][network]["address"])

		contract = Web3Helper.contract(
			address=Web3Helper.toChecksumAddress(address),
			abi=abi
		)
		return contract
