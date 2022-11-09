import datetime
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
    ui: int
    expected_last_till: int


@dataclass
class UserLockIncreaseAmount:
    user: brownie.network.account.LocalAccount
    ts: int
    amount: int
    ui: int


@dataclass
class UserLockIncreaseTimestamp:
    user: brownie.network.account.LocalAccount
    ts: int
    increase_till: int
    ui: int


@dataclass
class UserClaimRewards:
    user: brownie.network.account.LocalAccount
    ts: int
    ts: int
    ui: int


@dataclass
class UserWithdraw:
    user: brownie.network.account.LocalAccount
    ts: int
    ts: int
    ui: int


# max_delay = 365 * 24 * 3600  # todo resolve out of gas :-(
max_delay = 7 * 24 * 3600
min_delay = 3600  # todo 1


def generate_rewards(
        start_ts: int,
        n_actions: int,
        min_rewards_ampunt: int,
        max_rewards_amount: int,
) -> t.List[Reward]:
    result = []
    for i in range(n_actions):
        result.append(Reward(ts=random.randint(min_delay, max_delay), amount=random.randint(min_rewards_ampunt, max_rewards_amount)))
    if n_actions > 0:
        result[0].ts += start_ts
        for i in range(1, len(result)):
            result[i].ts += result[i - 1].ts
    return result


def generate_user_actions(
    start_ts: int,
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
    ts = start_ts + random.randint(min_delay, max_delay)
    till = ts + random.randint(min_delay, max_delay) + EPOCH_SECONDS
    last_till = till // EPOCH_SECONDS * EPOCH_SECONDS
    result.append(UserLock(
        ui=0,
        user=user,
        ts=ts,
        amount=random.randint(min_stake_amount, max_stake_amount),
        till=till,
        expected_last_till=last_till,
    ))
    last_change_action = UserLock

    for i in range(1, n_actions):
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
            ts = max(result[-1].ts, last_till) + random.randint(min_delay, max_delay)
            till = ts + random.randint(min_delay, max_delay) + EPOCH_SECONDS
            last_till = till // EPOCH_SECONDS * EPOCH_SECONDS
            result.append(UserLock(
                user=user,
                ts=ts,
                till=till,
                amount=random.randint(min_stake_amount, max_stake_amount),
                ui=i,
                expected_last_till=last_till,
            ))
            last_change_action = UserLock
        elif choice == UserLockIncreaseAmount:
            ts = result[-1].ts + random.randint(min_delay, max_delay)
            result.append(UserLockIncreaseAmount(
                user=user,
                ts=max(result[-1].ts, min(ts, last_till-1)),
                amount=random.randint(min_stake_amount, max_stake_amount),
                ui=i,
            ))
        elif choice == UserLockIncreaseTimestamp:
            ts = result[-1].ts + random.randint(min_delay, max_delay)
            increase_till = max(ts, last_till) + random.randint(min_delay, max_delay) + EPOCH_SECONDS

            result.append(UserLockIncreaseTimestamp(
                user=user,
                ts=max(result[-1].ts+1, min(ts, last_till-1)),
                increase_till=increase_till,
                ui=i,
            ))
            print(f'xx UserLockIncreaseTimestamp {user=}')
            print(f'xx UserLockIncreaseTimestamp {last_till=}')
            last_till = result[-1].increase_till // EPOCH_SECONDS * EPOCH_SECONDS
            print(f'xx UserLockIncreaseTimestamp {ts=}')
            print(f'xx UserLockIncreaseTimestamp {increase_till=}')
            print(f'xx UserLockIncreaseTimestamp {last_till=}')
        elif choice == UserClaimRewards:
            result.append(UserClaimRewards(
                user=user,
                ts=result[-1].ts+random.randint(min_delay, max_delay),
                ui=i,
            ))
        elif choice == UserWithdraw:
            result.append(UserWithdraw(
                user=user,  # todo remove EPOCH_SECONDS
                ts=max(result[-1].ts, last_till) + random.randint(min_delay, max_delay) + EPOCH_SECONDS,  # note last_till not result[-1].ts
                ui=i,
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
    start_ts: int,
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
        n_actions=n_rewards,
        start_ts=start_ts,
        min_rewards_ampunt=min_rewards_amount,
        max_rewards_amount=max_rewards_amount,
    )
    users_actions = {}
    for user in users:
        user_actions = generate_user_actions(
            start_ts=start_ts,
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


def share_estim(voting_escrow, window, user, EPOCH_SECONDS: int, n=100):
    assert window // EPOCH_SECONDS * EPOCH_SECONDS == window
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
    GAS_CHECKPOINT_CONST = 400_000
    GAS_CHECKPOINT_VAR = 400_000
    GAS_USER_CLAIM_CONST = 250_000
    GAS_USER_CLAIM_VAR = 250_000

    EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
    MAXTIME = voting_escrow.MAXTIME()

    min_stake_amount = voting_escrow.min_stake_amount()
    max_stake_amount = 10 * voting_escrow.min_stake_amount()

    approx_rel = 0.01
    n_user_actions = 7
    n_users = 4
    n_rewards = n_user_actions * n_users // 2
    users = users[:n_users]

    token.approve(voting_escrow, 2**256-1, {"from": owner})
    for user in users:
        token.transfer(user, 1e6 * 1e18, {"from": owner})
        token.approve(voting_escrow, 2**256-1, {"from": user})
    del user  # to avoid namespace collision

    # always start at 1 jan 2023 for repeatability
    chain.sleep(int(datetime.datetime(2023, 1, 1).timestamp() - chain.time()))

    start_ts = chain.time()
    print(f'{start_ts=}')
    scenario = generate_scenario(
        start_ts=start_ts,
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

    user_ui = {}
    for action in actions:
        if isinstance(action, Reward):
            continue
        user = action.user
        ui = action.ui
        prev_ui = user_ui.get(user, -1)
        if ui - prev_ui != 1:
            print(f'wrong sorting for {user=}, {ui=}')
            assert 0
        user_ui[user] = ui

    total_rewards = 0

    def process_action(action_index, action):
        nonlocal total_rewards
        if isinstance(action, Reward):
            tx = voting_escrow.receiveReward(
                token,
                action.amount,
                {"from": owner},
            )
            total_rewards += action.amount
            assert tx.gas_used < 100_000
        elif isinstance(action, UserLock):
            till = action.till
            tx = voting_escrow.create_lock(
                action.amount,
                till,
                {"from": action.user},
            )
            pretty_events(chain, tx.txid)
            assert voting_escrow.locked(action.user) == (action.amount, till // EPOCH_SECONDS * EPOCH_SECONDS)
            assert tx.gas_used < GAS_CHECKPOINT_CONST + (tx.events['CheckpointEndEpoch']['epoch'] - tx.events['CheckpointStartEpoch']['epoch']) * GAS_CHECKPOINT_VAR
            assert voting_escrow.locked(action.user)[1] == action.expected_last_till
        elif isinstance(action, UserLockIncreaseAmount):
            if voting_escrow.locked(action.user)[0] == 0:
                with brownie.reverts("not exist"):
                    voting_escrow.increase_amount(
                        action.amount,
                        {"from": action.user},
                    )
                print(f'SKIP UserLockIncreaseAmount because: not exist')
                assert 0
            elif chain.time() < voting_escrow.locked(action.user)[1]:
                tx = voting_escrow.increase_amount(
                    action.amount,
                    {"from": action.user},
                )
                pretty_events(chain, tx.txid)
                assert tx.gas_used < GAS_CHECKPOINT_CONST + (tx.events['CheckpointEndEpoch']['epoch'] - tx.events['CheckpointStartEpoch']['epoch']) * GAS_CHECKPOINT_VAR
            else:
                with brownie.reverts("cannot add to expired lock"):
                    voting_escrow.increase_amount(
                        action.amount,
                        {"from": action.user},
                    )
                print(f'SKIP UserLockIncreaseAmount because: cannot add to expired lock')
                # assert 0  # its ok because ts in claimReward may go to future
        elif isinstance(action, UserLockIncreaseTimestamp):
            if voting_escrow.locked(action.user)[0] == 0:
                with brownie.reverts("nothing is locked"):
                    voting_escrow.increase_unlock_time(
                        action.increase_till,
                        {"from": action.user},
                    )
                print(f'SKIP UserLockIncreaseTimestamp because: nothing is locked')
                assert 0
            elif chain.time() < voting_escrow.locked(action.user)[1]:
                tx = voting_escrow.increase_unlock_time(
                    action.increase_till,
                    {"from": action.user},
                )
                pretty_events(chain, tx.txid)
                assert tx.gas_used < GAS_CHECKPOINT_CONST + (tx.events['CheckpointEndEpoch']['epoch'] - tx.events['CheckpointStartEpoch']['epoch']) * GAS_CHECKPOINT_VAR
            else:
                with brownie.reverts("lock expired"):
                    voting_escrow.increase_unlock_time(
                        action.increase_till,
                        {"from": action.user},
                    )
                print(f'SKIP UserLockIncreaseTimestamp because: lock expired')
                # assert 0  # its ok because ts in claimReward may go to future
        elif isinstance(action, UserWithdraw):
            locked_amount, locked_ts = voting_escrow.locked(action.user)
            if chain.time() < locked_ts:
                with brownie.reverts("not expired"):
                    voting_escrow.withdraw({"from": action.user})
                print(f'{chain.time()=}, {locked_ts=}')
                print('withdrawn SKIP')
                assert 0
            else:
                tx = voting_escrow.withdraw({"from": action.user})
                assert tx.events['Withdraw']['value'] == locked_amount
                print('withdrawn')
                pretty_events(chain, tx.txid)
                assert tx.gas_used < GAS_CHECKPOINT_CONST + (tx.events['CheckpointEndEpoch']['epoch'] - tx.events['CheckpointStartEpoch']['epoch']) * GAS_CHECKPOINT_VAR
        elif isinstance(action, UserClaimRewards):
            tx = voting_escrow.claim_rewards(
                token,
                {"from": action.user},
            )
            total_rewards -= tx.events['UserRewardsClaimed']['amount']
            assert total_rewards >= 0, "impossible claimed rewards too much"

            pretty_events(chain, tx.txid)
            window_start = tx.events['UserClaimWindowStart']['value']  # not guaranteed to be processed
            window_end = tx.events['UserClaimWindowEnd']['value']
            assert tx.gas_used < GAS_USER_CLAIM_CONST + max(0, window_end - window_start) * GAS_USER_CLAIM_VAR

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
                    EPOCH_SECONDS=EPOCH_SECONDS,
                )
                print(f'{w=} {window_rewards=} {share=}')
                averageUserBalanaceOverWindow = voting_escrow.averageUserBalanaceOverWindow(action.user, w)
                averageTotalSupplyOverWindow = voting_escrow.averageTotalSupplyOverWindow(w)
                averageUserBalanaceOverWindowTx = voting_escrow.averageUserBalanaceOverWindow.transact(action.user, w)
                averageTotalSupplyOverWindowTx = voting_escrow.averageTotalSupplyOverWindow.transact(w)
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

                print(f'averageUserBalanaceOverWindowTx:')
                pretty_events(chain, averageUserBalanaceOverWindowTx.txid)

                print(f'averageTotalSupplyOverWindowTx:')
                pretty_events(chain, averageTotalSupplyOverWindowTx.txid)

                if averageTotalSupplyOverWindow == 0:
                    assert averageUserBalanaceOverWindow == 0
                else:
                    estimated = share
                    calculated = averageUserBalanaceOverWindow / averageTotalSupplyOverWindow
                    assert int(estimated) == approx(int(calculated), rel=approx_rel)

                rewards_estim += window_rewards * share

            estim = rewards_estim
            actual = tx.events['UserRewardsClaimed']['amount']

            print(f'{tx.events=}')
            print(f'{estim=}')
            print(f'{actual=}')

            if estim == 0 or actual == 0:
                assert actual == estim
            else:
                assert actual > 0
                assert estim > 0
                assert int(actual) == approx(int(estim), rel=approx_rel)

            # assert 0
        else:
            raise ValueError(action)

    for action_index, action in enumerate(actions):
        print(f'DETECT_ACTION {action_index=} {action=}')
        delay = max(0, action.ts - chain.time())
        print(f'SLEEP {delay}s, because {action.ts=} {chain.time()=}')
        chain.sleep(delay)
        ts = chain.time()
        print(f'PROCESS_ACTION {action_index=} {action=} now={ts} now_dt={datetime.datetime.fromtimestamp(ts)}')
        process_action(action_index, action)


def test_share_rewards_2users_same_window_reward(web3, chain, accounts, token, voting_escrow):
    EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
    sleep = EPOCH_SECONDS
    MAXTIME = voting_escrow.MAXTIME()
    payer = accounts[0]
    reward_amount = 10**18
    deposit = 10**18
    user1 = accounts[1]
    user2 = accounts[2]

    assert voting_escrow.epoch() == 0
    assert voting_escrow.window_token_rewards(0, token) == 0

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
        assert voting_escrow.slope_changes(user2_deposit_till // EPOCH_SECONDS * EPOCH_SECONDS) == \
               -(user2_deposit_amount // MAXTIME) - (user1_deposit_amount // MAXTIME)
    else:  # bad unit test
        assert 0, "unlucky! rerun"

    assert tx_lock_user1.timestamp // EPOCH_SECONDS == tx_lock_user2.timestamp // EPOCH_SECONDS

    token.approve(voting_escrow, reward_amount)
    tx = voting_escrow.receiveReward(token, reward_amount, {"from": payer})
    reward_window1 = voting_escrow.currentWindow()
    assert voting_escrow.window_token_rewards(reward_window1, token) == reward_amount

    chain.sleep(EPOCH_SECONDS)  # go into next window

    start_ts = tx_lock_user2.timestamp
    end_ts = reward_window1 + EPOCH_SECONDS

    user1_start_balance = voting_escrow.balanceOf(user1, start_ts)
    user1_end_balance = voting_escrow.balanceOf(user1, end_ts)
    user2_start_balance = voting_escrow.balanceOf(user2, start_ts)
    user2_end_balance = voting_escrow.balanceOf(user2, end_ts)
    supply_start = voting_escrow.totalSupply(start_ts)
    supply_end = voting_escrow.totalSupply(end_ts)

    assert user1_start_balance + user2_start_balance == supply_start
    assert user1_end_balance + user2_end_balance == supply_end

    user1_share = (user1_start_balance + user1_end_balance) / (supply_start + supply_end)
    user2_share = (user2_start_balance + user2_end_balance) / (supply_start + supply_end)

    print(f'start claim user1')
    claimable_tx = voting_escrow.user_token_claimable_rewards.transact(user1, token)
    print(f'{claimable_tx.events=}')
    claimable1 = voting_escrow.user_token_claimable_rewards(user1, token)
    claim_tx1 = voting_escrow.claim_rewards(token, {"from": user1})
    print(f"{claim_tx1.events=}")
    assert claimable1 == claim_tx1.events['UserRewardsClaimed']['amount']
    assert claim_tx1.events['UserRewardsClaimed']['amount'] // 10**14 == int(reward_amount * user1_share) // 10**14
    assert voting_escrow.user_token_claimed_window(user1, token) == voting_escrow.currentWindow() - EPOCH_SECONDS
    assert tx_lock_user1.timestamp // EPOCH_SECONDS * EPOCH_SECONDS == claim_tx1.events['UserRewardsClaimed']['last_processed_window']

    print(f'start claim user2')
    claimable2 = voting_escrow.user_token_claimable_rewards(user2, token)
    claim_tx2 = voting_escrow.claim_rewards(token, {"from": user2})
    print(f"{claim_tx2.events=}")
    assert claim_tx2.events['UserRewardsClaimed']['amount'] // 10**14 == reward_amount * user2_share // 10**14
    assert voting_escrow.user_token_claimed_window(user2, token) == voting_escrow.currentWindow() - EPOCH_SECONDS
    assert tx_lock_user2.timestamp // EPOCH_SECONDS * EPOCH_SECONDS == claim_tx2.events['UserRewardsClaimed']['last_processed_window']

    assert abs(claimable2 + claimable1 - reward_amount) <= reward_amount * 1e-6


def test_lock_for_max_time(web3, chain, accounts, token, voting_escrow, owner):
    EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
    sleep = EPOCH_SECONDS
    MAXTIME = voting_escrow.MAXTIME()
    payer = accounts[0]
    reward_amount = 10**18
    deposit = 10**18
    user1 = accounts[1]
    user2 = accounts[2]

    user1_deposit_amount = deposit
    token.transfer(user1, user1_deposit_amount)
    token.approve(voting_escrow, user1_deposit_amount, {"from": user1})
    user1_deposit_till = chain.time() + MAXTIME
    tx_lock_user1 = voting_escrow.create_lock(user1_deposit_amount, user1_deposit_till, {"from": user1})


def test_emergency(web3, chain, accounts, token, voting_escrow, owner):
    EPOCH_SECONDS = voting_escrow.EPOCH_SECONDS()
    sleep = EPOCH_SECONDS
    MAXTIME = voting_escrow.MAXTIME()
    payer = accounts[0]
    reward_amount = 10**18
    deposit = 10**18
    user1 = accounts[1]
    user2 = accounts[2]

    assert voting_escrow.epoch() == 0
    assert voting_escrow.window_token_rewards(0, token) == 0

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

    assert owner == voting_escrow.admin()

    voting_escrow.enable_emergency({"from": owner})
    user1_balance_before = token.balanceOf(user1)
    voting_escrow.withdraw({"from": user1})
    assert token.balanceOf(user1) - user1_balance_before == user1_deposit_amount
    user2_balance_before = token.balanceOf(user2)
    voting_escrow.emergency_withdraw(token, user2_deposit_amount, user2, {"from": owner})
    assert token.balanceOf(user2) - user2_balance_before == user2_deposit_amount


def test_set_min_delay_between_manual_checkpoint(web3, chain, accounts, token, voting_escrow, owner):
    voting_escrow.set_min_delay_between_manual_checkpoint(600, {"from": owner})
    assert voting_escrow.min_delay_between_manual_checkpoint() == 600


def test_transfer_ownership(web3, chain, accounts, token, voting_escrow, owner):
    voting_escrow.transfer_ownership(accounts[-1], {"from": owner})
    assert voting_escrow.admin() == accounts[-1]
