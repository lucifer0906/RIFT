from algosdk.atomic_transaction_composer import AccountTransactionSigner
from algosdk import account

pk, addr = account.generate_account()
signer = AccountTransactionSigner(pk)
print("Signer created successfully")
print("Signer private key:", signer.private_key[:5] + "...")
