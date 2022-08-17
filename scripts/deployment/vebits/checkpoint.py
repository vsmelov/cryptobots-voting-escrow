import os
import time
from brownie import *


def main():
    admin = accounts.load("brave_main", os.environ['BRAVE_MAIN_PASS'])
    voting_escrow = Contract.from_abi("VotingEscrow", os.environ['VOTING_ESCROW_ADDRESS'], VotingEscrow.abi)

    tx = voting_escrow.checkpoint({"from": admin})
    print(f"{tx.events=}")
