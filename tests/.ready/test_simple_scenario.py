import time

import brownie

from .utils import *


def test_searchForUserEpochByTimestamp(web3, chain, accounts, token, voting_escrow):
    EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
    payer = accounts[0]
    reward_amount = 10**18
    deposit = 10**18
    user1 = accounts[1]
    user2 = accounts[2]
    user3 = accounts[3]

    window = voting_escrow.currentWindow()

    token.transfer(user1, deposit)
    token.approve(voting_escrow, deposit, {"from": user1})
    till = chain.time() + EPOCH_SECONDS*10
    tx_lock = voting_escrow.create_lock(deposit, till, {"from": user1})
    tx_lock_timestamp = tx_lock.timestamp

    assert voting_escrow.searchForUserEpochByTimestamp(user1, tx_lock_timestamp-1) == 0
    assert voting_escrow.searchForUserEpochByTimestamp(user1, till) == 1


def test_averageUserBalanaceOverWindow(web3, chain, accounts, token, voting_escrow):
    EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
    payer = accounts[0]
    reward_amount = 10**18
    deposit = 10**18
    user1 = accounts[1]
    user2 = accounts[2]
    user3 = accounts[3]

    window = voting_escrow.currentWindow()

    token.transfer(user1, deposit)
    token.approve(voting_escrow, deposit, {"from": user1})
    till = chain.time() + EPOCH_SECONDS*10
    tx_lock = voting_escrow.create_lock(deposit, till, {"from": user1})
    tx_lock_timestamp = tx_lock.timestamp
    tx_lock_till = tx_lock.events['Deposit']['locktime']

    assert voting_escrow.searchForUserEpochByTimestamp(user1, window) == 0
    assert voting_escrow.searchForUserEpochByTimestamp(user1, tx_lock_timestamp) == 1
    assert voting_escrow.searchForUserEpochByTimestamp(user1, window+EPOCH_SECONDS) == 1

    period = till // EPOCH_SECONDS * EPOCH_SECONDS - tx_lock.timestamp
    bias = (deposit // voting_escrow.MAXTIME()) * period
    slope = (deposit // voting_escrow.MAXTIME())
    assert voting_escrow.user_point_history(user1, 1)[0] == bias  # bias
    assert voting_escrow.user_point_history(user1, 1)[1] == slope  # slope
    assert voting_escrow.user_point_history(user1, 1)[2] == tx_lock.timestamp  # ts
    assert voting_escrow.user_point_history(user1, 1)[3] == tx_lock.block_number  # blk

    ts_start = tx_lock.timestamp
    ts_end = (1 + ts_start // EPOCH_SECONDS) * EPOCH_SECONDS
    interval = ts_end - ts_start
    start_bias = bias
    end_bias = bias - slope * interval
    avg_bias = (start_bias + end_bias) / 2
    integral = avg_bias * interval
    avg_user_balance_expected = integral / EPOCH_SECONDS

    chain.sleep(EPOCH_SECONDS)
    chain.mine()
    assert voting_escrow.currentWindow() == window + EPOCH_SECONDS

    avg_tx = voting_escrow.averageUserBalanaceOverWindowTx(user1, window)
    avg = voting_escrow.averageUserBalanaceOverWindow(user1, window)
    print(f'{avg_tx.events=}')
    assert avg_tx.events['_averageUserBalanceOverWindowDebugS'][1]['_ts0'] == ts_start
    assert avg_tx.events['_averageUserBalanceOverWindowDebugS'][1]['_ts1'] == ts_end
    assert abs(avg - avg_user_balance_expected) <= 1  # some rounding error is OK


def test_averageTotalSupplyOverWindow(web3, chain, accounts, token, voting_escrow):
    EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
    payer = accounts[0]
    reward_amount = 10**18
    deposit = 10**18
    user1 = accounts[1]
    user2 = accounts[2]
    user3 = accounts[3]

    window = voting_escrow.currentWindow()

    token.transfer(user1, deposit)
    token.approve(voting_escrow, deposit, {"from": user1})
    till = chain.time() + EPOCH_SECONDS*10
    tx_lock = voting_escrow.create_lock(deposit, till, {"from": user1})
    tx_lock_timestamp = tx_lock.timestamp
    tx_lock_till = tx_lock.events['Deposit']['locktime']

    period = till // EPOCH_SECONDS * EPOCH_SECONDS - tx_lock.timestamp
    bias = (deposit // voting_escrow.MAXTIME()) * period
    slope = (deposit // voting_escrow.MAXTIME())
    assert voting_escrow.point_history(1)[0] == bias  # bias
    assert voting_escrow.point_history(1)[1] == slope  # slope
    assert voting_escrow.point_history(1)[2] == tx_lock.timestamp  # ts
    assert voting_escrow.point_history(1)[3] == tx_lock.block_number  # blk

    ts_start = tx_lock.timestamp
    ts_end = (1 + ts_start // EPOCH_SECONDS) * EPOCH_SECONDS
    interval = ts_end - ts_start
    start_bias = bias
    end_bias = bias - slope * interval
    avg_bias = (start_bias + end_bias) / 2
    integral = avg_bias * interval
    avg_user_balance_expected = integral / EPOCH_SECONDS

    with brownie.reverts('incorrect window'):
        assert voting_escrow.averageTotalSupplyOverWindow(window) == avg_user_balance_expected

    chain.sleep(EPOCH_SECONDS)
    chain.mine()
    assert voting_escrow.currentWindow() == window + EPOCH_SECONDS

    assert abs(voting_escrow.averageTotalSupplyOverWindow(window) - avg_user_balance_expected) <= 1


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

    reward_window = voting_escrow.currentWindow()
    assert voting_escrow.epoch() == 1
    token.approve(voting_escrow, reward_amount)
    voting_escrow.receiveReward(token, reward_amount, {"from": payer})
    assert voting_escrow.epoch() == 1
    assert voting_escrow.window_token_rewards(reward_window, token) == reward_amount

    assert voting_escrow.user_token_claimed_window(user1, token) == 0

    # on reward_window claimable == 0
    claimable = voting_escrow.user_token_claimable_rewards(user1, token)
    assert claimable == 0

    chain.sleep(voting_escrow.EPOCH_SECONDS())
    chain.mine()
    assert voting_escrow.currentWindow() == reward_window + voting_escrow.EPOCH_SECONDS()

    # on reward_window claimable == reward_amount
    claimable_tx = voting_escrow.user_token_claimable_rewardsTx(user1, token)
    print(f'{claimable_tx.events=}')
    claimable = voting_escrow.user_token_claimable_rewards(user1, token)
    assert claimable == reward_amount

    tx = voting_escrow.claim_rewards(token, {"from": user1})
    assert tx.events['UserRewardsClaimed']['amount'] == reward_amount
    assert tx.events['UserRewardsClaimed']['amount'] == claimable
    assert voting_escrow.user_token_claimed_window(user1, token) == tx.timestamp // EPOCH_SECONDS * EPOCH_SECONDS - EPOCH_SECONDS

    claimable = voting_escrow.user_token_claimable_rewards(user1, token)
    tx = voting_escrow.claim_rewards(token, {"from": user1})
    assert claimable == 0
    assert tx.events['UserRewardsClaimed']['amount'] == 0
    assert voting_escrow.user_token_claimed_window(user1, token) == tx.timestamp // EPOCH_SECONDS * EPOCH_SECONDS - EPOCH_SECONDS
