import os
import time
from brownie import *

GAS_PRICE = None  # 30 * 1e9
REQUIRED_CONFS = 2


def main():
    admin = accounts.load("cryptobots-test", '12341234')
    token = ERC20CRV.deploy(
        "BITS-tst",
        "BITS-tst",
        18,
        {"from": admin, "required_confs": REQUIRED_CONFS, 'gas_price': GAS_PRICE},
    )

    tos = [
        '0xb83FB3BFe2D228f240bC230fBD9ff387C7DF799d',  # cryptobots-test
        '0xb82d9e965BC9A9Cd8E7CD0b82667F27bf44d0F88',  # serg acc 1
        '0x8486B5302C7b955690a3BBce71690DeaC8923ed3',  # serg acc 2
    ]
    for to in tos:
        token.transfer(to, 1e6 * 10**18, {"from": admin})

    settings = VotingEscrowSettings.deploy(
        {"from": admin, "required_confs": REQUIRED_CONFS, 'gas_price': GAS_PRICE},
    )

    voting_escrow = VotingEscrow.deploy(
        settings,
        token,
        "veBITS-tst",
        "veBITS-tst",
        "veBITS_1.0.0-tst",
        30,  # max_pool_members,
        int(0.01 * 1e18),  # min_stake_amount
        {"from": admin, "required_confs": REQUIRED_CONFS, 'gas_price': GAS_PRICE},
    )

    time.sleep(10)
    ERC20CRV.publish_source(token)
    VotingEscrowSettings.publish_source(settings)
    VotingEscrow.publish_source(voting_escrow)
