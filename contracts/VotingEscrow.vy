# @version 0.2.4
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

DEPOSIT_FOR_TYPE: constant(int128) = 0
CREATE_LOCK_TYPE: constant(int128) = 1
INCREASE_LOCK_AMOUNT: constant(int128) = 2
INCREASE_UNLOCK_TIME: constant(int128) = 3


event CommitOwnership:
    admin: address

event ApplyOwnership:
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

last_manual_checkpoint_timestamp: public(uint256)
min_delay_between_manual_checkpoint: public(uint256)

event MinDelayBetweenManualCheckpointSet:
    value: uint256

@external
def set_min_delay_between_manual_checkpoint(value: uint256):
    assert msg.sender == self.admin, "not admin"
    assert self.last_manual_checkpoint_timestamp != value, "not changed"

token: public(address)
supply: public(uint256)

locked: public(HashMap[address, LockedBalance])

epoch: public(uint256)
point_history: public(Point[100000000000000000000000000000])  # epoch -> unsigned point
user_point_history: public(HashMap[address, Point[1000000000]])  # user -> Point[user_epoch]
user_point_epoch: public(HashMap[address, uint256])
slope_changes: public(HashMap[uint256, int128])  # time -> signed slope change
slope_changes_keys: public(uint256[100000])  # todo remove
slope_changes_keys_next_index: public(uint256)
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
future_smart_wallet_checker: public(address)
smart_wallet_checker: public(address)

admin: public(address)  # Can and will be a smart contract
future_admin: public(address)

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

event Emergency:
    pass

@external
def enable_emergency():
    assert msg.sender == self.admin
    assert not self.emergency
    self.emergency = True
    log Emergency()

@external
def set_min_stake_amount(_value: uint256):
    assert msg.sender == self.admin
    assert self.min_stake_amount != _value
    self.min_stake_amount = _value
    log MinStakeAmountSet(_value)

@external
def set_withdraw_disabled(_value: bool):
    assert msg.sender == self.admin
    assert self.withdraw_disabled != _value
    self.withdraw_disabled = _value
    log WithdrawDisabledSet(_value)

@external
def set_create_lock_disabled(_value: bool):
    assert msg.sender == self.admin
    assert self.create_lock_disabled != _value
    self.create_lock_disabled = _value
    log CreateLockDisabledSet(_value)

@external
def set_increase_amount_disabled(_value: bool):
    assert msg.sender == self.admin
    assert self.increase_amount_disabled != _value
    self.increase_amount_disabled = _value
    log IncreaseAmountDisabledSet(_value)

@external
def set_increase_unlock_time_disabled(_value: bool):
    assert msg.sender == self.admin
    assert self.increase_unlock_time_disabled != _value
    self.increase_unlock_time_disabled = _value
    log IncreaseUnlockTimeDisabledSet(_value)

@external
def pause():
    assert msg.sender == self.admin

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
    assert msg.sender == self.admin

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
def __init__(token_addr: address, _name: String[64], _symbol: String[32], _version: String[32]):
    """
    @notice Contract constructor
    @param token_addr `ERC20CRV` token address
    @param _name Token name
    @param _symbol Token symbol
    @param _version Contract version - required for Aragon compatibility
    """
    self.admin = msg.sender
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


@external
def commit_transfer_ownership(addr: address):
    """
    @notice Transfer ownership of VotingEscrow contract to `addr`
    @param addr Address to have ownership transferred to
    """
    assert msg.sender == self.admin, "not admin"  # dev: admin only
    self.future_admin = addr
    log CommitOwnership(addr)


@external
def apply_transfer_ownership():
    """
    @notice Apply ownership transfer
    """
    assert msg.sender == self.admin, "not admin"  # dev: admin only
    _admin: address = self.future_admin
    assert _admin != ZERO_ADDRESS  # dev: admin not set
    self.admin = _admin
    log ApplyOwnership(_admin)


@external
def commit_smart_wallet_checker(addr: address):
    """
    @notice Set an external contract to check for approved smart contract wallets
    @param addr Address of Smart contract checker
    """
    assert msg.sender == self.admin, "not admin"
    self.future_smart_wallet_checker = addr


@external
def apply_smart_wallet_checker():
    """
    @notice Apply setting external contract to check approved smart contract wallets
    """
    assert msg.sender == self.admin, "not admin"
    self.smart_wallet_checker = self.future_smart_wallet_checker


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
            u_old.slope = old_locked.amount / MAXTIME  # todo why??
            u_old.bias = u_old.slope * convert(old_locked.end - block.timestamp, int128)
        if new_locked.end > block.timestamp and new_locked.amount > 0:
            u_new.slope = new_locked.amount / MAXTIME
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
    last_checkpoint: uint256 = last_point.ts
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
    t_i: uint256 = (last_checkpoint / EPOCH_SECONDS) * EPOCH_SECONDS
    for i in range(255):
        # Hopefully it won't happen that this won't get used in 5 years!
        # If it does, users will be able to withdraw but vote weight will be broken
        t_i += EPOCH_SECONDS
        d_slope: int128 = 0
        if t_i > block.timestamp:
            t_i = block.timestamp
        else:
            d_slope = self.slope_changes[t_i]
        last_point.bias -= last_point.slope * convert(t_i - last_checkpoint, int128)
        last_point.slope += d_slope
        if last_point.bias < 0:  # This can happen
            last_point.bias = 0
        if last_point.slope < 0:  # This cannot happen - just in case
            last_point.slope = 0
        last_checkpoint = t_i
        last_point.ts = t_i
        last_point.blk = initial_last_point.blk + block_slope * (t_i - initial_last_point.ts) / MULTIPLIER
        _epoch += 1
        if t_i == block.timestamp:
            last_point.blk = block.number
            break
        else:
            self.point_history[_epoch] = last_point

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

    assert _locked.end > block.timestamp, "Lock expired"
    assert _locked.amount > 0, "Nothing is locked"
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

@external
def changeController(_newController: address):
    """
    @dev Dummy method required for Aragon compatibility
    """
    assert msg.sender == self.controller
    self.controller = _newController


# Rewards

# original contract - https://etherscan.io/address/0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2

user_token_claimed_epoch: public(HashMap[address, HashMap[address, uint256]])  # user -> token -> lastClaimedEpoch
epoch_token_rewards: public(HashMap[uint256, HashMap[address, uint256]])  # epoch -> token -> totalRewardsAmount

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
        return _max   #xx ???

    for i in range(128):  # Will be always enough for 128-bit numbers
        if _min >= _max:
            break
        _mid: uint256 = (_min + _max + 1) / 2
        if self.user_point_history[addr][_mid].ts <= ts:
            _min = _mid
        else:
            _max = _mid - 1
    return _min

event _averageUserBlanaceOverEpochDebug:
    user_epoch_start: uint256
    user_epoch_end: uint256

event _averageUserBlanaceOverEpochDebugS:
    user_epoch: uint256
    bias: int128
    slope: int128
    _ts0: uint256
    _ts1: uint256
    _ts: uint256
    trapezoidArea: uint256


# @external
# @view
# def _averageUserBlanaceOverEpochView(addr: address, _epoch: uint256) -> uint256:
#     assert _epoch < self.epoch, "unfnalized epoch"
#     ts_start: uint256 = self.point_history[_epoch].ts
#     ts_end: uint256 = self.point_history[_epoch+1].ts
#
#     user_epoch_start: uint256 = self._searchForUserEpochByTimestamp(addr, ts_start)
#     if user_epoch_start == MAX_UINT256:
#         raise "failed user_epoch_start searchForUserEpochByTimestamp"
#     user_epoch_end: uint256 = self._searchForUserEpochByTimestamp(addr, ts_end)
#     if user_epoch_end == MAX_UINT256:
#         raise "failed user_epoch_end searchForUserEpochByTimestamp"
#
#     # todo: check it
#     areaUnderPolyline: uint256 = 0  # todo think about phantom overflow
#     user_epoch: uint256 = user_epoch_start
#     for d_user_epoch in range(256):  # todo be careful here DoS attack!, we may use additional aggregation
#         if user_epoch > user_epoch_end:  # note: we use > because we want to process the end epoch as well
#             break
#         bias: int128 = self.user_point_history[addr][user_epoch].bias
#         slope: int128 = self.user_point_history[addr][user_epoch].slope
#         _ts0: uint256 = self.user_point_history[addr][user_epoch].ts
#         _ts1: uint256 = self.user_point_history[addr][user_epoch+1].ts
#         if _ts1 == 0:
#             _ts1 = ts_end
#
#         _ts: uint256 = _ts1 - _ts0 + 1  #xx ?? +1
#         trapezoidArea: uint256 = convert(bias + slope/2, uint256) * _ts  # todo: handle bias + slope/2 < 0
#         areaUnderPolyline += trapezoidArea
#
#         # next iteration
#         user_epoch += 1
#
#     avgBalance: uint256 = areaUnderPolyline / (ts_end - ts_start + 1)
#     return avgBalance

@internal
@view
def _averageUserBlanaceOverEpoch(addr: address, _epoch: uint256) -> uint256:
    assert _epoch < self.epoch, "unfnalized epoch"  # typo
    ts_start: uint256 = self.point_history[_epoch].ts
    ts_end: uint256 = self.point_history[_epoch+1].ts

    user_epoch_start: uint256 = self._searchForUserEpochByTimestamp(addr, ts_start)
    if user_epoch_start == MAX_UINT256:
        raise "failed user_epoch_start searchForUserEpochByTimestamp"
    user_epoch_end: uint256 = self._searchForUserEpochByTimestamp(addr, ts_end)
    if user_epoch_end == MAX_UINT256:
        raise "failed user_epoch_end searchForUserEpochByTimestamp"

    # todo: check it
    areaUnderPolyline: uint256 = 0
    user_epoch: uint256 = user_epoch_start
    for d_user_epoch in range(256):  # todo be careful here DoS attack!, we may use additional aggregation
        if user_epoch > user_epoch_end:  # note: we use > because we want to process the end epoch as well
            break
        bias: int128 = self.user_point_history[addr][user_epoch].bias
        slope: int128 = self.user_point_history[addr][user_epoch].slope
        _ts_begin: uint256 = self.user_point_history[addr][user_epoch].ts
        _ts0: uint256 = _ts_begin
        _ts1: uint256 = self.user_point_history[addr][user_epoch+1].ts

        if _ts1 == 0:
            _ts1 = ts_end

        #xx ??
        if _ts1 > ts_end:
            _ts1 = ts_end
        if _ts0 < ts_start:
            _ts0 = ts_start

        _ts: uint256 = _ts1 - _ts0
        start_bias: int128 = bias - slope * convert(_ts0 - _ts_begin, int128)
        end_bias: int128 = bias - slope * convert(_ts1 - _ts_begin, int128)

        trapezoidArea: uint256 = 0
        if start_bias < 0:
            trapezoidArea = 0
        elif end_bias < 0:
            end_ts: uint256 = _ts0 + convert(bias / slope, uint256)
            trapezoidArea = convert(start_bias, uint256) * (end_ts - _ts0) / 2  # triangle
        else:
            trapezoidArea = _ts * convert(start_bias + end_bias, uint256) / 2

        areaUnderPolyline += trapezoidArea

        if ts_end == ts_start:  #xx todo discuss
            assert user_epoch_start == user_epoch_end
            log _averageUserBlanaceOverEpochDebugS(
                user_epoch,
                bias,
                slope,
                _ts0,
                _ts1,
                _ts,
                0
            )
            log _averageUserBlanaceOverEpochDebug(user_epoch_start, user_epoch_end)
            return convert(start_bias, uint256)


        log _averageUserBlanaceOverEpochDebugS(
            user_epoch,
            bias,
            slope,
            _ts0,
            _ts1,
            _ts,
            trapezoidArea
        )

        # next iteration
        user_epoch += 1

    log _averageUserBlanaceOverEpochDebug(user_epoch_start, user_epoch_end)

    avgBalance: uint256 = areaUnderPolyline / (ts_end - ts_start)
    return avgBalance

event _averageTotalSupplyOverEpoch:
    _epoch: uint256
    _ts0: uint256
    _ts1: uint256
    bias: int128
    bias_end: int128
    slope: int128
    result: uint256

@internal
@view
def _averageTotalSupplyOverEpoch(_epoch: uint256) -> uint256:
    assert _epoch < self.epoch, "incorrect epoch"
    _ts0: uint256 = self.point_history[_epoch].ts
    _ts1: uint256 = self.point_history[_epoch+1].ts
    bias: int128 = self.point_history[_epoch].bias
    slope: int128 = self.point_history[_epoch].slope

    if _ts0 == _ts1:
        return convert(bias, uint256)

    _ts: uint256 = _ts1 - _ts0
    end_bias: int128 = bias - slope * convert(_ts, int128)
    trapezoidArea: uint256 = 0
    if end_bias < 0:
        end_ts: uint256 = _ts0 + convert(bias / slope, uint256)
        trapezoidArea = convert(bias, uint256) * (end_ts - _ts0) / 2  # triangle
    else:
        trapezoidArea = _ts * convert(bias + end_bias, uint256) / 2

    result: uint256 = trapezoidArea / _ts
    # log _averageTotalSupplyOverEpoch(
    #     _epoch,
    #     _ts0,
    #     _ts1,
    #     bias,
    #     end_bias,
    #     slope,
    #     result
    # )
    return result

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


event RewardReceived:
    token: indexed(address)
    amount: uint256
    actual_amount: uint256


@external
@payable
def receiveNativeReward():
    if (not (
               (self.point_history[self.epoch].ts <= block.timestamp) and
               (block.timestamp < self.point_history[self.epoch].ts + EPOCH_SECONDS)
    )):
        self._checkpoint(ZERO_ADDRESS, empty(LockedBalance), empty(LockedBalance))
    self.epoch_token_rewards[self.epoch][ZERO_ADDRESS] += msg.value
    log RewardReceived(ZERO_ADDRESS, msg.value, msg.value)


@external
def receiveReward(_token: address, amount: uint256):
    if (not (
               (self.point_history[self.epoch].ts <= block.timestamp) and
               (block.timestamp < self.point_history[self.epoch].ts + EPOCH_SECONDS)
    )):
        self._checkpoint(ZERO_ADDRESS, empty(LockedBalance), empty(LockedBalance))
    balance_before: uint256 = ERC20(_token).balanceOf(self)
    self.safe_transfer_from(_token, msg.sender, self, amount)
    actual_amount: uint256 = ERC20(_token).balanceOf(self) - balance_before
    self.epoch_token_rewards[self.epoch][_token] += actual_amount
    log RewardReceived(_token, amount, actual_amount)


event UserRewardsClaimed:
    user_claimed_epoch: indexed(uint256)
    token: indexed(address)
    amount: uint256


event UserRewardsClaimedDebug:
    _epoch: uint256
    _avgUserBlanace: uint256
    _avgTotalSupply: uint256
    _epochReward: uint256
    _userEpochReward: uint256


@external
@view
def claimable_rewards(_token: address, user: address = msg.sender) -> uint256:
    rewardsAmount: uint256 = 0
    _user_claimed_epoch: uint256 = self.user_token_claimed_epoch[user][_token]
    currentEpoch: uint256 = self.epoch  # load to memory once
    _epoch: uint256 = _user_claimed_epoch
    for d_epoch in range(255):  #xx 255?
        _epoch += 1  # move to process the next unprocessed epoch
        if _epoch >= currentEpoch:  # note: we use >= because currentEpoch is not finalized
            break
        _avgUserBlanace: uint256 = self._averageUserBlanaceOverEpoch(user, _epoch)
        _avgTotalSupply: uint256 = self._averageTotalSupplyOverEpoch(_epoch)
        _epochReward: uint256 = self.epoch_token_rewards[_epoch][_token]
        rewardsAmount += _epochReward * _avgUserBlanace / _avgTotalSupply
        log UserRewardsClaimedDebug(_epoch, _avgUserBlanace, _avgTotalSupply, _epochReward, _epochReward * _avgUserBlanace / _avgTotalSupply)
    log UserRewardsClaimed(_epoch - 1, _token, rewardsAmount)
    return rewardsAmount


#xx todo what if rewards but no locker?
@external
def claim_rewards(_token: address):
    rewardsAmount: uint256 = 0
    _user_claimed_epoch: uint256 = self.user_token_claimed_epoch[msg.sender][_token]
    currentEpoch: uint256 = self.epoch  # load to memory once
    _epoch: uint256 = _user_claimed_epoch
    for d_epoch in range(255):  #xx 255?
        _epoch += 1  # move to process the next unprocessed epoch
        if _epoch >= currentEpoch:  # note: we use >= because curerntEpoch is not finalized
            break
        _epochReward: uint256 = self.epoch_token_rewards[_epoch][_token]
        if _epochReward == 0:
            continue  #xx todo event
        _avgUserBlanace: uint256 = self._averageUserBlanaceOverEpoch(msg.sender, _epoch)
        if _avgUserBlanace == 0:
            continue  #xx todo event
        _avgTotalSupply: uint256 = self._averageTotalSupplyOverEpoch(_epoch)
        if _avgTotalSupply == 0:
            continue  #xx todo event
        rewardsAmount += _epochReward * _avgUserBlanace / _avgTotalSupply
        log UserRewardsClaimedDebug(_epoch, _avgUserBlanace, _avgTotalSupply, _epochReward, _epochReward * _avgUserBlanace / _avgTotalSupply)
    self.user_token_claimed_epoch[msg.sender][_token] = _epoch - 1

    if _token == ZERO_ADDRESS:
        send(msg.sender, rewardsAmount)
    else:
        self.safe_transfer(_token, msg.sender, rewardsAmount)

    log UserRewardsClaimed(_epoch - 1, _token, rewardsAmount)

@external
def emergency_withdraw(_token: address, _amount: uint256, to: address):
    assert msg.sender == self.admin
    if _token == ZERO_ADDRESS:
        send(to, _amount)
    else:
        self.safe_transfer(_token, to, _amount)

@external
def emergency_withdraw_many(_tokens: address[30], _amounts: uint256[30], tos: address[30]):
    assert msg.sender == self.admin
    for i in range(30):
        _token: address = _tokens[i]
        _amount: uint256 = _amounts[i]
        to: address = tos[i]
        if _token == ZERO_ADDRESS:
            send(to, _amount)
        else:
            self.safe_transfer(_token, to, _amount)
