import time

import brownie

from .utils import *


def test_receive_rewards(web3, chain, accounts, token, voting_escrow):
    EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
    payer = accounts[0]
    reward_amount = 10**18

    assert voting_escrow.epoch() == 0
    assert voting_escrow.window_token_rewards(0, token) == 0
    assert voting_escrow.window_token_rewards(1, token) == 0

    token.approve(voting_escrow, reward_amount)
    voting_escrow.receiveReward(token, reward_amount, {"from": payer})

    assert voting_escrow.epoch() == 0
    assert voting_escrow.window_token_rewards(0, token) == reward_amount
    assert voting_escrow.window_token_rewards(1, token) == 0

    token.approve(voting_escrow, reward_amount)
    voting_escrow.receiveReward(token, reward_amount, {"from": payer})

    assert voting_escrow.epoch() == 0
    assert voting_escrow.window_token_rewards(0, token) == reward_amount * 2
    assert voting_escrow.window_token_rewards(1, token) == 0

    chain.sleep(EPOCH_SECONDS)
    voting_escrow.checkpoint({"from": payer})
    token.approve(voting_escrow, reward_amount)
    voting_escrow.receiveReward(token, reward_amount, {"from": payer})

    assert voting_escrow.epoch() == 1
    assert voting_escrow.window_token_rewards(0, token) == reward_amount * 2
    assert voting_escrow.window_token_rewards(1, token) == reward_amount

    chain.sleep(EPOCH_SECONDS*10)
    voting_escrow.checkpoint({"from": payer})
    token.approve(voting_escrow, reward_amount)
    voting_escrow.receiveReward(token, reward_amount, {"from": payer})
    assert voting_escrow.epoch() == 12
    assert voting_escrow.window_token_rewards(12, token) == reward_amount


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

    assert voting_escrow.user_token_claimed_epoch(user1, token) == 0

    claimable = voting_escrow.user_token_claimable_rewards(user1, token)
    tx = voting_escrow.claim_rewards(token, {"from": user1})
    print(f"{tx.events['_averageUserBlanaceOverEpochDebug']=}\n")
    print(f"{tx.events['_averageUserBlanaceOverEpochDebugS']=}\n")
    print(f"{tx.events['UserRewardsClaimedDebug']=}\n")
    assert tx.events['UserRewardsClaimed']['amount'] == reward_amount
    assert tx.events['UserRewardsClaimed']['amount'] == claimable
    assert voting_escrow.user_token_claimed_epoch(user1, token) == 1

    claimable = voting_escrow.user_token_claimable_rewards(user1, token)
    tx = voting_escrow.claim_rewards(token, {"from": user1})
    assert claimable == 0
    assert tx.events['UserRewardsClaimed']['amount'] == 0
    assert voting_escrow.user_token_claimed_epoch(user1, token) == 1


def test_share_rewards_1user_delay_after_initialization(web3, chain, accounts, token, voting_escrow):
    EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
    payer = accounts[0]
    reward_amount = 10**18
    deposit = 10**18
    user1 = accounts[1]
    user2 = accounts[2]
    user3 = accounts[3]

    assert voting_escrow.epoch() == 0
    assert voting_escrow.window_token_rewards(0, token) == 0

    assert voting_escrow.user_token_claimable_rewards(user1, token) == 0
    chain.sleep(30 * 24 * 3600)  # todo check fail
    chain.mine()
    assert voting_escrow.user_token_claimable_rewards(user1, token) == 0
    voting_escrow.checkpoint()
    assert voting_escrow.user_token_claimable_rewards(user1, token) == 0

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

    assert voting_escrow.epoch() == 2
    token.approve(voting_escrow, reward_amount)
    voting_escrow.receiveReward(token, reward_amount, {"from": payer})
    assert voting_escrow.epoch() == 2
    assert voting_escrow.window_token_rewards(2, token) == reward_amount

    voting_escrow.checkpoint()
    assert voting_escrow.epoch() == 3

    assert voting_escrow.user_token_claimed_epoch(user1, token) == 0

    claimable = voting_escrow.user_token_claimable_rewards(user1, token)
    tx = voting_escrow.claim_rewards(token, {"from": user1})
    print(f"{tx.events['_averageUserBlanaceOverEpochDebug']=}\n")
    print(f"{tx.events['_averageUserBlanaceOverEpochDebugS']=}\n")
    print(f"{tx.events['UserRewardsClaimedDebug']=}\n")
    assert tx.events['UserRewardsClaimed']['amount'] == reward_amount
    assert tx.events['UserRewardsClaimed']['amount'] == claimable
    assert voting_escrow.user_token_claimed_epoch(user1, token) == 2

    claimable = voting_escrow.user_token_claimable_rewards(user1, token)
    tx = voting_escrow.claim_rewards(token, {"from": user1})
    assert claimable == 0
    assert tx.events['UserRewardsClaimed']['amount'] == 0
    assert voting_escrow.user_token_claimed_epoch(user1, token) == 2


def test_share_rewards_2users_same_time_deposit(web3, chain, accounts, token, voting_escrow):
    sleep = 3600
    EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
    MAXTIME = voting_escrow.MAXTIME()
    payer = accounts[0]
    reward_amount = 10**18
    deposit = 10**18
    user1 = accounts[1]
    user2 = accounts[2]

    assert voting_escrow.epoch() == 0
    assert voting_escrow.window_token_rewards(0, token) == 0

    chain.sleep(sleep)
    user1_deposit_amount = deposit
    user1_deposit_till = chain.time() + EPOCH_SECONDS*10
    token.transfer(user1, user1_deposit_amount)
    token.approve(voting_escrow, user1_deposit_amount, {"from": user1})
    tx_lock_user1 = voting_escrow.create_lock(user1_deposit_amount, user1_deposit_till, {"from": user1})
    user1_deposit_at = tx_lock_user1.timestamp
    epoch_after_user1_lock = voting_escrow.epoch()

    # number perfect check
    assert voting_escrow.locked(user1)[0] == user1_deposit_amount
    assert voting_escrow.locked(user1)[1] == user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS
    period_user1 = user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS - tx_lock_user1.timestamp
    assert voting_escrow.user_point_history(user1, 0) == (0, 0, 0, 0)
    assert voting_escrow.user_point_history(user1, 1)[0] == (user1_deposit_amount // MAXTIME) * period_user1  # bias
    assert voting_escrow.user_point_history(user1, 1)[1] == (user1_deposit_amount // MAXTIME)  # slope
    assert voting_escrow.user_point_history(user1, 1)[2] == tx_lock_user1.timestamp  # ts
    assert voting_escrow.user_point_history(user1, 1)[3] == tx_lock_user1.block_number  # blk
    assert voting_escrow.user_point_history(user1, 2) == (0, 0, 0, 0)
    assert voting_escrow.point_history(epoch_after_user1_lock)[0] == (user1_deposit_amount // MAXTIME) * period_user1
    assert voting_escrow.point_history(epoch_after_user1_lock)[1] == (user1_deposit_amount // MAXTIME)
    assert voting_escrow.point_history(epoch_after_user1_lock)[2] == tx_lock_user1.timestamp
    assert voting_escrow.point_history(epoch_after_user1_lock)[3] == tx_lock_user1.block_number
    assert voting_escrow.slope_changes(user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS) == -(user1_deposit_amount // MAXTIME)

    user2_deposit_amount = deposit * 2
    user2_deposit_till = chain.time() + EPOCH_SECONDS*10
    token.transfer(user2, user2_deposit_amount)
    token.approve(voting_escrow, user2_deposit_amount, {"from": user2})
    tx_lock_user2 = voting_escrow.create_lock(user2_deposit_amount, user2_deposit_till, {"from": user2})
    assert voting_escrow.epoch() == 2
    user2_deposit_at = tx_lock_user2.timestamp
    epoch_after_user2_lock = voting_escrow.epoch()

    # number perfect user 1
    assert voting_escrow.locked(user1)[0] == user1_deposit_amount
    assert voting_escrow.locked(user1)[1] == user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS
    assert voting_escrow.user_point_history(user1, 0) == (0, 0, 0, 0)
    assert voting_escrow.user_point_history(user1, 1)[0] == (user1_deposit_amount // MAXTIME) * period_user1  # bias
    assert voting_escrow.user_point_history(user1, 1)[1] == (user1_deposit_amount // MAXTIME)  # slope
    assert voting_escrow.user_point_history(user1, 1)[2] == tx_lock_user1.timestamp  # ts
    assert voting_escrow.user_point_history(user1, 1)[3] == tx_lock_user1.block_number  # blk
    assert voting_escrow.user_point_history(user1, 2) == (0, 0, 0, 0)
    # number perfect user 2
    assert voting_escrow.locked(user2)[0] == user2_deposit_amount
    assert voting_escrow.locked(user2)[1] == user2_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS
    period_user2 = user2_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS - tx_lock_user2.timestamp
    assert voting_escrow.user_point_history(user2, 0) == (0, 0, 0, 0)
    assert voting_escrow.user_point_history(user2, 1)[0] == (user2_deposit_amount // MAXTIME) * period_user2  # bias
    assert voting_escrow.user_point_history(user2, 1)[1] == (user2_deposit_amount // MAXTIME)  # slope
    assert voting_escrow.user_point_history(user2, 1)[2] == tx_lock_user2.timestamp  # ts
    assert voting_escrow.user_point_history(user2, 1)[3] == tx_lock_user2.block_number  # blk
    assert voting_escrow.user_point_history(user2, 2) == (0, 0, 0, 0)
    # number perfect general state
    assert voting_escrow.point_history(epoch_after_user2_lock)[0] == (user2_deposit_amount // MAXTIME) * period_user2 + (user1_deposit_amount // MAXTIME) * (period_user1 - (user2_deposit_at - user1_deposit_at))
    assert voting_escrow.point_history(epoch_after_user2_lock)[1] == (user2_deposit_amount // MAXTIME) + (user1_deposit_amount // MAXTIME)
    assert voting_escrow.point_history(epoch_after_user2_lock)[2] == tx_lock_user2.timestamp
    assert voting_escrow.point_history(epoch_after_user2_lock)[3] == tx_lock_user2.block_number

    if 1 or user2_deposit_at == user1_deposit_at:  # bad unit test (it may fail just rerun test)
        assert voting_escrow.slope_changes(user2_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS) == -(user2_deposit_amount // MAXTIME) - (user1_deposit_amount // MAXTIME)
    else:  # bad unit test
        assert 0

    chain.sleep(sleep)
    voting_escrow.checkpoint()
    assert voting_escrow.epoch() == 3

    assert voting_escrow.window_token_rewards(2, token) == 0
    token.approve(voting_escrow, reward_amount)
    voting_escrow.receiveReward(token, reward_amount, {"from": payer})
    assert voting_escrow.epoch() == 3
    reward_epoch1 = voting_escrow.epoch()

    chain.sleep(sleep)
    voting_escrow.checkpoint()
    assert voting_escrow.epoch() == 4


    start_ts = voting_escrow.point_history(reward_epoch1)[2]
    end_ts = voting_escrow.point_history(reward_epoch1+1)[2]

    user1_start_balance = voting_escrow.balanceOf(user1, start_ts)
    user1_end_balance = voting_escrow.balanceOf(user1, end_ts)
    user2_start_balance = voting_escrow.balanceOf(user2, start_ts)
    user2_end_balance = voting_escrow.balanceOf(user2, end_ts)
    supply_start = voting_escrow.point_history(reward_epoch1)[0]
    supply_end = voting_escrow.point_history(reward_epoch1+1)[0]

    assert user1_start_balance + user2_start_balance == supply_start
    assert user1_end_balance + user2_end_balance == supply_end

    user1_share = (user1_start_balance + user1_end_balance) / (supply_start + supply_end)
    user2_share = (user2_start_balance + user2_end_balance) / (supply_start + supply_end)

    print(f'start claim user1')
    print(f'reward_epoch1=       {reward_epoch1}')
    print(f'start_ts=            {start_ts}')
    print(f'end_ts=              {end_ts}')
    print(f'user1_start_balance= {user1_start_balance}')
    print(f'user1_end_balance=   {user1_end_balance}')
    print(f'user2_start_balance= {user2_start_balance}')
    print(f'user2_end_balance=   {user2_end_balance}')
    print(f'supply_start=        {supply_start}')
    print(f'supply_end=          {supply_end}')
    print(f'user1_share=         {user1_share}')
    print(f'user2_share=         {user2_share}')

    claimable = voting_escrow.user_token_claimable_rewards(user1, token)
    tx = voting_escrow.claim_rewards(token, {"from": user1})
    assert claimable == tx.events['UserRewardsClaimed']['amount']
    assert tx.events['UserRewardsClaimed']['amount'] // 1000 == int(reward_amount * user1_share)  // 1000
    assert voting_escrow.user_token_claimed_epoch(user1, token) == 3

    print(f'start claim user2')
    tx = voting_escrow.claim_rewards(token, {"from": user2})
    print(f"{tx.events['_averageUserBlanaceOverEpochDebug']=}\n")
    print(f"{tx.events['_averageUserBlanaceOverEpochDebugS']=}\n")
    print(f"{tx.events['UserRewardsClaimedDebug']=}\n")
    assert tx.events['UserRewardsClaimed']['amount'] // 1000 == reward_amount * user2_share // 1000
    assert voting_escrow.user_token_claimed_epoch(user2, token) == 3


def test_share_rewards_2users_3h_deposit(web3, chain, accounts, token, voting_escrow):
    sleep = 3600
    EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
    MAXTIME = voting_escrow.MAXTIME()
    payer = accounts[0]
    reward_amount = 10**18
    deposit = 10**18
    user1 = accounts[1]
    user2 = accounts[2]

    assert voting_escrow.epoch() == 0
    assert voting_escrow.window_token_rewards(0, token) == 0

    chain.sleep(sleep)
    user1_deposit_amount = deposit
    user1_deposit_till = chain.time() + EPOCH_SECONDS*10
    token.transfer(user1, user1_deposit_amount)
    token.approve(voting_escrow, user1_deposit_amount, {"from": user1})
    tx_lock_user1 = voting_escrow.create_lock(user1_deposit_amount, user1_deposit_till, {"from": user1})
    user1_deposit_at = tx_lock_user1.timestamp
    epoch_after_user1_lock = voting_escrow.epoch()

    # number perfect check
    assert voting_escrow.locked(user1)[0] == user1_deposit_amount
    assert voting_escrow.locked(user1)[1] == user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS
    period_user1 = user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS - tx_lock_user1.timestamp
    assert voting_escrow.user_point_history(user1, 0) == (0, 0, 0, 0)
    assert voting_escrow.user_point_history(user1, 1)[0] == (user1_deposit_amount // MAXTIME) * period_user1  # bias
    assert voting_escrow.user_point_history(user1, 1)[1] == (user1_deposit_amount // MAXTIME)  # slope
    assert voting_escrow.user_point_history(user1, 1)[2] == tx_lock_user1.timestamp  # ts
    assert voting_escrow.user_point_history(user1, 1)[3] == tx_lock_user1.block_number  # blk
    assert voting_escrow.user_point_history(user1, 2) == (0, 0, 0, 0)
    assert voting_escrow.point_history(epoch_after_user1_lock)[0] == (user1_deposit_amount // MAXTIME) * period_user1
    assert voting_escrow.point_history(epoch_after_user1_lock)[1] == (user1_deposit_amount // MAXTIME)
    assert voting_escrow.point_history(epoch_after_user1_lock)[2] == tx_lock_user1.timestamp
    assert voting_escrow.point_history(epoch_after_user1_lock)[3] == tx_lock_user1.block_number
    assert voting_escrow.slope_changes(user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS) == -(user1_deposit_amount // MAXTIME)

    chain.sleep(3 * 3600)  # sleep for 3 hours

    user2_deposit_amount = deposit * 2
    user2_deposit_till = chain.time() + EPOCH_SECONDS*10
    token.transfer(user2, user2_deposit_amount)
    token.approve(voting_escrow, user2_deposit_amount, {"from": user2})
    tx_lock_user2 = voting_escrow.create_lock(user2_deposit_amount, user2_deposit_till, {"from": user2})
    assert voting_escrow.epoch() == 2
    user2_deposit_at = tx_lock_user2.timestamp
    epoch_after_user2_lock = voting_escrow.epoch()

    # number perfect user 1
    assert voting_escrow.locked(user1)[0] == user1_deposit_amount
    assert voting_escrow.locked(user1)[1] == user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS
    assert voting_escrow.user_point_history(user1, 0) == (0, 0, 0, 0)
    assert voting_escrow.user_point_history(user1, 1)[0] == (user1_deposit_amount // MAXTIME) * period_user1  # bias
    assert voting_escrow.user_point_history(user1, 1)[1] == (user1_deposit_amount // MAXTIME)  # slope
    assert voting_escrow.user_point_history(user1, 1)[2] == tx_lock_user1.timestamp  # ts
    assert voting_escrow.user_point_history(user1, 1)[3] == tx_lock_user1.block_number  # blk
    assert voting_escrow.user_point_history(user1, 2) == (0, 0, 0, 0)
    # number perfect user 2
    assert voting_escrow.locked(user2)[0] == user2_deposit_amount
    assert voting_escrow.locked(user2)[1] == user2_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS
    period_user2 = user2_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS - tx_lock_user2.timestamp
    assert voting_escrow.user_point_history(user2, 0) == (0, 0, 0, 0)
    assert voting_escrow.user_point_history(user2, 1)[0] == (user2_deposit_amount // MAXTIME) * period_user2  # bias
    assert voting_escrow.user_point_history(user2, 1)[1] == (user2_deposit_amount // MAXTIME)  # slope
    assert voting_escrow.user_point_history(user2, 1)[2] == tx_lock_user2.timestamp  # ts
    assert voting_escrow.user_point_history(user2, 1)[3] == tx_lock_user2.block_number  # blk
    assert voting_escrow.user_point_history(user2, 2) == (0, 0, 0, 0)
    # number perfect general state
    assert voting_escrow.point_history(epoch_after_user2_lock)[0] == (user2_deposit_amount // MAXTIME) * period_user2 + (user1_deposit_amount // MAXTIME) * (period_user1 - (user2_deposit_at - user1_deposit_at))
    assert voting_escrow.point_history(epoch_after_user2_lock)[1] == (user2_deposit_amount // MAXTIME) + (user1_deposit_amount // MAXTIME)
    assert voting_escrow.point_history(epoch_after_user2_lock)[2] == tx_lock_user2.timestamp
    assert voting_escrow.point_history(epoch_after_user2_lock)[3] == tx_lock_user2.block_number

    if 1 or user2_deposit_at == user1_deposit_at:  # bad unit test (it may fail just rerun test)
        assert voting_escrow.slope_changes(user2_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS) == -(user2_deposit_amount // MAXTIME) - (user1_deposit_amount // MAXTIME)
    else:  # bad unit test
        assert 0

    chain.sleep(sleep)
    voting_escrow.checkpoint()
    assert voting_escrow.epoch() == 3

    assert voting_escrow.window_token_rewards(2, token) == 0
    token.approve(voting_escrow, reward_amount)
    voting_escrow.receiveReward(token, reward_amount, {"from": payer})
    assert voting_escrow.epoch() == 3
    reward_epoch1 = voting_escrow.epoch()

    chain.sleep(sleep+60)
    voting_escrow.checkpoint()
    assert voting_escrow.epoch() == 5


    start_ts = voting_escrow.point_history(reward_epoch1)[2]
    end_ts = voting_escrow.point_history(reward_epoch1+1)[2]

    user1_start_balance = voting_escrow.balanceOf(user1, start_ts)
    user1_end_balance = voting_escrow.balanceOf(user1, end_ts)
    user2_start_balance = voting_escrow.balanceOf(user2, start_ts)
    user2_end_balance = voting_escrow.balanceOf(user2, end_ts)
    supply_start = voting_escrow.point_history(reward_epoch1)[0]
    supply_end = voting_escrow.point_history(reward_epoch1+1)[0]

    assert user1_start_balance + user2_start_balance == supply_start
    assert user1_end_balance + user2_end_balance == supply_end

    user1_share = (user1_start_balance + user1_end_balance) / (supply_start + supply_end)
    user2_share = (user2_start_balance + user2_end_balance) / (supply_start + supply_end)

    print(f'start claim user1')
    print(f'reward_epoch1=       {reward_epoch1}')
    print(f'start_ts=            {start_ts}')
    print(f'end_ts=              {end_ts}')
    print(f'user1_start_balance= {user1_start_balance}')
    print(f'user1_end_balance=   {user1_end_balance}')
    print(f'user2_start_balance= {user2_start_balance}')
    print(f'user2_end_balance=   {user2_end_balance}')
    print(f'supply_start=        {supply_start}')
    print(f'supply_end=          {supply_end}')
    print(f'user1_share=         {user1_share}')
    print(f'user2_share=         {user2_share}')

    tx = voting_escrow.claim_rewards(token, {"from": user1})

    pretty_events(chain, tx.txid)

    # print(f"{tx.events['_averageUserBlanaceOverEpochDebug']=}\n")
    # print(f"{tx.events['_averageUserBlanaceOverEpochDebugS']=}\n")
    # print(f"{tx.events['UserRewardsClaimedDebug']=}\n")
    assert tx.events['UserRewardsClaimed']['amount'] // 1000 == int(reward_amount * user1_share)  // 1000
    assert voting_escrow.user_token_claimed_epoch(user1, token) == 4

    print(f'start claim user2')
    tx = voting_escrow.claim_rewards(token, {"from": user2})
    print(f"{tx.events['_averageUserBlanaceOverEpochDebug']=}\n")
    print(f"{tx.events['_averageUserBlanaceOverEpochDebugS']=}\n")
    print(f"{tx.events['UserRewardsClaimedDebug']=}\n")
    assert tx.events['UserRewardsClaimed']['amount'] // 1000 == reward_amount * user2_share // 1000
    assert voting_escrow.user_token_claimed_epoch(user2, token) == 4


def test_share_1user_lock1year_after_10epochs_checkpoint(web3, chain, accounts, token, voting_escrow):
    sleep = 3600
    EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
    MAXTIME = voting_escrow.MAXTIME()
    payer = accounts[0]
    reward_amount = 10**18
    deposit = 10**18
    user1 = accounts[1]
    user2 = accounts[2]

    assert voting_escrow.epoch() == 0
    assert voting_escrow.window_token_rewards(0, token) == 0

    chain.sleep(sleep)
    user1_deposit_amount = deposit
    user1_deposit_till = chain.time() + 365 * 24 * 3600
    token.transfer(user1, user1_deposit_amount)
    token.approve(voting_escrow, user1_deposit_amount, {"from": user1})
    tx_lock_user1 = voting_escrow.create_lock(user1_deposit_amount, user1_deposit_till, {"from": user1})
    user1_deposit_at = tx_lock_user1.timestamp
    epoch_after_user1_lock = voting_escrow.epoch()

    # number perfect check
    assert voting_escrow.locked(user1)[0] == user1_deposit_amount
    assert voting_escrow.locked(user1)[1] == user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS
    period_user1 = user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS - tx_lock_user1.timestamp
    assert voting_escrow.user_point_history(user1, 0) == (0, 0, 0, 0)
    assert voting_escrow.user_point_history(user1, 1)[0] == (user1_deposit_amount // MAXTIME) * period_user1  # bias
    user1_slope = voting_escrow.user_point_history(user1, 1)[1]
    assert voting_escrow.user_point_history(user1, 1)[1] == (user1_deposit_amount // MAXTIME)  # slope
    assert voting_escrow.user_point_history(user1, 1)[2] == tx_lock_user1.timestamp  # ts
    assert voting_escrow.user_point_history(user1, 1)[3] == tx_lock_user1.block_number  # blk
    assert voting_escrow.user_point_history(user1, 2) == (0, 0, 0, 0)
    assert voting_escrow.point_history(epoch_after_user1_lock)[0] == (user1_deposit_amount // MAXTIME) * period_user1
    assert voting_escrow.point_history(epoch_after_user1_lock)[1] == (user1_deposit_amount // MAXTIME)
    assert voting_escrow.point_history(epoch_after_user1_lock)[2] == tx_lock_user1.timestamp
    assert voting_escrow.point_history(epoch_after_user1_lock)[3] == tx_lock_user1.block_number
    assert voting_escrow.slope_changes(user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS) == -(user1_deposit_amount // MAXTIME)

    chain.sleep(10 * EPOCH_SECONDS)  # sleep for 10 epochs
    tx2 = voting_escrow.checkpoint()

    epoch_after = voting_escrow.epoch()
    assert epoch_after == 12

    # number perfect user 1
    assert voting_escrow.locked(user1)[0] == user1_deposit_amount
    assert voting_escrow.locked(user1)[1] == user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS
    assert voting_escrow.user_point_history(user1, 0) == (0, 0, 0, 0)
    assert voting_escrow.user_point_history(user1, 1)[0] == (user1_deposit_amount // MAXTIME) * period_user1  # bias
    assert voting_escrow.user_point_history(user1, 1)[1] == (user1_deposit_amount // MAXTIME)  # slope
    assert voting_escrow.user_point_history(user1, 1)[2] == tx_lock_user1.timestamp  # ts
    assert voting_escrow.user_point_history(user1, 1)[3] == tx_lock_user1.block_number  # blk
    assert voting_escrow.user_point_history(user1, 2) == (0, 0, 0, 0)
    # number perfect general state
    assert voting_escrow.point_history(epoch_after)[0] == (
            (user1_deposit_amount // MAXTIME) * period_user1 -
            user1_slope * (tx2.timestamp - user1_deposit_at)
    )
    assert voting_escrow.point_history(epoch_after)[1] == (user1_deposit_amount // MAXTIME)
    assert voting_escrow.point_history(epoch_after)[2] == tx2.timestamp
    assert voting_escrow.point_history(epoch_after)[3] == tx2.block_number


def test_share_1user_lock3epochs_after_10epochs_checkpoint(web3, chain, accounts, token, voting_escrow):
    sleep = 3600
    EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
    MAXTIME = voting_escrow.MAXTIME()
    payer = accounts[0]
    reward_amount = 10**18
    deposit = 10**18
    user1 = accounts[1]
    user2 = accounts[2]

    assert voting_escrow.epoch() == 0
    assert voting_escrow.window_token_rewards(0, token) == 0

    chain.sleep(sleep)
    user1_deposit_amount = deposit
    user1_deposit_till = chain.time() + 3 * EPOCH_SECONDS
    token.transfer(user1, user1_deposit_amount)
    token.approve(voting_escrow, user1_deposit_amount, {"from": user1})
    tx_lock_user1 = voting_escrow.create_lock(user1_deposit_amount, user1_deposit_till, {"from": user1})
    user1_deposit_at = tx_lock_user1.timestamp
    epoch_after_user1_lock = voting_escrow.epoch()

    # number perfect check
    assert voting_escrow.locked(user1)[0] == user1_deposit_amount
    assert voting_escrow.locked(user1)[1] == user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS
    period_user1 = user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS - tx_lock_user1.timestamp
    assert voting_escrow.user_point_history(user1, 0) == (0, 0, 0, 0)
    assert voting_escrow.user_point_history(user1, 1)[0] == (user1_deposit_amount // MAXTIME) * period_user1  # bias
    user1_slope = voting_escrow.user_point_history(user1, 1)[1]
    assert voting_escrow.user_point_history(user1, 1)[1] == (user1_deposit_amount // MAXTIME)  # slope
    assert voting_escrow.user_point_history(user1, 1)[2] == tx_lock_user1.timestamp  # ts
    assert voting_escrow.user_point_history(user1, 1)[3] == tx_lock_user1.block_number  # blk
    assert voting_escrow.user_point_history(user1, 2) == (0, 0, 0, 0)
    assert voting_escrow.point_history(epoch_after_user1_lock)[0] == (user1_deposit_amount // MAXTIME) * period_user1
    assert voting_escrow.point_history(epoch_after_user1_lock)[1] == (user1_deposit_amount // MAXTIME)
    assert voting_escrow.point_history(epoch_after_user1_lock)[2] == tx_lock_user1.timestamp
    assert voting_escrow.point_history(epoch_after_user1_lock)[3] == tx_lock_user1.block_number
    assert voting_escrow.slope_changes(user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS) == -(user1_deposit_amount // MAXTIME)

    chain.sleep(10 * EPOCH_SECONDS)  # sleep for 10 epochs
    tx2 = voting_escrow.checkpoint()

    epoch_after = voting_escrow.epoch()
    assert epoch_after == 12

    # number perfect general state
    assert voting_escrow.point_history(epoch_after)[0] == 0
    assert voting_escrow.point_history(epoch_after)[1] == 0
    assert voting_escrow.point_history(epoch_after)[2] == tx2.timestamp
    assert voting_escrow.point_history(epoch_after)[3] == tx2.block_number


def test_share_rewards_2users_lock100epochs_10epochs_deposit(web3, chain, accounts, token, voting_escrow):
    sleep = 3600
    EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
    MAXTIME = voting_escrow.MAXTIME()
    payer = accounts[0]
    reward_amount = 10**18
    deposit = 10**18
    user1 = accounts[1]
    user2 = accounts[2]

    assert voting_escrow.epoch() == 0
    assert voting_escrow.window_token_rewards(0, token) == 0

    chain.sleep(sleep)
    user1_deposit_amount = deposit
    user1_deposit_till = chain.time() + EPOCH_SECONDS*100
    token.transfer(user1, user1_deposit_amount)
    token.approve(voting_escrow, user1_deposit_amount, {"from": user1})
    tx_lock_user1 = voting_escrow.create_lock(user1_deposit_amount, user1_deposit_till, {"from": user1})
    user1_deposit_at = tx_lock_user1.timestamp
    epoch_after_user1_lock = voting_escrow.epoch()

    # number perfect check
    assert voting_escrow.locked(user1)[0] == user1_deposit_amount
    assert voting_escrow.locked(user1)[1] == user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS
    period_user1 = user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS - tx_lock_user1.timestamp
    assert voting_escrow.user_point_history(user1, 0) == (0, 0, 0, 0)
    assert voting_escrow.user_point_history(user1, 1)[0] == (user1_deposit_amount // MAXTIME) * period_user1  # bias
    user1_slope = voting_escrow.user_point_history(user1, 1)[1]
    assert voting_escrow.user_point_history(user1, 1)[1] == (user1_deposit_amount // MAXTIME)  # slope
    assert voting_escrow.user_point_history(user1, 1)[2] == tx_lock_user1.timestamp  # ts
    assert voting_escrow.user_point_history(user1, 1)[3] == tx_lock_user1.block_number  # blk
    assert voting_escrow.user_point_history(user1, 2) == (0, 0, 0, 0)
    assert voting_escrow.point_history(epoch_after_user1_lock)[0] == (user1_deposit_amount // MAXTIME) * period_user1
    assert voting_escrow.point_history(epoch_after_user1_lock)[1] == (user1_deposit_amount // MAXTIME)
    assert voting_escrow.point_history(epoch_after_user1_lock)[2] == tx_lock_user1.timestamp
    assert voting_escrow.point_history(epoch_after_user1_lock)[3] == tx_lock_user1.block_number
    assert voting_escrow.slope_changes(user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS) == -(user1_deposit_amount // MAXTIME)

    chain.sleep(10 * EPOCH_SECONDS)  # sleep for 10 epochs

    user2_deposit_amount = deposit * 2
    user2_deposit_till = chain.time() + EPOCH_SECONDS*100
    token.transfer(user2, user2_deposit_amount)
    token.approve(voting_escrow, user2_deposit_amount, {"from": user2})
    tx_lock_user2 = voting_escrow.create_lock(user2_deposit_amount, user2_deposit_till, {"from": user2})
    epoch_after_user2_lock = voting_escrow.epoch()
    assert epoch_after_user2_lock == 12
    user2_deposit_at = tx_lock_user2.timestamp

    # number perfect user 1
    assert voting_escrow.locked(user1)[0] == user1_deposit_amount
    assert voting_escrow.locked(user1)[1] == user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS
    assert voting_escrow.user_point_history(user1, 0) == (0, 0, 0, 0)
    assert voting_escrow.user_point_history(user1, 1)[0] == (user1_deposit_amount // MAXTIME) * period_user1  # bias
    assert voting_escrow.user_point_history(user1, 1)[1] == (user1_deposit_amount // MAXTIME)  # slope
    assert voting_escrow.user_point_history(user1, 1)[2] == tx_lock_user1.timestamp  # ts
    assert voting_escrow.user_point_history(user1, 1)[3] == tx_lock_user1.block_number  # blk
    assert voting_escrow.user_point_history(user1, 2) == (0, 0, 0, 0)
    # number perfect user 2
    assert voting_escrow.locked(user2)[0] == user2_deposit_amount
    assert voting_escrow.locked(user2)[1] == user2_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS
    period_user2 = user2_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS - tx_lock_user2.timestamp
    assert voting_escrow.user_point_history(user2, 0) == (0, 0, 0, 0)
    assert voting_escrow.user_point_history(user2, 1)[0] == (user2_deposit_amount // MAXTIME) * period_user2  # bias
    assert voting_escrow.user_point_history(user2, 1)[1] == (user2_deposit_amount // MAXTIME)  # slope
    assert voting_escrow.user_point_history(user2, 1)[2] == tx_lock_user2.timestamp  # ts
    assert voting_escrow.user_point_history(user2, 1)[3] == tx_lock_user2.block_number  # blk
    assert voting_escrow.user_point_history(user2, 2) == (0, 0, 0, 0)
    # number perfect general state
    assert voting_escrow.point_history(epoch_after_user2_lock)[0] == (
            (user2_deposit_amount // MAXTIME) * period_user2 +
            (user1_deposit_amount // MAXTIME) * period_user1 -
            user1_slope * (user2_deposit_at - user1_deposit_at)
    )
    assert voting_escrow.point_history(epoch_after_user2_lock)[1] == (user2_deposit_amount // MAXTIME) + (user1_deposit_amount // MAXTIME)
    assert voting_escrow.point_history(epoch_after_user2_lock)[2] == tx_lock_user2.timestamp
    assert voting_escrow.point_history(epoch_after_user2_lock)[3] == tx_lock_user2.block_number

    chain.sleep(sleep)
    voting_escrow.checkpoint()
    assert voting_escrow.epoch() == 13

    assert voting_escrow.window_token_rewards(2, token) == 0
    token.approve(voting_escrow, reward_amount)
    voting_escrow.receiveReward(token, reward_amount, {"from": payer})
    assert voting_escrow.epoch() == 13
    reward_epoch1 = voting_escrow.epoch()

    chain.sleep(sleep)
    voting_escrow.checkpoint()
    assert voting_escrow.epoch() == 14


    start_ts = voting_escrow.point_history(reward_epoch1)[2]
    end_ts = voting_escrow.point_history(reward_epoch1+1)[2]

    user1_start_balance = voting_escrow.balanceOf(user1, start_ts)
    user1_end_balance = voting_escrow.balanceOf(user1, end_ts)
    user2_start_balance = voting_escrow.balanceOf(user2, start_ts)
    user2_end_balance = voting_escrow.balanceOf(user2, end_ts)
    supply_start = voting_escrow.point_history(reward_epoch1)[0]
    supply_end = voting_escrow.point_history(reward_epoch1+1)[0]

    assert user1_start_balance + user2_start_balance == supply_start
    assert user1_end_balance + user2_end_balance == supply_end

    user1_share = (user1_start_balance + user1_end_balance) / (supply_start + supply_end)
    user2_share = (user2_start_balance + user2_end_balance) / (supply_start + supply_end)

    print(f'start claim user1')
    print(f'reward_epoch1=       {reward_epoch1}')
    print(f'start_ts=            {start_ts}')
    print(f'end_ts=              {end_ts}')
    print(f'user1_start_balance= {user1_start_balance}')
    print(f'user1_end_balance=   {user1_end_balance}')
    print(f'user2_start_balance= {user2_start_balance}')
    print(f'user2_end_balance=   {user2_end_balance}')
    print(f'supply_start=        {supply_start}')
    print(f'supply_end=          {supply_end}')
    print(f'user1_share=         {user1_share}')
    print(f'user2_share=         {user2_share}')

    tx = voting_escrow.claim_rewards(token, {"from": user1})

    pretty_events(chain, tx.txid)

    # print(f"{tx.events['_averageUserBlanaceOverEpochDebug']=}\n")
    # print(f"{tx.events['_averageUserBlanaceOverEpochDebugS']=}\n")
    # print(f"{tx.events['UserRewardsClaimedDebug']=}\n")
    assert tx.events['UserRewardsClaimed']['amount'] // 1000 == int(reward_amount * user1_share)  // 1000
    assert voting_escrow.user_token_claimed_epoch(user1, token) == 13

    print(f'start claim user2')
    tx = voting_escrow.claim_rewards(token, {"from": user2})
    print(f"{tx.events['_averageUserBlanaceOverEpochDebug']=}\n")
    print(f"{tx.events['_averageUserBlanaceOverEpochDebugS']=}\n")
    print(f"{tx.events['UserRewardsClaimedDebug']=}\n")
    assert tx.events['UserRewardsClaimed']['amount'] // 1000 == reward_amount * user2_share // 1000
    assert voting_escrow.user_token_claimed_epoch(user2, token) == 13


def test_share_rewards_2users_lock3epochs_10epochs_deposit(web3, chain, accounts, token, voting_escrow):
    sleep = 3600
    EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
    MAXTIME = voting_escrow.MAXTIME()
    payer = accounts[0]
    reward_amount = 10**18
    deposit = 10**18
    user1 = accounts[1]
    user2 = accounts[2]

    assert voting_escrow.epoch() == 0
    assert voting_escrow.window_token_rewards(0, token) == 0

    chain.sleep(sleep)
    user1_deposit_amount = deposit
    user1_deposit_till = chain.time() + EPOCH_SECONDS*3
    token.transfer(user1, user1_deposit_amount)
    token.approve(voting_escrow, user1_deposit_amount, {"from": user1})
    tx_lock_user1 = voting_escrow.create_lock(user1_deposit_amount, user1_deposit_till, {"from": user1})
    user1_deposit_at = tx_lock_user1.timestamp
    epoch_after_user1_lock = voting_escrow.epoch()

    # number perfect check
    assert voting_escrow.locked(user1)[0] == user1_deposit_amount
    assert voting_escrow.locked(user1)[1] == user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS
    period_user1 = user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS - tx_lock_user1.timestamp
    assert voting_escrow.user_point_history(user1, 0) == (0, 0, 0, 0)
    assert voting_escrow.user_point_history(user1, 1)[0] == (user1_deposit_amount // MAXTIME) * period_user1  # bias
    user1_slope = voting_escrow.user_point_history(user1, 1)[1]
    assert voting_escrow.user_point_history(user1, 1)[1] == (user1_deposit_amount // MAXTIME)  # slope
    assert voting_escrow.user_point_history(user1, 1)[2] == tx_lock_user1.timestamp  # ts
    assert voting_escrow.user_point_history(user1, 1)[3] == tx_lock_user1.block_number  # blk
    assert voting_escrow.user_point_history(user1, 2) == (0, 0, 0, 0)
    assert voting_escrow.point_history(epoch_after_user1_lock)[0] == (user1_deposit_amount // MAXTIME) * period_user1
    assert voting_escrow.point_history(epoch_after_user1_lock)[1] == (user1_deposit_amount // MAXTIME)
    assert voting_escrow.point_history(epoch_after_user1_lock)[2] == tx_lock_user1.timestamp
    assert voting_escrow.point_history(epoch_after_user1_lock)[3] == tx_lock_user1.block_number
    assert voting_escrow.slope_changes(user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS) == -(user1_deposit_amount // MAXTIME)

    chain.sleep(10 * EPOCH_SECONDS)  # sleep for 10 epochs

    user2_deposit_amount = deposit * 2
    user2_deposit_till = chain.time() + EPOCH_SECONDS*3
    token.transfer(user2, user2_deposit_amount)
    token.approve(voting_escrow, user2_deposit_amount, {"from": user2})
    tx_lock_user2 = voting_escrow.create_lock(user2_deposit_amount, user2_deposit_till, {"from": user2})
    epoch_after_user2_lock = voting_escrow.epoch()
    assert epoch_after_user2_lock == 12
    user2_deposit_at = tx_lock_user2.timestamp

    # number perfect user 1
    assert voting_escrow.locked(user1)[0] == user1_deposit_amount
    assert voting_escrow.locked(user1)[1] == user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS
    assert voting_escrow.user_point_history(user1, 0) == (0, 0, 0, 0)
    assert voting_escrow.user_point_history(user1, 1)[0] == (user1_deposit_amount // MAXTIME) * period_user1  # bias
    assert voting_escrow.user_point_history(user1, 1)[1] == (user1_deposit_amount // MAXTIME)  # slope
    assert voting_escrow.user_point_history(user1, 1)[2] == tx_lock_user1.timestamp  # ts
    assert voting_escrow.user_point_history(user1, 1)[3] == tx_lock_user1.block_number  # blk
    assert voting_escrow.user_point_history(user1, 2) == (0, 0, 0, 0)
    # number perfect user 2
    assert voting_escrow.locked(user2)[0] == user2_deposit_amount
    assert voting_escrow.locked(user2)[1] == user2_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS
    period_user2 = user2_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS - tx_lock_user2.timestamp
    assert voting_escrow.user_point_history(user2, 0) == (0, 0, 0, 0)
    assert voting_escrow.user_point_history(user2, 1)[0] == (user2_deposit_amount // MAXTIME) * period_user2  # bias
    assert voting_escrow.user_point_history(user2, 1)[1] == (user2_deposit_amount // MAXTIME)  # slope
    assert voting_escrow.user_point_history(user2, 1)[2] == tx_lock_user2.timestamp  # ts
    assert voting_escrow.user_point_history(user2, 1)[3] == tx_lock_user2.block_number  # blk
    assert voting_escrow.user_point_history(user2, 2) == (0, 0, 0, 0)
    # number perfect general state
    assert voting_escrow.point_history(epoch_after_user2_lock)[0] == (
            (user2_deposit_amount // MAXTIME) * period_user2
    )
    assert voting_escrow.point_history(epoch_after_user2_lock)[1] == (user2_deposit_amount // MAXTIME)
    assert voting_escrow.point_history(epoch_after_user2_lock)[2] == tx_lock_user2.timestamp
    assert voting_escrow.point_history(epoch_after_user2_lock)[3] == tx_lock_user2.block_number

    if 1 or user2_deposit_at == user1_deposit_at:  # bad unit test (it may fail just rerun test)
        assert voting_escrow.slope_changes(user2_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS) == \
               -(user2_deposit_amount // MAXTIME)
    else:  # bad unit test
        assert 0

    chain.sleep(sleep)
    voting_escrow.checkpoint()
    assert voting_escrow.epoch() == 13

    assert voting_escrow.window_token_rewards(2, token) == 0
    token.approve(voting_escrow, reward_amount)
    voting_escrow.receiveReward(token, reward_amount, {"from": payer})
    assert voting_escrow.epoch() == 13
    reward_epoch1 = voting_escrow.epoch()

    chain.sleep(sleep)
    voting_escrow.checkpoint()
    assert voting_escrow.epoch() == 14


    start_ts = voting_escrow.point_history(reward_epoch1)[2]
    end_ts = voting_escrow.point_history(reward_epoch1+1)[2]

    user1_start_balance = voting_escrow.balanceOf(user1, start_ts)
    user1_end_balance = voting_escrow.balanceOf(user1, end_ts)
    user2_start_balance = voting_escrow.balanceOf(user2, start_ts)
    user2_end_balance = voting_escrow.balanceOf(user2, end_ts)
    supply_start = voting_escrow.point_history(reward_epoch1)[0]
    supply_end = voting_escrow.point_history(reward_epoch1+1)[0]

    assert user1_start_balance + user2_start_balance == supply_start
    assert user1_end_balance + user2_end_balance == supply_end

    user1_share = (user1_start_balance + user1_end_balance) / (supply_start + supply_end)
    user2_share = (user2_start_balance + user2_end_balance) / (supply_start + supply_end)

    print(f'start claim user1')
    print(f'reward_epoch1=       {reward_epoch1}')
    print(f'start_ts=            {start_ts}')
    print(f'end_ts=              {end_ts}')
    print(f'user1_start_balance= {user1_start_balance}')
    print(f'user1_end_balance=   {user1_end_balance}')
    print(f'user2_start_balance= {user2_start_balance}')
    print(f'user2_end_balance=   {user2_end_balance}')
    print(f'supply_start=        {supply_start}')
    print(f'supply_end=          {supply_end}')
    print(f'user1_share=         {user1_share}')
    print(f'user2_share=         {user2_share}')

    tx = voting_escrow.claim_rewards(token, {"from": user1})

    pretty_events(chain, tx.txid)

    # print(f"{tx.events['_averageUserBlanaceOverEpochDebug']=}\n")
    # print(f"{tx.events['_averageUserBlanaceOverEpochDebugS']=}\n")
    # print(f"{tx.events['UserRewardsClaimedDebug']=}\n")
    assert tx.events['UserRewardsClaimed']['amount'] // 1000 == int(reward_amount * user1_share)  // 1000
    assert voting_escrow.user_token_claimed_epoch(user1, token) == 13

    print(f'start claim user2')
    tx = voting_escrow.claim_rewards(token, {"from": user2})
    print(f"{tx.events['_averageUserBlanaceOverEpochDebug']=}\n")
    print(f"{tx.events['_averageUserBlanaceOverEpochDebugS']=}\n")
    print(f"{tx.events['UserRewardsClaimedDebug']=}\n")
    assert tx.events['UserRewardsClaimed']['amount'] // 1000 == reward_amount * user2_share // 1000
    assert voting_escrow.user_token_claimed_epoch(user2, token) == 13


# def test_share_rewards_3users_after_12_months(web3, chain, accounts, token, voting_escrow):
#     sleep = 3600
#     EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
#     payer = accounts[0]
#     reward_amount = 10**18
#     deposit = 10**18
#     user1 = accounts[1]
#     user2 = accounts[2]
#     user3 = accounts[3]
#
#     assert voting_escrow.epoch() == 0
#     assert voting_escrow.window_token_rewards(0, token) == 0
#
#     chain.sleep(sleep)
#     token.transfer(user1, deposit)
#     token.approve(voting_escrow, deposit, {"from": user1})
#     voting_escrow.create_lock(deposit, chain.time() + 2 * 365 * 24 * 3600, {"from": user1})
#
#     chain.sleep(sleep)
#
#     token.transfer(user2, deposit*2)
#     token.approve(voting_escrow, deposit*2, {"from": user2})
#     voting_escrow.create_lock(deposit*2, chain.time() + 2 * 365 * 24 * 3600, {"from": user2})
#     assert voting_escrow.epoch() == 2
#
#     chain.sleep(sleep)
#
#     token.transfer(user3, deposit*3)
#     token.approve(voting_escrow, deposit*3, {"from": user3})
#     voting_escrow.create_lock(deposit*3, chain.time() + 2 * 365 * 24 * 3600, {"from": user3})
#     assert voting_escrow.epoch() == 3
#
#     chain.sleep(sleep)
#     voting_escrow.checkpoint()
#     assert voting_escrow.epoch() == 4
#
#     token.approve(voting_escrow, reward_amount)
#     voting_escrow.receiveReward(token, reward_amount, {"from": payer})
#     assert voting_escrow.epoch() == 4
#     assert voting_escrow.window_token_rewards(4, token) == reward_amount
#
#     voting_escrow.checkpoint()
#     assert voting_escrow.epoch() == 5
#
#     print(f'start claim user1')
#     tx = voting_escrow.claim_rewards(token, {"from": user1})
#     print(f"{tx.events['_averageUserBlanaceOverEpochDebug']=}\n")
#     print(f"{tx.events['_averageUserBlanaceOverEpochDebugS']=}\n")
#     print(f"{tx.events['UserRewardsClaimedDebug']=}\n")
#     eq(tx.events['UserRewardsClaimed']['amount'], reward_amount * 1 / 6)
#     assert voting_escrow.user_token_claimed_epoch(user1, token) == 4
#
#     print(f'start claim user2')
#     tx = voting_escrow.claim_rewards(token, {"from": user2})
#     print(f"{tx.events['_averageUserBlanaceOverEpochDebug']=}\n")
#     print(f"{tx.events['_averageUserBlanaceOverEpochDebugS']=}\n")
#     print(f"{tx.events['UserRewardsClaimedDebug']=}\n")
#     eq(tx.events['UserRewardsClaimed']['amount'], reward_amount * 2 / 6)
#     assert voting_escrow.user_token_claimed_epoch(user2, token) == 4
#
#     print(f'start claim user3')
#     tx = voting_escrow.claim_rewards(token, {"from": user3})
#     print(f"{tx.events['_averageUserBlanaceOverEpochDebug']=}\n")
#     print(f"{tx.events['_averageUserBlanaceOverEpochDebugS']=}\n")
#     print(f"{tx.events['UserRewardsClaimedDebug']=}\n")
#     eq(tx.events['UserRewardsClaimed']['amount'], reward_amount * 3 / 6)
#     assert voting_escrow.user_token_claimed_epoch(user3, token) == 4
#
#     import random
#     acc_fee = 0
#     p = 6 * 3600
#     for i in range(int(3 * 30 * 24 * 3600 / p)):  # 12 months hours
#         chain.sleep(p)
#         if random.random() < 0.1:
#             token.approve(voting_escrow, reward_amount)
#             voting_escrow.receiveReward(token, reward_amount, {"from": payer})
#             acc_fee += reward_amount
#
#     acc1 = 0
#     for i in range(10):
#         tx = voting_escrow.claim_rewards(token, {"from": user1})
#         acc1 += tx.events['UserRewardsClaimed']['amount']
#     eq(acc1, acc_fee * 1 / 6)
#
#     acc2 = 0
#     for i in range(10):
#         tx = voting_escrow.claim_rewards(token, {"from": user2})
#         acc2 += tx.events['UserRewardsClaimed']['amount']
#     eq(acc2, acc_fee * 2 / 6)
#
#     acc3 = 0
#     for i in range(10):
#         tx = voting_escrow.claim_rewards(token, {"from": user3})
#         acc3 += tx.events['UserRewardsClaimed']['amount']
#     eq(acc3, acc_fee * 3 / 6)
