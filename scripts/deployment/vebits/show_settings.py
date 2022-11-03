import os
import time
from brownie import *


def main():
    voting_escrow = Contract.from_abi("VotingEscrow", "0x377acee2817cac0f27355a97ce716ddcd6ed306c", VotingEscrow.abi)
    print(f'{voting_escrow.settings()=}')
    print(f'{voting_escrow.name()=}')
    print(f'{voting_escrow.symbol()=}')
    print(f'{voting_escrow.version()=}')
    print(f'{voting_escrow.decimals()=}')
    print(f'{voting_escrow.last_manual_checkpoint_timestamp()=}')
    print(f'{voting_escrow.token()=}')
    print(f'{voting_escrow.supply()=}')
    print(f'{voting_escrow.epoch()=}')
    print(f'{voting_escrow.min_delay_between_manual_checkpoint()=}')
    print(f'{voting_escrow.smart_wallet_checker()=}')
    print(f'{voting_escrow.emergency()=}')
    print(f'{voting_escrow.withdraw_disabled()=}')
    print(f'{voting_escrow.increase_amount_disabled()=}')
    print(f'{voting_escrow.increase_unlock_time_disabled()=}')
    print(f'{voting_escrow.create_lock_disabled()=}')
    print(f'{voting_escrow.admin()=}')
    print(f'{voting_escrow.min_stake_amount()=}')
    print(f'{voting_escrow.max_pool_members()=}')
    print(f'{voting_escrow.pool_members()=}')
    print(f'{voting_escrow.EPOCH_SECONDS()=}')
    print(f'{voting_escrow.MAXTIME()=}')
    print(f'{voting_escrow.currentWindow()=}')

    print(f'{voting_escrow.locked("0xc108382b38514349322aa9fead1d7bcbc9aadd45")=}')
