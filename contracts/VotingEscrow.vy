# @version 0.3.7
"""
@title Voting Escrow
@author Curve Finance
@license MIT
@notice Votes have a weight depending on time, so that users are
        committed to the future of (whatever they are voting for)
@dev Vote weight decays linearly over time. Lock time cannot be
     more than `MAXTIME` (4 years).
"""

# Voting escrow to have time-weighted votes
# Votes have a weight depending on time, so that users are committed
# to the future of (whatever they are voting for).
# The weight in this implementation is linear, and lock cannot be more than maxtime:
# w ^
# 1 +        /
#   |      /
#   |    /
#   |  /
#   |/
# 0 +--------+------> time
#       maxtime (4 years?)

struct Point:
    bias: int128
    slope: int128  # - dweight / dt
    ts: uint256
    blk: uint256  # block
# We cannot really do block numbers per se b/c slope is per time, not per block
# and per block could be fairly bad b/c Ethereum changes blocktimes.
# What we can do is to extrapolate ***At functions

struct LockedBalance:
    amount: int128
    end: uint256


interface ERC20:
    def balanceOf(account: address) -> uint256: view
    def decimals() -> uint256: view
    def name() -> String[64]: view
    def symbol() -> String[32]: view
    def transfer(to: address, amount: uint256) -> bool: nonpayable
    def transferFrom(spender: address, to: address, amount: uint256) -> bool: nonpayable


# Interface for checking whether address belongs to a whitelisted
# type of a smart wallet.
# When new types are added - the whole contract is changed
# The check() method is modifying to be able to use caching
# for individual wallet addresses
interface SmartWalletChecker:
    def check(addr: address) -> bool: nonpayable

storageUInt256: HashMap[bytes32, uint256]
storageAddress: HashMap[bytes32, address]
storageBool: HashMap[bytes32, bool]


DEPOSIT_FOR_TYPE: constant(int128) = 0
CREATE_LOCK_TYPE: constant(int128) = 1
INCREASE_LOCK_AMOUNT: constant(int128) = 2
INCREASE_UNLOCK_TIME: constant(int128) = 3

stuckWindowRewardClaimed: public(HashMap[uint256, bool])

event StuckWindowRewardClaimed:
    epoch: indexed(uint256)
    token: indexed(address)
    amount: uint256

event TransferOwnership:
    admin: address


event Deposit:
    provider: indexed(address)
    value: uint256
    locktime: indexed(uint256)
    type: int128
    ts: uint256


event Withdraw:
    provider: indexed(address)
    value: uint256
    ts: uint256


event Supply:
    prevSupply: uint256
    supply: uint256


EPOCH_SECONDS: constant(uint256) = 24 * 3600  # all future times are rounded by week
# EPOCH_SECONDS: constant(uint256) = 600
MAXTIME: constant(uint256) = 4 * 365 * 86400  # 4 years
MULTIPLIER: constant(uint256) = 10 ** 18

@external
@view
def EPOCH_SECONDS() -> uint256:
    return EPOCH_SECONDS


@external
@view
def MAXTIME() -> uint256:
    return MAXTIME

settings: public(address)

ADMIN_HASH: constant(bytes32) = keccak256("admin")
@external
@view
def admin() -> address:
    return self._admin()

@internal
@view
def _admin() -> address:
    return self.storageAddress[ADMIN_HASH]


last_manual_checkpoint_timestamp: public(uint256)
MIN_DELAY_BETWEEN_MANUAL_CHECKPOINT_HASH: constant(bytes32) = keccak256("min_delay_between_manual_checkpoint")

@external
@view
def min_delay_between_manual_checkpoint() -> uint256:
    return self._min_delay_between_manual_checkpoint()

@internal
@view
def _min_delay_between_manual_checkpoint() -> uint256:
    return self.storageUInt256[MIN_DELAY_BETWEEN_MANUAL_CHECKPOINT_HASH]

event MinDelayBetweenManualCheckpointSet:
    value: uint256

@external
def set_min_delay_between_manual_checkpoint(_value: uint256):
    raw_call(
        self.settings,
        _abi_encode(_value, method_id=method_id("set_min_delay_between_manual_checkpoint(uint256)")),
        is_delegate_call=True
    )

token: public(address)
supply: public(uint256)

locked: public(HashMap[address, LockedBalance])

integrated_totalSupply_over_window: public(HashMap[uint256, uint256])  # timestamp of the window start -> aggregated value (assuming checkpoint will not change)
user_token_claimed_window: public(HashMap[address, HashMap[address, uint256]])  # user -> token -> last claimed window
user_token_claimed_window_start: public(HashMap[address, uint256])  # user -> first unclaimed window
window_token_rewards: public(HashMap[uint256, HashMap[address, uint256]])  # epoch -> token -> totalRewardsAmount

epoch: public(uint256)
point_history: public(Point[100000000000000000000000000000])  # epoch -> unsigned point
user_point_history: public(HashMap[address, Point[1000000000]])  # user -> Point[user_epoch]
user_point_epoch: public(HashMap[address, uint256])  # user -> current user epoch (its different scale with just epochs)
slope_changes: public(HashMap[uint256, int128])  # time -> signed slope change

slope_changes_keys: public(uint256[100000])  #xx todo remove
slope_changes_keys_next_index: public(uint256)  #xx todo remove

pool_members: public(uint256)  # how many participants are already in the pool
max_pool_members: public(uint256)  # maximum number of the pool participants
min_stake_amount: public(uint256)  # min amount to stake (or increase)

# Aragon's view methods for compatibility
controller: public(address)  # todo remove never used
transfersEnabled: public(bool)  # todo remove never used

name: public(String[64])
symbol: public(String[32])
version: public(String[32])
decimals: public(uint256)

# Checker for whitelisted (smart contract) wallets which are allowed to deposit
# The goal is to prevent tokenizing the escrow
smart_wallet_checker: public(address)

increase_amount_disabled: public(bool)
increase_unlock_time_disabled: public(bool)
create_lock_disabled: public(bool)
withdraw_disabled: public(bool)
emergency: public(bool)  # warning: cannot be reverted!

event IncreaseAmountDisabledSet:
    value: bool

event IncreaseUnlockTimeDisabledSet:
    value: bool

event CreateLockDisabledSet:
    value: bool

event WithdrawDisabledSet:
    value: bool

event MinStakeAmountSet:
    value: uint256

event MaxPoolMembersSet:
    value: uint256

event Emergency:
    pass

event TransferNative:
    to: indexed(address)
    value: uint256


@external
def enable_emergency():
    assert msg.sender == self._admin()
    assert not self.emergency
    self.emergency = True
    log Emergency()


@external
def set_max_pool_members(_value: uint256):
    assert msg.sender == self._admin()
    assert self.max_pool_members != _value
    self.max_pool_members = _value
    log MaxPoolMembersSet(_value)


@external
def set_min_stake_amount(_value: uint256):
    assert msg.sender == self._admin()
    assert self.min_stake_amount != _value
    self.min_stake_amount = _value
    log MinStakeAmountSet(_value)


@external
def set_withdraw_disabled(_value: bool):
    assert msg.sender == self._admin()
    assert self.withdraw_disabled != _value
    self.withdraw_disabled = _value
    log WithdrawDisabledSet(_value)


@external
def set_create_lock_disabled(_value: bool):
    assert msg.sender == self._admin()
    assert self.create_lock_disabled != _value
    self.create_lock_disabled = _value
    log CreateLockDisabledSet(_value)


@external
def set_increase_amount_disabled(_value: bool):
    assert msg.sender == self._admin()
    assert self.increase_amount_disabled != _value
    self.increase_amount_disabled = _value
    log IncreaseAmountDisabledSet(_value)


@external
def set_increase_unlock_time_disabled(_value: bool):
    assert msg.sender == self._admin()
    assert self.increase_unlock_time_disabled != _value
    self.increase_unlock_time_disabled = _value
    log IncreaseUnlockTimeDisabledSet(_value)


@external
def pause():
    assert msg.sender == self._admin()

    if not self.withdraw_disabled:
        self.withdraw_disabled = True
        log WithdrawDisabledSet(True)

    if not self.create_lock_disabled:
        self.create_lock_disabled = True
        log CreateLockDisabledSet(True)

    if not self.increase_amount_disabled:
        self.increase_amount_disabled = True
        log IncreaseAmountDisabledSet(True)

    if not self.increase_unlock_time_disabled:
        self.increase_unlock_time_disabled = True
        log IncreaseUnlockTimeDisabledSet(True)


@external
def unpause():
    assert msg.sender == self._admin()

    if self.withdraw_disabled:
        self.withdraw_disabled = False
        log WithdrawDisabledSet(False)

    if self.create_lock_disabled:
        self.create_lock_disabled = False
        log CreateLockDisabledSet(False)

    if self.increase_amount_disabled:
        self.increase_amount_disabled = False
        log IncreaseAmountDisabledSet(False)

    if self.increase_unlock_time_disabled:
        self.increase_unlock_time_disabled = False
        log IncreaseUnlockTimeDisabledSet(False)


@external
def __init__(
        settings_addr: address,
        token_addr: address,
        _name: String[64],
        _symbol: String[32],
        _version: String[32],
        _max_pool_members: uint256,
        _min_stake_amount: uint256,
):
    """
    @notice Contract constructor
    @param settings_addr VotingEscrowSettings address
    @param token_addr `ERC20CRV` token address
    @param _name Token name
    @param _symbol Token symbol
    @param _version Contract version - required for Aragon compatibility
    """
    self.settings = settings_addr
    self.storageAddress[ADMIN_HASH] = msg.sender
    self.token = token_addr
    self.point_history[0].blk = block.number
    self.point_history[0].ts = block.timestamp
    self.controller = msg.sender
    self.transfersEnabled = True

    _decimals: uint256 = ERC20(token_addr).decimals()
    assert _decimals <= 255
    self.decimals = _decimals

    self.name = _name
    self.symbol = _symbol
    self.version = _version

    self.slope_changes_keys_next_index = 0  # todo remove

    self.max_pool_members = _max_pool_members
    self.min_stake_amount = _min_stake_amount


@external
def transfer_ownership(addr: address):
    """
    @notice Transfer ownership of VotingEscrow contract to `addr`
    @param addr Address to have ownership transferred to
    """
    raw_call(
        self.settings,
        _abi_encode(addr, method_id=method_id("transfer_ownership(address)")),
        is_delegate_call=True
    )


@external
def set_smart_wallet_checker(addr: address):
    """
    @notice Apply setting external contract to check approved smart contract wallets
    """
    assert msg.sender == self._admin(), "not admin"
    self.smart_wallet_checker = addr


@internal
def assert_not_contract(addr: address):
    """
    @notice Check if the call is from a whitelisted smart contract, revert if not
    @param addr Address to be checked
    """
    if addr != tx.origin:
        checker: address = self.smart_wallet_checker
        if checker != ZERO_ADDRESS:
            if SmartWalletChecker(checker).check(addr):
                return
        raise "Smart contract depositors not allowed"


@external
@view
def get_last_user_slope(addr: address) -> int128:
    """
    @notice Get the most recently recorded rate of voting power decrease for `addr`
    @param addr Address of the user wallet
    @return Value of the slope
    """
    uepoch: uint256 = self.user_point_epoch[addr]
    return self.user_point_history[addr][uepoch].slope


@external
@view
def user_point_history__ts(_addr: address, _idx: uint256) -> uint256:
    """
    @notice Get the timestamp for checkpoint `_idx` for `_addr`
    @param _addr User wallet address
    @param _idx User epoch number
    @return Epoch time of the checkpoint
    """
    return self.user_point_history[_addr][_idx].ts


@external
@view
def locked__end(_addr: address) -> uint256:
    """
    @notice Get timestamp when `_addr`'s lock finishes
    @param _addr User wallet
    @return Epoch time of the lock end
    """
    return self.locked[_addr].end


@internal
def _checkpoint(addr: address, old_locked: LockedBalance, new_locked: LockedBalance):
    """
    @notice Record global and per-user data to checkpoint
    @param addr User's wallet address. No user checkpoint if 0x0
    @param old_locked Pevious locked amount / end lock time for the user
    @param new_locked New locked amount / end lock time for the user
    """
    u_old: Point = empty(Point)
    u_new: Point = empty(Point)
    old_dslope: int128 = 0
    new_dslope: int128 = 0
    _epoch: uint256 = self.epoch

    if addr != ZERO_ADDRESS:
        # Calculate slopes and biases
        # Kept at zero when they have to
        if old_locked.end > block.timestamp and old_locked.amount > 0:
            u_old.slope = old_locked.amount / convert(MAXTIME, int128)  # todo why??
            u_old.bias = u_old.slope * convert(old_locked.end - block.timestamp, int128)
        if new_locked.end > block.timestamp and new_locked.amount > 0:
            u_new.slope = new_locked.amount / convert(MAXTIME, int128)
            u_new.bias = u_new.slope * convert(new_locked.end - block.timestamp, int128)

        # Read values of scheduled changes in the slope
        # old_locked.end can be in the past and in the future
        # new_locked.end can ONLY by in the FUTURE unless everything expired: than zeros
        old_dslope = self.slope_changes[old_locked.end]
        if new_locked.end != 0:
            if new_locked.end == old_locked.end:
                new_dslope = old_dslope
            else:
                new_dslope = self.slope_changes[new_locked.end]

    last_point: Point = Point({bias: 0, slope: 0, ts: block.timestamp, blk: block.number})
    if _epoch > 0:
        last_point = self.point_history[_epoch]
    # initial_last_point is used for extrapolation to calculate block number
    # (approximately, for *At methods) and save them
    # as we cannot figure that out exactly from inside the contract
    initial_last_point: Point = last_point
    block_slope: uint256 = 0  # dblock/dt
    if block.timestamp > last_point.ts:
        block_slope = MULTIPLIER * (block.number - last_point.blk) / (block.timestamp - last_point.ts)
    # If last point is already recorded in this block, slope=0
    # But that's ok b/c we know the block in such case

    # Go over weeks to fill history and calculate what the current point is
    checkpoint_ts: uint256 = (last_point.ts / EPOCH_SECONDS) * EPOCH_SECONDS
    for i in range(255):
        # Hopefully it won't happen that this won't get used in 5 years!
        # If it does, users will be able to withdraw but vote weight will be broken
        checkpoint_ts += EPOCH_SECONDS
        d_slope: int128 = 0
        if checkpoint_ts > block.timestamp:
            checkpoint_ts = block.timestamp  # when we crossed all window checkpoints lets make a checkpoint at NOW
        else:
            d_slope = self.slope_changes[checkpoint_ts]  #xx todo careful!

        # set attributes of the new checkpoint
        last_point.bias -= last_point.slope * convert(checkpoint_ts - last_point.ts, int128)
        last_point.slope += d_slope
        if last_point.bias < 0:  # This can happen
            last_point.bias = 0
        if last_point.slope < 0:  # This cannot happen - just in case
            last_point.slope = 0
        last_point.ts = checkpoint_ts
        last_point.blk = initial_last_point.blk + \
                         block_slope * (checkpoint_ts - initial_last_point.ts) / MULTIPLIER

        _epoch += 1
        if checkpoint_ts == block.timestamp:
            last_point.blk = block.number
            break
        else:
            self.point_history[_epoch] = last_point

        # handle integrated_totalSupply_over_window
        # todo test
        trapezoidArea: uint256 = 0
        prev_point: Point = self.point_history[_epoch - 1]
        _prev_point_window: uint256 = prev_point.ts / EPOCH_SECONDS * EPOCH_SECONDS
        _last_point_window: uint256 = last_point.ts / EPOCH_SECONDS * EPOCH_SECONDS
        if _prev_point_window < _last_point_window:
            assert _last_point_window - _prev_point_window == EPOCH_SECONDS, "impossible: window_diff>EPOCH_SECONDS"

            # finalize previous window aggregate
            trapezoidArea = self.anyTrapezoidArea(
                prev_point.ts,  # _bias_ts
                prev_point.bias,  # _bias
                prev_point.slope,  # _slope
                prev_point.ts,  # _ts0
                _last_point_window   # _ts1
            )
            self.integrated_totalSupply_over_window[_prev_point_window] += trapezoidArea

            assert last_point.ts == _last_point_window, "impossible: no point at window start"
            # no need to initialize integrated_totalSupply_over_window[_last_point_window] since interval=0
        elif _prev_point_window == _last_point_window:
            # extend aggregate
            trapezoidArea = self.anyTrapezoidArea(
                prev_point.ts,  # _bias_ts
                prev_point.bias,  # _bias
                prev_point.slope,  # _slope
                prev_point.ts,  # _ts0
                last_point.ts  # _ts1
            )
            self.integrated_totalSupply_over_window[checkpoint_ts] += trapezoidArea
        else:  # _prev_point_window > _last_point_window
            raise "impossible: prev window > last"

    self.epoch = _epoch
    # Now point_history is filled until t=now

    if addr != ZERO_ADDRESS:
        # If last point was in this block, the slope change has been applied already
        # But in such case we have 0 slope(s)
        last_point.slope += (u_new.slope - u_old.slope)
        last_point.bias += (u_new.bias - u_old.bias)
        if last_point.slope < 0:
            last_point.slope = 0
        if last_point.bias < 0:
            last_point.bias = 0

    # Record the changed point into history
    self.point_history[_epoch] = last_point

    if addr != ZERO_ADDRESS:
        # Schedule the slope changes (slope is going down)
        # We subtract new_user_slope from [new_locked.end]
        # and add old_user_slope to [old_locked.end]
        if old_locked.end > block.timestamp:
            # old_dslope was <something> - u_old.slope, so we cancel that
            old_dslope += u_old.slope
            if new_locked.end == old_locked.end:
                old_dslope -= u_new.slope  # It was a new deposit, not extension
            self.slope_changes[old_locked.end] = old_dslope
            self.slope_changes_keys[self.slope_changes_keys_next_index] = old_locked.end  # todo remove
            self.slope_changes_keys_next_index += 1

        if new_locked.end > block.timestamp:
            if new_locked.end > old_locked.end:
                new_dslope -= u_new.slope  # old slope disappeared at this point
                self.slope_changes[new_locked.end] = new_dslope
                self.slope_changes_keys[self.slope_changes_keys_next_index] = new_locked.end  # todo remove
                self.slope_changes_keys_next_index += 1

            # else: we recorded it already in old_dslope

        # Now handle user history
        user_epoch: uint256 = self.user_point_epoch[addr] + 1

        self.user_point_epoch[addr] = user_epoch
        u_new.ts = block.timestamp
        u_new.blk = block.number
        self.user_point_history[addr][user_epoch] = u_new


@internal
def _deposit_for(
        _addr: address,
        _value: uint256,
        unlock_time: uint256,
        locked_balance: LockedBalance,
        type: int128
):
    """
    @notice Deposit and lock tokens for a user
    @param _addr User's wallet address
    @param _value Amount to deposit
    @param unlock_time New time when to unlock the tokens, or 0 if unchanged
    @param locked_balance Previous locked amount / timestamp
    """
    _locked: LockedBalance = locked_balance
    supply_before: uint256 = self.supply

    self.supply = supply_before + _value
    old_locked: LockedBalance = _locked
    # Adding to existing lock, or if a lock is expired - creating a new one
    _locked.amount += convert(_value, int128)
    if unlock_time != 0:
        _locked.end = unlock_time
    self.locked[_addr] = _locked

    # Possibilities:
    # Both old_locked.end could be current or expired (>/< block.timestamp)
    # value == 0 (extend lock) or value > 0 (add to lock or extend lock)
    # _locked.end > block.timestamp (always)
    self._checkpoint(_addr, old_locked, _locked)

    if _value != 0:
        assert ERC20(self.token).transferFrom(_addr, self, _value)

    log Deposit(_addr, _value, _locked.end, type, block.timestamp)
    log Supply(supply_before, supply_before + _value)


@external
def checkpoint():
    """
    @notice Record global data to checkpoint
    """
    delay: uint256 = block.timestamp - self.last_manual_checkpoint_timestamp
    assert delay >= self._min_delay_between_manual_checkpoint(), "min delay failed"
    self.last_manual_checkpoint_timestamp = block.timestamp
    self._checkpoint(ZERO_ADDRESS, empty(LockedBalance), empty(LockedBalance))


@external
@nonreentrant('lock')
def deposit_for(_addr: address, _value: uint256):
    """
    @notice Deposit `_value` tokens for `_addr` and add to the lock
    @dev Anyone (even a smart contract) can deposit for someone else, but
         cannot extend their locktime and deposit for a brand new user
    @param _addr User's wallet address
    @param _value Amount to add to user's lock
    """
    assert not self.increase_amount_disabled, "increase amount disabled"
    assert not self.emergency, "not allowed in emergency"

    _locked: LockedBalance = self.locked[_addr]

    assert _value > 0, "zero stake not allowed"
    assert _value >= self.min_stake_amount, "too small stake amount"

    assert _locked.amount > 0, "No existing lock found"
    assert _locked.end > block.timestamp, "Cannot add to expired lock. Withdraw"

    self._deposit_for(_addr, _value, 0, self.locked[_addr], DEPOSIT_FOR_TYPE)


@external
@nonreentrant('lock')
def create_lock(_value: uint256, _unlock_time: uint256):
    """
    @notice Deposit `_value` tokens for `msg.sender` and lock until `_unlock_time`
    @param _value Amount to deposit
    @param _unlock_time Epoch time when tokens unlock, rounded down to whole weeks
    """
    assert not self.create_lock_disabled, "create lock disabled"
    assert not self.emergency, "not allowed in emergency"

    self.assert_not_contract(msg.sender)
    unlock_time: uint256 = (_unlock_time / EPOCH_SECONDS) * EPOCH_SECONDS  # Locktime is rounded down to weeks
    _locked: LockedBalance = self.locked[msg.sender]

    self.user_token_claimed_window_start[msg.sender] = self._currentWindow() - EPOCH_SECONDS   # to not process reward from =0
    self.pool_members += 1
    assert self.pool_members <= self.max_pool_members, "max_pool_members exceed"

    assert _value > 0, "zero stake not allowed"
    assert _value >= self.min_stake_amount, "too small stake amount"

    assert _locked.amount == 0, "Withdraw old tokens first"
    assert unlock_time > block.timestamp, "Can only lock until time in the future"
    assert unlock_time <= block.timestamp + MAXTIME, "Voting lock can be 4 years max"

    self._deposit_for(msg.sender, _value, unlock_time, _locked, CREATE_LOCK_TYPE)


@external
@nonreentrant('lock')
def increase_amount(_value: uint256):
    """
    @notice Deposit `_value` additional tokens for `msg.sender`
            without modifying the unlock time
    @param _value Amount of tokens to deposit and add to the lock
    """
    assert not self.increase_amount_disabled, "increase amount disabled"
    assert not self.emergency, "not allowed in emergency"

    self.assert_not_contract(msg.sender)
    _locked: LockedBalance = self.locked[msg.sender]

    assert _value > 0, "zero stake not allowed"
    assert _value >= self.min_stake_amount, "too small stake amount"

    assert _locked.amount > 0, "No existing lock found"
    assert _locked.end > block.timestamp, "Cannot add to expired lock. Withdraw"

    self._deposit_for(msg.sender, _value, 0, _locked, INCREASE_LOCK_AMOUNT)


@external
@nonreentrant('lock')
def increase_unlock_time(_unlock_time: uint256):
    """
    @notice Extend the unlock time for `msg.sender` to `_unlock_time`
    @param _unlock_time New epoch time for unlocking
    """
    assert not self.increase_unlock_time_disabled, "increase unlock time disabled"
    assert not self.emergency, "not allowed in emergency"

    self.assert_not_contract(msg.sender)
    _locked: LockedBalance = self.locked[msg.sender]
    unlock_time: uint256 = (_unlock_time / EPOCH_SECONDS) * EPOCH_SECONDS  # Locktime is rounded down to weeks

    assert _locked.amount > 0, "Nothing is locked"
    assert _locked.end > block.timestamp, "Lock expired"
    assert unlock_time > _locked.end, "Can only increase lock duration"
    assert unlock_time <= block.timestamp + MAXTIME, "Voting lock can be 4 years max"

    self._deposit_for(msg.sender, 0, unlock_time, _locked, INCREASE_UNLOCK_TIME)


@external
@nonreentrant('lock')
def withdraw():
    """
    @notice Withdraw all tokens for `msg.sender`
    @dev Only possible if the lock has expired
    """
    assert not self.withdraw_disabled, "withdraw disabled"
    assert not self.emergency, "not allowed in emergency"

    _locked: LockedBalance = self.locked[msg.sender]
    assert block.timestamp >= _locked.end, "The lock didn't expire"
    value: uint256 = convert(_locked.amount, uint256)

    old_locked: LockedBalance = _locked
    _locked.end = 0
    _locked.amount = 0
    self.locked[msg.sender] = _locked
    supply_before: uint256 = self.supply
    self.supply = supply_before - value

    # old_locked can have either expired <= timestamp or zero end
    # _locked has only 0 end
    # Both can have >= 0 amount
    self._checkpoint(msg.sender, old_locked, _locked)

    assert ERC20(self.token).transfer(msg.sender, value)

    self.pool_members -= 1

    log Withdraw(msg.sender, value, block.timestamp)
    log Supply(supply_before, supply_before - value)


# The following ERC20/minime-compatible methods are not real balanceOf and supply!
# They measure the weights for the purpose of voting, so they don't represent
# real coins.

@internal
@view
def find_block_epoch(_block: uint256, max_epoch: uint256) -> uint256:
    """
    @notice Binary search to estimate timestamp for block number
    @param _block Block to find
    @param max_epoch Don't go beyond this epoch
    @return Approximate timestamp for block
    """
    # Binary search
    _min: uint256 = 0
    _max: uint256 = max_epoch
    for i in range(128):  # Will be always enough for 128-bit numbers
        if _min >= _max:
            break
        _mid: uint256 = (_min + _max + 1) / 2
        if self.point_history[_mid].blk <= _block:
            _min = _mid
        else:
            _max = _mid - 1
    return _min


@internal
@view
def find_timestamp_epoch(_ts: uint256, max_epoch: uint256) -> uint256:
    """
    @notice Binary search for epoch timestamp
    @param _ts timestamp to find
    @param max_epoch Don't go beyond this epoch
    @return Approximate epoch for block
    """
    # Binary search
    _min: uint256 = 0
    _max: uint256 = max_epoch
    assert self.point_history[_min].ts <= _ts, "not found"
    # assert self.point_history[_max].ts >= _ts, "not found"  # commented out because you can search for the last epoch before ts
    for i in range(128):  # Will be always enough for 128-bit numbers
        if _min >= _max:
            break
        _mid: uint256 = (_min + _max + 1) / 2
        if self.point_history[_mid].ts <= _ts:
            _min = _mid
        else:
            _max = _mid - 1
    return _min


@external
@view
def balanceOf(addr: address, _t: uint256 = block.timestamp) -> uint256:
    """
    @notice Get the current voting power for `msg.sender`
    @dev Adheres to the ERC20 `balanceOf` interface for Aragon compatibility
    @param addr User wallet address
    @param _t Epoch time to return voting power at
    @return User voting power
    """
    _epoch: uint256 = self.user_point_epoch[addr]
    if _epoch == 0:
        return 0
    else:
        last_point: Point = self.user_point_history[addr][_epoch]
        last_point.bias -= last_point.slope * convert(_t - last_point.ts, int128)
        if last_point.bias < 0:
            last_point.bias = 0
        return convert(last_point.bias, uint256)


@external
@view
def balanceOfAt(addr: address, _block: uint256) -> uint256:
    """
    @notice Measure voting power of `addr` at block height `_block`
    @dev Adheres to MiniMe `balanceOfAt` interface: https://github.com/Giveth/minime
    @param addr User's wallet address
    @param _block Block to calculate the voting power at
    @return Voting power
    """
    # Copying and pasting totalSupply code because Vyper cannot pass by
    # reference yet
    assert _block <= block.number

    # Binary search
    _min: uint256 = 0
    _max: uint256 = self.user_point_epoch[addr]
    for i in range(128):  # Will be always enough for 128-bit numbers
        if _min >= _max:
            break
        _mid: uint256 = (_min + _max + 1) / 2
        if self.user_point_history[addr][_mid].blk <= _block:
            _min = _mid
        else:
            _max = _mid - 1

    upoint: Point = self.user_point_history[addr][_min]

    max_epoch: uint256 = self.epoch
    _epoch: uint256 = self.find_block_epoch(_block, max_epoch)
    point_0: Point = self.point_history[_epoch]
    d_block: uint256 = 0
    d_t: uint256 = 0
    if _epoch < max_epoch:
        point_1: Point = self.point_history[_epoch + 1]
        d_block = point_1.blk - point_0.blk
        d_t = point_1.ts - point_0.ts
    else:
        d_block = block.number - point_0.blk
        d_t = block.timestamp - point_0.ts
    block_time: uint256 = point_0.ts
    if d_block != 0:
        block_time += d_t * (_block - point_0.blk) / d_block

    upoint.bias -= upoint.slope * convert(block_time - upoint.ts, int128)
    if upoint.bias >= 0:
        return convert(upoint.bias, uint256)
    else:
        return 0


@external
@view
def balanceOfAtTimestamp(addr: address, _ts: uint256) -> uint256:
    """
    @notice Measure voting power of `addr` at block height `_block`
    @dev Adheres to MiniMe `balanceOfAt` interface: https://github.com/Giveth/minime
    @param addr User's wallet address
    @param _ts Timestamp
    @return Voting power
    """
    assert _ts <= block.timestamp  # xx todo extend

    # Binary search
    _min: uint256 = 0
    _max: uint256 = self.user_point_epoch[addr]
    for i in range(128):  # Will be always enough for 128-bit numbers
        if _min >= _max:
            break
        _mid: uint256 = (_min + _max + 1) / 2
        if self.user_point_history[addr][_mid].ts <= _ts:
            _min = _mid
        else:
            _max = _mid - 1

    upoint: Point = self.user_point_history[addr][_min]

    max_epoch: uint256 = self.epoch
    _epoch: uint256 = self.find_timestamp_epoch(_ts, max_epoch)

    upoint.bias -= upoint.slope * convert(_ts - upoint.ts, int128)
    if upoint.bias >= 0:
        return convert(upoint.bias, uint256)
    else:
        return 0


@internal
@view
def supply_at(point: Point, t: uint256) -> uint256:
    """
    @notice Calculate total voting power at some point in the past
    @param point The point (bias/slope) to start search from
    @param t Time to calculate the total voting power at
    @return Total voting power at that time
    """
    last_point: Point = point
    t_i: uint256 = (last_point.ts / EPOCH_SECONDS) * EPOCH_SECONDS
    for i in range(255):
        t_i += EPOCH_SECONDS
        d_slope: int128 = 0
        if t_i > t:
            t_i = t
        else:
            d_slope = self.slope_changes[t_i]
        last_point.bias -= last_point.slope * convert(t_i - last_point.ts, int128)
        if t_i == t:
            break
        last_point.slope += d_slope
        last_point.ts = t_i

    if last_point.bias < 0:
        last_point.bias = 0
    return convert(last_point.bias, uint256)


@external
@view
def totalSupply(t: uint256 = block.timestamp) -> uint256:
    return self._totalSupply(t)


@internal
@view
def _totalSupply(t: uint256 = block.timestamp) -> uint256:
    """
    @notice Calculate total voting power
    @dev Adheres to the ERC20 `totalSupply` interface for Aragon compatibility
    @return Total voting power
    """
    _epoch: uint256 = self.epoch
    last_point: Point = self.point_history[_epoch]
    return self.supply_at(last_point, t)


@external
@view
def totalSupplyAtTimestamp(_ts: uint256) -> (uint256, uint256):
    """
    @notice Calculate total voting power at some point in the past
    @param _ts Timestamp to calculate the total voting power at
    @return target_epoch, Total voting power at `_ts`
    """
    return self._totalSupplyAtTimestamp(_ts)


@internal
@view
def _totalSupplyAtTimestamp(_ts: uint256) -> (uint256, uint256):
    """
    @notice Calculate total voting power at some point in the past
    @param _ts Timestamp to calculate the total voting power at
    @return target_epoch, Total voting power at `_ts`
    """
    _epoch: uint256 = self.epoch
    target_epoch: uint256 = self.find_timestamp_epoch(_ts, _epoch)
    point: Point = self.point_history[target_epoch]
    return target_epoch, self.supply_at(point, _ts)


@external
@view
def totalSupplyAt(_block: uint256) -> uint256:
    """
    @notice Calculate total voting power at some point in the past
    @param _block Block to calculate the total voting power at
    @return Total voting power at `_block`
    """
    assert _block <= block.number
    _epoch: uint256 = self.epoch
    target_epoch: uint256 = self.find_block_epoch(_block, _epoch)

    point: Point = self.point_history[target_epoch]
    dt: uint256 = 0
    if target_epoch < _epoch:
        point_next: Point = self.point_history[target_epoch + 1]
        if point.blk != point_next.blk:
            dt = (_block - point.blk) * (point_next.ts - point.ts) / (point_next.blk - point.blk)
    else:
        if point.blk != block.number:
            dt = (_block - point.blk) * (block.timestamp - point.ts) / (block.number - point.blk)
    # Now dt contains info on how far are we beyond point

    return self.supply_at(point, point.ts + dt)


# Dummy methods for compatibility with Aragon

# todo uncomment
# @external
# def changeController(_newController: address):
#     """
#     @dev Dummy method required for Aragon compatibility
#     """
#     assert msg.sender == self.controller
#     self.controller = _newController


# Rewards
# original contract - https://etherscan.io/address/0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2

# inspired by balanceOfAt
@external
@view
def searchForUserEpochByTimestamp(addr: address, ts: uint256) -> uint256:
    return self._searchForUserEpochByTimestamp(addr, ts)


# inspired by balanceOfAt
@internal
@view
def _searchForUserEpochByTimestamp(addr: address, ts: uint256) -> uint256:
    # Binary search - as in balanceOfAt BUT OVER ts
    _min: uint256 = 0
    _max: uint256 = self.user_point_epoch[addr]

    if self.user_point_history[addr][_min].ts > ts:
        return MAX_UINT256
    if self.user_point_history[addr][_max].ts < ts:
        return _max   # note!

    for i in range(128):  # Will be always enough for 128-bit numbers
        if _min >= _max:
            break
        _mid: uint256 = (_min + _max + 1) / 2
        if self.user_point_history[addr][_mid].ts <= ts:
            _min = _mid
        else:
            _max = _mid - 1
    return _min


event _averageUserBalanaceOverWindowDebug:
    user_epoch_start: uint256
    user_epoch_end: uint256
    avg_balance: uint256


event _averageUserBalanceOverWindowDebugSZeroInterval:
    user_epoch: uint256
    bias: int128
    slope: int128
    _ts0: uint256
    _ts1: uint256
    _ts: uint256
    trapezoidArea: uint256


event _averageUserBalanceOverWindowDebugS:
    user_epoch: uint256
    bias: int128
    slope: int128
    _ts0: uint256
    _ts1: uint256
    _ts: uint256
    trapezoidArea: uint256


@internal
@view
def anyTrapezoidArea(
        _bias_ts: uint256,
        _bias: int128,
        _slope: int128,
        _ts0: uint256,
        _ts1: uint256
) -> uint256:
    assert _ts1 >= _ts0, "wrong ts"
    start_bias: int128 = _bias - _slope * convert(_ts0 - _bias_ts, int128)
    end_bias: int128 = _bias - _slope * convert(_ts1 - _bias_ts, int128)
    if start_bias < 0:
        return 0
    elif end_bias < 0:
        end_ts: uint256 = _ts0 + convert(_bias / _slope, uint256)
        _ts: uint256 = end_ts - _ts0
        return convert(start_bias, uint256) * _ts / 2  # triangle
    else:
        _ts: uint256 = _ts1 - _ts0
        return _ts * convert(start_bias + end_bias, uint256) / 2  # trapezoid


@external
def averageUserBalanaceOverWindowTx(addr: address, _window: uint256) -> uint256:
    return self._averageUserBalanaceOverWindow(addr, _window)


@external
@view
def averageUserBalanaceOverWindow(addr: address, _window: uint256) -> uint256:
    return self._averageUserBalanaceOverWindow(addr, _window)


@internal
@view
def _averageUserBalanaceOverWindow(addr: address, _window: uint256) -> uint256:
    assert _window < self._currentWindow(), "unfinalized window"
    ts_start: uint256 = _window
    ts_end: uint256 = _window + EPOCH_SECONDS

    user_epoch_start: uint256 = self._searchForUserEpochByTimestamp(addr, ts_start)
    if user_epoch_start == MAX_UINT256:
        raise "failed user_epoch_start searchForUserEpochByTimestamp"
    user_epoch_end: uint256 = self._searchForUserEpochByTimestamp(addr, ts_end)
    if user_epoch_end == MAX_UINT256:
        raise "failed user_epoch_end searchForUserEpochByTimestamp"

    areaUnderPolyline: uint256 = 0
    user_epoch: uint256 = user_epoch_start
    for d_user_epoch in range(1024):  # todo be careful here
        if user_epoch > user_epoch_end:  # note: we use > because we want to process the end epoch as well
            break
        bias: int128 = self.user_point_history[addr][user_epoch].bias
        slope: int128 = self.user_point_history[addr][user_epoch].slope
        _ts_begin: uint256 = self.user_point_history[addr][user_epoch].ts
        _ts0: uint256 = _ts_begin

        _ts1: uint256 = self.user_point_history[addr][user_epoch+1].ts
        if _ts1 == 0:  # the last user epoch
            _ts1 = ts_end

        if _ts1 > ts_end:
            _ts1 = ts_end
        if _ts0 < ts_start:
            _ts0 = ts_start

        trapezoidArea: uint256 = self.anyTrapezoidArea(_ts_begin, bias, slope, _ts0, _ts1)
        areaUnderPolyline += trapezoidArea

        if ts_end == ts_start:  #xx todo discuss
            assert user_epoch_start == user_epoch_end
            assert _ts0 == _ts1
            log _averageUserBalanceOverWindowDebugSZeroInterval(
                user_epoch,
                bias,
                slope,
                _ts0,
                _ts1,
                _ts1-_ts0,
                0
            )
            log _averageUserBalanaceOverWindowDebug(user_epoch_start, user_epoch_end, convert(bias, uint256))
            return convert(bias, uint256)


        log _averageUserBalanceOverWindowDebugS(
            user_epoch,
            bias,
            slope,
            _ts0,
            _ts1,
            _ts1 - _ts0,
            trapezoidArea
        )

        # next iteration
        user_epoch += 1

    avgBalance: uint256 = areaUnderPolyline / (ts_end - ts_start)
    log _averageUserBalanaceOverWindowDebug(user_epoch_start, user_epoch_end, avgBalance)
    return avgBalance


event _averageTotalSupplyOverEpoch:
    _epoch: uint256
    _ts0: uint256
    _ts1: uint256
    bias: int128
    bias_end: int128
    slope: int128
    result: uint256


@external
@view
def averageTotalSupplyOverWindow(_window: uint256) -> uint256:
    return self._averageTotalSupplyOverWindow(_window)


event _averageTotalSupplyOverWindow_NewWindow:
    _window: uint256
    target_epoch_start: uint256
    total_supply_start: uint256
    target_epoch_end: uint256
    total_supply_end: uint256
    trapezoidArea: uint256


@internal
@view
def _averageTotalSupplyOverWindow(_window: uint256) -> uint256:
    assert _window < self._currentWindow(), "incorrect window"
    trapezoidArea: uint256 = 0
    _epoch: uint256 = self.epoch
    if self.point_history[_epoch].ts < _window:
        # you know the last point, and only need to integrate the curve
        # do not forget about slope changes! (it's handled inside _totalSupplyAtTimestamp)
        target_epoch_start: uint256 = 0
        total_supply_start: uint256 = 0
        target_epoch_end: uint256 = 0
        total_supply_end: uint256 = 0
        target_epoch_start, total_supply_start = self._totalSupplyAtTimestamp(_window)
        target_epoch_end, total_supply_end = self._totalSupplyAtTimestamp(_window + EPOCH_SECONDS)
        assert _epoch == target_epoch_start, "impossible: not last epoch"
        assert _epoch == target_epoch_end, "impossible: not last epoch"
        trapezoidArea = (total_supply_start + total_supply_end) * EPOCH_SECONDS / 2
        log _averageTotalSupplyOverWindow_NewWindow(
            _window,
            target_epoch_start,
            total_supply_start,
            target_epoch_end,
            total_supply_end,
            trapezoidArea,
        )
    elif self.point_history[_epoch].ts < _window + EPOCH_SECONDS:
        # the window is partially aggregated in interval [_window; self.point_history[_epoch].ts]
        # so we calculate trapezoid area in [self.point_history[_epoch].ts; _window + EPOCH_SECONDS]
        trapezoidArea = self.anyTrapezoidArea(
            self.point_history[_epoch].ts,
            self.point_history[_epoch].bias,
            self.point_history[_epoch].slope,
            self.point_history[_epoch].ts,
            _window + EPOCH_SECONDS
        )
        trapezoidArea += self.integrated_totalSupply_over_window[_window]
    else: # _window + EPOCH_SECONDS <= self.point_history[_epoch].ts
        # the window is fully aggregated
        trapezoidArea = self.integrated_totalSupply_over_window[_window]

    return trapezoidArea / EPOCH_SECONDS


# from https://ethereum.stackexchange.com/questions/84775/is-there-a-vyper-equivalent-to-openzeppelins-safeerc20-safetransfer
@internal
def safe_transfer(_token: address, _to: address, _value: uint256):
    _response: Bytes[32] = raw_call(
        _token,
        concat(
            method_id("transfer(address,uint256)"),
            convert(_to, bytes32),
            convert(_value, bytes32)
        ),
        max_outsize=32
    )
    if len(_response) > 0:
        assert convert(_response, bool), "Transfer failed!"


@internal
def safe_transfer_from(_token: address, _from: address, _to: address, _value: uint256):
    _response: Bytes[32] = raw_call(
        _token,
        concat(
            method_id("transferFrom(address,address,uint256)"),
            convert(_from, bytes32),
            convert(_to, bytes32),
            convert(_value, bytes32)
        ),
        max_outsize=32
    )
    if len(_response) > 0:
        assert convert(_response, bool), "Transfer failed!"


event WindowRewardReceived:
    window: indexed(uint256)
    token: indexed(address)
    amount: uint256
    actual_amount: uint256


@external
@payable
def receiveNativeReward():
    self.window_token_rewards[self._currentWindow()][ZERO_ADDRESS] += msg.value
    log WindowRewardReceived(self._currentWindow(), ZERO_ADDRESS, msg.value, msg.value)


@external
def receiveReward(_token: address, amount: uint256):
    balance_before: uint256 = ERC20(_token).balanceOf(self)
    self.safe_transfer_from(_token, msg.sender, self, amount)
    actual_amount: uint256 = ERC20(_token).balanceOf(self) - balance_before  # handle fee token
    self.window_token_rewards[self._currentWindow()][_token] += actual_amount
    log WindowRewardReceived(self._currentWindow(), _token, amount, actual_amount)


event UserRewardsClaimed:
    user_claimed_epoch: indexed(uint256)
    token: indexed(address)
    amount: uint256


event UserRewardsClaimedDebug:
    _epoch: uint256
    _avgUserBalanace: uint256
    _avgTotalSupply: uint256
    _epochReward: uint256
    _userEpochReward: uint256


event Log0Args:
    message: String[256]


event Log1Args:
    message1: String[256]
    value1: uint256


event Log2Args:
    message1: String[256]
    value1: uint256
    message2: String[256]
    value2: uint256


@internal
@view
def _currentWindow() -> uint256:
    return block.timestamp / EPOCH_SECONDS * EPOCH_SECONDS


@external
@view
def currentWindow() -> uint256:
    return self._currentWindow()


event _user_token_claimable_rewards_log:
    _window: uint256
    _avgUserBalanace: uint256
    _avgTotalSupply: uint256
    _windowReward: uint256
    _thisWindowUserReward: uint256


event UserClaimWindowStart:
    value: uint256


event UserClaimWindowEnd:
    value: uint256


@internal
@view
def _user_token_claimable_rewards(user: address, _token: address) -> (uint256, uint256):
    rewardsAmount: uint256 = 0

    __currentWindow: uint256 = self._currentWindow()
    log Log1Args("__currentWindow", __currentWindow)

    _window: uint256 = self.user_token_claimed_window[user][_token]
    if _window == 0:
        _window = self.user_token_claimed_window_start[user]
        assert _window != 0, "no deposit or broken state"
    log UserClaimWindowStart(_window)
    log Log1Args("initial _window", _window)

    for d_window in range(1024):
        _window += EPOCH_SECONDS  # move to process the next unprocessed widnow
        if _window >= __currentWindow:  # note: we use >= because currentWindow is not finalized
            _window -= EPOCH_SECONDS  # we want to keep last processed value
            break
        _avgUserBalanace: uint256 = self._averageUserBalanaceOverWindow(user, _window)
        if _avgUserBalanace == 0:
            log Log1Args("_user_token_claimable_rewards skip _window = {0} because _avgUserBalanace=0", _window)
            continue
        _avgTotalSupply: uint256 = self._averageTotalSupplyOverWindow(_window)
        if _avgTotalSupply == 0:
            log Log1Args("_user_token_claimable_rewards skip _window = {0} because _avgTotalSupply=0", _window)
            continue
        _windowReward: uint256 = self.window_token_rewards[_window][_token]
        if _windowReward == 0:
            log Log1Args("_user_token_claimable_rewards skip _window = {0} because _windowReward=0", _window)
            continue
        _thisWindowUserReward: uint256 = _windowReward * _avgUserBalanace / _avgTotalSupply
        log _user_token_claimable_rewards_log(
            _window,
            _avgUserBalanace,
            _avgTotalSupply,
            _windowReward,
            _thisWindowUserReward
        )
        rewardsAmount += _thisWindowUserReward
    return rewardsAmount, _window


@external
def user_token_claimable_rewardsTx(user: address, _token: address) -> uint256:
    rewardsAmount: uint256 = 0
    lastProcessedWindow: uint256 = 0
    (rewardsAmount, lastProcessedWindow) = self._user_token_claimable_rewards(user, _token)
    return rewardsAmount


@external
@view
def user_token_claimable_rewards(user: address, _token: address) -> uint256:
    rewardsAmount: uint256 = 0
    lastProcessedWindow: uint256 = 0
    (rewardsAmount, lastProcessedWindow) = self._user_token_claimable_rewards(user, _token)
    return rewardsAmount


# todo uncomment
# # if there was no stake, but reward was transferred to the contract
# # no one can claim it in a usual way, so it will be forever stuck
# # for such situation we have this special method to transfer
# # stuck reward to the owner
# @external
# def claim_stuck_rewards(_token: address, _window: uint256):
#     assert msg.sender == self._admin()
#     assert _window < self._currentWindow(), "unfinalized window"
#     assert not self.stuckWindowRewardClaimed[_window], "already claimed"
#     self.stuckWindowRewardClaimed[_window] = True
#
#     _windowReward: uint256 = self.window_token_rewards[_window][_token]
#     if _windowReward == 0:
#         log Log1Args("skip _window {0} because _windowReward=0", _window)
#         return
#
#     _avgTotalSupply: uint256 = self._averageTotalSupplyOverWindow(_window)
#     assert _avgTotalSupply == 0, "reward not stuck"
#
#     log StuckWindowRewardClaimed(_window, _token, _windowReward)
#
#     if _token == ZERO_ADDRESS:
#         send(msg.sender, _windowReward)
#     else:
#         self.safe_transfer(_token, msg.sender, _windowReward)


@external
def claim_rewards(_token: address):
    rewardsAmount: uint256 = 0
    lastProcessedWindow: uint256 = 0
    (rewardsAmount, lastProcessedWindow) = self._user_token_claimable_rewards(msg.sender, _token)
    self.user_token_claimed_window[msg.sender][_token] = lastProcessedWindow
    log UserClaimWindowEnd(lastProcessedWindow)

    self.any_transfer(_token, msg.sender, rewardsAmount)
    log UserRewardsClaimed(lastProcessedWindow, _token, rewardsAmount)


@internal
def any_transfer(_token: address, _to: address, _value: uint256):
    if _token == ZERO_ADDRESS:
        send(_to, _value)
        log TransferNative(_to, _value)
    else:
        self.safe_transfer(_token, _to, _value)

# emergency

# todo uncomment
# @external
# def emergency_withdraw(_token: address, _amount: uint256, to: address):
#     assert msg.sender == self._admin()
#     if _token == ZERO_ADDRESS:
#         send(to, _amount)
#     else:
#         self.safe_transfer(_token, to, _amount)
#
#
# @external
# def emergency_withdraw_many(_tokens: address[30], _amounts: uint256[30], tos: address[30]):
#     assert msg.sender == self._admin()
#     for i in range(30):
#         _token: address = _tokens[i]
#         _amount: uint256 = _amounts[i]
#         to: address = tos[i]
#         if _token == ZERO_ADDRESS:
#             send(to, _amount)
#         else:
#             self.safe_transfer(_token, to, _amount)
