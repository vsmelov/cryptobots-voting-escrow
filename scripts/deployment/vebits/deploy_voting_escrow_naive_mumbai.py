import os
import time
from brownie import *

GAS_PRICE = None
REQUIRED_CONFS = 2


def main():
    deployer = accounts.load("brave_main", os.environ['BRAVE_MAIN_PASS'])
    token = '0x9cEb6Ed22e44Ae7eCFe677DEB2b63157B4829792'
    future_admin = '0xBF65FA749164B356Ab28318e77A3a655C7D34755'

    voting_escrow_naive = VotingEscrowNaive.deploy(
        {"from": deployer, "required_confs": REQUIRED_CONFS, 'gas_price': GAS_PRICE}
    )
    voting_escrow_naive.initialize(
        token,
        "veBITS",
        "veBITS",
        "veBITS_1.0.0",
        100000,  # max_pool_members,
        int(0.1 * 1e18),  # min_stake_amount
        {"from": deployer, "required_confs": REQUIRED_CONFS, 'gas_price': GAS_PRICE},
    )
    voting_escrow.transfer_ownership(
        future_admin,
        {"from": deployer, "required_confs": REQUIRED_CONFS, 'gas_price': GAS_PRICE}
    )
