import time
import typing as t
from dataclasses import dataclass
import random
import pprint

import brownie

from .utils import *


@dataclass
class Reward:
    ts: int
    amount: int


@dataclass
class UserLock:
    user: brownie.network.account.LocalAccount
    ts: int
    amount: int
    till: int


@dataclass
class UserLockIncreaseAmount:
    user: brownie.network.account.LocalAccount
    ts: int
    amount: int


@dataclass
class UserLockIncreaseTimestamp:
    user: brownie.network.account.LocalAccount
    ts: int
    increase_till: int


@dataclass
class UserClaimRewards:
    user: brownie.network.account.LocalAccount
    ts: int
    ts: int


@dataclass
class UserWithdraw:
    user: brownie.network.account.LocalAccount
    ts: int
    ts: int


max_delay = 365 * 24 * 3600  # out of gas :-(
max_delay = 30 * 24 * 3600


def generate_rewards(n_actions: int, min_rewards_ampunt: int, max_rewards_amount: int) -> t.List[Reward]:
    result = []
    for i in range(n_actions):
        result.append(Reward(ts=random.randint(0, max_delay), amount=random.randint(min_rewards_ampunt, max_rewards_amount)))
    for i in range(1, len(result)):
        result[i].ts += result[i - 1].ts
    return result


EPOCH_SECONDS = 24 * 3600


def generate_user_actions(
    user,
    n_actions: int,
    min_stake_amount: int,
    max_stake_amount: int,
    EPOCH_SECONDS: int,
) -> t.List[t.Union[
    UserLock,
    UserLockIncreaseAmount,
    UserLockIncreaseTimestamp,
    UserClaimRewards,
    UserWithdraw,
]]:
    result = []
    ts = random.randint(0, max_delay)
    result.append(UserLock(
        user=user,
        ts=ts,
        amount=random.randint(min_stake_amount, max_stake_amount),
        till=ts+random.randint(0, max_delay)+EPOCH_SECONDS,
    ))
    last_change_action = UserLock
    last_till = result[-1].till

    for i in range(n_actions-1):
        if last_change_action == UserLock:
            choice = random.choice([
                UserLockIncreaseAmount,
                UserLockIncreaseTimestamp,
                UserClaimRewards,
                UserWithdraw,
            ])
        elif last_change_action == UserWithdraw:
            choice = random.choice([
                UserLock,
            ])
        else:
            raise ValueError(last_change_action)

        if choice == UserLock:
            ts = max(result[-1].ts, last_till) + random.randint(0, max_delay)
            result.append(UserLock(
                user=user,
                ts=ts,
                till=ts+random.randint(0, max_delay) + EPOCH_SECONDS,
                amount=random.randint(min_stake_amount, max_stake_amount),
            ))
            # last_till = result[-1].till // EPOCH_SECONDS * EPOCH_SECONDS
            last_till = result[-1].till
            last_change_action = UserLock
        elif choice == UserLockIncreaseAmount:
            result.append(UserLockIncreaseAmount(
                user=user,
                ts=result[i-1].ts+random.randint(0, min(max_delay, last_till)),
                amount=random.randint(min_stake_amount, max_stake_amount),
            ))
        elif choice == UserLockIncreaseTimestamp:
            result.append(UserClaimRewards(
                user=user,
                ts=result[i-1].ts+random.randint(0, max_delay),
            ))  # todo
        #     ts = result[i-1].ts + random.randint(0, max_delay)
        #     result.append(UserLockIncreaseTimestamp(
        #         user=user,
        #         ts=ts,
        #         increase_till=max(ts, last_till) + random.randint(0, max_delay) + EPOCH_SECONDS,
        #     ))
        #     # last_till = result[-1].increase_till // EPOCH_SECONDS * EPOCH_SECONDS
        #     last_till = result[-1].increase_till  # xx todo some mistake here
        elif choice == UserClaimRewards:
            result.append(UserClaimRewards(
                user=user,
                ts=result[i-1].ts+random.randint(0, max_delay),
            ))
        elif choice == UserWithdraw:
            result.append(UserWithdraw(
                user=user,
                ts=last_till+random.randint(0, max_delay),  # note last_till not result[i-1].ts
            ))
            last_change_action = UserWithdraw
            last_till = result[-1].ts
        else:
            raise ValueError(choice)

    return result


@dataclass
class Scenario:
    rewards: t.List[Reward]
    users_actions: t.Dict[
        brownie.network.account.LocalAccount,
        t.List[t.Union[
            UserLock,
            UserLockIncreaseAmount,
            UserLockIncreaseTimestamp,
            UserClaimRewards,
            UserWithdraw,
        ]]
    ]


def generate_scenario(
    users: t.List,
    n_user_actions: int,
    n_rewards: int,
    min_stake_amount: int,
    max_stake_amount: int,
    min_rewards_amount: int,
    max_rewards_amount: int,
    EPOCH_SECONDS: int,
) -> Scenario:
    rewards = generate_rewards(
        n_rewards,
        min_rewards_ampunt=min_rewards_amount,
        max_rewards_amount=max_rewards_amount,
    )
    users_actions = {}
    for user in users:
        user_actions = generate_user_actions(
            user=user,
            n_actions=n_user_actions,
            min_stake_amount=min_stake_amount,
            max_stake_amount=max_stake_amount,
            EPOCH_SECONDS=EPOCH_SECONDS,
        )
        users_actions[user] = user_actions
    return Scenario(rewards=rewards, users_actions=users_actions)


# def check_reward(voting_escrow, window, user, token, claimed_amount):
#     assert window // EPOCH_SECONDS * EPOCH_SECONDS == window
#     n = 100
#     d = EPOCH_SECONDS // n
#     assert d * n == EPOCH_SECONDS
#     balances = [
#         voting_escrow.totalBalanceAtTimestamp(user, window + d * i)
#         for i in range(n + 1)
#     ]
#     totalSupplys = [
#         voting_escrow.totalSupplyAtTimestamp(window + d * i)
#         for i in range(n + 1)
#     ]
#     points = [x / y for (x, y) in zip(balances, totalSupplys)]
#     estimation_share = sum(points) / len(points)
#     window_rewards = voting_escrow.window_token_rewards(window, token)
#     assert window_rewards * estimation_share == claimed_amount


def share_estim(voting_escrow, window, user):
    assert window // EPOCH_SECONDS * EPOCH_SECONDS == window
    n = 100
    d = EPOCH_SECONDS // n
    assert d * n == EPOCH_SECONDS
    balances = [
        voting_escrow.balanceOfAtTimestamp(user, window + d * i)
        for i in range(n + 1)
    ]
    totalSupplys = [
        voting_escrow.totalSupplyAtTimestamp(window + d * i)[1]
        for i in range(n + 1)
    ]
    points = []
    for (x, y) in zip(balances, totalSupplys):
        if y == 0:
            points.append(0)
        else:
            points.append(x/y)
    estimation_share = sum(points) / len(points)
    return estimation_share


def test_scenario(web3, chain, accounts, token, voting_escrow, owner, users):
    EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
    MAXTIME = voting_escrow.MAXTIME()

    min_stake_amount = voting_escrow.min_stake_amount()
    max_stake_amount = 10 * voting_escrow.min_stake_amount()

    n_user_actions = 10
    n_users = 3
    n_rewards = n_user_actions * n_users
    users = users[:n_users]

    token.approve(voting_escrow, 2**256-1, {"from": owner})
    for user in users:
        token.transfer(user, 1e6 * 1e18, {"from": owner})
        token.approve(voting_escrow, 2**256-1, {"from": user})

    scenario = generate_scenario(
        users=users,
        n_user_actions=n_user_actions,
        n_rewards=n_rewards,
        min_stake_amount=min_stake_amount,
        max_stake_amount=max_stake_amount,
        min_rewards_amount=10**18,
        max_rewards_amount=10 * 10**18,
        EPOCH_SECONDS=voting_escrow.EPOCH_SECONDS(),
    )

    users_actions = sum(scenario.users_actions.values(), start=[])
    actions: t.List[t.Union[
        Reward,
        UserLock,
        UserLockIncreaseAmount,
        UserLockIncreaseTimestamp,
        UserClaimRewards,
        UserWithdraw,
    ]] = users_actions + scenario.rewards

    actions = sorted(actions, key=lambda _: _.ts)

    pprint.pprint(list(enumerate(actions)))

    start_ts = chain.time()
    last_ts = 0

    def process_action(action_index, action):
        if isinstance(action, Reward):
            voting_escrow.receiveReward(
                token,
                action.amount,
                {"from": owner},
            )
        elif isinstance(action, UserLock):
            till = start_ts+action.till
            tx = voting_escrow.create_lock(
                action.amount,
                till,
                {"from": action.user},
            )
            assert voting_escrow.locked(action.user) == (action.amount, till // EPOCH_SECONDS * EPOCH_SECONDS)
        elif isinstance(action, UserLockIncreaseAmount):
            if voting_escrow.locked(action.user)[0] == 0:
                with brownie.reverts("No existing lock found"):
                    voting_escrow.increase_amount(
                        action.amount,
                        {"from": action.user},
                    )
            elif chain.time() < voting_escrow.locked(action.user)[1]:
                voting_escrow.increase_amount(
                    action.amount,
                    {"from": action.user},
                )
            else:
                with brownie.reverts("Cannot add to expired lock. Withdraw"):
                    voting_escrow.increase_amount(
                        action.amount,
                        {"from": action.user},
                    )
        elif isinstance(action, UserLockIncreaseTimestamp):
            if voting_escrow.locked(action.user)[0] == 0:
                with brownie.reverts("Nothing is locked"):
                    voting_escrow.increase_unlock_time(
                        start_ts + action.increase_till,
                        {"from": action.user},
                    )
            elif chain.time() < voting_escrow.locked(action.user)[1]:
                voting_escrow.increase_unlock_time(
                    start_ts+action.increase_till,
                    {"from": action.user},
                )
            else:
                with brownie.reverts("Lock expired"):
                    voting_escrow.increase_unlock_time(
                        start_ts + action.increase_till,
                        {"from": action.user},
                    )
        elif isinstance(action, UserWithdraw):
            locked_amount, locked_ts = voting_escrow.locked(action.user)
            if chain.time() < locked_ts:
                with brownie.reverts("The lock didn't expire"):
                    voting_escrow.withdraw({"from": action.user})
                print('withdrawn SKIP')
            else:
                tx = voting_escrow.withdraw({"from": action.user})
                assert tx.events['Withdraw']['value'] == locked_amount
                print('withdrawn')
        elif isinstance(action, UserClaimRewards):
            tx = voting_escrow.claim_rewards(
                token,
                {"from": action.user},
            )
            window_start = tx.events['UserClaimWindowStart']['value']
            window_end = tx.events['UserClaimWindowEnd']['value']

            print(f'{window_start=}')
            print(f'{window_end=}')

            rewards_estim = 0
            for w in range(window_start, window_end+EPOCH_SECONDS, EPOCH_SECONDS):
                window_rewards = voting_escrow.window_token_rewards(w, token)
                share = share_estim(
                    voting_escrow=voting_escrow,
                    window=w,
                    user=action.user,
                )
                rewards_estim += window_rewards * share

            estim = rewards_estim
            actual = tx.events['UserRewardsClaimed']['amount']
            if estim == 0 or actual == 0:
                assert actual == estim
            else:
                assert actual > 0
                assert estim > 0
                alpha = max(actual, estim) * 0.001 / min(actual, estim)
                assert abs(actual - estim) / min(actual, estim) < alpha
        else:
            raise ValueError(action)

    for action_index, action in enumerate(actions):
        print(f'START {action_index=} {action=}')
        delay = max(0, action.ts - last_ts)
        chain.sleep(delay)
        print(f'SLEEP {delay}s, because {action.ts=} {last_ts=}')
        process_action(action_index, action)
        last_ts = action.ts
        print(f'SET {last_ts=}')
        # last_ts = chain.time()
