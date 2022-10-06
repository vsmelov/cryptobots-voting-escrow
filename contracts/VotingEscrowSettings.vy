# @version 0.3.7

storageUInt256: HashMap[bytes32, uint256]
storageAddress: HashMap[bytes32, address]
storageBool: HashMap[bytes32, bool]


event TransferOwnership:
    admin: address


event MinDelayBetweenManualCheckpointSet:
    value: uint256


ADMIN_HASH: constant(bytes32) = keccak256("admin")
MIN_DELAY_BETWEEN_MANUAL_CHECKPOINT_HASH: constant(bytes32) = keccak256("min_delay_between_manual_checkpoint")


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