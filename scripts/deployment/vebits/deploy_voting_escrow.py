import os
import time
from brownie import *

GAS_PRICE = 120 * 1e9
REQUIRED_CONFS = 2


def main():
    deployer = accounts.load("cryptobots-deployer-prod", '12341234')
    token = '0x10Ef8736545726eFdD086DdE8311c4DDDFBEB9f2'

    settings = VotingEscrowSettings.deploy(
        {"from": deployer, "required_confs": REQUIRED_CONFS, 'gas_price': GAS_PRICE},
    )

    voting_escrow = VotingEscrow.deploy(
        settings,
        token,
        "veBITS",
        "veBITS",
        "veBITS_1.0.0",
        100000,  # max_pool_members,
        int(100 * 1e18),  # min_stake_amount
        {"from": deployer, "required_confs": REQUIRED_CONFS, 'gas_price': GAS_PRICE},
    )
    voting_escrow.transfer_ownership('0xd40A68fe78dC8a166770Eb8B906f1149f32F639F', {"from": deployer})
