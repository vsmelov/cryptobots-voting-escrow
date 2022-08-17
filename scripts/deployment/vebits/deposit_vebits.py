import os
import time
from brownie import *


def main():
    admin = accounts.load("brave_main", os.environ['BRAVE_MAIN_PASS'])
    user1 = accounts.load('testacc0', '12341234')
    user2 = accounts.load('testacc1', '12341234')
    for u in [user1, user2]:
        if u.balance() < int(0.02 * 1e18):
            admin.transfer(u, int(0.05 * 1e18)-u.balance())

    token = Contract.from_abi("ERC20CRV", os.environ['TOKEN_ADDRESS'], ERC20CRV.abi)
    voting_escrow = Contract.from_abi("VotingEscrow", os.environ['VOTING_ESCROW_ADDRESS'], VotingEscrow.abi)

    deposit = int(1e18)
    till = int(time.time() + 10 * 3600)

    token.transfer(user1, deposit, {"from": admin, "required_confs": 2})
    token.approve(voting_escrow, deposit, {"from": user1, "required_confs": 2})
    voting_escrow.create_lock(deposit, till, {"from": user1, "required_confs": 2})

    deposit = int(2*1e18)
    till = int(time.time() + 20 * 3600)

    token.transfer(user2, deposit, {"from": admin, "required_confs": 2})
    token.approve(voting_escrow, deposit, {"from": user2, "required_confs": 2})
    voting_escrow.create_lock(deposit, till, {"from": user2, "required_confs": 2})
