// SPDX-License-Identifier: None

pragma solidity ^0.8.0;

import {SafeERC20} from '@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol';
import {IERC20} from '@openzeppelin/contracts/token/ERC20/IERC20.sol';
import {EnumerableSet} from '@openzeppelin/contracts/utils/structs/EnumerableSet.sol';
import {OwnableUpgradeable} from '@openzeppelin-upgradeable/contracts/access/OwnableUpgradeable.sol';

contract VotingEscrowNaive is OwnableUpgradeable {
    using SafeERC20 for IERC20;
    using EnumerableSet for EnumerableSet.AddressSet;

    struct UserLock {
        uint256 amount;
        uint256 till;
    }

    event CreateLock(
        address indexed provider,
        address indexed account,
        uint256 value,
        uint256 indexed locktime
    );

    event IncreaseLockAmount(
        address indexed provider,
        address indexed account,
        uint256 value
    );

    event IncreaseUnlockTime(
        address indexed account,
        uint256 indexed locktime
    );

    event Withdraw(
        address indexed account,
        uint256 value
    );

    event MinLockTimeSet(uint256 value);
    event MinLockAmountSet(uint256 value);
    event MaxPoolMembersSet(uint256 value);
    event IncreaseAmountDisabledSet(bool value);
    event IncreaseUnlockTimeDisabledSet(bool value);
    event CreateLockDisabledSet(bool value);
    event WithdrawDisabledSet(bool value);
    event ClaimRewardsDisabledSet(bool value);
    event Emergency();
    event WindowRewardReceived(
        uint256 indexed window,
        address indexed token,
        uint256 amount
    );
    event UserRewardsClaimed(
        address indexed user,
        address indexed token,
        uint256 first_processed_window,
        uint256 last_processed_window,
        uint256 totalRewards
    );
    event WindowRewardClaimed(
        address indexed account,
        uint256 indexed window,
        uint256 userWindowBalance,
        uint256 windowRewardPerToken,
        uint256 lastClaimedRewardPerToken,
        uint256 reward
    );
    event TransferNative(
        address indexed from,
        address indexed to,
        uint256 amount
    );
    event StuckRewardReceived(
        uint256 indexed window,
        address indexed token,
        uint256 amount
    );
    event StuckWindowRewardClaimed(
        uint256 indexed window,
        address indexed token,
        uint256 stuckAmount
    );
    event RewardTokenAdded(address indexed token);

    uint256 public constant MAXTIME = 4 * 360 * 24 * 3600;
    uint256 public constant WINDOW = 30 * 24 * 3600;
    uint256 internal constant ONE = 10**18;
    IERC20 public bits;

    mapping (address => UserLock) public locked;
    uint256 public minLockTime;
    uint256 public minLockAmount;
    uint256 public maxPoolMembers;
    uint256 public poolMembers;

    bool public emergency;
    bool public increase_amount_disabled;
    bool public increase_unlock_time_disabled;
    bool public create_lock_disabled;
    bool public withdraw_disabled;
    bool public claim_rewards_disabled;

    string public name;
    string public symbol;
    string public version;
    uint8 constant public decimals = 18;  // same decimals as in BITS

    mapping (uint256 /*window*/ => uint256) public windowTotalSupply;
    mapping (address /*user*/ => mapping (uint256 /*window*/ => uint256 /*balance*/)) public userWindowBalance;
    mapping (address /*user*/ => uint256 /*window*/) public defaultUserTokenLastClaimedWindow;
    mapping (address /*user*/ => mapping (address /*token*/ => uint256 /*window*/)) public userTokenLastClaimedWindow;
    mapping (uint256 /*window*/ => mapping(address /*token*/ => uint256 /*rewardPerToken*/)) public windowRewardPerToken;
    mapping (address /*user*/ => mapping(address /*token*/ => uint256)) public userTokenLastClaimedRewardPerToken;
    mapping (uint256 /*window*/ => mapping(address /*token*/ => uint256)) public windowTokenStuckAmount;
    EnumerableSet.AddressSet internal _rewardTokens;

    function rewardTokensLength() external view returns(uint256 length) {
        length = _rewardTokens.length();
    }

    function rewardTokenAt(uint256 index) external view returns(address token) {
        token = _rewardTokens.at(index);
    }

    function addRewardToken(address token) external onlyOwner {
        require(_rewardTokens.add(token), "already in");
        emit RewardTokenAdded(token);
    }
    // note: removal are not allowed!

    function getWindow(uint256 timestamp) public pure returns(uint256) {
        return timestamp / WINDOW * WINDOW;
    }

    function currentWindow() public view returns(uint256) {
        return getWindow(block.timestamp);
    }

    function enableEmergency() external onlyOwner {
        require(!emergency, "already emergency");
        emergency = true;
        emit Emergency();
    }

    function set_increase_amount_disabled(bool _value) external onlyOwner {
        require(increase_amount_disabled != _value, "not changed");
        increase_amount_disabled = _value;
        emit IncreaseAmountDisabledSet(_value);
    }

    function set_increase_unlock_time_disabled(bool _value) external onlyOwner {
        require(increase_unlock_time_disabled != _value, "not changed");
        increase_unlock_time_disabled = _value;
        emit IncreaseUnlockTimeDisabledSet(_value);
    }

    function set_claim_rewards_disabled(bool _value) external onlyOwner {
        require(claim_rewards_disabled != _value, "not changed");
        claim_rewards_disabled = _value;
        emit ClaimRewardsDisabledSet(_value);
    }

    function set_create_lock_disabled(bool _value) external onlyOwner {
        require(create_lock_disabled != _value, "not changed");
        create_lock_disabled = _value;
        emit CreateLockDisabledSet(_value);
    }

    function set_withdraw_disabled(bool _value) external onlyOwner {
        require(withdraw_disabled != _value, "not changed");
        withdraw_disabled = _value;
        emit WithdrawDisabledSet(_value);
    }

    constructor() {}

    function initialize(
        IERC20 _bits,
        string memory _name,
        string memory _symbol,
        string memory _version,
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
        _create_lock(msg.sender, amount, till);
    }

    function create_lock_for(address user, uint256 amount, uint256 till) external onlyOwner {
        _create_lock(user, amount, till);
    }

    function _create_lock(address user, uint256 amount, uint256 till) internal {
        require(!emergency, "emergency");
        require(!create_lock_disabled, "disabled");
        require(locked[user].amount == 0, "already locked");
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
        userWindowBalance[user][_currentWindow] = scaledAmount;
        defaultUserTokenLastClaimedWindow[user] = _currentWindow;
        for (uint256 rewardTokenIndex = 0; rewardTokenIndex < _rewardTokens.length(); rewardTokenIndex += 1) {
            address rewardToken = _rewardTokens.at(rewardTokenIndex);
            userTokenLastClaimedRewardPerToken[user][rewardToken] = windowRewardPerToken[_currentWindow][rewardToken];
        }

        for (uint256 _window = _currentWindow + WINDOW; _window < till; _window += WINDOW) {
            uint256 _windowScaledAmount = scaledAmount * (till - _window) / period;
            windowTotalSupply[_window] += _windowScaledAmount;
            userWindowBalance[user][_window] = _windowScaledAmount;
        }

        poolMembers += 1;
        require(poolMembers <= maxPoolMembers, "max pool members exceed");
        locked[user] = UserLock(amount, till);
        emit CreateLock({
            provider: msg.sender,
            account: user,
            value: amount,
            locktime: till
        });
        bits.safeTransferFrom(msg.sender, address(this), amount);  // note: transferred from msg.sender
    }

    function increase_unlock_time(uint256 till) external {
        require(!emergency, "emergency");
        require(!increase_unlock_time_disabled, "disabled");
        UserLock memory lock = locked[msg.sender];
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

        for (uint256 _window = _currentWindow + WINDOW; _window < till; _window += WINDOW) {
            uint256 _windowScaledAmount = scaledAmount * (till - _window) / period;
            windowTotalSupply[_window] =
                windowTotalSupply[_window] - userWindowBalance[msg.sender][_window] + _windowScaledAmount;
            userWindowBalance[msg.sender][_window] = _windowScaledAmount;
        }

        locked[msg.sender].till = till;
        emit IncreaseUnlockTime({
            account: msg.sender,
            locktime: till
        });
    }

    function increase_lock_amount_for(address user, uint256 amount) external onlyOwner {
        _increase_lock_amount(user, amount);
    }

    function increase_amount(uint256 amount) external {
        _increase_lock_amount(msg.sender, amount);
    }

    function _increase_lock_amount(address user, uint256 amount) internal {
        require(!emergency, "emergency");
        require(!increase_amount_disabled, "disabled");
        UserLock memory lock = locked[user];
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
        userWindowBalance[user][_currentWindow] += scaledAmount;

        for (uint256 _window = _currentWindow + WINDOW; _window < lock.till; _window += WINDOW) {
            uint256 _windowScaledAmount = scaledAmount * (lock.till - _window) / period;
            windowTotalSupply[_window] += _windowScaledAmount;
            userWindowBalance[user][_window] += _windowScaledAmount;
        }

        locked[user].amount += amount;
        emit IncreaseLockAmount({
            provider: msg.sender,
            account: user,
            value: amount
        });
        bits.safeTransferFrom(msg.sender, address(this), amount);  // note: transferred from msg.sender
    }

    function withdraw() external {
        UserLock memory lock = locked[msg.sender];
        require(lock.amount != 0, "nothing locked");
        require(block.timestamp >= lock.till, "too early");

        if (emergency) {
            // erase storage
            locked[msg.sender] = UserLock(0, 0);
            emit Withdraw(msg.sender, lock.amount);
            bits.safeTransfer(msg.sender, lock.amount);
            return;
        }

        claim_rewards();

        // erase storage
        locked[msg.sender] = UserLock(0, 0);
        defaultUserTokenLastClaimedWindow[msg.sender] = 0;
        for (uint256 rewardTokenIndex = 0; rewardTokenIndex < _rewardTokens.length(); rewardTokenIndex += 1) {
            address rewardToken = _rewardTokens.at(rewardTokenIndex);
            userTokenLastClaimedRewardPerToken[msg.sender][rewardToken] = 0;
            userTokenLastClaimedWindow[msg.sender][rewardToken] = 0;
        }
        poolMembers -= 1;

        emit Withdraw(msg.sender, lock.amount);
        bits.safeTransfer(msg.sender, lock.amount);
    }

    function user_token_claimable_rewards(
        address user,
        address _token
    ) public view returns(
        uint256 totalRewards
    ) {
        UserLock memory lock = locked[user];
        require(lock.amount > 0, "nothing lock");
        uint256 _currentWindow = currentWindow();

        totalRewards = 0;
        uint256 _startWindow = userTokenLastClaimedWindow[user][_token];
        if (_startWindow == 0) _startWindow = defaultUserTokenLastClaimedWindow[user];

        for(
            uint256 _processingWindow = _startWindow;
            _processingWindow <= _currentWindow;
            _processingWindow += WINDOW
        ) {
            uint256 _userWindowBalance = userWindowBalance[user][_processingWindow];
            uint256 reward;
            uint256 _windowRewardPerToken = windowRewardPerToken[_processingWindow][_token];

            if (_processingWindow == _startWindow) {
                uint256 _lastClaimedRewardPerToken = userTokenLastClaimedRewardPerToken[user][_token];
                reward = _userWindowBalance * (_windowRewardPerToken - _lastClaimedRewardPerToken) / ONE;
//                emit WindowRewardClaimed({
//                    account: user,
//                    window: _processingWindow,
//                    userWindowBalance: _userWindowBalance,
//                    windowRewardPerToken: _windowRewardPerToken,
//                    lastClaimedRewardPerToken: _lastClaimedRewardPerToken,
//                    reward: reward
//                });
            } else {
                reward = _userWindowBalance * _windowRewardPerToken / ONE;
//                emit WindowRewardClaimed({
//                    account: user,
//                    window: _processingWindow,
//                    userWindowBalance: _userWindowBalance,
//                    windowRewardPerToken: _windowRewardPerToken,
//                    lastClaimedRewardPerToken: 0,
//                    reward: reward
//                });
            }
            totalRewards += reward;
        }
    }

    function claim_rewards() public {
        for (uint256 rewardTokenIndex = 0; rewardTokenIndex < _rewardTokens.length(); rewardTokenIndex += 1) {
            address rewardToken = _rewardTokens.at(rewardTokenIndex);
            claim_rewards(rewardToken);
        }
    }

    function claim_rewards(address _token) public {
        require(!emergency, "emergency");
        require(!claim_rewards_disabled, "disabled");
        uint256 totalRewards = user_token_claimable_rewards(msg.sender, _token);

        uint256 _currentWindow = currentWindow();
        emit UserRewardsClaimed({
            user: msg.sender,
            token: _token,
            first_processed_window: userTokenLastClaimedWindow[msg.sender][_token],
            last_processed_window: _currentWindow,
            totalRewards: totalRewards
        });
        userTokenLastClaimedWindow[msg.sender][_token] = _currentWindow;
        userTokenLastClaimedRewardPerToken[msg.sender][_token] = windowRewardPerToken[_currentWindow][_token];
        _anyTransfer({
            token: _token,
            to: msg.sender,
            amount: totalRewards
        });
    }

    function _anyTransfer(address token, address to, uint256 amount) internal {
        if (token == address(0)) {
            emit TransferNative(address(this), to, amount);
            (bool success, ) = to.call{value: amount}("");
            require(success, "transfer native failed");
        } else {
            IERC20(token).safeTransfer(to, amount);
        }
    }

    function claim_stuck_rewards(uint256 _window, address _token) external onlyOwner {
        uint256 stuckAmount = windowTokenStuckAmount[_window][_token];
        require(stuckAmount > 0, "no stuck reward");
        windowTokenStuckAmount[_window][_token] = 0;
        emit StuckWindowRewardClaimed({
            window: _window,
            token: _token,
            stuckAmount: stuckAmount
        });
        _anyTransfer({
            token: _token,
            to: msg.sender,
            amount: stuckAmount
        });
    }

    function receiveReward(address token, uint256 amount) external {
        uint256 _currentWindow = currentWindow();
        uint256 _windowTotalSupply = windowTotalSupply[_currentWindow];
        if (_windowTotalSupply == 0) {
            windowTokenStuckAmount[_currentWindow][token] += amount;
            emit StuckRewardReceived({
                window: _currentWindow,
                token: token,
                amount: amount
            });
        } else {
            windowRewardPerToken[_currentWindow][token] += amount * ONE / _windowTotalSupply;
        }
        emit WindowRewardReceived(_currentWindow, token, amount);
        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);
    }

    function receiveNativeReward() external payable {
        uint256 _currentWindow = currentWindow();
        uint256 _windowTotalSupply = windowTotalSupply[_currentWindow];
        if (_windowTotalSupply == 0) {
            windowTokenStuckAmount[_currentWindow][address(0)] += msg.value;
            emit StuckRewardReceived({
                window: _currentWindow,
                token: address(0),
                amount: msg.value
            });
        } else {
            windowRewardPerToken[_currentWindow][address(0)] += msg.value * ONE / _windowTotalSupply;
        }
        emit WindowRewardReceived(_currentWindow, address(0), msg.value);
    }
}
