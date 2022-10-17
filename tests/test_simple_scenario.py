import time

import brownie

from .utils import *


def test_share_rewards_1user(web3, chain, accounts, token, voting_escrow):
    EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
    payer = accounts[0]
    reward_amount = 10**18
    deposit = 10**18
    user1 = accounts[1]
    user2 = accounts[2]
    user3 = accounts[3]

    assert voting_escrow.epoch() == 0
    assert voting_escrow.window_token_rewards(0, token) == 0

    token.transfer(user1, deposit)
    token.approve(voting_escrow, deposit, {"from": user1})
    till = chain.time() + EPOCH_SECONDS*10
    tx = voting_escrow.create_lock(deposit, till, {"from": user1})

    # number perfect check
    assert voting_escrow.locked(user1)[0] == deposit
    assert voting_escrow.locked(user1)[1] == till // EPOCH_SECONDS * EPOCH_SECONDS
    period = till // EPOCH_SECONDS * EPOCH_SECONDS - tx.timestamp
    assert voting_escrow.user_point_history(user1, 0) == (0, 0, 0, 0)
    assert voting_escrow.user_point_history(user1, 1)[0] == (deposit // voting_escrow.MAXTIME()) * period  # bias
    assert voting_escrow.user_point_history(user1, 1)[1] == (deposit // voting_escrow.MAXTIME())  # slope
    assert voting_escrow.user_point_history(user1, 1)[2] == tx.timestamp  # ts
    assert voting_escrow.user_point_history(user1, 1)[3] == tx.block_number  # blk
    assert voting_escrow.user_point_history(user1, 2) == (0, 0, 0, 0)
    assert voting_escrow.point_history(voting_escrow.epoch())[0] == (deposit // voting_escrow.MAXTIME()) * period
    assert voting_escrow.point_history(voting_escrow.epoch())[1] == (deposit // voting_escrow.MAXTIME())
    assert voting_escrow.point_history(voting_escrow.epoch())[2] == tx.timestamp
    assert voting_escrow.point_history(voting_escrow.epoch())[3] == tx.block_number
    assert voting_escrow.slope_changes(till // EPOCH_SECONDS * EPOCH_SECONDS) == -(deposit // voting_escrow.MAXTIME())

    assert voting_escrow.epoch() == 1
    token.approve(voting_escrow, reward_amount)
    voting_escrow.receiveReward(token, reward_amount, {"from": payer})
    assert voting_escrow.epoch() == 1
    assert voting_escrow.window_token_rewards(1, token) == reward_amount

    voting_escrow.checkpoint()

    assert voting_escrow.user_token_claimed_window(user1, token) == 0

    claimable = voting_escrow.user_token_claimable_rewards(user1, token)
    assert claimable == reward_amount

    tx = voting_escrow.claim_rewards(token, {"from": user1})
    assert tx.events['UserRewardsClaimed']['amount'] == reward_amount
    assert tx.events['UserRewardsClaimed']['amount'] == claimable
    assert voting_escrow.user_token_claimed_window(user1, token) == 1

    claimable = voting_escrow.user_token_claimable_rewards(user1, token)
    tx = voting_escrow.claim_rewards(token, {"from": user1})
    assert claimable == 0
    assert tx.events['UserRewardsClaimed']['amount'] == 0
    assert voting_escrow.user_token_claimed_window(user1, token) == 1
