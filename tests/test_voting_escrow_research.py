import brownie

from .utils import *


def test_share_rewards_2users(web3, chain, accounts, token, voting_escrow):
    sleep = 3600
    EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
    payer = accounts[0]
    fee = 10**18
    deposit = 10**18
    user1 = accounts[1]
    user2 = accounts[2]

    print_state("init", voting_escrow, user1, user2)

    chain.sleep(sleep)
    user1_deposit_amount = deposit
    user1_deposit_till = chain.time() + EPOCH_SECONDS*10
    token.transfer(user1, user1_deposit_amount)
    token.approve(voting_escrow, user1_deposit_amount, {"from": user1})
    tx = voting_escrow.create_lock(user1_deposit_amount, user1_deposit_till, {"from": user1})
    user1_deposit_at = tx.timestamp

    print_state("after first lock", voting_escrow, user1, user2)

    assert voting_escrow.epoch() == 1
    assert voting_escrow.epoch_rewards(1) == 0

    token.approve(voting_escrow, fee)
    voting_escrow.receiveReward(fee, {"from": payer})

    assert voting_escrow.epoch() == 1
    assert voting_escrow.epoch_rewards(1) == fee

    chain.sleep(sleep)
    voting_escrow.checkpoint()
    assert voting_escrow.epoch() == 2

    print_state("after empty checkpoint", voting_escrow, user1, user2)

    user2_deposit_amount = deposit * 2
    user2_deposit_till = chain.time() + EPOCH_SECONDS*20
    token.transfer(user2, user2_deposit_amount)
    token.approve(voting_escrow, user2_deposit_amount, {"from": user2})
    voting_escrow.create_lock(user2_deposit_amount, user2_deposit_till, {"from": user2})
    assert voting_escrow.epoch() == 3

    print_state("after second lock", voting_escrow, user1, user2)

    chain.sleep(sleep)
    voting_escrow.checkpoint()
    assert voting_escrow.epoch() == 4

    print_state("after 2nd empty checkout", voting_escrow, user1, user2)

    assert voting_escrow.epoch_rewards(2) == 0
    token.approve(voting_escrow, fee)
    voting_escrow.receiveReward(fee, {"from": payer})
    assert voting_escrow.epoch() == 4
    assert voting_escrow.epoch_rewards(1) == fee


    chain.sleep(3600)
    voting_escrow.checkpoint()
    assert voting_escrow.epoch() == 5

    print_state("after 3rd empty checkout", voting_escrow, user1, user2)

    tx = voting_escrow.claim_rewards({"from": user1})
    assert voting_escrow.user_claimed_epoch(user1) == 4

    tx = voting_escrow.claim_rewards({"from": user2})
    assert voting_escrow.user_claimed_epoch(user2) == 4

    print_state("after claims", voting_escrow, user1, user2)

    # raise ValueError('x')

