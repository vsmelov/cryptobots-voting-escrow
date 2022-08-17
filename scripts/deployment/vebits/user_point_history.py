import os
import time
from brownie import *


def main():
    admin = accounts.load("brave_main", os.environ['BRAVE_MAIN_PASS'])
    user1 = accounts.load('testacc0', '12341234')
    user2 = accounts.load('testacc1', '12341234')

    voting_escrow = Contract.from_abi("VotingEscrow", os.environ['VOTING_ESCROW_ADDRESS'], VotingEscrow.abi)

    def print_user_points(user1name, user1):
        print(user1name)
        for i in range(10):
            user_point = voting_escrow.user_point_history(user1, i)
            print(user_point)

    print_user_points('user1', user1)
    print_user_points('user2', user2)
