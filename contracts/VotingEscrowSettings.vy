# @version 0.3.7

_nonreentrant: bool  # under the hood we reserve the first storage slot

storageUInt256: HashMap[bytes32, uint256]
storageAddress: HashMap[bytes32, address]
storageBool: HashMap[bytes32, bool]


event TransferOwnership:
    admin: address


event MinDelayBetweenManualCheckpointSet:
    value: uint256


event Emergency:
    pass


ADMIN_HASH: constant(bytes32) = keccak256("admin")
MIN_DELAY_BETWEEN_MANUAL_CHECKPOINT_HASH: constant(bytes32) = keccak256("min_delay_between_manual_checkpoint")
EMERGENCY_HASH: constant(bytes32) = keccak256("emergency")


@internal
@view
def _emergency() -> bool:
    return self.storageBool[EMERGENCY_HASH]


@internal
@view
def _admin() -> address:
    return self.storageAddress[ADMIN_HASH]


@internal
@view
def min_delay_between_manual_checkpoint() -> uint256:
    return self.storageUInt256[MIN_DELAY_BETWEEN_MANUAL_CHECKPOINT_HASH]


@external
def set_min_delay_between_manual_checkpoint(_value: uint256):
    assert msg.sender == self._admin(), "not admin"
    assert self.min_delay_between_manual_checkpoint() != _value, "not changed"
    self.storageUInt256[MIN_DELAY_BETWEEN_MANUAL_CHECKPOINT_HASH] = _value
    log MinDelayBetweenManualCheckpointSet(_value)


@external
def transfer_ownership(addr: address):
    """
    @notice Transfer ownership of VotingEscrow contract to `addr`
    @param addr Address to have ownership transferred to
    """
    assert msg.sender == self._admin(), "not admin"  # dev: admin only
    assert addr != ZERO_ADDRESS  # dev: admin not set
    self.storageAddress[ADMIN_HASH] = addr
    log TransferOwnership(addr)

# emergency

@external
def emergency_withdraw(_token: address, _amount: uint256, to: address):
    assert msg.sender == self._admin(), "not admin"
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
    assert msg.sender == self._admin(), "not admin"
    assert not self.storageBool[EMERGENCY_HASH]
    self.storageBool[EMERGENCY_HASH] = True
    log Emergency()
