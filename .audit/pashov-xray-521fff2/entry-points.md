# Entry Point Map

> stETH Accumulator Strategy | 17 first-party entry points | 1 permissionless | 15 role-gated | 1 self-gated callback surface

---

## Protocol Flow Paths

### Deployment

`Strategy4626Factory.newStrategy4626()` -> `new Strategy4626()` -> `Strategy4626.constructor()` -> `BaseStrategy.initialize()` -> role setters on the new strategy.

### User Flow

`[deployment above]` -> `TokenizedStrategy.deposit()/mint()` -> `BaseStrategy.deployFunds()` -> `BaseLSTAccumulator._deployFunds()` -> `Strategy._stake()` -> Lido submit or Curve stETH swap.

`[deposit above]` -> `TokenizedStrategy.withdraw()/redeem()` -> `availableWithdrawLimit()` limits exits to idle WETH.

### Keeper Flow

`[deposit above]` -> `TokenizedStrategy.report()` -> `BaseHealthCheck.harvestAndReport()` -> `BaseLSTAccumulator._harvestAndReport()` <- requires no pending Lido redemptions.

`[deposit above]` -> `TokenizedStrategy.tend()` -> `BaseLSTAccumulator._tend()` -> `Strategy._stake()`.

`[pending Lido withdrawal]` -> `claimLSTWithdrawal()` -> `Strategy._claimLSTWithdrawal()` -> WETH deposit.

### Management / Emergency Flow

`manualSwapToAsset()` -> `Strategy._swapLSTToAsset()` -> Curve stETH->ETH -> WETH deposit.

`initiateLSTWithdrawal()` -> `Strategy4626._freeStETH()` -> `Strategy._initiateLSTWithdrawal()` -> Lido queue request.

`manualRedeem()` / `manualUnwrap()` -> free wstETH/vault assets -> later `manualSwapToAsset()` or `initiateLSTWithdrawal()`.

---

## Permissionless

### `Strategy4626Factory.newStrategy4626(address _vault)`

| Aspect | Detail |
|--------|--------|
| Visibility | external |
| Caller | Anyone |
| Parameters | `_vault` (user-controlled) |
| Call chain | `Strategy4626Factory.newStrategy4626()` -> `Strategy4626.constructor()` -> TokenizedStrategy role setters |
| State modified | `deployments[_vault]`; new strategy TokenizedStrategy roles and fee/unlock config |
| Value flow | None |
| Reentrancy guard | No |

---

## Role-Gated

### Management

| Contract | Function | Parameters | State Modified / External Calls |
|----------|----------|------------|---------------------------------|
| BaseLSTAccumulator | `setReportBuffer(uint256)` | `_reportBuffer` (management-provided) | `reportBuffer` |
| BaseLSTAccumulator | `setStakeAsset(bool)` | `_stakeAsset` (management-provided) | `stakeAsset` |
| BaseLSTAccumulator | `setDepositLimit(uint256)` | `_limit` (management-provided) | `depositLimit` |
| BaseLSTAccumulator | `setOpenDeposits(bool)` | `_openDeposits` (management-provided) | `openDeposits` |
| BaseLSTAccumulator | `setAllowed(address,bool)` | address/status (management-provided) | `allowed[address]` |
| BaseLSTAccumulator | `setMinAmountToTend(uint256)` | `_minAmountToTend` (management-provided) | `minAmountToTend` |
| BaseLSTAccumulator | `setMaxGasPriceToTend(uint256)` | `_maxGasPriceToTend` (management-provided) | `maxGasPriceToTend` |
| BaseLSTAccumulator | `manualSwapToAsset(uint256,uint256)` | amount/minOut (management-provided) | Curve stETH->ETH, WETH deposit |
| BaseLSTAccumulator | `manualStake(uint256)` | amount (management-provided) | WETH withdraw, Lido submit or Curve ETH->stETH |
| BaseLSTAccumulator | `initiateLSTWithdrawal(uint256)` | amount (management-provided) | `pendingRedemptions += amount`, Lido queue request |
| BaseLSTAccumulator | `clearPendingRedemptions(uint256)` | amount (management-provided) | decreases `pendingRedemptions` |
| Strategy | `setReferral(address)` | referral (management-provided) | `referral` |
| Strategy4626Factory | `setAddresses(address,address,address,address)` | role addresses (management-provided) | factory deployment role defaults |

### Keeper / Management

| Contract | Function | Parameters | State Modified / External Calls |
|----------|----------|------------|---------------------------------|
| BaseLSTAccumulator | `claimLSTWithdrawal(bytes)` | encoded request id (keeper-provided) | Lido claim, WETH deposit, decreases `pendingRedemptions` |

### Emergency Authorized

| Contract | Function | Parameters | State Modified / External Calls |
|----------|----------|------------|---------------------------------|
| Strategy | `manualClaimWithdrawals(uint256[],uint256[],bool)` | request ids/hints/zero flag (emergency-provided) | Lido batch claim, optional `pendingRedemptions = 0`, WETH deposit |
| Strategy4626 | `manualRedeem(uint256)` | vault share amount (emergency-provided) | ERC4626 vault redeem |
| Strategy4626 | `manualUnwrap(uint256)` | wstETH amount (emergency-provided) | wstETH unwrap |

---

## Self-Gated Callback Surface

These functions are externally visible through BaseStrategy but gated by `onlySelf`, so the effective caller is the TokenizedStrategy delegatecall flow.

| Contract | Function | Caller Path | State / Value Effect |
|----------|----------|-------------|----------------------|
| BaseStrategy -> strategy override | `deployFunds(uint256)` | TokenizedStrategy deposit/mint | stakes idle WETH when `stakeAsset` and above dust |
| BaseStrategy -> strategy override | `freeFunds(uint256)` | TokenizedStrategy withdraw/redeem | no-op in this strategy |
| BaseHealthCheck -> strategy override | `harvestAndReport()` | TokenizedStrategy report | claims rewards, stakes idle WETH, returns ETA |
| BaseStrategy -> strategy override | `tendThis(uint256)` | TokenizedStrategy tend | stakes keeper-provided idle amount |
| BaseStrategy -> strategy override | `shutdownWithdraw(uint256)` | TokenizedStrategy emergencyWithdraw | swaps LST to WETH via Curve |

---

## View-Only

`availableDepositLimit`, `availableWithdrawLimit`, `estimatedTotalAssets`, `balanceOfWstETH`, `valueOfWstETH`, `aprAfterDebtChange`, `isDeployedStrategy`, and inherited ERC4626 views are structural read paths and excluded from state-changing entry-point counts.
