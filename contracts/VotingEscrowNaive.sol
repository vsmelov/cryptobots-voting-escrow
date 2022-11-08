// SPDX-License-Identifier: None

pragma solidity ^0.8.0;

import {SafeERC20} from '@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol';
import {IERC20} from '@openzeppelin/contracts/token/ERC20/IERC20.sol';
import {Ownable} from '@openzeppelin/contracts/access/Ownable.sol';

contract VotingEscrowNaive is Ownable {
    using SafeERC20 for IERC20;

    struct UserLock {
        uint256 amount;
        uint256 till;
    }

    event MinLockTimeSet(uint256 value);
    event MinLockAmountSet(uint256 value);

    uint256 public constant MAX_TIME = 4 * 360 * 24 * 3600;
    uint256 public constant WINDOW = 30 * 24 * 3600;
    uint256 internal constant ONE = 10**18;
    IERC20 public bits;

    mapping (address => UserLock) public locks;
    uint256 public minLockTime;
    uint256 public minLockAmount;

    mapping (uint256 /*window*/ => uint256) public windowTotalSupply;
    mapping (address /*user*/ => mapping (uint256 /*window*/ => uint256 /*balance*/)) public userWindowBalance;
    mapping (address /*user*/ => uint256 /*window*/) public userLastClaimedWindow;
    mapping (uint256 /*window*/ => uint256 /*rewardPerToken*/) public windowRewardPerToken_MATIC;
    mapping (uint256 /*window*/ => uint256 /*rewardPerToken*/) public windowRewardPerToken_BITS;
    mapping (address /*user*/ => uint256) public userLastClaimedRewardPerToken_MATIC;
    mapping (address /*user*/ => uint256) public userLastClaimedRewardPerToken_BITS;

    function getWindow(uint256 timestamp) public pure returns(uint256) {
        return timestamp / WINDOW * WINDOW;
    }

    function currentWindow() public view returns(uint256) {
        return getWindow(block.timestamp);
    }

    constructor(
        IERC20 _bits
    ) {
        bits = _bits;
    }

    function setMinLockTime(uint256 value) public onlyOwner {
        require(value > 0, "zero value");
        minLockTime = value;
        emit MinLockTimeSet(value);
    }

    function setMinLockAmount(uint256 value) public onlyOwner {
        require(value > 0, "zero value");
        minLockAmount = value;
        emit MinLockAmountSet(value);
    }

    function lock(uint256 amount, uint256 till) external {
        require(locks[msg.sender].amount == 0, "already locked");
        require(amount > 0, "zero amount");
        require(amount >= minLockAmount, "small amount");

        till = till / WINDOW * WINDOW;
        uint256 _currentWindow = currentWindow();
        uint256 period = till - block.timestamp;
        require(till >= block.timestamp + minLockTime, "too small till");
        require(till <= MAX_TIME, "too big till");

        uint256 scaledAmount = amount * period / MAX_TIME;

        windowTotalSupply[_currentWindow] += scaledAmount;
        userWindowBalance[msg.sender][_currentWindow] = scaledAmount;
        userLastClaimedWindow[msg.sender] = _currentWindow;
        userLastClaimedRewardPerToken_MATIC[msg.sender] = windowRewardPerToken_MATIC[_currentWindow];
        userLastClaimedRewardPerToken_BITS[msg.sender] = windowRewardPerToken_BITS[_currentWindow];

        for (uint256 _window = _currentWindow + WINDOW; _window < till; _window += WINDOW) {
            uint256 _windowScaledAmount = scaledAmount * (till - _window) / period;
            windowTotalSupply[_window] += _windowScaledAmount;
            userWindowBalance[msg.sender][_window] = _windowScaledAmount;
        }

        locks[msg.sender] = UserLock(amount, till);
        bits.safeTransferFrom(msg.sender, address(this), amount);
    }

    function unlock() external {
        UserLock memory lock = locks[msg.sender];
        require(lock.amount != 0, "nothing locked");
        require(block.timestamp >= lock.till, "too early");

        claimReward();

        // erase storage
        locks[msg.sender] = UserLock(0, 0);
        userLastClaimedWindow[msg.sender] = 0;
        userLastClaimedRewardPerToken_BITS[msg.sender] = 0;
        userLastClaimedRewardPerToken_MATIC[msg.sender] = 0;

        bits.safeTransfer(msg.sender, lock.amount);
    }

    function claimReward() public {
        UserLock memory lock = locks[msg.sender];
        require(lock.amount > 0, "nothing lock");
        uint256 _currentWindow = currentWindow();

        uint256 totalRewards_MATIC = 0;
        uint256 totalRewards_BITS = 0;

        uint256 _startWindow = userLastClaimedWindow[msg.sender];
        for(
            uint256 _processingWindow = _startWindow;
            _processingWindow <= _currentWindow;
            _processingWindow += 0
        ) {
            uint256 _userWindowBalance = userWindowBalance[msg.sender][_processingWindow];
            uint256 reward_MATIC;
            uint256 reward_BITS;
            uint256 _windowRewardPerToken_MATIC = windowRewardPerToken_MATIC[_processingWindow];
            uint256 _windowRewardPerToken_BITS = windowRewardPerToken_BITS[_processingWindow];

            if (_processingWindow == _startWindow) {
                uint256 _lastClaimedRewardPerToken_MATIC = userLastClaimedRewardPerToken_MATIC[msg.sender];
                uint256 _lastClaimedRewardPerToken_BITS = userLastClaimedRewardPerToken_BITS[msg.sender];
                reward_MATIC = _userWindowBalance * (_windowRewardPerToken_MATIC - _lastClaimedRewardPerToken_MATIC) / ONE;
                reward_BITS = _userWindowBalance * (_windowRewardPerToken_BITS - _lastClaimedRewardPerToken_BITS) / ONE;
            } else {
                reward_MATIC = _userWindowBalance * _windowRewardPerToken_MATIC / ONE;
                reward_BITS = _userWindowBalance * _windowRewardPerToken_BITS / ONE;
            }

            totalRewards_MATIC += reward_MATIC;
            totalRewards_BITS += reward_BITS;
        }

        userLastClaimedWindow[msg.sender] = _currentWindow;
        userLastClaimedRewardPerToken_MATIC[msg.sender] = windowRewardPerToken_MATIC[_currentWindow];
        userLastClaimedRewardPerToken_BITS[msg.sender] = windowRewardPerToken_BITS[_currentWindow];

        bits.safeTransfer(msg.sender, totalRewards_BITS);
        (bool success, ) = msg.sender.call{value: totalRewards_MATIC}("");
        require(success, "transfer MATIC failed");
    }

    function receiveReward_BITS(uint256 amount) external {
        uint256 _currentWindow = currentWindow();
        uint256 _windowTotalSupply = windowTotalSupply[_currentWindow];
        windowRewardPerToken_BITS[_currentWindow] += amount * ONE / _windowTotalSupply;
        bits.safeTransferFrom(msg.sender, address(this), amount);
    }

    function receiveReward_MATIC(uint256 amount) external payable {
        uint256 _currentWindow = currentWindow();
        uint256 _windowTotalSupply = windowTotalSupply[_currentWindow];
        windowRewardPerToken_MATIC[_currentWindow] += msg.value * ONE / _windowTotalSupply;
    }
}
