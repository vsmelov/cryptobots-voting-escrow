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

    reward = int(1e18)
    token.approve(voting_escrow, reward, {"from": admin, "required_confs": 2})
    voting_escrow.receiveReward(reward, {"from": admin, "required_confs": 2})
