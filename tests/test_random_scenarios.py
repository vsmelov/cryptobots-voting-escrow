import time
import typing as t
from dataclasses import dataclass
import random
import pprint

from pytest import approx
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
                ts=result[i-1].ts+random.randint(0, max_delay) + 365 * 24 * 3600,  # todo remove
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
    n = 100  # todo 200
    d = EPOCH_SECONDS // n
    assert d * n == EPOCH_SECONDS
    balances = [
        voting_escrow.balanceOf(user, window + d * i)
        for i in range(n)
    ]
    totalSupplys = [
        voting_escrow.totalSupplyAtTimestamp(window + d * i)[1]
        for i in range(n)
    ]
    if sum(totalSupplys) == 0:
        assert sum(balances) == 0
        return 0
    # print(f'share_estim     balances={[round(_/1e18, 4) for _ in balances]}')
    # print(f'share_estim totalSupplys={[round(_/1e18, 4) for _ in totalSupplys]}')
    return sum(balances) / sum(totalSupplys)
    # points = []
    # for (x, y) in zip(balances, totalSupplys):
    #     if y == 0:
    #         points.append(0)
    #     else:
    #         points.append(x/y)
    # estimation_share = sum(points) / len(points)
    # return estimation_share


def test_scenario(web3, chain, accounts, token, voting_escrow, owner, users):
    EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
    MAXTIME = voting_escrow.MAXTIME()

    min_stake_amount = voting_escrow.min_stake_amount()
    max_stake_amount = 10 * voting_escrow.min_stake_amount()

    approx_rel = 0.03  # todo 0.03
    n_user_actions = 5  # todo set higher
    n_users = 3
    n_rewards = n_user_actions * n_users
    users = users[:n_users]

    token.approve(voting_escrow, 2**256-1, {"from": owner})
    for user in users:
        token.transfer(user, 1e6 * 1e18, {"from": owner})
        token.approve(voting_escrow, 2**256-1, {"from": user})
    del user  # to avoid namespace collision

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
            pretty_events(chain, tx.txid)
            assert voting_escrow.locked(action.user) == (action.amount, till // EPOCH_SECONDS * EPOCH_SECONDS)
        elif isinstance(action, UserLockIncreaseAmount):
            if voting_escrow.locked(action.user)[0] == 0:
                with brownie.reverts("No existing lock found"):
                    voting_escrow.increase_amount(
                        action.amount,
                        {"from": action.user},
                    )
            elif chain.time() < voting_escrow.locked(action.user)[1]:
                tx = voting_escrow.increase_amount(
                    action.amount,
                    {"from": action.user},
                )
                pretty_events(chain, tx.txid)
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
                tx = voting_escrow.increase_unlock_time(
                    start_ts+action.increase_till,
                    {"from": action.user},
                )
                pretty_events(chain, tx.txid)
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
                pretty_events(chain, tx.txid)
        elif isinstance(action, UserClaimRewards):
            tx = voting_escrow.claim_rewards(
                token,
                {"from": action.user},
            )
            pretty_events(chain, tx.txid)
            window_start = tx.events['UserClaimWindowStart']['value']
            window_end = tx.events['UserClaimWindowEnd']['value']

            print(f'{window_start=}')
            print(f'{window_end=}')

            rewards_estim = 0
            for w in range(window_start, window_end+EPOCH_SECONDS, EPOCH_SECONDS):
                print(f'check rewards for {w=}')
                window_rewards = voting_escrow.window_token_rewards(w, token)
                share = share_estim(
                    voting_escrow=voting_escrow,
                    window=w,
                    user=action.user,
                )
                print(f'{w=} {window_rewards=} {share=}')
                averageUserBalanaceOverWindow = voting_escrow.averageUserBalanaceOverWindow(action.user, w)
                averageTotalSupplyOverWindow = voting_escrow.averageTotalSupplyOverWindow(w)
                averageUserBalanaceOverWindowTx = voting_escrow.averageUserBalanaceOverWindowTx(action.user, w)
                averageTotalSupplyOverWindowTx = voting_escrow.averageTotalSupplyOverWindowTx(w)
                print(f'{w=}, averageUserBalanaceOverWindow={round(averageUserBalanaceOverWindow/1e18, 4)}, averageTotalSupplyOverWindow={round(averageTotalSupplyOverWindow/1e18, 4)}')

                def get_history_epochs(voting_escrow):
                    epoch = voting_escrow.epoch()
                    result = []
                    for i in range(0, epoch + 1):
                        _ = voting_escrow.point_history(i)
                        point = {
                            'epoch': i,
                            'bias': _[0],
                            'slope': _[1],
                            'ts': _[2],
                            'blk': _[3],
                        }
                        result.append(point)
                    return result

                def get_history(window, voting_escrow):
                    history_len = voting_escrow.integrated_totalSupply_over_window_history_index(window)
                    result = []
                    for index in range(0, history_len):
                        _ = voting_escrow.integrated_totalSupply_over_window_history(window, index)
                        record = {
                            '_msg': _[0],
                            'window': _[1],
                            '_epoch': _[2],
                            'bias_ts': _[3],
                            'bias': _[4],
                            'slope': _[5],
                            '_ts0': _[6],
                            '_ts1': _[7],
                            'interval': _[8],
                            'trapezoidArea': _[9],
                            'avg': _[10],
                        }
                        result.append(record)
                    return result

                if 0:
                    print(f'get_history_epochs:')
                    pprint.pprint(get_history_epochs(voting_escrow))
                print(f'{get_history(w, voting_escrow)=}')

                print(f'{averageUserBalanaceOverWindowTx.events=}')
                print(f'{averageTotalSupplyOverWindowTx.events=}')

                if averageTotalSupplyOverWindow == 0:
                    assert averageUserBalanaceOverWindow == 0
                else:
                    estimated = share
                    calculated = averageUserBalanaceOverWindow / averageTotalSupplyOverWindow
                    assert int(estimated) == approx(int(calculated), rel=approx_rel)

                rewards_estim += window_rewards * share

            estim = rewards_estim
            actual = tx.events['UserRewardsClaimed']['amount']
            if estim == 0 or actual == 0:
                assert actual == estim
            else:
                assert actual > 0
                assert estim > 0
                assert int(actual) == approx(int(estim), rel=approx_rel)
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

    assert 0
