# Nemesis Feynman Pass - Raw Hypotheses

## Scope Snapshot
- Repo: `/Users/dudesahn/Documents/GitHub/codex/review/steth-accumulator-strategy`
- HEAD: `521fff28ad978a37115be8995a1d631611fa1d3d`
- Dirty state at start: `?? .audit/`
- Production scope: `src/BaseLSTAccumulator.sol`, `src/Strategy.sol`, `src/Strategy4626.sol`, `src/Strategy4626Factory.sol`, `src/periphery/StrategyAprOracle.sol`, `src/interfaces/*.sol`
- Context-only scope: Yearn TokenizedStrategy/BaseStrategy and HealthCheck inheritance under `lib/`, tests under `src/test/`

## Recon
- Worst outcomes considered: stale accounting, unavailable exits, incorrect report/loss realization, debt allocator misallocation, management-only configuration traps, withdrawal queue liveness failure.
- Novel code: LST accumulation wrapper, stETH route choice, pending Lido redemption tracking, ERC4626-wrapped stETH variant, factory, placeholder APR oracle.
- Value stores: WETH idle balance, stETH balance, wstETH balance, ERC4626 vault shares, Lido withdrawal queue claims, TokenizedStrategy `totalAssets`.
- Complex paths: deposit -> `_deployFunds` -> stETH route; report -> health check -> `_harvestAndReport`; management queue initiation -> keeper claim -> report; Strategy4626 vault redeem/unwrap/swap; factory deployment into Yearn TokenizedStrategy roles.
- Initial coupling hypothesis: `totalAssets` must track WETH + LST/vault + queued redemptions; `pendingRedemptions` must track outstanding Lido queue claims; `reportBuffer` must stay within BPS bounds; oracle APR must reflect strategy/delta/capacity if used for allocation.

## FF-001: Unbounded report buffer can enter an underflowing accounting state
- Severity hypothesis: Low.
- Question: What if the management setter accepts a value outside the denominator used by accounting?
- Affected code path: `BaseLSTAccumulator.setReportBuffer()` writes `reportBuffer` without a cap, then `estimatedTotalAssets()` computes `MAX_BPS - reportBuffer`.
- Trigger sequence: management calls `setReportBuffer(10_001)`; any caller invokes `estimatedTotalAssets()`, `availableDepositLimit()`, or keeper `report()`.
- Why current code fails: Solidity 0.8 underflows on `MAX_BPS - reportBuffer`, so accounting views and report/deposit gating revert.
- State variables to feed into state pass: `reportBuffer`, `MAX_BPS`, `depositLimit`, `pendingRedemptions`, TokenizedStrategy `totalAssets`.
- Verification plan: Static trace sufficient for Low. Check existing tests for valid buffer coverage and absence of invalid-bound test.
- Status: Promoted as NEM-001.

## FF-002: Withdrawal initiation and claim bytes use different implicit encodings
- Severity hypothesis: Low.
- Question: Can the return data from initiating a withdrawal be passed back into the claim function as the API shape suggests?
- Affected code path: `initiateLSTWithdrawal()` returns `abi.encode(uint256[] requestIds)`, while `_claimLSTWithdrawal()` decodes `_claimData` as a single `uint256`.
- Trigger sequence: management calls `initiateLSTWithdrawal(amount)` and stores returned bytes; keeper later calls `claimLSTWithdrawal(returnData)` directly.
- Why current code fails: the first ABI word of an encoded dynamic array is the offset `0x20`, so a single-uint decode reads request id `32`, not `requestIds[0]`.
- State variables to feed into state pass: `pendingRedemptions`, Lido queue request id ownership, untyped `claimData`.
- Verification plan: Static ABI trace plus existing tests. Existing tests succeed only because they decode the returned array and re-encode `requestIds[0]`.
- Status: Promoted as NEM-002.

## FF-003: APR oracle returns a constant 4% for any strategy and debt delta
- Severity hypothesis: Low.
- Question: Why does the APR answer ignore the exact strategy, debt change, shutdown/capacity state, and LST/vault conditions?
- Affected code path: `StrategyAprOracle.aprAfterDebtChange(address,int256)` returns `4e16` unconditionally.
- Trigger sequence: a debt allocator or operator queries APR for a shutdown strategy, no-capacity strategy, unsupported strategy, or very large positive `_delta`.
- Why current code fails: the oracle does not inspect `_strategy`, `_delta`, deposit capacity, idle/deployed composition, Lido staking state, or external yield source APR.
- State variables to feed into state pass: strategy state, deposit capacity, shutdown, debt delta, external APR inputs.
- Verification plan: Static trace; existing oracle test only asserts non-zero and less than 100%, with TODOs for delta-sensitive behavior.
- Status: Promoted as NEM-003 if this periphery contract is considered runtime, with deployment-risk caveat.

## FF-004: `stakeAsset` does not prevent report-time staking
- Severity hypothesis: Low.
- Question: Does disabling the stake flag keep WETH idle across all automated paths?
- Affected code path: `_deployFunds()` checks `stakeAsset`; `_harvestAndReport()` always stakes `Math.min(balanceOfAsset(), availableDepositLimit(address(this)))`.
- Trigger sequence: management sets `stakeAsset=false`; a user deposits and WETH remains idle; keeper calls `report()`; idle WETH is staked anyway.
- Why current code fails or may not fail: the code comment/setter wording can imply harvest control, but tests explicitly assert report bypasses the flag.
- Verification plan: Existing `test_harvestStakesBypassesStakeAssetFlag` confirms behavior.
- Status: Downgraded to documentation/configuration hazard, not a verified security finding.

## FF-005: Factory deployment leaves management pending until explicit acceptance
- Severity hypothesis: Informational.
- Question: Can the factory-created strategy be managed immediately by the intended management address?
- Affected code path: `Strategy4626Factory.newStrategy4626()` deploys with factory as current management, then sets pending management.
- Trigger sequence: factory deploys a strategy; intended management has not yet called `acceptManagement()`.
- Why current code may not fail: tests assert this two-step state explicitly and the strategy can be accepted by the configured management.
- Verification plan: Existing factory tests.
- Status: Downgraded; expected Yearn two-step management pattern.
