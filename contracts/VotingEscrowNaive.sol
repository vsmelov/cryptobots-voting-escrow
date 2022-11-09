// SPDX-License-Identifier: None

pragma solidity ^0.8.0;

import {SafeERC20} from '@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol';
import {IERC20} from '@openzeppelin/contracts/token/ERC20/IERC20.sol';
import {OwnableUpgradeable} from '@openzeppelin-upgradeable/contracts/access/OwnableUpgradeable.sol';

contract VotingEscrowNaive is OwnableUpgradeable {
    using SafeERC20 for IERC20;

    struct UserLock {
        uint256 amount;
        uint256 till;
    }

    event MinLockTimeSet(uint256 value);
    event MinLockAmountSet(uint256 value);
    event MaxPoolMembersSet(uint256 value);

    uint256 public constant MAXTIME = 4 * 360 * 24 * 3600;
    uint256 public constant WINDOW = 30 * 24 * 3600;
    uint256 internal constant ONE = 10**18;
    IERC20 public bits;

    mapping (address => UserLock) public locks;
    uint256 public minLockTime;
    uint256 public minLockAmount;
    uint256 public maxPoolMembers;
    uint256 public poolMembers;

    string public name;
    string public symbol;
    string public version;
    uint8 public decimals;

    mapping (uint256 /*window*/ => uint256) public windowTotalSupply;
    mapping (address /*user*/ => mapping (uint256 /*window*/ => uint256 /*balance*/)) public userWindowBalance;
    mapping (address /*user*/ => uint256 /*window*/) public userLastClaimedWindow;
    mapping (uint256 /*window*/ => uint256 /*rewardPerToken*/) public windowRewardPerToken_MATIC;
    mapping (uint256 /*window*/ => uint256 /*rewardPerToken*/) public windowRewardPerToken_BITS;
    mapping (address /*user*/ => uint256) public userLastClaimedRewardPerToken_MATIC;
    mapping (address /*user*/ => uint256) public userLastClaimedRewardPerToken_BITS;
//    mapping (uint256 /*window*/ => bool) public stuckWindowRewardClaimed;

    function getWindow(uint256 timestamp) public pure returns(uint256) {
        return timestamp / WINDOW * WINDOW;
    }

    function currentWindow() public view returns(uint256) {
        return getWindow(block.timestamp);
    }

    constructor() {}

    function initialize(
        IERC20 _bits,
        string memory _name,
        string memory _symbol,
        string memory _version,
        uint8 _decimals,
        uint256 _maxPoolMembers,
        uint256 _minLockAmount,
        uint256 _minLockTime
    ) external initializer {
        __Ownable_init();
        bits = _bits;
        name = _name;
        symbol = _symbol;
        version = _version;
        setMaxPoolMembers(_maxPoolMembers);
        setMinLockAmount(_minLockAmount);
        setMinLockTime(_minLockTime);
    }

    function balanceOf(address account) external view returns(uint256) {
        return userWindowBalance[account][currentWindow()];
    }

    function totalSupply() external view returns(uint256) {
        return windowTotalSupply[currentWindow()];
    }

    function setMinLockTime(uint256 value) public onlyOwner {
        minLockTime = value;
        emit MinLockTimeSet(value);
    }

    function setMinLockAmount(uint256 value) public onlyOwner {
        require(value > 0, "zero value");
        minLockAmount = value;
        emit MinLockAmountSet(value);
    }

    function setMaxPoolMembers(uint256 value) public onlyOwner {
        require(value > 0, "zero value");
        maxPoolMembers = value;
        emit MaxPoolMembersSet(value);
    }

    function create_lock(uint256 amount, uint256 till) external {
        require(locks[msg.sender].amount == 0, "already locked");
        require(amount > 0, "zero amount");
        require(amount >= minLockAmount, "small amount");

        till = till / WINDOW * WINDOW;
        uint256 _currentWindow = currentWindow();
        require(till > block.timestamp, "too small till");
        uint256 period = till - block.timestamp;
        require(period >= minLockTime, "too small till");
        require(period <= MAXTIME, "too big till");

        uint256 scaledAmount = amount * period / MAXTIME;

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

        poolMembers += 1;
        locks[msg.sender] = UserLock(amount, till);
        bits.safeTransferFrom(msg.sender, address(this), amount);
    }

    function increase_unlock_time(uint256 till) external {
        UserLock memory lock = locks[msg.sender];
        require(lock.amount > 0, "nothing locked");

        till = till / WINDOW * WINDOW;
        require(lock.till > block.timestamp, "expired lock, withdraw first");
        require(till > lock.till, "not increased");

        claim_rewards();

        uint256 _currentWindow = currentWindow();
        require(till > block.timestamp, "too small till");
        uint256 period = till - block.timestamp;
        require(period >= minLockTime, "too small till");
        require(period <= MAXTIME, "too big till");

        uint256 scaledAmount = lock.amount * period / MAXTIME;

        windowTotalSupply[_currentWindow] =
            windowTotalSupply[_currentWindow] - userWindowBalance[msg.sender][_currentWindow] + scaledAmount;
        userWindowBalance[msg.sender][_currentWindow] = scaledAmount;

        // this not need because claim_rewards already called
//        userLastClaimedWindow[msg.sender] = _currentWindow;
//        userLastClaimedRewardPerToken_MATIC[msg.sender] = windowRewardPerToken_MATIC[_currentWindow];
//        userLastClaimedRewardPerToken_BITS[msg.sender] = windowRewardPerToken_BITS[_currentWindow];

        for (uint256 _window = _currentWindow + WINDOW; _window < till; _window += WINDOW) {
            uint256 _windowScaledAmount = scaledAmount * (till - _window) / period;
            windowTotalSupply[_window] =
                windowTotalSupply[_window] - userWindowBalance[msg.sender][_window] + _windowScaledAmount;
            userWindowBalance[msg.sender][_window] = _windowScaledAmount;
        }

        locks[msg.sender].till = till;
    }

    function increase_lock_amount(uint256 amount) external {
        UserLock memory lock = locks[msg.sender];
        require(lock.amount > 0, "nothing locked");
        require(amount > 0, "zero amount");
        require(amount >= minLockAmount, "small amount");
        require(lock.till > block.timestamp, "expired lock, withdraw first");

        uint256 _currentWindow = currentWindow();
        uint256 period = lock.till - block.timestamp;
        require(period >= minLockTime, "too small till");
        require(period <= MAXTIME, "too big till");

        claim_rewards();

        uint256 scaledAmount = amount * period / MAXTIME;

        windowTotalSupply[_currentWindow] += scaledAmount;
        userWindowBalance[msg.sender][_currentWindow] += scaledAmount;

        // not need because claim_rewards is already called
//        userLastClaimedWindow[msg.sender] = _currentWindow;
//        userLastClaimedRewardPerToken_MATIC[msg.sender] = windowRewardPerToken_MATIC[_currentWindow];
//        userLastClaimedRewardPerToken_BITS[msg.sender] = windowRewardPerToken_BITS[_currentWindow];

        for (uint256 _window = _currentWindow + WINDOW; _window < lock.till; _window += WINDOW) {
            uint256 _windowScaledAmount = scaledAmount * (lock.till - _window) / period;
            windowTotalSupply[_window] += _windowScaledAmount;
            userWindowBalance[msg.sender][_window] += _windowScaledAmount;
        }

        locks[msg.sender].amount += amount;
        bits.safeTransferFrom(msg.sender, address(this), amount);
    }

    function withdraw() external {
        UserLock memory lock = locks[msg.sender];
        require(lock.amount != 0, "nothing locked");
        require(block.timestamp >= lock.till, "too early");

        claim_rewards();

        // erase storage
        locks[msg.sender] = UserLock(0, 0);
        userLastClaimedWindow[msg.sender] = 0;
        userLastClaimedRewardPerToken_BITS[msg.sender] = 0;
        userLastClaimedRewardPerToken_MATIC[msg.sender] = 0;
        poolMembers -= 1;

        bits.safeTransfer(msg.sender, lock.amount);
    }

    function user_claimable_rewards(address user) public view returns(uint256 totalRewards_MATIC, uint256 totalRewards_BITS){
        UserLock memory lock = locks[user];
        require(lock.amount > 0, "nothing lock");
        uint256 _currentWindow = currentWindow();

        totalRewards_MATIC = 0;
        totalRewards_BITS = 0;
        uint256 _startWindow = userLastClaimedWindow[user];
        for(
            uint256 _processingWindow = _startWindow;
            _processingWindow <= _currentWindow;
            _processingWindow += 0
        ) {
            uint256 _userWindowBalance = userWindowBalance[user][_processingWindow];
            uint256 reward_MATIC;
            uint256 reward_BITS;
            uint256 _windowRewardPerToken_MATIC = windowRewardPerToken_MATIC[_processingWindow];
            uint256 _windowRewardPerToken_BITS = windowRewardPerToken_BITS[_processingWindow];

            if (_processingWindow == _startWindow) {
                uint256 _lastClaimedRewardPerToken_MATIC = userLastClaimedRewardPerToken_MATIC[user];
                uint256 _lastClaimedRewardPerToken_BITS = userLastClaimedRewardPerToken_BITS[user];
                reward_MATIC = _userWindowBalance * (_windowRewardPerToken_MATIC - _lastClaimedRewardPerToken_MATIC) / ONE;
                reward_BITS = _userWindowBalance * (_windowRewardPerToken_BITS - _lastClaimedRewardPerToken_BITS) / ONE;
            } else {
                reward_MATIC = _userWindowBalance * _windowRewardPerToken_MATIC / ONE;
                reward_BITS = _userWindowBalance * _windowRewardPerToken_BITS / ONE;
            }

            totalRewards_MATIC += reward_MATIC;
            totalRewards_BITS += reward_BITS;
        }
    }

    function claim_rewards() public {
        (uint256 totalRewards_MATIC, uint256 totalRewards_BITS) = user_claimable_rewards(msg.sender);

        uint256 _currentWindow = currentWindow();
        userLastClaimedWindow[msg.sender] = _currentWindow;
        userLastClaimedRewardPerToken_MATIC[msg.sender] = windowRewardPerToken_MATIC[_currentWindow];
        userLastClaimedRewardPerToken_BITS[msg.sender] = windowRewardPerToken_BITS[_currentWindow];

        bits.safeTransfer(msg.sender, totalRewards_BITS);
        (bool success, ) = msg.sender.call{value: totalRewards_MATIC}("");
        require(success, "transfer MATIC failed");
    }

//    function claim_stuck_rewards(uint256 _window) external onlyOwner {
//        require(_window < _currentWindow(), "unfinalized window");
//        require(!stuckWindowRewardClaimed[_window], "already claimed");
//        stuckWindowRewardClaimed[_window] = True;
//
//        _windowReward: uint256 = self.window_token_rewards[_window][_token]
//        if _windowReward == 0:
//            log Log1Args("skip _window {0} because _windowReward=0", _window)
//            return
//
//        _avgTotalSupply: uint256 = self._averageTotalSupplyOverWindow(_window)
//        assert _avgTotalSupply == 0, "reward not stuck"
//
//        log StuckWindowRewardClaimed(_window, _token, _windowReward)
//        self.any_transfer(_token, msg.sender, _windowReward)
//    }

    function receiveReward_BITS(uint256 amount) external {
        uint256 _currentWindow = currentWindow();
        uint256 _windowTotalSupply = windowTotalSupply[_currentWindow];
        require(_windowTotalSupply != 0, "no pool members");
        windowRewardPerToken_BITS[_currentWindow] += amount * ONE / _windowTotalSupply;
        bits.safeTransferFrom(msg.sender, address(this), amount);
    }

    function receiveReward_MATIC(uint256 amount) external payable {
        uint256 _currentWindow = currentWindow();
        uint256 _windowTotalSupply = windowTotalSupply[_currentWindow];
        require(_windowTotalSupply != 0, "no pool members");
        windowRewardPerToken_MATIC[_currentWindow] += msg.value * ONE / _windowTotalSupply;
    }
}
