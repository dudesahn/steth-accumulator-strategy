# Lane 04 — Tests, invariants, operations, roles/configuration, and deployment assumptions

## Scope and provenance

- Review object: `steth-accumulator-strategy` at exact commit `4580174c60ccac4658d97b02f0951aec92b218b2`.
- Worktree: `/Users/dudesahn/.codex/worktrees/8c5a/steth-accumulator-strategy`.
- Lane start confirmation: `git rev-parse HEAD` returned the exact commit; `git symbolic-ref -q --short HEAD` returned no branch (detached); `git status --porcelain=v1` showed only the orchestrator-created untracked `.review-output/` directory. The root orchestrator separately recorded the pre-review clean state.
- Lane end confirmation: HEAD remained the exact detached commit and status still showed only `.review-output/`.
- Exact initialized dependency gitlinks used for compilation: `forge-std@fc560fa34fa12a335a50c35d92e55a6628ca467c`, `openzeppelin-contracts@bd325d56b4c62c9c5c1aff048c37c6bb18ac0290`, `tokenized-strategy@82806289f967590c4efbf6bc3d237e4e7f0a0966`, and `tokenized-strategy-periphery@fc1b1d4ab5c9a0b65b7ac785734c404d3742317a`.
- Reviewed only committed source, tests, dependency source at the pinned gitlinks, scripts, and CI/config needed for this lane. Did not read broadcast JSON, issue comments, audit/report artifacts, manual review, other agents' output, parent checkout content, history, branches, reflogs, stashes, or later fixes/deployment evidence.
- External state was limited to the fork test suite and one pinned, read-only Curve quote used to validate the emergency configuration assumption.
- Evidence grades: source `exact_commit`; tests `local_stdout_saved in this artifact (compact result), failed`; deployed code `unknown/not checked`; live config `not checked`; lifecycle `unknown`.

## Lane result

The suite has useful happy-path and fork coverage, but it is not green and contains no stateful invariant suite. More importantly, the tests and deployment paths expose two production gates: the standalone 4626 script never performs its advertised role handoff, and emergency withdrawal is not executable with the default zero `reportBuffer` at the sampled Curve state. The factory path avoids the first role bug but produces materially different fee/unlock configuration and still requires explicit role acceptance, strategy deposit permissioning, downstream-vault authorization, and emergency buffer configuration.

| ID | Classification | Severity (Impact x Likelihood) | Summary | Stop/go |
| --- | --- | --- | --- | --- |
| L4-V1 | validated deployment defect; conditional on using standalone `Deploy4626` | High (High x Medium) | Script declares/logs intended management but never sets pending management or any other role; deployer retains management, keeper, fee recipient, and no emergency admin is installed | block that deployment path |
| L4-V2 | validated operational/config defect | High (High x High for an unconfigured deployment) | Default emergency min-out is exact 1:1; current pinned Curve quote is below 1:1; only management can set the buffer that all emergency tests require | block attachment until configured/tested |
| L4-T1 | validated test defect, not a demonstrated fund-loss bug | Low (Low x High) | Full suite deterministically fails because `test_depositLimit` expects zero but 1 wei of capacity remains | fix CI assertion/rounding model |

## Validated findings

### L4-V1 — `Deploy4626` does not perform its advertised management handoff or role initialization

**Severity:** High (Impact High x Likelihood Medium). Applicability is conditional on the standalone `script/Deploy4626.s.sol` path being intended for production; the factory path does configure roles.

**Evidence and path:**

- `script/Deploy4626.s.sol:12-18` declares an intended `management` address but only calls `new Strategy4626(...)`.
- `script/Deploy4626.s.sol:20-28` logs that management is the declared address and says it must call `acceptManagement()`, but there is no preceding `setPendingManagement(management)` and no calls to `setKeeper`, `setEmergencyAdmin`, `setPerformanceFeeRecipient`, `setPerformanceFee`, or `setProfitMaxUnlockTime`.
- Pinned `lib/tokenized-strategy/src/BaseStrategy.sol:138-150` initializes management, performance-fee recipient, and keeper to `msg.sender`; `lib/tokenized-strategy/src/TokenizedStrategy.sol:466-470` stores those values. Emergency admin remains its zero default.
- Pinned `TokenizedStrategy.sol:1502-1517` requires current management to set pending management before that address can accept. Therefore the script's note is not merely incomplete documentation: the advertised `acceptManagement()` call reverts with `!pending`.
- The standalone deployment also retains TokenizedStrategy defaults of 10% performance fee and 10-day profit unlock, whereas `Strategy4626Factory.newStrategy4626` explicitly sets fee and unlock to zero (`src/Strategy4626Factory.sol:51-56`). There is no script smoke test or documented selection rule that makes this economic/config divergence intentional.
- The configured name is unrelated copy text, `"wstETH/yvUSD Morpho Lender Borrower Convertor"` (`script/Deploy4626.s.sol:14`), increasing operator ambiguity over which artifact is being deployed.

**Impact:** The broadcasting deployer, not the declared management/SMS, retains every management-only strategy control and keeper/report control; fees initially accrue to it; no separate emergency admin is installed. If the deployer key is discarded after following the misleading handoff note, management cannot be accepted and the strategy cannot be configured, permissioned, or manually unwound. If the deployer remains live, it retains powerful unexpected control over principal operations and arbitrary-min-out manual swaps.

**Smallest regression test:** Execute the deployment script against a fork and assert `management`, `pendingManagement`, `keeper`, `emergencyAdmin`, `performanceFeeRecipient`, `performanceFee`, `profitMaxUnlockTime`, `open/allowed`, and `reportBuffer` against an explicit manifest, then impersonate the intended management and prove `acceptManagement()` succeeds and clears pending management.

**Recommendation:** Either remove the standalone script if the factory is canonical, or make it apply the same explicit manifest as the factory plus pending-management handoff. Fail the script if any required address is zero or if a post-deploy readback differs. Treat management acceptance and post-accept config readback as attachment gates.

### L4-V2 — Emergency exit requires an undocumented management-only buffer; the default path is presently unexecutable

**Severity:** High (Impact High x Likelihood High for a deployment left at source/script defaults).

**Evidence and path:**

- `reportBuffer` is declared without a nonzero constructor assignment (`src/BaseLSTAccumulator.sol:33,41-58`), so the default is zero.
- Emergency withdrawal computes Curve `minOut = amount * (10_000 - reportBuffer) / 10_000` and swaps (`src/BaseLSTAccumulator.sol:148-155`). At zero buffer, this demands at least 1 ETH per stETH.
- Only management can change the buffer (`src/BaseLSTAccumulator.sol:192-195`). An emergency admin can call shutdown/emergency functions but cannot loosen this bound if management is unavailable.
- Every shutdown test silently supplies the missing operational precondition: `_setEmergencySwapBuffer()` impersonates management and sets 50 bps (`src/test/Shutdown.t.sol:7,13-16`), then tests call it immediately before `emergencyWithdraw` (`:35-45`, `:81-92`, `:132-139`). There is no regression that exercises source defaults.
- Neither standalone deployment script nor the factory sets `reportBuffer`.
- Reproducible state check at Ethereum block `25533225`:

  ```text
  cast call 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022 \
    "get_dy(int128,int128,uint256)(uint256)" 1 0 1000000000000000000 \
    --block 25533225 --rpc-url https://ethereum.publicnode.com
  => 999797856520084312
  ```

  This is less than the default emergency `minOut` of `1e18`, so a one-stETH default emergency swap would revert at that block. Larger exits can have at least as much price impact.

**Impact:** In the state where emergency withdrawal matters most (depeg or stressed liquidity), emergency admin alone cannot free principal. Recovery requires the management key/SMS to remain responsive and first modify a valuation parameter that also changes report accounting and deposit capacity. This couples emergency liveness to a separate actor and config change not encoded in deployment scripts.

**Smallest regression test:** Deposit, shutdown as emergency admin without changing defaults, mock/execute a Curve quote below 1:1, and assert the current emergency path reverts. Then apply the intended bounded buffer as management, prove emergency admin can fully/partially unwind, and assert realized output/loss and remaining positions. Add a deployment-manifest assertion that the production buffer is nonzero and within the approved bound before debt.

**Recommendation:** Make emergency slippage policy explicit and independent from report valuation policy, or ensure deployment atomically installs an approved nonzero bound. If emergency admin is expected to act without management, give it only a tightly bounded emergency slippage control or a separately bounded unwind method. Monitor Curve output against the configured threshold.

### L4-T1 — The pinned fork suite is red on an exact-zero rounding assertion

**Severity:** Low test-quality defect (Impact Low x Likelihood High); no material loss demonstrated.

- `src/test/StethSpecific.t.sol:239-246` deposits the computed remaining capacity and then requires `availableDepositLimit == 0` exactly.
- At current fork state, stETH rounding leaves `1` wei of reported capacity. The full and focused runs both fail with `Left: 1, Right: 0`.
- This is not evidence that deposits can exceed the configured economic limit materially; it is evidence that CI is not green and the test's exact-zero model is inconsistent with the token's rounding behavior.

Fix the test to assert a documented dust bound and add an invariant that estimated assets plus remaining capacity cannot exceed the configured limit by more than that bound. Decide whether sub-`ASSET_DUST` deposits should be accepted as idle WETH or rejected.

## Plausible / conditional concerns

### C1 — The downstream vault and upstream depositor permission gates are absent from deployment automation

- `src/test/utils/Setup4626.sol:21-22` creates an `ERC4626Mock` and immediately discards it for a live vault address. It then reads that vault's management and cheats the required authorization by impersonating management to call `setAllowed(strategy, true)` (`:24-43`).
- This proves the tests' successful deposits rely on privileged external configuration, not only the constructor's `vault.asset() == wstETH` check.
- The production deployment script does not authorize the new strategy in the destination vault. Separately, BaseHealthCheck starts `open == false`; only `allowed[address(this)]` is initialized (`src/BaseLSTAccumulator.sol:57`), and neither script/factory opens the strategy or allows the intended upstream vault/depositor.
- **Conditional harm:** first deployment/debt may revert or the strategy may remain unattached until both permission surfaces are configured. No live config/deployment evidence was allowed in this blind phase, so current observed state is unknown.
- **Gate:** before debt, read back destination `open/allowed(strategy)` and strategy `open/allowed(upstreamVault)` (or the exact expected owner semantics), then execute a real upstream deposit.

### C2 — The APR oracle test cannot detect the oracle's input-independent placeholder behavior

- `src/periphery/StrategyAprOracle.sol:28-32` ignores both strategy and debt delta and always returns 4%.
- `src/test/Oracle.t.sol:16-36` explicitly leaves debt-sensitivity assertions commented out; its only live assertions are `0 < APR < 100%` (`:20-24`). The fuzz test therefore passes for any fixed number in that range (`:51-60`).
- **Conditional harm:** if this example oracle is registered for allocation decisions, it can misprice strategy APR and route debt on a constant, unrelated estimate. No deployment/registration evidence was read, so this remains conditional.
- Require intended-use evidence. If production, test fixed strategy/debt samples and compare against the real yield source; otherwise exclude the example from deployable production artifacts.

### C3 — Factory role rotation is one-step and permits zero-address self-bricking

- `src/Strategy4626Factory.sol:64-75` immediately replaces all role/config addresses. `_management == address(0)` permanently removes the only caller able to update factory config; subsequent `newStrategy4626` calls also revert at `setPendingManagement(0)`.
- Tests cover only a valid happy-path rotation and unauthorized caller (`src/test/Strategy4626Factory.t.sol:61-79`), not zero addresses, wrong-address recovery, or old-vs-new child effects.
- This is management-only misconfiguration, not an external exploit. Treat it as a low operational foot gun unless factory permanence/high deployment volume raises impact. Prefer two-step management transfer and zero-address validation.

## Tests and evidence hardness

### Commands executed

Toolchain:

```text
forge --version
forge Version: 1.5.1-stable
Commit SHA: b0a9dd9ceda36f63e2326ce530c10e6916f4b8a2
```

Full fork suite:

```text
env ETH_RPC_URL=https://ethereum.publicnode.com forge test -vv \
  --fork-url https://ethereum.publicnode.com
exit 1
45 passed; 1 failed; 0 skipped (46 total)
failure: StethSpecificTest.test_depositLimit()
Left: 1; Right: 0; "Limit not exhausted"
fork cache path identified mainnet block 25533217
```

Focused rerun (the substring also selects two related deposit-limit tests):

```text
env ETH_RPC_URL=https://ethereum.publicnode.com forge test \
  --match-test test_depositLimit -vv \
  --fork-url https://ethereum.publicnode.com
exit 1
2 passed; 1 failed; 0 skipped
same deterministic 1-wei failure
fork cache path identified mainnet block 25533219
```

Coverage attempt:

```text
env ETH_RPC_URL=https://ethereum.publicnode.com forge coverage \
  --report summary --fork-url https://ethereum.publicnode.com
exit 1
45 passed; 1 failed; 0 skipped
same test failure; no successful summary produced
Foundry also emitted numerous coverage-anchor warnings
fork cache path identified mainnet block 25533230
```

Do not claim this suite or coverage run is green.

### What the current suite does cover

| Area | Grade | Evidence / limitation |
| --- | --- | --- |
| Base deposit, report, manual swap, redeem | happy-path fork/fuzz | Uses zero min-out for manual swap and permissive 0.5% terminal tolerance; no adversarial liquidity manipulation |
| Profit report | happy-path/assertion-light | Airdrops stETH; no mixed loss, destination loss, or locked-profit invariant |
| Available withdraw | exact current design | Proves only idle WETH is withdrawable; does not test upstream vault max-loss/integration behavior |
| Tend and gas threshold | branch/fuzz | Covers configured positive/negative triggers; default disables trigger |
| Shutdown/emergency | happy path with hidden config precondition | All success tests first set 50-bps `reportBuffer` as management |
| Queue initiate/claim/pending guard | deterministic mock | Mock pays requested amount exactly and omits finalization delay, partial/slashed claims, hint semantics, NFT/request ownership, and real queue limits |
| 4626 deposit/report/manual swap/queue initiation | happy-path fork/fuzz | Uses one mutable live vault and privileged `setAllowed`; no illiquidity/loss/PPS manipulation |
| Factory | happy-path role assertions | Covers configured child and duplicate vault; no script, config-zero, rotation, multi-child, or attachment test |
| Oracle | assertion-light | Only range-checks a fixed 4% constant; TODOs disable meaningful behavior assertions |
| Stateful invariants | missing | `git grep` found no `StdInvariant`, handler, `targetContract`, or `invariant_` in committed project tests/config |

### Highest-value missing regressions/invariants

1. **Deployment manifest smoke tests:** run each deployment path and assert exact roles, pending acceptance/clear, fees, profit unlock, `open/allowed`, deposit limit, report buffer, API version, vault address/asset, downstream authorization, and successful first deposit/report/emergency exit.
2. **Emergency default/config transition:** quote below 1:1, management unavailable, emergency-admin-only shutdown/unwind, bounded slippage, partial/full exits, and realized loss.
3. **ERC-4626 adversarial destination:** PPS not 1, donation, share price loss, `maxDeposit == 0`, `maxRedeem == 0` and partial, `previewWithdraw` greater than redeemable shares, paused/reverting redeem, rounding across preview/redeem/unwrap, vault returning fewer assets, and report after each state.
4. **Position/accounting invariant:** `estimatedTotalAssets` equals loose WETH plus discounted stETH-equivalent of loose stETH/wstETH/vault shares, excluding queued claims while `pendingRedemptions > 0`; after claim/report, no position bucket is double counted or lost beyond explicit bounds.
5. **Queue state machine:** multiple concurrent request IDs, out-of-order/partial claims, less ETH than stETH queued, invalid/stale hints, manual claim without blindly zeroing unrelated pending value, and management clearing followed by later claim.
6. **Custom role matrix:** negative and positive access tests for every custom setter/manual path, especially `manualStake`, `manualSwapToAsset`, queue initiation/claim, `manualRedeem`, `manualUnwrap`, referral, and emergency manual claims.
7. **Factory lifecycle:** zero/duplicate/malicious vaults, wrong symbol behavior, two-step role changes, existing-vs-future child config, multiple children, per-child acceptance, and per-child config readback.
8. **Upstream integration/max-loss:** actual Yearn vault attachment and user withdraw/redeem behavior when strategy liquidity is zero, partial, or loss-making; current direct user tests do not prove the production integration path.
9. **Economic/reproducibility:** pin a fork block and Foundry release, test fixed Curve/Lido/vault samples, and avoid mutable-live-state assumptions. Current CI uses Foundry `nightly` and an unpinned latest fork (`.github/workflows/test.yml:25-38`; no fork block in `foundry.toml`).

## Operations and attachment gates

| Gate | Source-observed state | Blind-phase status |
| --- | --- | --- |
| Exact deployment path selected | Standalone base, standalone 4626, and factory paths differ materially | unresolved; must select one |
| Management accepted by intended SMS | Base standalone sets pending; standalone 4626 does not; factory child sets pending | block standalone 4626; readback required for others |
| Pending management cleared | Tested only for factory unit deployment | live state not checked |
| Keeper | Base standalone explicitly sets; standalone 4626 leaves deployer; factory sets configured keeper | block/readback |
| Emergency admin | Base standalone explicitly sets; standalone 4626 leaves zero; factory sets configured admin | block/readback |
| Fee recipient / fee / unlock | Standalone defaults recipient to deployer until changed and fee/unlock to 10%/10 days; factory sets recipient, 0 fee, 0 unlock | resolve intended economics |
| Emergency `reportBuffer` | zero in every deployment path unless post-configured | block attachment until bounded value is set/tested |
| Strategy depositor permission | `open` false; only self allowed by constructor | configure intended upstream owner |
| Destination vault authorization | test cheats `setAllowed(strategy,true)` as vault management | external privileged action/readback required |
| Keeper/emergency runbook | no concrete payload/timing/monitoring artifact in scope | `operator_action: none_named` |
| Deployment generation/fork block | scripts hardcode addresses; CI/foundry config does not pin fork block or Foundry release | source-only, not deployment ready |
| Deployed-code LGTM/live config | intentionally excluded from blind phase | required later |

## Rejected or downgraded leads

- **Permissionless factory deployment:** `newStrategy4626` is public, but child roles come from factory config and duplicate deployment per vault is blocked. No caller-directed fund control was demonstrated; retain as an operational spam/symbol-revert surface, not a finding.
- **Default disabled tend trigger:** `minAmountToTend == max` disables autonomous triggering, but deposits and reports stake directly and keeper can call tend. This is an efficiency/keeper-config decision, not a demonstrated safety issue.
- **One-wei remaining deposit capacity:** reproducible test failure, but no material cap bypass or asset loss was shown. Downgraded to test-quality/rounding evidence.
- **Generic TokenizedStrategy access controls:** project tests are shallow for custom methods, but the pinned dependency contains its own generic role machinery/tests. Missing repo-specific composition tests remain; no generic modifier bypass was found in this lane.
- **Mock Curve “better route” test:** `test_optimalStakingRoute_curveSwap` does not assert output or call occurrence after mocking; this is missing proof, not proof the production route is wrong.

## Evidence gaps and questions for synthesis/later comparison

1. Is `Deploy4626.s.sol` intended/canonical, or is `Strategy4626Factory` the only authorized production path? If obsolete, remove it to prevent operator use.
2. What exact post-deployment manifest is required: SMS management, keeper, emergency admin, fee recipient/fee, unlock time, `open/allowed`, deposit limit, `reportBuffer`, upstream vault, and downstream-vault authorization?
3. What `reportBuffer`/emergency slippage bound is approved, who is expected to change it during an incident, and what happens if management is unavailable but emergency admin is online?
4. Is the hardcoded 4% APR oracle deployable/registered, or example-only?
5. What block and destination-vault implementation/config should the fork suite pin? The present test outcome drifts with latest mainnet state.
6. Should the factory be long-lived? If so, should management rotation be two-step and should zero addresses be rejected?
7. No deployed address, code parity, SMS acceptance, vault attachment, destination authorization, or live role/config snapshot was available by design in this blind phase. Those remain production blockers, not evidence of an unsafe deployed instance.

## Lane stop/go

`source_replay_complete_not_deployment_ready`. Block use of the standalone 4626 script as written. For any deployment path, require a post-deploy config readback, accepted SMS management, explicit upstream/downstream permissions, and a tested nonzero emergency slippage policy before debt/attachment. The test suite must not be represented as green at this commit/current fork state.
