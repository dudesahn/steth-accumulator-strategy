### src/BaseLSTAccumulator.sol

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.23;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {BaseHealthCheck} from "@periphery/Bases/HealthCheck/BaseHealthCheck.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

/// @title Base LST Accumulator
/// @author yearn.fi
/// @notice Abstract base contract for LST (Liquid Staking Token) accumulation strategies
abstract contract BaseLSTAccumulator is BaseHealthCheck {
    using SafeERC20 for ERC20;

    // Events
    event StakeAssetUpdated(bool indexed stakeAsset);
    event OpenDepositsUpdated(bool indexed openDeposits);
    event AllowedUpdated(address indexed user, bool indexed allowed);
    event DepositLimitUpdated(uint256 indexed depositLimit);
    event ReportBufferUpdated(uint256 indexed reportBuffer);
    event MinAmountToTendUpdated(uint256 indexed minAmountToTend);
    event MaxGasPriceToTendUpdated(uint256 indexed maxGasPriceToTend);

    uint256 internal constant WAD = 1e18;

    uint256 internal constant ASSET_DUST = 1000;

    address public immutable LST;

    // Common parameters for all LST strategies
    bool public stakeAsset; // If true, the strategy will stake asset to LST during deposits

    uint256 public depositLimit;

    uint256 public reportBuffer;

    uint256 public minAmountToTend;

    uint256 public maxGasPriceToTend;

    uint256 public pendingRedemptions;

    // Access control
    bool public openDeposits; // If the strategy is open for any depositors

    mapping(address => bool) public allowed; // Addresses allowed to deposit when not open

    constructor(address _asset, string memory _name, address _lst) BaseHealthCheck(_asset, _name) {
        LST = _lst;

        stakeAsset = true;
        emit StakeAssetUpdated(true);

        // Default parameters - can be overridden in child constructors
        depositLimit = type(uint256).max;
        emit DepositLimitUpdated(type(uint256).max);

        minAmountToTend = type(uint256).max;
        emit MinAmountToTendUpdated(type(uint256).max);

        maxGasPriceToTend = 10e9;
        emit MaxGasPriceToTendUpdated(10e9);

        allowed[address(this)] = true;
    }

    /*//////////////////////////////////////////////////////////////
                VIRTUAL FUNCTIONS - MUST BE IMPLEMENTED
    //////////////////////////////////////////////////////////////*/

    /// @notice Stake asset to LST using the most optimal route
    /// @param _amount Amount of asset to stake
    function _stake(uint256 _amount) internal virtual;

    /// @notice Manually swap LST back to asset
    /// @param _amount Amount of LST to swap
    function _swapLSTToAsset(uint256 _amount, uint256 _minOut) internal virtual;

    /// @notice Initiate LST withdrawal through Lido queue for 1:1 redemption
    /// @dev Should revert if the withdrawal request is not successful
    /// @param _amount Amount of LST to queue for withdrawal
    /// @return returnData Return data from the withdrawal request
    function _initiateLSTWithdrawal(uint256 _amount) internal virtual returns (bytes memory returnData);

    /// @notice Claim ETH from completed Lido withdrawal request
    /// @param _claimData The claim data from the withdrawal request
    /// @return _redeemedAmount Amount of LST claimed
    function _claimLSTWithdrawal(bytes memory _claimData) internal virtual returns (uint256 _redeemedAmount);

    /// @notice Claim and sell rewards
    function _claimAndSellRewards() internal virtual {}

    /// @notice Get the deposit limit
    /// @dev Can be overridden by child contracts to implement custom deposit limits
    /// @return _depositLimit The deposit limit
    function _depositLimit() internal view virtual returns (uint256) {
        uint256 _estimatedTotalAssets = estimatedTotalAssets();
        uint256 _limit = depositLimit;
        if (_estimatedTotalAssets < _limit) {
            return _limit - _estimatedTotalAssets;
        }
        return 0;
    }

    /*//////////////////////////////////////////////////////////////
                INTERNAL BASE IMPLEMENTATION
    //////////////////////////////////////////////////////////////*/

    function _deployFunds(uint256 _amount) internal virtual override {
        if (stakeAsset && _amount > ASSET_DUST) {
            _stake(_amount);
        }
    }

    function _freeFunds(
        uint256 /*_amount*/
    )
        internal
        virtual
        override
    {
        // Do nothing - no automatic unstaking
        // Management must manually swap LST to asset if needed
    }

    function availableDepositLimit(address _owner) public view virtual override returns (uint256) {
        if (openDeposits || allowed[_owner]) {
            return _depositLimit();
        }
        return 0;
    }

    function availableWithdrawLimit(
        address /*_owner*/
    )
        public
        view
        virtual
        override
        returns (uint256)
    {
        // Only allow liquid withdrawals (available asset)
        return balanceOfAsset();
    }

    function _harvestAndReport() internal virtual override returns (uint256 _totalAssets) {
        require(pendingRedemptions == 0, "Pending redemptions");

        _claimAndSellRewards();

        // Stake any loose asset
        _stake(Math.min(balanceOfAsset(), availableDepositLimit(address(this))));

        // Simple accounting: Asset + LST (assuming LST rebases or maintains peg)
        _totalAssets = estimatedTotalAssets();
    }

    function _emergencyWithdraw(uint256 _amount) internal virtual override {
        uint256 lstBalance = balanceOfLST();
        if (lstBalance == 0) return;

        _swapLSTToAsset(Math.min(_amount, lstBalance), 0);
    }

    function _tend(uint256 _totalIdle) internal virtual override {
        _stake(_totalIdle);
    }

    function _tendTrigger() internal view virtual override returns (bool) {
        return balanceOfAsset() > minAmountToTend && block.basefee <= maxGasPriceToTend;
    }

    /*//////////////////////////////////////////////////////////////
                EXTERNAL VIEW FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    function estimatedTotalAssets() public view virtual returns (uint256) {
        return balanceOfAsset() + ((valueOfLST() * (MAX_BPS - reportBuffer)) / MAX_BPS);
    }

    function balanceOfAsset() internal view virtual returns (uint256) {
        return asset.balanceOf(address(this));
    }

    function balanceOfLST() internal view virtual returns (uint256) {
        return ERC20(LST).balanceOf(address(this));
    }

    // @notice Default to 1:1 value of LST
    function valueOfLST() internal view virtual returns (uint256) {
        return balanceOfLST();
    }

    /*//////////////////////////////////////////////////////////////
                MANAGEMENT FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    function setReportBuffer(uint256 _reportBuffer) external virtual onlyManagement {
        reportBuffer = _reportBuffer;
        emit ReportBufferUpdated(_reportBuffer);
    }

    /// @notice Set whether the strategy will stake asset to LST during harvest
    function setStakeAsset(bool _stakeAsset) external virtual onlyManagement {
        stakeAsset = _stakeAsset;
        emit StakeAssetUpdated(_stakeAsset);
    }

    /// @notice Set the maximum amount that can be staked in a single harvest
    function setDepositLimit(uint256 _limit) external virtual onlyManagement {
        depositLimit = _limit;
        emit DepositLimitUpdated(_limit);
    }

    /// @notice Set whether the strategy is open for deposits
    function setOpenDeposits(bool _openDeposits) external virtual onlyManagement {
        openDeposits = _openDeposits;
        emit OpenDepositsUpdated(_openDeposits);
    }

    /// @notice Set or update an address's whitelist status
    function setAllowed(address _address, bool _allowed) external virtual onlyManagement {
        allowed[_address] = _allowed;
        emit AllowedUpdated(_address, _allowed);
    }

    /// @notice Set the minimum amount of asset to tend
    function setMinAmountToTend(uint256 _minAmountToTend) external virtual onlyManagement {
        minAmountToTend = _minAmountToTend;
        emit MinAmountToTendUpdated(_minAmountToTend);
    }

    /// @notice Set the maximum gas price to tend
    function setMaxGasPriceToTend(uint256 _maxGasPriceToTend) external virtual onlyManagement {
        maxGasPriceToTend = _maxGasPriceToTend;
        emit MaxGasPriceToTendUpdated(_maxGasPriceToTend);
    }

    /// @notice Manually swap LST to asset
    /// @param _amount Amount of LST to swap
    function manualSwapToAsset(uint256 _amount, uint256 _minOut) external virtual onlyManagement {
        _amount = Math.min(_amount, valueOfLST());
        require(_amount > 0, "!amount");

        _swapLSTToAsset(_amount, _minOut);
    }

    /// @notice Stake available asset to LST
    /// @param _amount Amount of asset to stake
    function manualStake(uint256 _amount) external virtual onlyManagement {
        _amount = Math.min(_amount, balanceOfAsset());
        require(_amount > 0, "!amount");
        _stake(_amount);
    }

    /// @notice Initiate stETH withdrawal through Lido queue for 1:1 redemption
    /// @param _amount Amount of LST to queue for withdrawal
    /// @return returnData Return data from the withdrawal request
    function initiateLSTWithdrawal(uint256 _amount) external virtual onlyManagement returns (bytes memory returnData) {
        _amount = Math.min(_amount, valueOfLST());
        require(_amount > 0, "!amount");
        pendingRedemptions += _amount;
        return _initiateLSTWithdrawal(_amount);
    }

    /// @notice Claim ETH from completed Lido withdrawal request
    /// @param _claimData The claim data from the withdrawal request
    /// @return _amount Amount of LST claimed
    function claimLSTWithdrawal(bytes memory _claimData) external virtual onlyKeepers returns (uint256) {
        uint256 _redeemedAmount = _claimLSTWithdrawal(_claimData);
        pendingRedemptions = _redeemedAmount >= pendingRedemptions ? 0 : pendingRedemptions - _redeemedAmount;
        return _redeemedAmount;
    }

    /// @notice Clear pending redemptions in emergency
    /// @dev This should only be used in extreme scenarios when there are
    ///    issues with the redemtion process in order to "unstick" a strategy.
    ///    Using this will cause losses to potentially be realized during the next report
    function clearPendingRedemptions(uint256 _amount) external virtual onlyManagement {
        pendingRedemptions = _amount >= pendingRedemptions ? 0 : pendingRedemptions - _amount;
    }
}

```

### src/Strategy.sol

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.23;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {BaseLSTAccumulator} from "./BaseLSTAccumulator.sol";
import {IQueue} from "./interfaces/IQueue.sol";
import {IWETH} from "./interfaces/IWETH.sol";
import {ICurve} from "./interfaces/ICurve.sol";
import {ISTETH} from "./interfaces/ISTETH.sol";

/// @title stETH Accumulator Strategy
/// @author yearn.fi
/// @notice Yearn V3 strategy for accumulating stETH through optimal staking routes
contract Strategy is BaseLSTAccumulator {
    using SafeERC20 for ERC20;

    // stETH specific constants
    address internal constant WITHDRAWAL_QUEUE = 0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1; // stETH withdrawal queue

    address internal constant CURVE_POOL = 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022; // Curve ETH/stETH pool

    int128 internal constant ASSET_ID = 0; // ETH index in Curve pool

    int128 internal constant LST_ID = 1; // stETH index in Curve pool

    address public referral;

    constructor(address _asset, string memory _name)
        BaseLSTAccumulator(_asset, _name, 0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84)
    {
        // Approve Curve pool for asset (WETH)
        asset.forceApprove(CURVE_POOL, type(uint256).max);
    }

    receive() external payable {}

    function _depositLimit() internal view virtual override returns (uint256) {
        if (ISTETH(LST).isStakingPaused()) {
            return 0;
        }
        return super._depositLimit();
    }

    /*//////////////////////////////////////////////////////////////
                REQUIRED VIRTUAL FUNCTION IMPLEMENTATIONS
    //////////////////////////////////////////////////////////////*/

    /// @notice Stake ETH to stETH using the most optimal route
    /// @param _amount Amount of WETH to stake
    function _stake(uint256 _amount) internal virtual override {
        if (_amount == 0) return;

        // Convert WETH to ETH
        IWETH(address(asset)).withdraw(_amount);

        // Check if Curve swap gives better than 1:1 rate
        if (ICurve(CURVE_POOL).get_dy(ASSET_ID, LST_ID, _amount) > _amount) {
            // Swap through Curve for better rate
            ICurve(CURVE_POOL).exchange{value: _amount}(
                ASSET_ID,
                LST_ID,
                _amount,
                _amount // Minimum 1:1
            );
        } else {
            // Stake directly with Lido for 1:1
            ISTETH(LST).submit{value: _amount}(referral);
        }
    }

    /// @notice Swap stETH to WETH through Curve
    /// @param _amount Amount of stETH to swap
    function _swapLSTToAsset(uint256 _amount, uint256 _minOut) internal virtual override {
        ERC20(LST).forceApprove(CURVE_POOL, _amount);

        // Swap stETH for ETH through Curve
        ICurve(CURVE_POOL).exchange(LST_ID, ASSET_ID, _amount, _minOut);

        // Convert received ETH to WETH
        IWETH(address(asset)).deposit{value: address(this).balance}();
    }

    /*//////////////////////////////////////////////////////////////
                STETH SPECIFIC FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    /// @notice Initiate stETH withdrawal through Lido queue for 1:1 redemption
    /// @param _amount Amount of LST to queue for withdrawal
    /// @return returnData Return data from the withdrawal request
    function _initiateLSTWithdrawal(uint256 _amount) internal virtual override returns (bytes memory returnData) {
        ERC20(LST).forceApprove(WITHDRAWAL_QUEUE, _amount);

        uint256[] memory _amounts = new uint256[](1);
        _amounts[0] = _amount;

        uint256[] memory requestIds = IQueue(WITHDRAWAL_QUEUE).requestWithdrawals(_amounts, address(this));

        return abi.encode(requestIds);
    }

    /// @notice Claim ETH from completed Lido withdrawal request
    /// @param _claimData The claim data from the withdrawal request
    function _claimLSTWithdrawal(bytes memory _claimData) internal virtual override returns (uint256 _redeemedAmount) {
        uint256 _requestId = abi.decode(_claimData, (uint256));

        uint256 preBalance = address(this).balance;
        IQueue(WITHDRAWAL_QUEUE).claimWithdrawal(_requestId);
        _redeemedAmount = address(this).balance - preBalance;

        // Convert received ETH to WETH
        IWETH(address(asset)).deposit{value: address(this).balance}();
    }

    // @dev Only needed if the hint and batch ID are too far from each other.
    function manualClaimWithdrawals(uint256[] calldata _requestIds, uint256[] calldata _hints, bool _zeroRedemptions)
        external
        onlyEmergencyAuthorized
    {
        IQueue(WITHDRAWAL_QUEUE).claimWithdrawals(_requestIds, _hints);
        if (_zeroRedemptions) {
            pendingRedemptions = 0;
        }

        IWETH(address(asset)).deposit{value: address(this).balance}();
    }

    function setReferral(address _referral) external virtual onlyManagement {
        referral = _referral;
    }
}

```

### src/Strategy4626.sol

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.23;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {IERC4626} from "@openzeppelin/contracts/interfaces/IERC4626.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {Strategy} from "./Strategy.sol";
import {IWstETH} from "./interfaces/IWstETH.sol";

/// @title stETH Accumulator With ERC-4626 Vault
/// @author yearn.fi
contract Strategy4626 is Strategy {
    using SafeERC20 for *;

    IWstETH public constant wstETH = IWstETH(0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0);

    IERC4626 public immutable vault;

    constructor(address _asset, string memory _name, address _vault) Strategy(_asset, _name) {
        require(IERC4626(_vault).asset() == address(wstETH), "wrong vault");

        vault = IERC4626(_vault);

        ERC20(LST).forceApprove(address(wstETH), type(uint256).max);
        wstETH.forceApprove(_vault, type(uint256).max);
    }

    function _stake(uint256 _amount) internal virtual override {
        super._stake(_amount);

        uint256 stethBalance = balanceOfLST();
        if (stethBalance > 0) {
            wstETH.wrap(stethBalance);
        }

        uint256 wstETHBalance = balanceOfWstETH();
        // Can round to 0 if stethBalance is too small
        if (wstETHBalance == 0) return;

        vault.deposit(wstETHBalance, address(this));
    }

    function _swapLSTToAsset(uint256 _amount, uint256 _minOut) internal virtual override {
        _freeStETH(_amount);
        super._swapLSTToAsset(Math.min(_amount, balanceOfLST()), _minOut);
    }

    function _initiateLSTWithdrawal(uint256 _amount) internal virtual override returns (bytes memory returnData) {
        _freeStETH(_amount);
        require(balanceOfLST() >= _amount, "!available");
        return super._initiateLSTWithdrawal(_amount);
    }

    function availableDepositLimit(address _owner) public view virtual override returns (uint256) {
        uint256 superLimit = super.availableDepositLimit(_owner);
        if (superLimit == 0) return 0;

        uint256 maxDeposit = vault.maxDeposit(address(this));
        if (maxDeposit == type(uint256).max) return superLimit;

        return Math.min(superLimit, _stETHValue(maxDeposit));
    }

    function balanceOfWstETH() public view virtual returns (uint256) {
        return wstETH.balanceOf(address(this));
    }

    function valueOfWstETH() public view virtual returns (uint256) {
        return _stETHValue(balanceOfWstETH() + vault.convertToAssets(vault.balanceOf(address(this))));
    }

    function valueOfLST() internal view virtual override returns (uint256) {
        return balanceOfLST() + valueOfWstETH();
    }

    function _freeStETH(uint256 _amount) internal {
        uint256 stethBalance = balanceOfLST();
        if (stethBalance >= _amount) return;

        // Add two wei to cover double rounding across stETH->wstETH conversion and unwrap.
        uint256 neededWstETH = wstETH.getWstETHByStETH(_amount - stethBalance) + 2;

        uint256 wrappedBalance = balanceOfWstETH();
        if (wrappedBalance < neededWstETH) {
            // Redeem the difference up to max redeem.
            uint256 shares =
                Math.min(vault.previewWithdraw(neededWstETH - wrappedBalance), vault.maxRedeem(address(this)));

            if (shares > 0) {
                wrappedBalance += vault.redeem(shares, address(this), address(this));
            }
        }

        wstETH.unwrap(wrappedBalance);
    }

    function _stETHValue(uint256 _amount) internal view returns (uint256) {
        if (_amount == 0) return 0;
        return wstETH.getStETHByWstETH(_amount);
    }

    function manualRedeem(uint256 _amount) external onlyEmergencyAuthorized {
        _amount = Math.min(_amount, vault.balanceOf(address(this)));
        if (_amount == 0) return;

        vault.redeem(_amount, address(this), address(this));
    }

    function manualUnwrap(uint256 _amount) external onlyEmergencyAuthorized {
        _amount = Math.min(_amount, balanceOfWstETH());
        if (_amount == 0) return;

        wstETH.unwrap(_amount);
    }
}

```

### src/Strategy4626Factory.sol

```solidity
// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.23;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Strategy4626} from "./Strategy4626.sol";
import {IStrategy4626Interface} from "./interfaces/IStrategy4626Interface.sol";

contract Strategy4626Factory {
    /// @notice Revert message for when a strategy has already been deployed.
    error AlreadyDeployed(address _strategy);

    event NewStrategy4626(address indexed strategy, address indexed vault);

    address public immutable ASSET;

    address public management;
    address public performanceFeeRecipient;
    address public keeper;
    address public emergencyAdmin;

    /// @notice Track the deployments. vault => strategy
    mapping(address => address) public deployments;

    constructor(
        address _management,
        address _performanceFeeRecipient,
        address _keeper,
        address _emergencyAdmin,
        address _asset
    ) {
        management = _management;
        performanceFeeRecipient = _performanceFeeRecipient;
        keeper = _keeper;
        emergencyAdmin = _emergencyAdmin;
        ASSET = _asset;
    }

    /**
     * @notice Deploy a new Strategy4626.
     * @param _vault The ERC4626 vault for the strategy to use.
     * @return . The address of the new strategy.
     */
    function newStrategy4626(address _vault) external returns (address) {
        if (deployments[_vault] != address(0)) {
            revert AlreadyDeployed(deployments[_vault]);
        }

        string memory _name = string(abi.encodePacked("stETH ", ERC20(_vault).symbol(), " Accumulator"));

        // We need to use the custom interface with the
        // tokenized strategies available setters.
        IStrategy4626Interface newStrategy = IStrategy4626Interface(address(new Strategy4626(ASSET, _name, _vault)));

        newStrategy.setPerformanceFeeRecipient(performanceFeeRecipient);

        newStrategy.setKeeper(keeper);

        newStrategy.setPendingManagement(management);

        newStrategy.setEmergencyAdmin(emergencyAdmin);

        newStrategy.setPerformanceFee(0);

        newStrategy.setProfitMaxUnlockTime(0);

        emit NewStrategy4626(address(newStrategy), _vault);

        deployments[_vault] = address(newStrategy);
        return address(newStrategy);
    }

    function setAddresses(
        address _management,
        address _performanceFeeRecipient,
        address _keeper,
        address _emergencyAdmin
    ) external {
        require(msg.sender == management, "!management");
        management = _management;
        performanceFeeRecipient = _performanceFeeRecipient;
        keeper = _keeper;
        emergencyAdmin = _emergencyAdmin;
    }

    function isDeployedStrategy(address _strategy) external view returns (bool) {
        address _vault = address(IStrategy4626Interface(_strategy).vault());
        return deployments[_vault] == _strategy;
    }
}

```

### src/periphery/StrategyAprOracle.sol

```solidity
// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.18;

import {AprOracleBase} from "@periphery/AprOracle/AprOracleBase.sol";

contract StrategyAprOracle is AprOracleBase {
    constructor() AprOracleBase("Strategy Apr Oracle Example", msg.sender) {}

    /**
     * @notice Will return the expected Apr of a strategy post a debt change.
     * @dev _delta is a signed integer so that it can also represent a debt
     * decrease.
     *
     * This should return the annual expected return at the current timestamp
     * represented as 1e18.
     *
     *      ie. 10% == 1e17
     *
     * _delta will be == 0 to get the current apr.
     *
     * This will potentially be called during non-view functions so gas
     * efficiency should be taken into account.
     *
     * @param _strategy The token to get the apr for.
     * @param _delta The difference in debt.
     * @return . The expected apr for the strategy represented as 1e18.
     */
    function aprAfterDebtChange(address _strategy, int256 _delta) external view override returns (uint256) {
        // Return a simple estimation for stETH APR
        // stETH typically yields around 3-5% APR
        // We'll return 4% as base APR (4e16)
        return 4e16;
    }
}

```
# Senior Auditor's Mindset

This is how a senior auditor thinks. Pattern-matching catches the obvious bugs — your specialty file teaches that. The high-value bugs, the ones everyone else misses, come from HOW you reason about code, not from WHAT bugs you know.

The senior auditor's edge is not "knowing more bug patterns" — it is having internalized mental tools they reach for instinctively when something feels off, when a path seems clean, or when a conclusion comes too quickly.

This file gives you three tools. They are not steps. You reach for the right one the moment the trigger fires — see `shared-rules.md` for the binding trigger→tool protocol. Use them. Trust your discomfort.

A finding is not real until you've traced the attack with concrete values. You are an attacker, not a defender — when you find a bug, deepen the attack; never argue yourself out of one.

---

## 1. The Feynman test (FIRST — use it before anything else)

**This is the first tool. Apply it the moment you open any new function or contract — before you reason about anything else.** Code you have not Feynman'd is code you have not actually understood.

When you read code, STOP and ask: "Can I explain what this function does to someone who doesn't know Solidity?"

Try it. In plain words. The places where your explanation gets fuzzy — where you reach for Solidity jargon instead of plain meaning — are where you're papering over an assumption. That's where bugs hide.

Example: you read `_handleFeeTransfer(zrc20, fee)` and your explanation comes out as "it transfers the fee." That's not Feynman. Feynman is: "it picks up the protocol's commission off the user's payment and moves it to the treasury wallet." Now keep going: what if the payment is in ETH and the function uses an ERC20 method? Your plain-English explanation breaks. Bug.

A senior auditor doesn't trust their understanding until they can explain it without the safety net of technical vocabulary.

---

## 2. Socratic questioning

For every line of code, ask: why is this here? What does it assume? What happens if the assumption breaks?

Don't accept "because that's how it's written" as an answer. Don't accept "the function name says so" as an answer. Drill until you reach the implicit belief the code rests on. The first answer is usually a restatement. The actual assumption is two or three "whys" deeper.

Example: `if (zrc20 != _ETH_ADDRESS_) IERC20(zrc20).transferFrom(msg.sender, address(this), amount);`
- Why is `zrc20 != _ETH_ADDRESS_` checked? → because ETH isn't transferable via transferFrom.
- Why is there no else branch? → because the developer assumed ETH arrives via `msg.value`.
- Where is `msg.value` enforced to equal `amount` for the ETH path? → **nowhere**. Bug.

A senior auditor accepts no "because" without examining it.

---

## 3. Inversion

Every clean path gets a backward pass. After you understand what the code IS supposed to do, ask: how would I make it NOT do that?

Same code, attacker's eye instead of developer's eye. The developer asks "does this work?" The attacker asks "how do I break this?" Read every check and ask "what value slips past it?" Read every state update and ask "what state am I in just before this?"

A senior auditor never reads code only forward.

---

## When to reach for which tool

You don't apply these in order — except Feynman, which is always first. You reach for what the moment calls for:

- Opening any new function or contract → **Feynman** (always — before anything else)
- Trying to understand a line you don't yet → **Socratic**
- Something looks too clean → **Inversion**
- You reached a "bug" conclusion → amplify the attack (chain it, find more victims, lower the precondition cost — do NOT refute it)

The tools are how you keep yourself honest. Without them, you fall into the trap of every junior auditor: trusting your first read, accepting code that "looks right," moving on when something feels off.

Trust your discomfort. Reach for the tool. Don't stop until the discomfort has a name.
# Math Precision Agent

You are an attacker that exploits integer arithmetic: rounding errors, precision loss, decimal mismatches, overflow, and scale mixing. Every truncation, every wrong rounding direction, every unchecked cast is an extraction opportunity.

Other agents cover logic, state, and access control. You exploit the math.

## Attack surfaces

**Map the math.** Identify all fixed-point systems (WAD, RAY, BPS, token decimals, oracle decimals), scale conversion points, and every division in value-moving functions.

**Exploit wrong rounding.** Deposits must round shares DOWN, withdrawals round assets DOWN, debt rounds UP, fees round UP. Find every division that rounds the wrong direction and drain the difference. Compoundable wrong direction = critical.

**Zero-round to steal.** Feed minimum inputs (1 wei, 1 share) into every calculation. Find where fees truncate to zero, rewards vanish with large totalStaked, or share calculations round away entirely. A ratio truncating to zero flips formulas — exploit it.

**Amplify truncation.** Find division-before-multiplication chains — intermediate truncation amplified by later multiplication. Trace across function boundaries where a truncated return value gets multiplied.

**Overflow intermediates.** For every `a * b / c`, construct inputs where `a * b` overflows uint256 before the division saves it. Use flash-loan-scale values for user-influenced operands.

**Mismatch decimals.** Exploit hardcoded `1e18` on 6-decimal tokens. Underflow `18 - decimals` for >18 decimal tokens. Feed variable oracle decimals into code assuming constant decimals.

**Break downcasts.** uint256 → uint128/uint96/uint64 without bounds check. Construct realistic values that overflow the target type.

**Inflate share prices.** As the first depositor, donate to inflate the exchange rate. Make subsequent depositors round to 0 shares and steal their deposits.

**Lose sign on narrow-int casts.** `uint24`/`int24` round-trips drop the sign bit; negative ticks or signed offsets become huge positive values, corrupting downstream tree-tick or interval math.

**Overflow inside intermediate shifts.** `(x << shift) / y` overflows uint256 when shift makes x exceed type max — even though the divided result is safe. Construct flash-loan-scale x that breaks the intermediate.

**Round at sole-occupant boundary.** Strict-less-than guards on participant counts or pool sizes exclude the single-occupant case; verify `<=` is the correct comparator for every distinguishing-from-zero check.

**Cast-wrap at saturation.** Down-casts `uint64((x << 64) / y)` wrap to near-zero when the ratio approaches 1; at saturation utilization, fees and rates silently collapse instead of being capped.

**Truncate interest accrual on tiny principals.** Lending utilization curves scaling by `rate / SECONDS_PER_YEAR` produce zero accrual when `principal · rate < SCALE`; borrowers pay nothing across the period.

**Underflow in unsigned-bonus computations.** `unsigned a - unsigned b` underflows when `b > a` at insolvent or edge positions; downstream code interprets the wrap-around as a huge value. Walk every `a - b` where bounds aren't asserted.

**Mask the wrong bits.** Bitmask constants in pack/unpack helpers silently clear or preserve adjacent fields when miscalculated; downstream readers receive zero for fields that should carry data. Verify every mask against the bit layout it claims to extract.

**Divide by an unconstrained edge value.** Formulas `x / tickSpacing`, `x / config.value`, `x / decimals` revert or zero when the edge case (1, 0) is permitted. Construct an input where the divisor reaches the edge.

**Every finding needs concrete numbers.** Walk through the arithmetic with specific values. No numbers = LEAD.

## Output fields

Add to FINDINGs:
```
proof: concrete arithmetic showing the bug with actual numbers
```
# Shared Scan Rules

## Bundle contents

Your bundle is four concatenated files: all in-scope source code, the SOP (HOW to think), your specialty agent (WHAT to look for), and these shared rules (output format, dedup tags, AND mandatory mental tool protocol).

Read the whole bundle once at the start. The bundle contains all in-scope source. Use Read/Grep only for cross-file searches or out-of-scope context (interfaces/, lib/, mocks/, test/) — do not re-read in-scope files for the initial scan.

**The protocol below applies continuously during source reading — not just before it.** The "read source" phase does not turn off the protocol; every trigger condition fires the moment it occurs, throughout your entire review.

When matching function names, check both `functionName` and `_functionName` (Solidity convention).

## Mental tool protocol — MANDATORY

The three tools in `senior-auditor-sop.md` are NOT optional. Each tool has a specific trigger. **When the trigger fires, you MUST emit the corresponding marker in your output stream BEFORE continuing.** No skipping. The markers live in your working text — they do NOT go into the FINDING/LEAD output blocks.

### Triggers → required markers

| Trigger (the condition) | Marker (required immediately, literal `[Tool: ...]` syntax) | Content |
|---|---|---|
| You open a new function or contract to read | `[Feynman: <name>]` | Explain what it does in plain English — no Solidity jargon, no `mload`/`assembly`/`mstore`/`safeTransfer`/etc. Use as many sentences as you need until the explanation is solid. If your wording slips back to jargon, you're papering over an assumption — keep going. Wherever your plain-English explanation gets fuzzy or you have to reach for a Solidity term to keep it accurate, mark that spot — that is where bugs hide. |
| You stop on a line whose purpose isn't immediately clear | `[Socratic: <file:line> — why?]` | A one-line question that drills past "because that's how it's written." If your first answer is a restatement of the code, ask again. Stop when the answer exposes the implicit belief the code rests on — don't pad with extra steps just to hit a quota. |
| A code path reads as clean / a check looks sufficient / a guard looks correct | `[Inversion: <function>]` | Three concrete attacker moves that attempt to defeat the path. Specific addresses/values/states, not abstractions. |

### Rules

1. **Triggers are not optional.** If the condition fires, the marker follows. Always. No skipping.
2. **Use the literal `[Tool: ...]` syntax.** The orchestrator greps your output for these tags after the run.
3. **You may emit a marker without a trigger.** Extra Feynman / Inversion markers are fine. You may NOT skip a marker after its trigger fired.
4. **The protocol applies to reasoning depth, not output volume.** Heavy use of these tools is what produces the audit work. Skipping them = surface-level scanning, which is the failure mode of every junior auditor.

The orchestrator verifies marker counts after every run. Skipped markers downgrade the value of your findings and are recorded as workflow violations.

## Cross-contract patterns

When you find a bug in one contract, **weaponize that pattern across every other contract in the bundle.** Search by function name AND by code pattern. Finding native/ERC20 confusion in `ContractA.onRevert` means you check every other contract's `onRevert` — missing a repeat instance is an audit failure.

After scanning: escalate every finding to its worst exploitable variant (DoS may hide fund theft). Then revisit every function where you found something and attack the other branches.

## Do not report

Admin-only functions doing admin things. Standard DeFi tradeoffs (MEV, rounding dust, first-depositor with MINIMUM_LIQUIDITY). Self-harm-only bugs. "Admin can rug" without a concrete mechanism.

## Output

Return findings as structured blocks:

FINDINGs have concrete, unguarded, exploitable attack paths. LEADs have real code smells with partial paths — default to LEAD over dropping.

**Every FINDING must have a `proof:` field** — concrete values, traces, or state sequences from the actual code. No proof = LEAD, no exceptions.

**One vulnerability per item.** Same root cause = one item. Different fixes needed = separate items.

```
FINDING | contract: Name | function: func | bug_class: kebab-tag | group_key: Contract | function | bug-class
path: caller → function → state change → impact
proof: concrete values/trace demonstrating the bug
description: one sentence
fix: one-sentence suggestion

LEAD | contract: Name | function: func | bug_class: kebab-tag | group_key: Contract | function | bug-class
code_smells: what you found
description: one sentence explaining trail and what remains unverified
```

The `group_key` enables deduplication: `ContractName | functionName | bug_class`. Agents may add custom fields.
