import os
import time
from brownie import *

GAS_PRICE = None
REQUIRED_CONFS = 2


def main():
    deployer = accounts.load("brave_main", os.environ['BRAVE_MAIN_PASS'])
    token = '0x9cEb6Ed22e44Ae7eCFe677DEB2b63157B4829792'
    future_admin = '0xBF65FA749164B356Ab28318e77A3a655C7D34755'

    # voting_escrow_naive = Contract.from_abi('VotingEscrowNaive', '0x6968a7846D8B55Fa711071993503b0E8847949dc', VotingEscrowNaive.abi)
    voting_escrow_naive = VotingEscrowNaive.deploy(
        {"from": deployer, "required_confs": REQUIRED_CONFS, 'gas_price': GAS_PRICE}
    )
    voting_escrow_naive.initialize(
        token,  # bits
        "veBITS",  # name
        "veBITS",  # symbol
        "1.0.0",  # version
        100000,  # _maxPoolMembers,
        int(0.1 * 1e18),  # _minLockAmount
        60,  # _minLockTime
        {"from": deployer, "required_confs": REQUIRED_CONFS, 'gas_price': GAS_PRICE},
    )
    voting_escrow_naive.addRewardToken(
        token,
        {"from": deployer, "required_confs": REQUIRED_CONFS, 'gas_price': GAS_PRICE},
    )
    voting_escrow_naive.addRewardToken(
        '0x0000000000000000000000000000000000000000',
        {"from": deployer, "required_confs": REQUIRED_CONFS, 'gas_price': GAS_PRICE},
    )
    voting_escrow_naive.transferOwnership(
        future_admin,
        {"from": deployer, "required_confs": REQUIRED_CONFS, 'gas_price': GAS_PRICE}
    )
    VotingEscrowNaive.publish_source(voting_escrow_naive)
