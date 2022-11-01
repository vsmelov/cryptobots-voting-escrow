# @version 0.3.7

_nonreentrant: bool  # under the hood we reserve the first storage slot

storageUInt256: HashMap[bytes32, uint256]
storageAddress: HashMap[bytes32, address]
storageBool: HashMap[bytes32, bool]


event TransferOwnership:
    admin: address


event MinDelayBetweenManualCheckpointSet:
    value: uint256


event SmartWalletCheckerSet:
    value: address


event Emergency:
    pass


ADMIN_HASH: constant(bytes32) = keccak256("admin")  # address
MIN_DELAY_BETWEEN_MANUAL_CHECKPOINT_HASH: constant(bytes32) = keccak256("min_delay_between_manual_checkpoint")  # uint256
MAX_POOL_MEMBERS_HASH: constant(bytes32) = keccak256("max_pool_members")  # uint256
MIN_STAKE_AMOUNT_HASH: constant(bytes32) = keccak256("min_stake_amount")  # uint256
WITHDRAW_DISABLED_HASH: constant(bytes32) = keccak256("withdraw_disabled")  # bool
CREATE_LOCK_DISABLED_HASH: constant(bytes32) = keccak256("create_lock_disabled")  # bool
INCREASE_UNLOCK_TIME_DISABLED_HASH: constant(bytes32) = keccak256("increase_unlock_time_disabled")  # bool
INCREASE_AMOUNT_DISABLED_HASH: constant(bytes32) = keccak256("increase_amount_disabled")  # bool
EMERGENCY_HASH: constant(bytes32) = keccak256("emergency")  # bool
SMART_WALLET_CHECKER_HASH: constant(bytes32) = keccak256("smart_wallet_checker")  # address


@external
def set_smart_wallet_checker(addr: address):
    """
    @notice Apply setting external contract to check approved smart contract wallets
    """
    assert msg.sender == self._admin(), ERROR_NOT_ADMIN
    self.storageAddress[SMART_WALLET_CHECKER_HASH] = addr
    log SmartWalletCheckerSet(addr)


@internal
@view
def _emergency() -> bool:
    return self.storageBool[EMERGENCY_HASH]


@internal
@view
def _admin() -> address:
    return self.storageAddress[ADMIN_HASH]


@external
def set_min_delay_between_manual_checkpoint(_value: uint256):
    assert msg.sender == self._admin(), ERROR_NOT_ADMIN
    assert self.storageUInt256[MIN_DELAY_BETWEEN_MANUAL_CHECKPOINT_HASH] != _value, "not changed"
    self.storageUInt256[MIN_DELAY_BETWEEN_MANUAL_CHECKPOINT_HASH] = _value
    log MinDelayBetweenManualCheckpointSet(_value)


@external
def transfer_ownership(addr: address):
    """
    @notice Transfer ownership of VotingEscrow contract to `addr`
    @param addr Address to have ownership transferred to
    """
    assert msg.sender == self._admin(), ERROR_NOT_ADMIN
    assert addr != ZERO_ADDRESS, "zero address"  # dev: admin not set
    self.storageAddress[ADMIN_HASH] = addr
    log TransferOwnership(addr)

# emergency

@external
def emergency_withdraw(_token: address, _amount: uint256, to: address):
    assert msg.sender == self._admin(), ERROR_NOT_ADMIN
    assert self._emergency(), "not emergency"
    if _token == ZERO_ADDRESS:
        send(to, _amount)
    else:
        self.safe_transfer(_token, to, _amount)


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


@external
def enable_emergency():
    assert msg.sender == self._admin(), ERROR_NOT_ADMIN
    assert not self.storageBool[EMERGENCY_HASH], "already enabled"
    self.storageBool[EMERGENCY_HASH] = True
    log Emergency()


event MaxPoolMembersSet:
    value: uint256


event MinStakeAmountSet:
    value: uint256


@external
def set_max_pool_members(_value: uint256):
    assert msg.sender == self._admin(), ERROR_NOT_ADMIN
    assert self.storageUInt256[MAX_POOL_MEMBERS_HASH] != _value, "not changed"
    self.storageUInt256[MAX_POOL_MEMBERS_HASH] = _value
    log MaxPoolMembersSet(_value)


@external
def set_min_stake_amount(_value: uint256):
    assert msg.sender == self._admin(), ERROR_NOT_ADMIN
    assert self.storageUInt256[MIN_STAKE_AMOUNT_HASH] != _value, "not changed"
    self.storageUInt256[MIN_STAKE_AMOUNT_HASH] = _value
    log MinStakeAmountSet(_value)

event WithdrawDisabledSet:
    value: bool

@external
def set_withdraw_disabled(_value: bool):
    assert msg.sender == self._admin(), ERROR_NOT_ADMIN
    assert self.storageBool[WITHDRAW_DISABLED_HASH] != _value, "not changed"
    self.storageBool[WITHDRAW_DISABLED_HASH] = _value
    log WithdrawDisabledSet(_value)

event CreateLockDisabledSet:
    value: bool

@external
def set_create_lock_disabled(_value: bool):
    assert msg.sender == self._admin(), ERROR_NOT_ADMIN
    assert self.storageBool[CREATE_LOCK_DISABLED_HASH] != _value, "not changed"
    self.storageBool[CREATE_LOCK_DISABLED_HASH] = _value
    log CreateLockDisabledSet(_value)

ERROR_NOT_ADMIN: constant(String[9]) = "not admin"
ERROR_NOT_CHANGED: constant(String[11]) = "not changed"

event IncreaseUnlockTimeDisabledSet:
    value: bool


@external
def set_increase_unlock_time_disabled(_value: bool):
    assert msg.sender == self._admin(), ERROR_NOT_ADMIN
    assert self.storageBool[INCREASE_UNLOCK_TIME_DISABLED_HASH] != _value, ERROR_NOT_CHANGED
    self.storageBool[INCREASE_UNLOCK_TIME_DISABLED_HASH] = _value
    log IncreaseUnlockTimeDisabledSet(_value)


event IncreaseAmountDisabledSet:
    value: bool


@external
def set_increase_amount_disabled(_value: bool):
    assert msg.sender == self._admin(), ERROR_NOT_ADMIN
    assert self.storageBool[INCREASE_AMOUNT_DISABLED_HASH] != _value, ERROR_NOT_CHANGED
    self.storageBool[INCREASE_AMOUNT_DISABLED_HASH] = _value
    log IncreaseAmountDisabledSet(_value)


# Interface for checking whether address belongs to a whitelisted
# type of a smart wallet.
# When new types are added - the whole contract is changed
# The check() method is modifying to be able to use caching
# for individual wallet addresses
interface SmartWalletChecker:
    def check(addr: address) -> bool: nonpayable


@external
def assert_not_contract(addr: address):
    """
    @notice Check if the call is from a whitelisted smart contract, revert if not
    @param addr Address to be checked
    """
    if addr != tx.origin:
        checker: address = self.storageAddress[SMART_WALLET_CHECKER_HASH]
        if checker != ZERO_ADDRESS:
            if SmartWalletChecker(checker).check(addr):
                return
        raise "Smart contract depositors not allowed"


@external
@pure
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
