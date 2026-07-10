# Entry-Point Analysis

This table maps state-changing external/public entry points in local production contracts plus inherited TokenizedStrategy entry points reachable through the strategy fallback. View/pure functions are omitted unless they gate state-changing behavior.

## Inherited TokenizedStrategy / BaseHealthCheck Surface

| Function | File:Line | Access | Classification |
|----------|-----------|--------|----------------|
| `deposit(uint256,address)` | `lib/tokenized-strategy/src/TokenizedStrategy.sol:487` | Requires strategy not shutdown and `assets <= maxDeposit(receiver)` | Public (Unrestricted) |
| `mint(uint256,address)` | `lib/tokenized-strategy/src/TokenizedStrategy.sol:519` | Requires strategy not shutdown and `shares <= maxMint(receiver)` | Public (Unrestricted) |
| `withdraw(uint256,address,address)` | `lib/tokenized-strategy/src/TokenizedStrategy.sol:547` | Owner or approved spender; limited by loose asset via `availableWithdrawLimit` | Public (Unrestricted) |
| `withdraw(uint256,address,address,uint256)` | `lib/tokenized-strategy/src/TokenizedStrategy.sol:565` | Owner or approved spender; `maxLoss <= MAX_BPS` | Public (Unrestricted) |
| `redeem(uint256,address,address)` | `lib/tokenized-strategy/src/TokenizedStrategy.sol:596` | Owner or approved spender; limited by loose asset via `availableWithdrawLimit` | Public (Unrestricted) |
| `redeem(uint256,address,address,uint256)` | `lib/tokenized-strategy/src/TokenizedStrategy.sol:615` | Owner or approved spender; `maxLoss <= MAX_BPS` | Public (Unrestricted) |
| `report()` | `lib/tokenized-strategy/src/TokenizedStrategy.sol:1081` | `onlyKeepers` via keeper or management | Role-Restricted |
| `tend()` | `lib/tokenized-strategy/src/TokenizedStrategy.sol:1314` | `onlyKeepers` via keeper or management | Role-Restricted |
| `shutdownStrategy()` | `lib/tokenized-strategy/src/TokenizedStrategy.sol:1337` | `onlyEmergencyAuthorized` via management or emergencyAdmin | Role-Restricted |
| `emergencyWithdraw(uint256)` | `lib/tokenized-strategy/src/TokenizedStrategy.sol:1356` | `onlyEmergencyAuthorized`, requires shutdown | Role-Restricted |
| `setPendingManagement(address)` | `lib/tokenized-strategy/src/TokenizedStrategy.sol:1502` | `onlyManagement` and nonzero pending management | Role-Restricted |
| `acceptManagement()` | `lib/tokenized-strategy/src/TokenizedStrategy.sol:1512` | Must be current `pendingManagement` | Role-Restricted |
| `setKeeper(address)` | `lib/tokenized-strategy/src/TokenizedStrategy.sol:1528` | `onlyManagement` | Role-Restricted |
| `setEmergencyAdmin(address)` | `lib/tokenized-strategy/src/TokenizedStrategy.sol:1540` | `onlyManagement` | Role-Restricted |
| `setPerformanceFee(uint16)` | `lib/tokenized-strategy/src/TokenizedStrategy.sol:1557` | `onlyManagement`, max fee enforced | Role-Restricted |
| `setPerformanceFeeRecipient(address)` | `lib/tokenized-strategy/src/TokenizedStrategy.sol:1572` | `onlyManagement`, nonzero and not self | Role-Restricted |
| `setProfitMaxUnlockTime(uint256)` | `lib/tokenized-strategy/src/TokenizedStrategy.sol:1596` | `onlyManagement`, max 1 year | Role-Restricted |
| `setName(string)` | `lib/tokenized-strategy/src/TokenizedStrategy.sol:1624` | `onlyManagement` | Role-Restricted |
| `setProfitLimitRatio(uint256)` | `lib/tokenized-strategy-periphery/src/Bases/HealthCheck/BaseHealthCheck.sol:66` | `onlyManagement`, nonzero and uint16 bound | Role-Restricted |
| `setLossLimitRatio(uint256)` | `lib/tokenized-strategy-periphery/src/Bases/HealthCheck/BaseHealthCheck.sol:88` | `onlyManagement`, below `MAX_BPS` | Role-Restricted |
| `setDoHealthCheck(bool)` | `lib/tokenized-strategy-periphery/src/Bases/HealthCheck/BaseHealthCheck.sol:109` | `onlyManagement` | Role-Restricted |
| `initialize(address,string,address,address,address)` | `lib/tokenized-strategy/src/TokenizedStrategy.sol:433` | One-time initializer; guarded by `address(S.asset) == address(0)` | Contract-Only |
| `deployFunds(uint256)` | `lib/tokenized-strategy/src/BaseStrategy.sol:378` | `onlySelf` callback from TokenizedStrategy | Contract-Only |
| `freeFunds(uint256)` | `lib/tokenized-strategy/src/BaseStrategy.sol:392` | `onlySelf` callback from TokenizedStrategy | Contract-Only |
| `harvestAndReport()` | `lib/tokenized-strategy-periphery/src/Bases/HealthCheck/BaseHealthCheck.sol:117` | `onlySelf` callback from TokenizedStrategy | Contract-Only |
| `tendThis(uint256)` | `lib/tokenized-strategy/src/BaseStrategy.sol:422` | `onlySelf` callback from TokenizedStrategy | Contract-Only |
| `shutdownWithdraw(uint256)` | `lib/tokenized-strategy/src/BaseStrategy.sol:440` | `onlySelf` callback from TokenizedStrategy | Contract-Only |
| ERC20 share `transfer/approve/transferFrom` and permit methods | `lib/tokenized-strategy/src/TokenizedStrategy.sol` | Standard ERC20/ERC20Permit authorization | Public (Unrestricted) |

## `BaseLSTAccumulator`

| Function | File:Line | Access | Classification |
|----------|-----------|--------|----------------|
| `setReportBuffer(uint256)` | `src/BaseLSTAccumulator.sol:198` | `onlyManagement` | Role-Restricted |
| `setStakeAsset(bool)` | `src/BaseLSTAccumulator.sol:204` | `onlyManagement` | Role-Restricted |
| `setDepositLimit(uint256)` | `src/BaseLSTAccumulator.sol:210` | `onlyManagement` | Role-Restricted |
| `setOpenDeposits(bool)` | `src/BaseLSTAccumulator.sol:216` | `onlyManagement` | Role-Restricted |
| `setAllowed(address,bool)` | `src/BaseLSTAccumulator.sol:222` | `onlyManagement` | Role-Restricted |
| `setMinAmountToTend(uint256)` | `src/BaseLSTAccumulator.sol:228` | `onlyManagement` | Role-Restricted |
| `setMaxGasPriceToTend(uint256)` | `src/BaseLSTAccumulator.sol:234` | `onlyManagement` | Role-Restricted |
| `manualSwapToAsset(uint256,uint256)` | `src/BaseLSTAccumulator.sol:241` | `onlyManagement` | Role-Restricted |
| `manualStake(uint256)` | `src/BaseLSTAccumulator.sol:250` | `onlyManagement` | Role-Restricted |
| `initiateLSTWithdrawal(uint256)` | `src/BaseLSTAccumulator.sol:259` | `onlyManagement` | Role-Restricted |
| `claimLSTWithdrawal(bytes)` | `src/BaseLSTAccumulator.sol:269` | `onlyKeepers` via keeper or management | Role-Restricted |
| `clearPendingRedemptions(uint256)` | `src/BaseLSTAccumulator.sol:279` | `onlyManagement` | Role-Restricted |

## `Strategy`

| Function | File:Line | Access | Classification |
|----------|-----------|--------|----------------|
| `receive()` | `src/Strategy.sol:36` | Accepts ETH from anyone | Public (Unrestricted) |
| `manualClaimWithdrawals(uint256[],uint256[],bool)` | `src/Strategy.sol:116` | `onlyEmergencyAuthorized` via management or emergencyAdmin | Role-Restricted |
| `setReferral(address)` | `src/Strategy.sol:128` | `onlyManagement` | Role-Restricted |

## `Strategy4626`

| Function | File:Line | Access | Classification |
|----------|-----------|--------|----------------|
| `manualRedeem(uint256)` | `src/Strategy4626.sol:103` | `onlyEmergencyAuthorized` via management or emergencyAdmin | Role-Restricted |
| `manualUnwrap(uint256)` | `src/Strategy4626.sol:110` | `onlyEmergencyAuthorized` via management or emergencyAdmin | Role-Restricted |

## `Strategy4626Factory`

| Function | File:Line | Access | Classification |
|----------|-----------|--------|----------------|
| `newStrategy4626(address)` | `src/Strategy4626Factory.sol:43` | Anyone; rejects already deployed vault | Public (Unrestricted) |
| `setAddresses(address,address,address,address)` | `src/Strategy4626Factory.sol:72` | `require(msg.sender == management)` | Role-Restricted |

## `StrategyAprOracle`

| Function | File:Line | Access | Classification |
|----------|-----------|--------|----------------|
| `transferGovernance(address)` | `lib/tokenized-strategy-periphery/src/utils/Governance.sol:35` | `onlyGovernance`, nonzero new governance | Role-Restricted |
