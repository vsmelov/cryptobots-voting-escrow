import os
import time
from brownie import *


def main():
    admin = accounts.load("brave_main", os.environ['BRAVE_MAIN_PASS'])
    token = ERC20CRV.deploy(
        "BITS-tst",
        "BITS-tst",
        18,
        {"from": admin, "required_confs": 2, 'gas_price': 30 * 1e9},
    )

    tos = [
        '0xb82d9e965BC9A9Cd8E7CD0b82667F27bf44d0F88',
        '0x8486B5302C7b955690a3BBce71690DeaC8923ed3',
    ]
    for to in tos:
        token.transfer(to, 1e6 * 10**18, {"from": admin})

    voting_escrow = VotingEscrow.deploy(
        token,
        "veBITS-tst",
        "veBITS-tst",
        "veBITS_1.0.0-tst",
        {"from": admin, "required_confs": 2, 'gas_price': 30 * 1e9},
    )

    time.sleep(10)
    ERC20CRV.publish_source(token)
    VotingEscrow.publish_source(voting_escrow)
