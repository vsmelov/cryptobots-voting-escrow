from brownie import *


def main():
    txid = '0x39a2aa4570930b865670a5aecae64f8b699bad787cab84e2eea8aedf04a45cc8'
    ve = Contract.from_abi("ve", "0x2Fb72972BEF3b08f9D5AE6B6031165bBEF9E12bD", VotingEscrow.abi)
    tx = chain.get_transaction(txid)
    print(f'{tx=}')
    # print(f'{tx.revert_msg=}')
    tx.traceback()

    tx.call_trace()

