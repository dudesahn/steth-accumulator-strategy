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
