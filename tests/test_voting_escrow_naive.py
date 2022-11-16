from pytest import approx
import time

import brownie

from .utils import *


def test_share_rewards_2users_same_time_deposit(web3, chain, accounts, token, voting_escrow_naive):
    voting_escrow = voting_escrow_naive

    MAXTIME = voting_escrow.MAXTIME()
    payer = accounts[0]
    reward_amount = 10**18
    deposit = 10**18
    user1 = accounts[1]
    user2 = accounts[2]

    user1_deposit_amount = deposit
    user1_deposit_till = chain.time() + voting_escrow.WINDOW() + 3600 * 10
    token.transfer(user1, user1_deposit_amount)
    token.approve(voting_escrow, user1_deposit_amount, {"from": user1})
    tx_lock_user1 = voting_escrow.create_lock(user1_deposit_amount, user1_deposit_till, {"from": user1})

    user2_deposit_amount = deposit * 2
    user2_deposit_till = chain.time() + voting_escrow.WINDOW() + 3600 * 10
    token.transfer(user2, user2_deposit_amount)
    token.approve(voting_escrow, user2_deposit_amount, {"from": user2})
    tx_lock_user2 = voting_escrow.create_lock(user2_deposit_amount, user2_deposit_till, {"from": user2})

    token.approve(voting_escrow, reward_amount)
    tx = voting_escrow.receiveReward(token, reward_amount, {"from": payer})

    totalRewards_BITS1 = voting_escrow.user_token_claimable_rewards(user1, token)
    claim_tx1 = voting_escrow.claim_rewards(token, {"from": user1})
    totalRewards_BITS2 = voting_escrow.user_token_claimable_rewards(user2, token)
    claim_tx2 = voting_escrow.claim_rewards(token, {"from": user2})

    reward1 = claim_tx1.events['UserRewardsClaimed']['totalRewards']
    reward2 = claim_tx2.events['UserRewardsClaimed']['totalRewards']

    assert reward1 == totalRewards_BITS1
    assert reward2 == totalRewards_BITS2

    assert int(reward1 + reward2) == approx(reward_amount)
    assert int(reward1) == approx(reward_amount * user1_deposit_amount / (user1_deposit_amount + user2_deposit_amount), rel=1e-6)
    assert int(reward2) == approx(reward_amount * user2_deposit_amount / (user1_deposit_amount + user2_deposit_amount), rel=1e-6)


def test_share_rewards_2users_same_time_deposit_4years(web3, chain, accounts, token, voting_escrow_naive):
    voting_escrow = voting_escrow_naive

    MAXTIME = voting_escrow.MAXTIME()
    payer = accounts[0]
    reward_amount = 10**18
    deposit = 10**18
    user1 = accounts[1]
    user2 = accounts[2]

    user1_deposit_amount = deposit
    user1_deposit_till = chain.time() + 4 * 360 * 24 * 3600
    token.transfer(user1, user1_deposit_amount)
    token.approve(voting_escrow, user1_deposit_amount, {"from": user1})
    tx_lock_user1 = voting_escrow.create_lock(user1_deposit_amount, user1_deposit_till, {"from": user1})
    print(f'{tx_lock_user1.events=}')
    print(f'{tx_lock_user1.gas_used=}')

    user2_deposit_amount = deposit * 2
    user2_deposit_till = chain.time() + 4 * 360 * 24 * 3600
    token.transfer(user2, user2_deposit_amount)
    token.approve(voting_escrow, user2_deposit_amount, {"from": user2})
    tx_lock_user2 = voting_escrow.create_lock(user2_deposit_amount, user2_deposit_till, {"from": user2})
    print(f'{tx_lock_user2.events=}')
    print(f'{tx_lock_user2.gas_used=}')

    start = chain.time()
    end = chain.time() + 4 * 360 * 24 * 3600
    n_rewards = 4 * 12 * 2  # twice a month
    total_reward_amount = 0
    for _ in range(n_rewards):
        chain.sleep(int((end - start) / n_rewards))
        token.approve(voting_escrow, reward_amount)
        tx = voting_escrow.receiveReward(token, reward_amount, {"from": payer})
        # print(f'reward {tx.events=}')
        if 'StuckRewardReceived' not in tx.events:
            assert tx.events['WindowRewardReceived']['amount'] == reward_amount
            total_reward_amount += reward_amount
    if chain.time() < end:
        chain.sleep(end - chain.time())
        chain.mine()

    totalRewards_BITS1 = voting_escrow.user_token_claimable_rewards(user1, token)
    claim_tx1 = voting_escrow.claim_rewards(token, {"from": user1})
    print(f'{claim_tx1.events=}')
    print(f'{claim_tx1.gas_used=}')

    totalRewards_BITS2 = voting_escrow.user_token_claimable_rewards(user2, token)
    claim_tx2 = voting_escrow.claim_rewards(token, {"from": user2})
    print(f'{claim_tx2.events=}')
    print(f'{claim_tx2.gas_used=}')

    reward1 = claim_tx1.events['UserRewardsClaimed']['totalRewards']
    reward2 = claim_tx2.events['UserRewardsClaimed']['totalRewards']

    assert reward1 == totalRewards_BITS1
    assert reward2 == totalRewards_BITS2

    assert int(reward1 + reward2) == approx(total_reward_amount, rel=1e-6)
    assert int(reward1) == approx(total_reward_amount * user1_deposit_amount / (user1_deposit_amount + user2_deposit_amount), rel=1e-6)
    assert int(reward2) == approx(total_reward_amount * user2_deposit_amount / (user1_deposit_amount + user2_deposit_amount), rel=1e-6)

    assert tx_lock_user1.gas_used < 3 * 1e6
    assert tx_lock_user2.gas_used < 3 * 1e6
    assert claim_tx1.gas_used < 300_000
    assert claim_tx2.gas_used < 300_000
