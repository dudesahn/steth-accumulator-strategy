# Validation Report: CS-351C58EB-003

Title: Donated loose stETH/wstETH can exceed downstream ERC4626 `maxDeposit` and revert maintenance flows.

Disposition: `reportable`

Confidence: `0.88`

## Rubric

- [x] Untrusted token donation source is plausible.
- [x] Keeper/management maintenance entrypoint reaches `_stake`.
- [x] `availableDepositLimit` caps only new WETH deposits, not full loose wstETH balance.
- [x] `vault.deposit(wstETHBalance, address(this))` is the reverting sink.
- [x] Dynamic PoC demonstrates the wstETH donation path against copied target code.

## Evidence

`src/Strategy4626.sol:32-41` wraps all loose stETH and deposits all loose wstETH. `src/Strategy4626.sol:55-63` caps only the new deposit availability returned to callers. `src/BaseLSTAccumulator.sol:146-154` reaches `_stake` during report and `src/BaseLSTAccumulator.sol:165-166` reaches `_stake` during tend. OpenZeppelin ERC4626 reverts when `assets > maxDeposit(receiver)`.

The disposable PoC under `validation_artifacts/repro/src/test/MaxDepositDonationPoC.t.sol` deploys the original `Strategy4626` against a bounded wstETH ERC4626 vault, donates 2 WSTETH to the strategy while the vault cap is 1 WSTETH, and confirms `strategy.tend()` reverts with `ERC4626: deposit more than max`.

## Counterevidence and Gaps

This is an availability/accounting griefing issue, not theft. The attacker must donate stETH or wstETH and the later triggering call is keeper/management-gated. If the downstream vault has unlimited or ample `maxDeposit`, the issue does not trigger. Severity depends on live headroom and donation cost for intended vaults.

## Closure

The wstETH donation path is dynamically validated and the stETH path follows from the same wrapping branch. The candidate survives as reportable.
