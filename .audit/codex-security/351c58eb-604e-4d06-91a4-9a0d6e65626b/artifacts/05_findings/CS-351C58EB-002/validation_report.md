# Validation Report: CS-351C58EB-002

Title: `stakeAsset` disable switch is bypassed by keeper report and tend paths.

Disposition: `reportable`

Confidence: `0.82`

## Rubric

- [x] Management-controlled source and keeper entrypoint are identified.
- [x] `_deployFunds` applies `stakeAsset`, while `_harvestAndReport` and `_tend` do not.
- [x] Existing fork test confirms report stakes idle WETH after `stakeAsset=false`.
- [x] Direct `tend()` path is statically reachable and has no deposit-limit or `stakeAsset` guard.
- [x] Keeper trust and design-intent ambiguity are recorded as counterevidence.

## Evidence

`src/BaseLSTAccumulator.sol:109-112` checks `stakeAsset` before deposit-time staking. `src/BaseLSTAccumulator.sol:146-153` stakes loose WETH during report without checking `stakeAsset`; `src/BaseLSTAccumulator.sol:165-166` stakes `_totalIdle` during tend without checking `stakeAsset`. `src/BaseLSTAccumulator.sol:203-206` exposes a management setter whose notice says it controls whether the strategy stakes during harvest.

The focused fork test `test_harvestStakesBypassesStakeAssetFlag` passed. The test sets `stakeAsset=false`, deposits WETH that remains idle, then keeper `report()` stakes it into stETH.

## Counterevidence and Gaps

The path is keeper/management-gated, not public. The report path is bounded by `availableDepositLimit(address(this))`; management can mitigate indirectly with deposit limits or keeper changes. One state-variable comment describes deposit staking, which weakens certainty if maintainers intended the flag to be deposit-only. No external design note was available to settle intent.

## Closure

The behavior is confirmed and survives as a management-control bypass with bounded, role-gated impact. Final severity should be lower than public loss findings.
