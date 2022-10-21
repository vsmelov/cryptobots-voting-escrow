# import time
# from dataclasses import dataclass
#
# import brownie
#
# from .utils import *
#
#
# @dataclass
# class Reward:
#     ts: int
#     amount: int
#
#
# @dataclass
# class UserLockIncrease:
#     ts: int
#     amount: int
#
#
# @dataclass
# class UserLock:
#     ts: int
#     amount: int
#
#
# @dataclass
# class Scenario:
#
#
#
# def test_share_rewards_2users_3h_deposit(web3, chain, accounts, token, voting_escrow):
#     EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
#     sleep = EPOCH_SECONDS
#     MAXTIME = voting_escrow.MAXTIME()
#     payer = accounts[0]
#     reward_amount = 10**18
#     deposit = 10**18
#     user1 = accounts[1]
#     user2 = accounts[2]
#
#     assert voting_escrow.epoch() == 0
#     assert voting_escrow.window_token_rewards(0, token) == 0
#
#     chain.sleep(sleep)
#     user1_deposit_amount = deposit
#     user1_deposit_till = chain.time() + EPOCH_SECONDS*10
#     token.transfer(user1, user1_deposit_amount)
#     token.approve(voting_escrow, user1_deposit_amount, {"from": user1})
#     tx_lock_user1 = voting_escrow.create_lock(user1_deposit_amount, user1_deposit_till, {"from": user1})
#     user1_deposit_at = tx_lock_user1.timestamp
#     epoch_after_user1_lock = voting_escrow.epoch()
#
#     # number perfect check
#     assert voting_escrow.locked(user1)[0] == user1_deposit_amount
#     assert voting_escrow.locked(user1)[1] == user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS
#     period_user1 = user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS - tx_lock_user1.timestamp
#     assert voting_escrow.user_point_history(user1, 0) == (0, 0, 0, 0)
#     assert voting_escrow.user_point_history(user1, 1)[0] == (user1_deposit_amount // MAXTIME) * period_user1  # bias
#     assert voting_escrow.user_point_history(user1, 1)[1] == (user1_deposit_amount // MAXTIME)  # slope
#     assert voting_escrow.user_point_history(user1, 1)[2] == tx_lock_user1.timestamp  # ts
#     assert voting_escrow.user_point_history(user1, 1)[3] == tx_lock_user1.block_number  # blk
#     assert voting_escrow.user_point_history(user1, 2) == (0, 0, 0, 0)
#     assert voting_escrow.point_history(epoch_after_user1_lock)[0] == (user1_deposit_amount // MAXTIME) * period_user1
#     assert voting_escrow.point_history(epoch_after_user1_lock)[1] == (user1_deposit_amount // MAXTIME)
#     assert voting_escrow.point_history(epoch_after_user1_lock)[2] == tx_lock_user1.timestamp
#     assert voting_escrow.point_history(epoch_after_user1_lock)[3] == tx_lock_user1.block_number
#     assert voting_escrow.slope_changes(user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS) == -(user1_deposit_amount // MAXTIME)
#
#     # 3h before user2 deposit
#     chain.sleep(3 * 3600)
#     chain.mine()
#
#     user2_deposit_amount = deposit * 2
#     user2_deposit_till = chain.time() + EPOCH_SECONDS*10
#     token.transfer(user2, user2_deposit_amount)
#     token.approve(voting_escrow, user2_deposit_amount, {"from": user2})
#     tx_lock_user2 = voting_escrow.create_lock(user2_deposit_amount, user2_deposit_till, {"from": user2})
#     assert voting_escrow.epoch() == 2
#     user2_deposit_at = tx_lock_user2.timestamp
#     epoch_after_user2_lock = voting_escrow.epoch()
#
#     # number perfect user 1
#     assert voting_escrow.locked(user1)[0] == user1_deposit_amount
#     assert voting_escrow.locked(user1)[1] == user1_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS
#     assert voting_escrow.user_point_history(user1, 0) == (0, 0, 0, 0)
#     assert voting_escrow.user_point_history(user1, 1)[0] == (user1_deposit_amount // MAXTIME) * period_user1  # bias
#     assert voting_escrow.user_point_history(user1, 1)[1] == (user1_deposit_amount // MAXTIME)  # slope
#     assert voting_escrow.user_point_history(user1, 1)[2] == tx_lock_user1.timestamp  # ts
#     assert voting_escrow.user_point_history(user1, 1)[3] == tx_lock_user1.block_number  # blk
#     assert voting_escrow.user_point_history(user1, 2) == (0, 0, 0, 0)
#     # number perfect user 2
#     assert voting_escrow.locked(user2)[0] == user2_deposit_amount
#     assert voting_escrow.locked(user2)[1] == user2_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS
#     period_user2 = user2_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS - tx_lock_user2.timestamp
#     assert voting_escrow.user_point_history(user2, 0) == (0, 0, 0, 0)
#     assert voting_escrow.user_point_history(user2, 1)[0] == (user2_deposit_amount // MAXTIME) * period_user2  # bias
#     assert voting_escrow.user_point_history(user2, 1)[1] == (user2_deposit_amount // MAXTIME)  # slope
#     assert voting_escrow.user_point_history(user2, 1)[2] == tx_lock_user2.timestamp  # ts
#     assert voting_escrow.user_point_history(user2, 1)[3] == tx_lock_user2.block_number  # blk
#     assert voting_escrow.user_point_history(user2, 2) == (0, 0, 0, 0)
#     # number perfect general state
#     assert voting_escrow.point_history(epoch_after_user2_lock)[0] == (user2_deposit_amount // MAXTIME) * period_user2 + (user1_deposit_amount // MAXTIME) * (period_user1 - (user2_deposit_at - user1_deposit_at))
#     assert voting_escrow.point_history(epoch_after_user2_lock)[1] == (user2_deposit_amount // MAXTIME) + (user1_deposit_amount // MAXTIME)
#     assert voting_escrow.point_history(epoch_after_user2_lock)[2] == tx_lock_user2.timestamp
#     assert voting_escrow.point_history(epoch_after_user2_lock)[3] == tx_lock_user2.block_number
#
#     if 1 or user2_deposit_at == user1_deposit_at:  # bad unit test (it may fail just rerun test)
#         assert voting_escrow.slope_changes(user2_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS) == \
#                -(user2_deposit_amount // MAXTIME) - (user1_deposit_amount // MAXTIME)
#     else:  # bad unit test
#         assert 0, "unlucky! rerun"
#
#     assert tx_lock_user1.timestamp // EPOCH_SECONDS == tx_lock_user2.timestamp // EPOCH_SECONDS
#     chain.sleep(sleep)
#
#     token.approve(voting_escrow, reward_amount)
#     tx = voting_escrow.receiveReward(token, reward_amount, {"from": payer})
#     reward_window1 = voting_escrow.currentWindow()
#     reward_epoch1 = voting_escrow.epoch()
#     assert voting_escrow.window_token_rewards(reward_window1, token) == reward_amount
#
#     chain.sleep(EPOCH_SECONDS)  # go into next window
#
#     start_ts = reward_window1
#     end_ts = reward_window1 + EPOCH_SECONDS
#
#     user1_start_balance = voting_escrow.balanceOf(user1, start_ts)
#     user1_end_balance = voting_escrow.balanceOf(user1, end_ts)
#     user2_start_balance = voting_escrow.balanceOf(user2, start_ts)
#     user2_end_balance = voting_escrow.balanceOf(user2, end_ts)
#     supply_start = voting_escrow.totalSupply(start_ts)
#     supply_end = voting_escrow.totalSupply(end_ts)
#
#     assert user1_start_balance + user2_start_balance == supply_start
#     assert user1_end_balance + user2_end_balance == supply_end
#
#     user1_share = (user1_start_balance + user1_end_balance) / (supply_start + supply_end)
#     user2_share = (user2_start_balance + user2_end_balance) / (supply_start + supply_end)
#
#     print(f'start claim user1')
#     claimable_tx = voting_escrow.user_token_claimable_rewardsTx(user1, token)
#     print(f'{claimable_tx.events=}')
#     claimable = voting_escrow.user_token_claimable_rewards(user1, token)
#     claim_tx1 = voting_escrow.claim_rewards(token, {"from": user1})
#     print(f"{claim_tx1.events=}")
#     assert claimable == claim_tx1.events['UserRewardsClaimed']['amount']
#     assert claim_tx1.events['UserRewardsClaimed']['amount'] // 1000 == int(reward_amount * user1_share) // 1000
#     assert voting_escrow.user_token_claimed_window(user1, token) == voting_escrow.currentWindow() - EPOCH_SECONDS
#
#     print(f'start claim user2')
#     claim_tx2 = voting_escrow.claim_rewards(token, {"from": user2})
#     print(f"{claim_tx2.events=}")
#     assert claim_tx2.events['UserRewardsClaimed']['amount'] // 1000 == reward_amount * user2_share // 1000
#     assert voting_escrow.user_token_claimed_window(user2, token) == voting_escrow.currentWindow() - EPOCH_SECONDS
