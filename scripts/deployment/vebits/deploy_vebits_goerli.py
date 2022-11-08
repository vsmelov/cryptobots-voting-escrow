import os
import time
from brownie import *

GAS_PRICE = 50 * 1e9
REQUIRED_CONFS = 2


TOKEN_ADDRESS = '0x61502bA2314de5d6e93945504489752D0fc37fF2'
SETTINGS_ADDRESS = '0xaEE1136dd31a5868a0912eDD9478f8e2241ec25F'
VOTING_ESCROW_ADDRESS = '0x82850d68b3858732E67C6E855CBfc9CC4BAC2a35'


def main():
    admin = accounts.load("brave_main", os.environ['BRAVE_MAIN_PASS'])

    print(f'{admin.balance()=}')

    if TOKEN_ADDRESS is None:
        token = ERC20CRV.deploy(
            "BITS-tst",
            "BITS-tst",
            18,
            {"from": admin, "required_confs": REQUIRED_CONFS, 'gas_price': GAS_PRICE},
        )
    else:
        token = Contract.from_abi("ERC20CRV", TOKEN_ADDRESS, ERC20CRV.abi)
    print(f'{token.address=}')

    if 0:
        tos = [
            '0xb83FB3BFe2D228f240bC230fBD9ff387C7DF799d',  # cryptobots-test
            '0xb82d9e965BC9A9Cd8E7CD0b82667F27bf44d0F88',  # serg acc 1
            '0x8486B5302C7b955690a3BBce71690DeaC8923ed3',  # serg acc 2
        ]
        for to in tos:
            token.transfer(to, 1e6 * 10**18, {"from": admin})

    if SETTINGS_ADDRESS is None:
        settings = VotingEscrowSettings.deploy(
            {"from": admin, "required_confs": REQUIRED_CONFS, 'gas_price': GAS_PRICE},
        )
    else:
        settings = Contract.from_abi("Settings", SETTINGS_ADDRESS, VotingEscrowSettings.abi)
    print(f'{settings.address=}')

    voting_escrow = VotingEscrow.deploy({
        "from": admin,
        "required_confs": REQUIRED_CONFS,
        'gas_price': GAS_PRICE,
    })
    voting_escrow.initialize(
        settings,
        token,
        "veBITS-tst",
        "veBITS-tst",
        "veBITS_1.0.0-tst",
        10000,  # max_pool_members,
        int(0.01 * 1e18),  # min_stake_amount
        {"from": admin, "required_confs": REQUIRED_CONFS, 'gas_price': GAS_PRICE},
    )
    print(f'{voting_escrow.address=}')

    time.sleep(10)
    ERC20CRV.publish_source(token)
    VotingEscrowSettings.publish_source(settings)
    VotingEscrow.publish_source(voting_escrow)
