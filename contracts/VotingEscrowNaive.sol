// SPDX-License-Identifier: None

pragma solidity ^0.8.0;

import {SafeERC20} from '@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol';
import {IERC20} from '@openzeppelin/contracts/token/ERC20/IERC20.sol';

contract VotingEscrowNaive is Ownable {
    using SafeERC20 for IERC20;

    struct UserLock {
        uint256 amount;
        uint256 till;
        uint256 claimedRewardPerToken;
    }

    uint256 public constant MAX_TIME = 4 * 360 * 24 * 3600;
    uint256 public constant WINDOW = 30 * 24 * 3600;
    uint256 internal constant ONE = 10**18;
    address public token;
    address public rewardToken;

    mapping (address => UserLock) public locks;
    uint256 public minLockTime;
    uint256 public minLockAmount;

    function getWindow(uint256 timestamp) public pure returns(uint256) {
        return timestamp / WINDOW * WINDOW;
    }

    function currentWindow() public view returns(uint256) {
        return getWindow(block.timestamp);
    }

    mapping (uint256 /*window*/ => uint256) public windowTotalSupply;
    mapping (address => (uint256 /*window*/ => uint256)) public userWindowBalance;
    mapping (uint256 => uint256) public windowRewardPerToken;
    mapping (address => uint256) public userLastClaimedWindow;
    mapping (address => uint256) public userLastClaimedRewardPerToken;

    constructor(
        address _token,
        address _rewardToken
    ) {
        token = _token;
        rewardToken = _rewardToken;
    }

    event MinLockTimeSet(uint256 value);
    event MinLockAmountSet(uint256 value);

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
        userWindowBalance[msg.sender] = scaledAmount;
        userLastClaimedWindow[msg.sender] = _currentWindow;
        userLastClaimedRewardPerToken[msg.sender] = windowRewardPerToken[_currentWindow];

        for (uint256 _window = _currentWindow + WINDOW; _window < till; _window += WINDOW) {
            uint256 _windowScaledAmount = scaledAmount * (till - _window) / period;
            windowTotalSupply[_currentWindow] += _windowScaledAmount;
            userWindowBalance[msg.sender] = _windowScaledAmount;
        }

        locks[msg.sender] = UserLock(amount, till);
        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);
    }

    function unlock() external {
        UserLock memory lock = locks[msg.sender];
        require(lock.amount != 0, "nothing locked");
        require(block.timestamp >= lock.till, "too early");

        claimReward();

        // erase storage
        locks[msg.sender] = UserLock(0, 0);
        userLastClaimedWindow[msg.sender] = 0;
        userLastClaimedRewardPerToken[msg.sender] = 0;

        IERC20(token).safeTransfer(msg.sender, amount);
    }

    function claimReward() public {
        UserLock memory lock = locks[msg.sender];
        require(lock.amount > 0, "nothing lock");
        uint256 _currentWindow = currentWindow();

        uint256 totalReward = 0;
        uint256 claimedRewardPerToken = userLastClaimedRewardPerToken[msg.sender];
        for(uint256 _window=userLastClaimedWindow[msg.sender];;) {
            uint256 _userWindowBalance = userWindowBalance[msg.sender][_window];
            uint256 _windowRewardPerToken = windowRewardPerToken[_window];
            uint256 reward = _userWindowBalance * (_windowRewardPerToken - claimedRewardPerToken) / ONE;
            totalReward += reward;
            if (_window == _currentWindow) {
                userLastClaimedWindow[msg.sender] = _currentWindow;
                userLastClaimedRewardPerToken[msg.sender] = _windowRewardPerToken;
                break;
            }
            claimedRewardPerToken = 0;
            unchecked {
                _window += WINDOW;
            }
        }

        IERC20(rewardToken).safeTransfer(msg.sender, totalReward);
    }

    function receiveReward(address rewardToken, uint256 amount) external {
        IERC20(rewardToken).safeTransferFrom(msg.sender, address(this), amount);
        rewardPerToken += amount * ONE / totalLocked;
    }
}
