# Blind lane 1 — accounting, exits, losses, and emergency behavior

## Scope and provenance

- Review object: `/Users/dudesahn/.codex/worktrees/8c5a/steth-accumulator-strategy`
- Exact strategy commit: `4580174c60ccac4658d97b02f0951aec92b218b2`
- State at lane start: detached HEAD (empty `git symbolic-ref -q --short HEAD` output); the only root status entry was the shared run directory, `?? .review-output/`.
- Exact inherited TokenizedStrategy gitlink: `82806289f967590c4efbf6bc3d237e4e7f0a0966`; submodule `git status --short` was empty before inherited-code inspection.
- Exact periphery gitlink: `fc1b1d4ab5c9a0b65b7ac785734c404d3742317a`; submodule `git status --short` was empty before inherited-code inspection.
- Evidence boundary: committed source/tests/config at the hashes above only. No issue comments, manual report, audit output, other lane output, history, later commits, deployment evidence, or external known findings were read.
- Proof grades: source `exact_commit`; tests `local_run_no_artifact` (temporary Foundry build/cache paths under `/tmp`); deployed/live config `not_checked`; destination state `not_checked` in this lane.

## Mechanics and denomination map

| Path | Denomination / position | Actual movement and accounting | Failure / shortfall behavior |
| --- | --- | --- | --- |
| Deposit/deploy | User deposits WETH; strategy receives stETH, wraps to wstETH, then deposits wstETH into the downstream ERC-4626 vault | `BaseLSTAccumulator._deployFunds` calls `_stake`; `Strategy4626._stake` performs WETH -> ETH -> stETH -> wstETH -> vault shares. TokenizedStrategy increments stored `totalAssets` by deposited WETH. | Deposit reverts atomically if staking/wrapping/vault deposit fails. Any loose WETH already present is included in TokenizedStrategy's deployment callback and can also be re-deployed. |
| Report | `estimatedTotalAssets = loose WETH + discounted stETH-equivalent value of loose stETH, loose wstETH, and vault shares` | Vault shares are converted to wstETH with `vault.convertToAssets`, then to stETH units with `wstETH.getStETHByWstETH`; `reportBuffer` haircuts deployed value. | Report is blocked while `pendingRedemptions != 0`. Otherwise it first stakes loose WETH, even after shutdown, before returning the accounting value. |
| User withdraw/redeem | Only loose WETH is immediately withdrawable | `availableWithdrawLimit` returns `balanceOfAsset()`; `_freeFunds` does nothing. | Conservative liquidity view: stETH/wstETH/vault shares are not advertised as liquid. Management must free WETH first. Standard `redeem` permits 100% loss, but this strategy's max-redeem view normally restricts calls to existing WETH. |
| Manual free | Requested amount starts in stETH-value units | `Strategy4626._freeStETH` uses loose stETH, then loose wstETH, then up to `vault.maxRedeem`; the swap is clamped to actual stETH held. | Partial downstream exit causes a partial swap rather than requested-as-actual accounting. The TokenizedStrategy stored `totalAssets` is not updated until a later report. |
| Queue withdrawal | Request amount and `pendingRedemptions` are stETH units; claim return is actual ETH/WETH | stETH is transferred to the Lido queue and ceases to be included in `estimatedTotalAssets`; report remains blocked. Claim wraps received ETH to WETH. | The normal return payload is incompatible with the normal claim decoder (A-03). Aggregate pending is decremented by actual ETH, not requested stETH (C-02). |
| Shutdown/emergency | Emergency amount is WETH/stETH-value units | `Strategy4626._emergencyWithdraw` frees wstETH/vault assets to stETH, then swaps available stETH to WETH with the configured report buffer. | Emergency movement deliberately does not update stored accounting. Report and tend remain callable, but this child re-deploys the freed WETH (A-01). |

## Finding summary

| ID | Status | Severity | Impact x likelihood | Title |
| --- | --- | --- | --- | --- |
| A-01 | validated | High | High x Medium | Report or tend after shutdown can re-deploy all emergency-freed principal into stETH and the downstream vault |
| A-02 | validated | Medium | Medium x Medium | Pending queue claims disappear from the deposit-limit basis, allowing the configured cap to be refilled and repeatedly exceeded |
| A-03 | validated API/path incompatibility | Medium | Medium x Medium | The initiation return payload decodes as request ID 32 in the normal scalar claim path |
| C-01 | plausible/conditional consequence | Medium | Medium x Medium | Out-of-band swap loss can be shifted from early redeemers to remaining shareholders before it is reported |
| C-02 | plausible/conditional | Low | Low x Medium | Subtracting actual ETH from requested-stETH pending accounting can leave reports stuck after a haircut or rounding shortfall |

## Validated findings

### A-01 — Report or tend after shutdown can re-deploy all emergency-freed principal into stETH and the downstream vault

**Severity:** High (`Impact: High`, `Likelihood: Medium`).

**Source path**

1. TokenizedStrategy intentionally leaves `report` and `tend` enabled after shutdown so the child can perform final maintenance and record losses: pinned `lib/tokenized-strategy/src/TokenizedStrategy.sol:1325-1333`.
2. The inherited author guidance explicitly says a child should check `TokenizedStrategy.isShutdown()` before re-deploying in `_harvestAndReport`: pinned `lib/tokenized-strategy/src/BaseStrategy.sol:204-229`. Its emergency-withdraw guidance separately warns that a later report must not simply re-deploy freed funds: `BaseStrategy.sol:334-355`.
3. This child does not make that check. `BaseLSTAccumulator._harvestAndReport` always calls `_stake` on loose WETH before accounting (`src/BaseLSTAccumulator.sol:136-146`), `_tend` always calls `_stake` on all idle WETH (`:158-160`), and `_tendTrigger` has no shutdown guard (`:162-165`).
4. In the target 4626 strategy, `_stake` converts the WETH to stETH, wraps all stETH to wstETH, and deposits all wstETH into the external vault (`src/Strategy4626.sol:29-42`).

**Impact**

- A keeper report or tend can reverse an emergency exit and re-expose the full freed balance to Lido and the exact downstream vault the shutdown may be responding to.
- `tendTrigger` can continue advertising this action when its amount/gas thresholds are met.
- A report is the documented mechanism for recording the profit/loss realized by `emergencyWithdraw`, but the default report path cannot both preserve WETH liquidity and update accounting. Management can first set `depositLimit = 0`, but that is an undocumented, multi-transaction operational workaround and is not enforced by source or tests.
- Outside shutdown, a new deposit also invokes `deployFunds` with the strategy's *entire* loose WETH balance (pinned `TokenizedStrategy.sol:954-972`), so liquidity created by `manualSwapToAsset` can be re-staked by an intervening deposit while capacity remains.

**Evidence and missing regression**

- Focused committed test `test_harvestStakesBypassesStakeAssetFlag` passed and confirms that report deliberately stakes idle WETH even when `stakeAsset == false`; source shows shutdown does not change this path.
- The committed shutdown suite passes only because it calls `emergencyWithdraw` and then immediately redeems; it never calls report/tend after shutdown (`src/test/Shutdown.t.sol:18-144`).
- Smallest regression: deposit -> shutdown -> emergency withdraw -> assert WETH idle -> call `report` and separately `tend` -> assert WETH remains idle, no stETH/wstETH/vault shares increase, and final loss can be recorded.

**Suggested resolution**

Gate deployment behavior on `!TokenizedStrategy.isShutdown()` in `_harvestAndReport`, `_tend`, and `_tendTrigger`; after shutdown, report should only claim/sell as intentionally allowed and return accounting without staking loose asset. Also protect manually freed withdrawal liquidity from the full-balance deployment callback or define/enforce an atomic operational state for manual exits.

### A-02 — Pending queue claims disappear from the deposit-limit basis, allowing the configured cap to be refilled and repeatedly exceeded

**Severity:** Medium (`Impact: Medium`, `Likelihood: Medium`).

**Source path**

1. `initiateLSTWithdrawal` increments `pendingRedemptions` in stETH-value units and transfers the stETH to the external queue (`src/BaseLSTAccumulator.sol:239-247`; `src/Strategy.sol:87-99`).
2. `estimatedTotalAssets` counts only WETH plus currently held LST value and never adds `pendingRedemptions` or the queue claim (`src/BaseLSTAccumulator.sol:171-185`).
3. The configured strategy cap is enforced as `depositLimit - estimatedTotalAssets` (`:89-96`) and is exposed by `availableDepositLimit` (`:119-121`). Report being blocked while pending (`:136-138`) does not block deposits or further queue initiations.
4. For Strategy4626, the additional downstream check is only current `vault.maxDeposit` (`src/Strategy4626.sol:55-60`). Redeeming vault shares into a queue request can reopen downstream room at the same time the queued principal disappears from the strategy cap basis.

**Concrete sequence**

- Set `depositLimit = 100 WETH`; fill it.
- Queue the approximately 100 stETH principal. ETA falls toward zero while stored TokenizedStrategy `totalAssets` remains 100 and `pendingRedemptions` becomes approximately 100.
- `availableDepositLimit` reopens toward 100, so another 100 WETH can be deposited and deployed.
- Management can queue the refill again before resolving the first request; pending grows while the configured 100-WETH cap can reopen again.

This does not misprice new shares because TokenizedStrategy's stored `totalAssets` remains stale-high while reports are blocked; the failure is that the risk/TVL cap does not include a principal-bearing queue claim and can be exceeded, potentially repeatedly.

**Missing regression and resolution**

- There is no committed test that asserts `availableDepositLimit` remains reduced by pending principal.
- Smallest regression: fill cap -> initiate withdrawal -> assert `availableDepositLimit == 0` (modulo realized haircut), attempt refill and expect revert; repeat with multiple request IDs.
- Include a conservative asset-denominated value for pending claims in the cap basis, or use a cap basis that cannot lose principal merely because its representation moved from stETH to a queue claim.

### A-03 — The initiation return payload decodes as request ID 32 in the normal scalar claim path

**Severity:** Medium (`Impact: Medium`, `Likelihood: Medium`). Severity reflects delayed access/reporting rather than permanent loss because an emergency batch-claim path exists.

**Source path**

- `_initiateLSTWithdrawal` receives `uint256[] requestIds` and returns `abi.encode(requestIds)` (`src/Strategy.sol:90-99`).
- `_claimLSTWithdrawal` decodes its bytes as a scalar `uint256` (`src/Strategy.sol:101-108`).
- ABI encoding a dynamic array begins with a `0x20` offset. Passing the returned bytes directly therefore invokes `claimWithdrawal(32)`, not the returned request ID (unless the actual ID coincidentally equals 32).

**Reproduction**

```text
$ cast abi-encode 'f(uint256[])' '[12345]'
0x000...020000...001000...03039

$ cast abi-decode 'f()(uint256)' 0x000...020000...001000...03039
32
```

The committed tests conceal the incompatibility by decoding the returned array and re-encoding its first element before the claim, e.g. `src/test/WithdrawalQueue.t.sol:72-80`, `:104-117`, and `:133-147`. Consequently the 7/7 passing queue suite is not an exact regression for forwarding the initiation result.

**Impact and resolution**

Normal automation that treats `returnData`/`claimData` as composable will target the wrong request, normally reverting and leaving `pendingRedemptions` nonzero; report remains blocked. Return `abi.encode(requestIds[0])`, accept/decode the array in the claim function, or expose a typed request ID and add a test that forwards the exact returned bytes without transformation.

## Plausible / conditional concerns

### C-01 — Out-of-band swap loss can be shifted from early redeemers to remaining shareholders before it is reported

`manualSwapToAsset` and `emergencyWithdraw` can realize Curve slippage but do not update stored TokenizedStrategy `totalAssets`; inherited documentation makes the latter explicit (`BaseStrategy.sol:342-355`, `TokenizedStrategy.sol:1343-1364`). `availableWithdrawLimit` immediately exposes the actual WETH, while TokenizedStrategy converts shares using stale stored assets and treats a withdrawal as lossless whenever idle WETH covers the stale requested amount (`TokenizedStrategy.sol:894-938`, `:989-1049`).

Example: two users each own 50 of 100 shares; liquidation returns 90 WETH but stored assets remain 100. The first user can redeem 50 shares for 50 WETH. Only 40 WETH remains for the second user's 50 shares, concentrating the entire 10-WETH loss on the second user instead of 5 WETH each. This is transaction-order exploitable around a visible manual/emergency swap. A timely report would normally synchronize PPS, but A-01 means default report re-deploys the WETH; even with a shutdown guard, emergency exit and report remain separate transactions. Exact severity depends on Curve loss, profit-lock state, operator sequencing, and whether the upstream vault rather than end users owns all strategy shares.

Required proof: a two-holder regression with forced swap shortfall, one redemption before report, and comparison to pro-rata loss after a safe report.

### C-02 — Subtracting actual ETH from requested-stETH pending accounting can leave reports stuck after a haircut or rounding shortfall

`pendingRedemptions` is increased by requested stETH (`src/BaseLSTAccumulator.sol:242-246`) but decreased by `_redeemedAmount`, which is the ETH balance delta returned by the queue (`src/Strategy.sol:103-111`; `BaseLSTAccumulator.sol:249-255`). If a finalized request returns less ETH than requested stETH because of a protocol haircut, negative rebase/slashing, or denomination rounding, a fully claimed request leaves residual pending and all reports continue reverting. Management/emergency roles can clear the residue (`BaseLSTAccumulator.sol:258-264`; `Strategy.sol:114-125`), so this is a liveness/operations concern, not proven permanent loss. Exact Lido behavior under those states is destination-protocol evidence outside this lane.

## Rejected / downgraded leads

| Lead | Disposition | Reason |
| --- | --- | --- |
| Vault-share denomination is added directly to stETH | rejected | `vault.convertToAssets` first yields wstETH, and `_stETHValue` converts the combined wstETH to stETH units (`src/Strategy4626.sol:71-76`). |
| Partial vault exit is treated as the full requested amount | rejected | `_freeStETH` adds the actual return from `vault.redeem`, then `_swapLSTToAsset` clamps the swap to actual stETH balance (`src/Strategy4626.sol:79-98`, `:44-47`). Emergency also recomputes/clamps from actual held stETH. |
| Withdraw views overstate downstream liquidity | rejected | `availableWithdrawLimit` exposes only loose WETH and `_freeFunds` intentionally does nothing (`src/BaseLSTAccumulator.sol:108-134`). This is conservative, though operationally illiquid. |
| Pending claims can be silently omitted by an ordinary report | rejected for ordinary path | `require(pendingRedemptions == 0)` blocks report. Mis-accounting can still be forced by the explicit emergency clear functions. |
| `stakeAsset = false` being ignored by report is itself an unambiguous bug | downgraded | A committed test explicitly specifies report-time bypass (`src/test/StethSpecific.t.sol:332-354`). It remains relevant to A-01 because it is not a shutdown safety switch. |
| Report buffer opening cap room | downgraded / intended by tests | `src/test/StethSpecific.t.sol:393-417` expressly expects the haircut to create deposit room. This is a management-selected exposure interpretation, distinct from A-02's omission of a principal claim. |
| Unwrapping all loose wstETH in `_freeStETH` loses assets | rejected | It can over-unwind the position form but does not discard value; the final swap remains requested/actual clamped and excess stays as stETH. |

## Tests and reproducible evidence

All successful Foundry runs used the exact pinned source and gitlinks, temporary build/cache paths, and the latest mainnet state served by `https://ethereum.publicnode.com`; therefore they are source-path evidence, not deployment-parity evidence. The observed fork blocks ranged from `25533231` to `25533242`.

| Exact command | Result |
| --- | --- |
| `env FOUNDRY_OUT=/tmp/steth-accumulator-lane1-out FOUNDRY_CACHE_PATH=/tmp/steth-accumulator-lane1-cache forge test --offline --match-contract WithdrawalQueueTest -vv --fork-url https://ethereum.publicnode.com` | 7 passed, 0 failed. Tests transform array payload to scalar and do not cover A-03. |
| `env FOUNDRY_OUT=/tmp/steth-accumulator-lane1-out FOUNDRY_CACHE_PATH=/tmp/steth-accumulator-lane1-cache forge test --offline --match-contract Strategy4626Test -vv --fork-url https://ethereum.publicnode.com` | 5 passed, 0 failed (256 fuzz runs for each of four fuzz tests). No shutdown+report/tend test, pending-cap test, or loss-socialization test. |
| `env FOUNDRY_OUT=/tmp/steth-accumulator-lane1-out FOUNDRY_CACHE_PATH=/tmp/steth-accumulator-lane1-cache forge test --offline --match-contract OperationTest -vv --fork-url https://ethereum.publicnode.com` | 8 passed, 0 failed (256 fuzz runs for each fuzz test). Manual swap is immediately followed by redeem; no intervening deposit/report or multi-user loss case. |
| `env FOUNDRY_OUT=/tmp/steth-accumulator-lane1-out FOUNDRY_CACHE_PATH=/tmp/steth-accumulator-lane1-cache forge test --offline --match-contract ShutdownTest -vv --fork-url https://ethereum.publicnode.com` | 3 passed, 0 failed (256 fuzz runs each). No post-shutdown report/tend. |
| `env FOUNDRY_OUT=/tmp/steth-accumulator-lane1-out FOUNDRY_CACHE_PATH=/tmp/steth-accumulator-lane1-cache forge test --offline --match-test test_harvestStakesBypassesStakeAssetFlag -vv --fork-url https://ethereum.publicnode.com` | 1 passed, 0 failed; confirms report stakes idle WETH despite the flag. |
| `cast abi-encode 'f(uint256[])' '[12345]'` then `cast abi-decode 'f()(uint256)' <encoded>` | Encoded first word is `0x20`; scalar decode output is `32`. |

Two preliminary runs are not claimed green: without `--offline`, Foundry compiled then crashed in macOS `system-configuration` before tests; with `--offline` but no fork, compilation succeeded but `WithdrawalQueueTest.setUp()` reverted because mainnet code was absent. Running the fork commands outside the restricted sandbox resolved the environment issue.

## Missing evidence / questions for synthesis

- No deployed/live role or configuration snapshot: actual `open`, `allowed`, `depositLimit`, `reportBuffer`, keeper automation, shutdown runbook, and downstream `maxDeposit/maxRedeem` policies are unknown.
- No historical block is pinned by the repository test configuration; successful fork runs used current mainnet state and cannot establish audit-era destination behavior.
- No exact PoC test file was added because this lane was restricted to writing this single artifact. Source paths plus the ABI CLI reproduction validate A-03; A-01/A-02 need the minimal regressions specified above for executable harm coverage.
- Destination-protocol evidence needed from its lane: Lido claim ownership/revert behavior for a wrong request ID, claim amount behavior under haircut/slashing/rounding, and vault behavior under pause/partial exit.
- Ask before the later comparison: was the intended operator contract/API expected to forward `initiateLSTWithdrawal` bytes directly, or explicitly decode the returned array and re-encode one ID? Is there a documented shutdown sequence that sets `depositLimit = 0`, disables keeper automation, performs emergency exit, and reports loss before enabling redemptions?

## Training extraction notes

- `blind_agent_found`: when a parent framework deliberately permits report/tend after shutdown, prove the child is shutdown-aware before considering emergency exit complete.
- `blind_agent_found`: cap accounting must follow principal across tokenized and async claim representations; blocking reports does not make omission from deposit limits safe.
- `blind_agent_found`: generic `bytes returnData`/`bytes claimData` APIs require an exact round-trip test; decode/re-encode in tests can hide a non-composable production interface.
- Negative/finality label for this lane: `source_replay_complete_not_deployment_ready`; live configuration and destination state remain unverified.
