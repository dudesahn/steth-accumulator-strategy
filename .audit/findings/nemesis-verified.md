# Nemesis Audit - Verified Findings

## Scope
- Target repo: `/Users/dudesahn/Documents/GitHub/codex/review/steth-accumulator-strategy`
- HEAD: `521fff28ad978a37115be8995a1d631611fa1d3d`
- Dirty state at start: `?? .audit/`
- In-scope files: `src/BaseLSTAccumulator.sol`, `src/Strategy.sol`, `src/Strategy4626.sol`, `src/Strategy4626Factory.sol`, `src/periphery/StrategyAprOracle.sol`, `src/interfaces/*.sol`
- Out-of-scope files: tests except for context/verification, scripts, broadcasts, dependencies, generated/untracked audit artifacts
- Verification limits: no fixes were made; Medium+ promotion required PoC or strong trace, and no Medium/Critical/High issues were confirmed. Fork tests used `https://ethereum.publicnode.com`.

## Recon Summary
- Attack goals: stale accounting, exit denial, incorrect loss/profit reports, allocator misdirection, stuck Lido queue redemptions.
- Novel code: LST accumulator accounting, stETH route choice, pending redemption accounting, Strategy4626 vault wrapping, Strategy4626 factory, APR oracle.
- Value stores: WETH, stETH, wstETH, ERC4626 vault shares, Lido queue claims, TokenizedStrategy `totalAssets`.
- Complex paths: deposit -> stake/wrap/vault deposit; report -> health check -> restake/report; queue initiation -> claim -> pending clear -> report; shutdown/emergency withdraw; factory role initialization.
- Initial coupled-state hypothesis: reported assets must stay coherent with WETH/LST/vault/queue state; `pendingRedemptions` must track claimable queue value; BPS parameters must stay in range; APR must reflect strategy state if used for allocation.

## Pass Summary
| Pass | Auditor | Scope | New findings | Notes |
| ---- | ------- | ----- | ------------ | ----- |
| 1 | Feynman | Entry points, assumptions, multi-tx paths | 3 promoted, 2 downgraded | Focused on report/deposit/withdraw/queue/oracle/factory behavior |
| 2 | State inconsistency | Coupled-state and mutation matrix | 3 promoted | `reportBuffer`, claim data shape, APR-state coupling |
| 3 | Feynman feedback | State-pass root causes | 0 | Confirmed no Medium+ path from promoted lows |
| 4 | State feedback | Propagation and masking checks | 0 | Converged |

## Verified Findings

### NEM-001: Report Buffer Can Be Set Above Its BPS Denominator
**Severity:** Low
**Discovery Path:** Cross-feed Pass 1 -> Pass 2
**Verification:** Code trace
**Affected Code:** `src/BaseLSTAccumulator.sol:177`, `src/BaseLSTAccumulator.sol:198`

**Root Cause:**
`setReportBuffer()` accepts any `uint256`, but `estimatedTotalAssets()` subtracts `reportBuffer` from `MAX_BPS`. Values above 10,000 are not meaningful buffers and cause a Solidity 0.8 underflow.

**Trigger Sequence:**
1. Management calls `setReportBuffer(10_001)` or any value above `MAX_BPS`.
2. A caller invokes `estimatedTotalAssets()`, `availableDepositLimit()`, or keeper `report()`.
3. `MAX_BPS - reportBuffer` underflows and the call reverts.

**Impact:**
Management misconfiguration can temporarily break accounting views, deposit-limit checks, and reports. Management can recover by resetting the buffer, so this is an operational DoS/footgun rather than direct fund loss.

**Fix:**
Require `_reportBuffer <= MAX_BPS` in `setReportBuffer()`. Consider a tighter protocol-level maximum if only small discount buffers are intended.

**Verification Evidence:**
Static trace:
- `estimatedTotalAssets()` computes `balanceOfAsset() + ((valueOfLST() * (MAX_BPS - reportBuffer)) / MAX_BPS)`.
- `setReportBuffer()` stores `_reportBuffer` without a bound.
- Existing tests cover normal buffers but not invalid values above `MAX_BPS`.

### NEM-002: Withdrawal Initiation Return Bytes Do Not Match Normal Claim Bytes
**Severity:** Low
**Discovery Path:** Cross-feed Pass 1 -> Pass 2
**Verification:** Static ABI trace plus existing test behavior
**Affected Code:** `src/Strategy.sol:97`, `src/Strategy.sol:104`, `src/interfaces/IBaseLSTAccumulator.sol:40`

**Root Cause:**
`initiateLSTWithdrawal()` returns untyped bytes containing `abi.encode(uint256[] requestIds)`, while `claimLSTWithdrawal(bytes)` ultimately decodes its bytes as a single `uint256`. The interface does not make this transformation explicit.

**Trigger Sequence:**
1. Management calls `initiateLSTWithdrawal(amount)` and receives `returnData`.
2. Keeper/operator later calls `claimLSTWithdrawal(returnData)` directly.
3. `_claimLSTWithdrawal()` decodes the first ABI word as a scalar request id. For an encoded dynamic array, that first word is the offset `0x20`, so the decoded id is `32` rather than `requestIds[0]`.

**Impact:**
The normal claim can revert or target the wrong request id, leaving `pendingRedemptions` nonzero and blocking reports until a privileged manual claim/clear path is used. Existing tests avoid this by decoding the returned array and re-encoding `requestIds[0]`.

**Fix:**
Make the API typed or align the bytes shape. Options:
- return and accept `uint256[] requestIds`;
- return `abi.encode(requestIds[0])` while only one request is supported;
- store outstanding request ids on-chain and validate claim input against them.

**Verification Evidence:**
- `src/Strategy.sol:97-99` encodes the `uint256[]` returned by Lido's queue.
- `src/Strategy.sol:104-108` decodes claim data as `uint256`.
- `src/test/WithdrawalQueue.t.sol:72-80` decodes `returnData` as `uint256[]` and passes `abi.encode(requestIds[0])`, proving the hidden convention.
- `cast abi-encode "f(uint256[])" "[1]"` shows the first data word is `0x20`; `cast --to-dec 0x20` returns `32`.

### NEM-003: APR Oracle Returns A Constant Positive APR For Every Strategy And Delta
**Severity:** Low
**Discovery Path:** Cross-feed Pass 1 -> Pass 2
**Verification:** Code trace
**Affected Code:** `src/periphery/StrategyAprOracle.sol:28`

**Root Cause:**
`aprAfterDebtChange(address _strategy, int256 _delta)` ignores both inputs and always returns `4e16`.

**Trigger Sequence:**
1. Allocation tooling queries the oracle for a strategy.
2. The strategy may be shutdown, full, unable to deposit, idle, unsupported, or queried with a large positive `_delta`.
3. The oracle still returns a positive 4% APR.

**Impact:**
If this periphery oracle is wired into production debt allocation, it can mislead allocators into assigning debt where deployable yield is unavailable or materially different. No in-repo caller was found, so this remains a deployment-dependent Low.

**Fix:**
Either mark/exclude this oracle as non-production, or implement strategy-aware APR:
- return zero for shutdown/no-capacity states;
- account for `_delta`;
- read current deployable capacity and LST/vault yield source assumptions;
- add tests that APR changes with positive/negative debt changes.

**Verification Evidence:**
- `src/periphery/StrategyAprOracle.sol:28-32` ignores `_strategy` and `_delta`.
- `src/test/Oracle.t.sol:26-36` leaves delta-sensitive checks as TODOs and only asserts the constant is nonzero and below 100%.

## False Positives Eliminated
- Report-time staking while `stakeAsset=false`: existing test `test_harvestStakesBypassesStakeAssetFlag` confirms this as expected behavior, though the setter naming/comments could be clearer.
- Factory-created strategies with factory as current management: existing factory test confirms the intended pending-management acceptance flow.
- Emergency clearing of pending redemptions: source comments explicitly warn that losses may be realized on the next report.

## Downgraded Findings
- Factory `setAddresses()` has no zero-address checks or event. This can misconfigure future deployments, but it is management-only, obvious at deployment time, and not enough for a security finding without stronger impact.
- Strategy4626 `_freeStETH()` unwraps all loose wstETH after redeeming from the vault. This may free more stETH than requested, but downstream paths either swap/request only the requested amount or leave economically accounted LST in the strategy.

## Test Evidence
- `env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-path src/test/WithdrawalQueue.t.sol -vv --fork-url https://ethereum.publicnode.com`: 7 passed.
- `env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-path src/test/Strategy4626.t.sol -vv --fork-url https://ethereum.publicnode.com`: 5 passed.
- `env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-path src/test/Operation.t.sol -vv --fork-url https://ethereum.publicnode.com`: 8 passed.
- `env ETH_RPC_URL=https://ethereum.publicnode.com forge test -vv --fork-url https://ethereum.publicnode.com`: 46 passed.

## Residual Risk
- No Critical, High, or Medium findings were confirmed.
- This pass did not use a bespoke PoC file because promoted issues were Low and trace-verifiable.
- Periphery APR impact depends on whether `StrategyAprOracle` is actually deployed or configured in allocator infrastructure.
- Existing tests validate the current withdrawal convention, but they do not prevent integrators from passing initiation return bytes directly to the claim function.
