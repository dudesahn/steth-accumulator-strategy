# Attack Path Analysis: CS-351C58EB-003

## Title

Donated loose stETH/wstETH can exceed downstream ERC4626 maxDeposit and revert maintenance flows

## Attack Path

1. Any external account transfers stETH or wstETH directly to the `Strategy4626` address.
2. The strategy's `availableDepositLimit` limits new WETH acceptance using the downstream vault's `maxDeposit(address(this))`.
3. During report, tend, deposit deployment, or manual stake, `Strategy4626._stake` wraps all loose stETH and then deposits the entire loose wstETH balance into the downstream vault.
4. If the donated loose wstETH balance exceeds the downstream vault's current `maxDeposit`, `vault.deposit` reverts and blocks the maintenance flow.

## Facts

- Service mapping: `Strategy4626` maintenance flow crossing WETH, stETH, wstETH, and a downstream ERC4626 vault.
- Entry points: direct ERC20 donations are permissionless; the reverting deposit is triggered by normal keeper/management/deposit maintenance calls.
- Trust boundary: the attacker cannot call `_stake` directly, but can alter the strategy's token balance before an authorized maintenance call.
- Reachability: the disposable Foundry PoC copied the target code, donated loose wstETH, bounded the mock vault's max deposit, and observed the expected ERC4626 max-deposit revert.
- Existing controls: `availableDepositLimit` checks `vault.maxDeposit`, but only for the new WETH deposit limit, not for the actual loose wstETH amount passed to `vault.deposit`.

## Counterevidence

The attacker must donate value and needs an authorized maintenance call to trigger the revert. Existing emergency methods can redeem or unwrap balances in some states. These factors constrain impact to availability/griefing rather than theft, but they do not remove the unauthenticated donation boundary or the direct PoC.

## Severity Calibration

- Impact: medium. The bug can block deposits, reports, tends, or manual staking for affected vault configurations and force operator intervention.
- Likelihood: high. Direct token transfers are permissionless and a very small donation can be enough when `maxDeposit` is zero or nearly exhausted.
- Matrix result: medium.

## Final Policy Decision

`report`. Emit as a medium-severity donation-griefing and ERC4626 limit-bypass finding.
