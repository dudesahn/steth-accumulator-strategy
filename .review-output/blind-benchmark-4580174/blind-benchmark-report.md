# stETH Accumulator 4626 — Controlled Blind Benchmark Review

## 1. Concise strategy summary

The strategy accepts WETH and normally converts it through:

```text
WETH -> ETH -> stETH -> wstETH -> shares of a constructor-supplied ERC-4626 vault
```

Deposits use Curve only when its ETH-to-stETH quote is better than 1:1 and otherwise submit ETH to Lido. Profit is the stETH rebase plus any yield/loss produced by the downstream wstETH ERC-4626 vault. Immediate user withdrawals are deliberately limited to loose WETH; management must first free principal synchronously through Curve or asynchronously through Lido's withdrawal queue.

The blind source pass found no public sweep, auction, reward-sale, forged callback, or caller-directed principal drain. The material risks are instead concentrated in shutdown behavior, emergency configuration, deployment initialization, asynchronous-claim accounting, and the unconstrained downstream ERC-4626 trust boundary.

## 2. Scope, provenance, and clean-room ledger

| Field | Value |
| --- | --- |
| Review anchor | Yearn strategy review [Issue #765 — stETH Accumulator 4626](https://github.com/yearn/yearn-strategies/issues/765), title and URL supplied by the user |
| Target repository named by user | `/Users/dudesahn/Documents/GitHub/codex/review/steth-accumulator-strategy` |
| Fresh review worktree | `/Users/dudesahn/.codex/worktrees/8c5a/steth-accumulator-strategy` |
| Exact reviewed commit | `4580174c60ccac4658d97b02f0951aec92b218b2` |
| Branch state | detached `HEAD` |
| Initial cleanliness | clean; zero porcelain entries before review artifacts were created |
| Current tracked-source state | unchanged; only `.review-output/` is untracked |
| TokenizedStrategy gitlink | `82806289f967590c4efbf6bc3d237e4e7f0a0966` (`v3.0.4`) |
| TokenizedStrategy periphery gitlink | `fc1b1d4ab5c9a0b65b7ac785734c404d3742317a` (`v3.0.4`) |
| OpenZeppelin gitlink | `bd325d56b4c62c9c5c1aff048c37c6bb18ac0290` (`v4.9.5`) |
| Forge | `1.5.1-stable`, commit `b0a9dd9ceda36f63e2326ce530c10e6916f4b8a2` |
| Issue-body evidence | not used; an unauthenticated issue-only API request returned `404`, and source was sufficient for blind scope orientation |
| Comments/manual report/prior findings | not read; reserved for the later comparison phase |
| Deployed-code/live-config evidence | deliberately not checked in this blind phase |
| Review output | `.review-output/blind-benchmark-4580174/` |

The exact pinning transcript and isolation boundary are in `provenance.md`. The parent checkout, other worktrees, later commits, branches, reflogs, stashes, pre-existing untracked files, `.audit/`, `.scratchpad/`, prior reports, manual review, comments, known findings, linked review artifacts, later fixes, LGTMs, reactions, and deployment evidence were not inspected.

### Proof layers

| Layer | Status | Caveat |
| --- | --- | --- |
| Issue/context | `thin` | only user-supplied title/URL; body unavailable and unnecessary |
| Source | `exact_commit` | exact root and dependency gitlinks initialized and inspected |
| Tests | `local_stdout_saved` | full suite red; isolated PoCs green; exact commands below |
| Deployed code | `unknown` | excluded from blind phase |
| Live strategy config | `not_checked` | excluded from blind phase |
| Destination protocol | `bounded_dd` | source mechanics and official specifications; exact vault/admin/live state unresolved |
| Lifecycle | `unknown` | comments/LGTM/deployment chronology reserved for later comparison |

## 3. Findings table

Severity uses Impact x Likelihood. `High x Medium` maps to High, `Medium x Medium` to Medium, and `Medium x Low` to Low. Conditional deployment applicability is stated separately rather than hidden in severity.

| ID | Status | Severity | Impact x likelihood | Title | Evidence |
| --- | --- | --- | --- | --- | --- |
| F-01 | validated | High | High x Medium | `report()` and `tend()` can redeploy emergency-freed principal after shutdown | source + 2 passing PoCs |
| F-02 | validated default/config flaw | High | High x Medium | default zero emergency buffer makes below-peg emergency exit revert and emergency admin cannot configure it | source + fixed-block quote + passing PoC |
| F-03 | validated source/operations flaw; activation depends on using standalone script | High | High x Medium | standalone `Deploy4626` never installs its advertised management or roles | source + passing PoC |
| F-04 | validated | Medium | Medium x Medium | queued principal disappears from the deposit-cap basis, allowing repeated cap refills | source + passing PoC |
| F-05 | validated API incompatibility | Low | Medium x Low | initiation return bytes decode as request ID 32 in the normal claim path | source + passing PoC |

### Conditional concerns

| ID | Severity | Impact x likelihood | Concern |
| --- | --- | --- | --- |
| C-01 | Medium conditional | Medium x Medium | a lossy manual/emergency swap leaves stale PPS, so early redeemers can shift loss to later shareholders before report |
| C-02 | Medium conditional | High x Low | management can execute a full-principal Curve unwind with zero or stale-low caller min-out |
| C-03 | Medium conditional | High x Low | arbitrary ERC-4626 vault is only asset-checked; gross valuation, unlimited allowance, fees, admin, upgrade, donation, and exitability remain unproved |
| C-04 | Low conditional | Low x Medium | subtracting actual claimed ETH from requested-stETH pending accounting can leave a residual that blocks reports after a haircut |
| C-05 | Low conditional | Low/Medium x Low | placeholder fixed 4% APR oracle, Lido stake-limit omissions, large queue-request bounds, and near-cap Curve bonus are unverified operational edges |

## 4. Detailed validated findings

### F-01 — Shutdown does not stop principal redeployment

**Severity: High — Impact High x Likelihood Medium.**

`TokenizedStrategy` intentionally leaves `report` and `tend` callable after shutdown so a child can finish maintenance and record losses (`lib/tokenized-strategy/src/TokenizedStrategy.sol:1314-1333`). Its base guidance explicitly tells child strategies to check shutdown before redeploying during report and after emergency withdrawal (`lib/tokenized-strategy/src/BaseStrategy.sol:219-221,342-351`).

This child does not. `BaseLSTAccumulator._harvestAndReport` always stakes loose WETH before returning accounting, `_tend` always stakes the full idle balance, and `_tendTrigger` has no shutdown guard (`src/BaseLSTAccumulator.sol:136-165`). `Strategy4626._stake` then converts WETH to stETH, wraps it, and deposits all wstETH into the downstream vault (`src/Strategy4626.sol:29-42`). `stakeAsset = false` does not stop report, and even `stakeAsset = false` plus `depositLimit = 0` does not stop a direct keeper `tend()`.

This reverses the emergency action and can re-expose the full recovered balance to the exact destination being escaped. It also makes the accounting step required after a lossy emergency swap unsafe by default: reporting the loss redeploys the newly liquid WETH.

Reproduction:

```text
EmergencyAndCapPoC::test_keeperCanTendRecoveredFundsAfterShutdownDespiteConfigStops       PASS
EmergencyAndCapPoC::test_reportRedeploysRecoveredFundsAfterShutdownWhenStakeFlagIsFalse  PASS
```

Recommended invariant: once `isShutdown()` is true, no report, tend, trigger, or deposit callback may increase stETH, wstETH, or downstream-vault shares. Gate `_harvestAndReport`, `_tend`, and `_tendTrigger` on shutdown; report after shutdown should account without redeploying. Do not rely solely on keeper revocation or a multi-transaction runbook.

### F-02 — Default emergency exit is unusable below exact 1:1

**Severity: High — Impact High x Likelihood Medium.**

`reportBuffer` defaults to zero. Emergency withdrawal computes `minOut = amount * (10_000 - reportBuffer) / 10_000`, so defaults demand one ETH for each stETH (`src/BaseLSTAccumulator.sol:148-155`). Only management can set the buffer (`:192-195`); emergency admin can shut down and call emergency withdrawal but cannot change the bound. Neither the standalone scripts nor the factory initialize it.

Every committed shutdown success test silently adds the missing precondition by setting a 50-bps buffer as management before emergency withdrawal (`src/test/Shutdown.t.sol:7-16,35-45,81-92,132-139`). At mainnet block `25533225`, the fixed Curve pool returned:

```text
cast call 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022 \
  "get_dy(int128,int128,uint256)(uint256)" 1 0 1000000000000000000 \
  --block 25533225 --rpc-url "$ETH_RPC_URL"
=> 999797856520084312
```

The isolated default-config regression therefore reverts as expected:

```text
EmergencyAndCapPoC::test_defaultEmergencyBufferRevertsAtPinnedBelowPegCurveState PASS
```

In an incident, emergency liveness depends on a separate management/SMS action that also changes report valuation and deposit-cap room. Make emergency slippage policy explicit and separate from report valuation, install/read back a bounded production value before debt, or give emergency admin only a tightly bounded emergency adjustment. Add a default-state negative test and configured-state positive test.

### F-03 — Standalone 4626 deployment leaves control with the broadcaster

**Severity: High — Impact High x Likelihood Medium if this script is used.**

`script/Deploy4626.s.sol:12-28` declares and logs a management address and instructs it to call `acceptManagement()`, but the script only constructs `Strategy4626`. It never calls `setPendingManagement`, `setKeeper`, `setEmergencyAdmin`, or `setPerformanceFeeRecipient`.

The pinned `BaseStrategy` constructor assigns management, keeper, and performance-fee recipient to `msg.sender`; emergency admin and pending management remain zero. Therefore the logged management address reverts with `!pending`. The standalone path also retains TokenizedStrategy's default 10% fee and 10-day unlock, while the factory explicitly sets both to zero (`src/Strategy4626Factory.sol:51-56`).

Reproduction:

```text
DeploymentConfigPoC::test_directDeploymentDoesNotConfigureAdvertisedManagementOrRoles PASS
```

If the broadcaster key is discarded, the intended management cannot recover control; if it remains active, it retains unexpected management/report and fee authority. Remove the script if obsolete or make it apply a complete manifest, hand off pending management, and read back every role/economic/config field before attachment.

### F-04 — Pending queue principal bypasses the configured deposit cap

**Severity: Medium — Impact Medium x Likelihood Medium.**

`initiateLSTWithdrawal` increases `pendingRedemptions` and transfers stETH to the external queue (`src/BaseLSTAccumulator.sol:239-247`; `src/Strategy.sol:87-99`). `estimatedTotalAssets` counts only loose WETH and currently held LST positions, not the queue claim (`src/BaseLSTAccumulator.sol:171-185`). The deposit cap is calculated as `depositLimit - estimatedTotalAssets` (`:89-96`).

After a full-cap position is queued, the configured cap reopens even though the principal-bearing queue claim still exists. Deposits remain enabled while report is blocked. Management can queue the refill again, so pending plus active economic exposure can repeatedly exceed the nominal cap. Share pricing is not proven wrong because TokenizedStrategy's stored assets remain stale-high; the broken invariant is the risk/TVL cap.

Reproduction:

```text
EmergencyAndCapPoC::test_pendingQueuePrincipalReopensAndBypassesDepositCap PASS
```

Include a conservative asset value for pending claims in the cap basis, or use a position-bucket cap that cannot forget principal when its representation changes.

### F-05 — Withdrawal return/claim bytes are not composable

**Severity: Low — Impact Medium x Likelihood Low.**

`_initiateLSTWithdrawal` returns `abi.encode(uint256[] requestIds)` (`src/Strategy.sol:90-99`), but `_claimLSTWithdrawal` decodes its bytes as one scalar `uint256` (`:101-108`). ABI-encoding a dynamic array starts with offset `0x20`, so directly forwarding the advertised `returnData` claims request ID `32`.

The committed tests hide the mismatch by decoding the returned array and re-encoding its first element before claim (`src/test/WithdrawalQueue.t.sol:70-80,104-117,133-147`). A direct-forward PoC reverts on ID 32 and then succeeds only with the hidden adapter step:

```text
ClaimDataMismatchPoC::test_directForwardOfReturnedClaimDataUsesWrongRequestId PASS
```

This normally delays claims and leaves `pendingRedemptions` blocking report rather than losing funds; the batch emergency path remains. Use typed APIs, return one encoded scalar, or accept/decode the array, and add an exact direct-forward regression.

## 5. Mechanics and trust-boundary map

### Path matrix

| Path | Assets moved | First external action | Accounting source | Failure / shortfall behavior |
| --- | --- | --- | --- | --- |
| Deposit/deploy | WETH -> ETH -> stETH -> wstETH -> vault shares | canonical WETH withdraw | TokenizedStrategy increments stored assets by deposited WETH | atomic revert on Curve/Lido/wrapper/vault failure; deployment callback uses entire loose WETH balance |
| Report | loose WETH and all deployed position forms | `_stake` before accounting | WETH + buffered stETH value of stETH/wstETH/vault shares | blocked while pending; after shutdown it redeploys (F-01) |
| User withdraw/redeem | loose WETH only | no external strategy action when idle is enough | cached TokenizedStrategy PPS | conservative liquidity; out-of-band loss can be order-shifted before report (C-01) |
| Manual free | vault shares/wstETH/stETH -> Curve -> WETH | downstream redeem if needed | not updated until report | partial exit clamps to actual held stETH; caller min-out may be zero (C-02) |
| Queue withdrawal | stETH -> unstETH claim -> ETH -> WETH | Lido queue request | pending blocks report; actual ETH measured on claim | cap forgets claim (F-04); payload mismatch (F-05); shortfall can leave residual (C-04) |
| Emergency | vault shares/wstETH/stETH -> Curve -> WETH | downstream redeem if needed | cached until later report | default exact-peg floor reverts (F-02); later report/tend redeploys (F-01) |
| Migration/release | no custom migration path | inherited generic surface only | not specifically tested | old approvals/positions/runbook unproved |

### Token movement matrix

| Position | Principal role | Counted? | Movers | Protection / residual risk |
| --- | --- | --- | --- | --- |
| WETH | vault asset / liquid principal | yes | deposits, WETH, users, report/tend | no generic sweep; keeper can redeploy after shutdown |
| native ETH | transient principal/donation | not directly | WETH, Curve, Lido | entire balance is wrapped after swap/claim and remains principal |
| stETH | rebasing principal | yes, buffered | Curve, wstETH, Lido queue | exact approvals to Curve/queue; max approval to canonical wrapper |
| wstETH | wrapped principal | yes via stETH value | downstream vault, wrapper | permanent max vault allowance (C-03) |
| downstream vault shares | receipt principal | yes via `convertToAssets` | downstream vault redemption | exact vault implementation/admin/fees/liquidity unproved |
| withdrawal request | async principal claim | omitted from ETA | Lido queue roles/finalization | report lock but cap omission and operational claim assumptions |

No auction, swapper, reward sale, `protectedTokens`, generic sweep, rescue, or recover function exists in the pinned strategy generation. Exact-amount stETH approvals are used for Curve and queue operations; max approvals are used for the wstETH wrapper and downstream vault.

## 6. Destination protocol due diligence

### Destination instances

| Instance | Principal / exit form | Mutable control surface | Blind-phase evidence |
| --- | --- | --- | --- |
| Lido stETH `0xae7a...e84` | ETH -> rebasing stETH | staking pause/rate, oracle/accounting, governance/proxy | source mechanics + bounded official-doc review; live state not checked |
| wstETH `0x7f39...2Ca0` | stETH -> non-rebasing wstETH | depends on canonical stETH accounting | denomination mechanics confirmed |
| Lido WithdrawalQueue `0x889e...F9B1` | stETH -> async NFT claim -> ETH | pause/resume/finalize/oracle/upgrade and ETH availability | mock tests only; live state not checked |
| Curve ETH/stETH `0xDC24...022` | synchronous ETH/stETH swap | pool price, depth, admin/pause | fixed-block quote only; depth/admin not checked |
| constructor-supplied ERC-4626 vault | wstETH -> vault shares -> wstETH | arbitrary admin, proxy, allocator, fee, cap, pause, strategy set | dominant unresolved trust surface |

The strategy checks only `vault.asset() == wstETH`. It does not constrain implementation hash, factory provenance, proxy/admin, fees, rounding, donation/inflation behavior, allocation strategy, or exit liquidity. It grants the vault unlimited wstETH allowance, deposits without a minimum-shares assertion, and reports gross `convertToAssets`, which is not proof of immediate realizability under [EIP-4626](https://eips.ethereum.org/EIPS/eip-4626).

The example address `0xE73b2561309Bed1035D2145275BCA1aEcf85A8F7` appears in the standalone script and tests, but its source, proxy/admin, nested positions, fees, caps, allowlist, and live exit state were deliberately not inspected. `Setup4626` impersonates that vault's management to allowlist the new strategy; production automation does not perform or verify that action.

Lido's [core contract documentation](https://docs.lido.fi/contracts/lido/) distinguishes staking pause from the mutable current stake limit; source checks only pause, so direct submit can revert while advertised capacity remains. The [withdrawal queue documentation](https://docs.lido.fi/contracts/withdrawal-queue-erc721/) describes bounded, asynchronous requests and possible below-1:1 finalization; the strategy does not chunk a request and may require manual residual clearing after a haircut. These are operational constraints and missing proof, not additional validated loss findings in this blind phase.

### Fund-control surface

| Actor | Power over funds | Source bound | Residual requirement |
| --- | --- | --- | --- |
| strategy management | cap/buffer/keeper/admin, manual stake/swap/queue/clear | role-gated; manual min-out caller supplied | SMS identity, bounds, private execution, and runbook unknown |
| keeper | report, tend, single claim | cannot redirect receiver | can re-expose all idle principal after shutdown (F-01) |
| emergency admin | shutdown, emergency swap, manual redeem/unwrap/batch claim | cannot set buffer or revoke keeper | emergency independence is incomplete (F-02) |
| downstream vault control actors | potentially reprice, pause, upgrade, allocate, impair exit | no strategy-side constraint beyond `asset()` | exact source/admin/delay/config review required per child |
| Lido roles/governance | staking availability, queue finalization, accounting/upgrade | two exit routes but correlated protocol exposure | exact reviewed-era holders and states unverified |
| Curve state/admin | synchronous exit price/depth/availability | caller min-out or report buffer | lot/depth/private relay and admin/pause state unverified |

## 7. Tests, PoCs, and missing invariants

### Executed outcomes

| Command / group | Outcome |
| --- | --- |
| `forge test -vv --fork-url "$ETH_RPC_URL"` in sandbox | crashed before tests with macOS `system-configuration` NULL-object panic |
| same full suite outside sandbox | **45 passed, 1 failed, 0 skipped**; `test_depositLimit` left 1 wei |
| focused `test_depositLimit` rerun | same deterministic 1-wei failure |
| isolated `ClaimDataMismatchPoC` | 1 passed |
| isolated `EmergencyAndCapPoC` at block `25533225` | 4 passed |
| isolated `DeploymentConfigPoC` at block `25533225` | 1 passed |
| final PoC-only combined run at block `25533225` | **6 passed, 0 failed, 0 skipped** |
| lane-focused committed suites | 22/22 token-movement subset passed; exact commands in lane artifact |

The suite is not green. The 1-wei remaining capacity is a Low test-quality defect, not a material cap-bypass proof. Tests and CI use a mutable latest mainnet fork and Foundry nightly, so results can drift.

### Highest-value missing checks

1. invariant: shutdown cannot increase stETH, wstETH, or downstream-vault shares under report/tend/deposit callbacks;
2. two-holder forced-loss regression proving or rejecting C-01 loss redistribution;
3. deployment manifest smoke test for every script/factory path and management acceptance;
4. default/configured emergency buffer, management-unavailable, and bounded partial/full exit tests;
5. pending-claim-inclusive deposit-cap invariant across multiple requests/refills;
6. real typed queue state machine: direct return forwarding, out-of-order claims, below-1:1 claims, pause/finalization delays, request size bounds;
7. hostile ERC-4626: zero/partial max redeem, fee, donation/inflation, malicious allowance pull, upgrade/pause, `convertToAssets > previewRedeem`;
8. exact intended vault code/config and fixed-block fork tests;
9. upstream Yearn vault attachment and max-loss behavior;
10. APR oracle debt/strategy sensitivity or explicit removal as non-production example.

Exact commands and concise outputs are preserved in `evidence/test-results.md`. PoCs live under `poc/` and do not modify production source.

## 8. Operations, configuration, and attachment gates

| Gate | Source-observed state | Blind-phase decision |
| --- | --- | --- |
| canonical deployment path | base script, standalone 4626 script, and factory differ materially | select one; block standalone script as written |
| management/SMS | standalone 4626 does not set pending management | block until accepted and read back |
| keeper/emergency admin | standalone leaves broadcaster keeper and emergency admin zero | block; factory values still need live readback |
| fee recipient/fee/unlock | standalone defaults differ from factory's 0 fee/0 unlock | resolve intended economics |
| emergency buffer | zero unless post-configured | block debt until bounded value is installed/tested |
| strategy deposit permission | BaseHealthCheck defaults closed; only self allowed | configure intended upstream owner/vault |
| downstream allowlist | tests cheat `setAllowed(strategy,true)` as vault management | explicit privileged action and readback required |
| shutdown runbook | source permits keeper redeployment | code fix preferred; otherwise revoke keeper atomically and name every payload |
| Curve unwind | management chooses min-out; tests normalize zero | require bounded lot/min-out/private relay policy |
| destination vault | only asset-checked | exact per-child source/admin/fee/liquidity review required |
| deployed parity/live config | excluded | required in later deployment-aware phase |

### Accepted-risk / operator-action ledger

| Risk | Required action | Current source/runbook evidence | Residual blast radius |
| --- | --- | --- | --- |
| emergency below peg | management sets approved buffer before emergency admin swap | tests imply 50 bps; production policy absent | full position remains trapped if management unavailable |
| post-shutdown redeploy | revoke keeper, set cap zero, avoid tend, report safely | `operator_action: none_named`; cap zero does not stop tend | full recovered WETH |
| manual Curve unwind | calculate fresh min-out, bound lot, use private execution if required | `operator_action: none_named`; tests use zero | caller-selected amount, potentially full principal |
| queue shortfall | monitor IDs/amounts, claim, approve and clear exact residual | only generic emergency clear exists | reporting liveness and loss recognition |
| downstream vault impairment | pause deposits, revoke allowance, redeem/unwrap/queue based on state | no allowance revoke or atomic runbook | all vault principal plus transient loose wstETH |

## 9. Rejected and downgraded leads

| Lead | Decision | Reason |
| --- | --- | --- |
| public caller can forge strategy callbacks | rejected | inherited callbacks are `onlySelf`; external entrypoints are non-reentrant |
| generic sweep/auction can sell principal | rejected | no such surface exists in the pinned strategy generation |
| Curve deposit route can accept less than 1:1 | rejected | route selected only above 1:1 and exchange minimum is the WETH input |
| downstream vault shares are added in wrong denomination | rejected | shares -> wstETH via `convertToAssets`, then wstETH -> stETH |
| partial downstream exit treated as full requested return | rejected | redemption/swap clamps to actual returned/held balances |
| normal withdrawal views overstate downstream liquidity | rejected | views expose loose WETH only |
| permissionless factory caller receives child control | rejected | factory retains initial control and installs configured roles/pending management |
| one-wei deposit capacity is a material cap bypass | downgraded | reproducible red test, but only dust; F-04 is the separate queue-claim cap bypass |
| `stakeAsset=false` ignored by report is independently unintended | downgraded | committed test explicitly specifies this; it is security-relevant only because shutdown lacks its own guard |
| max vault allowance is an unconditional drain | conditional | harmful pull requires malicious/upgraded/compromised vault; vault already holds ordinary deployed principal |

## 10. Stop/go status and residual risk

**Status: `source_replay_complete_not_deployment_ready`.**

Block reliance on the current shutdown path until F-01 is fixed or a concrete atomic keeper-revocation procedure is demonstrated. Block any standalone `Deploy4626` use until F-03 is corrected. Before debt or attachment, require exact role/config readback, accepted SMS management, explicit upstream/downstream permissions, bounded emergency and manual Curve policies, and exact destination-vault code/control/exitability review.

Residual risks after source fixes remain dominated by stETH/Curve liquidity and pricing, Lido queue delays and loss finalization, downstream ERC-4626 valuation/fees/admin/exitability, operator key/runbook correctness, and unverified deployed-code/live-config parity.

## 11. Open questions before manual/comment-aware comparison

1. Is `Strategy4626Factory` the only canonical production deployment path, or is `script/Deploy4626.s.sol` intended to remain usable?
2. What exact destination vault(s) are in scope, and what source commit, proxy implementation, nested positions, fees, caps, allowlist, and admin/timelock control them?
3. What is the required post-deployment manifest: SMS management, keeper, emergency admin, fee recipient/fee, unlock time, `open/allowed`, cap, buffer, upstream vault, and downstream authorization?
4. What emergency `reportBuffer` or separate slippage bound is approved, and must emergency admin be able to act without management?
5. Is keeper revocation atomic with shutdown? If not, is post-shutdown tend intentionally accepted?
6. What automation consumes Lido request return data: direct bytes forwarding or explicit array decode/scalar re-encode?
7. Is the fixed 4% APR oracle production-deployable or example-only?
8. What fixed fork block and Foundry release should become the reproducible benchmark baseline?
9. For the later comparison, should deployed/LGTM/live-config evidence be included together with the manual report, or should manual-report delta remain a separate intermediate artifact?

## 12. Manual-report comparison placeholder

| Comparison field | Blind-phase value | Later phase |
| --- | --- | --- |
| Manual report read | no | pending user supply/authorization |
| Issue comments/reviewer feedback read | no | pending |
| Blind findings matched by humans | unknown | placeholder |
| Human findings missed by blind pass | unknown | placeholder |
| Blind-only findings | F-01 through F-05 pending comparison | placeholder |
| Later fixes/status | not inspected | placeholder |
| Deployment/live applicability | not inspected | placeholder |

## 13. Training-extraction notes

- `blind_agent_found`: trace post-shutdown functions to their first external action; shutdown stopping deposits does not stop keeper re-exposure.
- `blind_agent_found`: treat async request objects as principal in caps and accounting-state machines even while reports are intentionally blocked.
- `blind_agent_found`: compare returned ABI shape with the exact automation handoff and downstream decoder, not just unit tests that adapt the payload.
- `blind_agent_found`: execute deployment artifacts and assert role/config postconditions; logged intent is not state.
- `production_caveat`: an ERC-4626 `asset()` check proves denomination, not realizable value, safety, governance, or exitability.
- `production_caveat`: default emergency settings must be tested in the failure state they are supposed to handle.
- `negative_example`: a red exact-equality fork test is a reproducibility/test-quality signal and should not be promoted into a material security finding without harm evidence.
- `source_replay_complete_not_deployment_ready`: deployed parity, live config, exact destination vault, issue comments, manual report, and deployment lifecycle remain intentionally unresolved.

## 14. Artifact index

- `provenance.md` — pinning transcript and isolation boundary
- `lanes/01-accounting.md` — blind accounting/exit lane
- `lanes/02-token-movement.md` — blind custody/approval/callback lane
- `lanes/03-destination-dd.md` — blind destination-protocol lane
- `lanes/04-tests-ops.md` — blind tests/roles/deployment lane
- `evidence/test-results.md` — exact test/PoC commands and outcomes
- `poc/ClaimDataMismatch.t.sol` — claim payload regression
- `poc/EmergencyAndCap.t.sol` — shutdown, emergency buffer, and cap regressions
- `poc/DeploymentConfig.t.sol` — standalone deployment-role regression
- `MANIFEST.sha256` — integrity hashes for the blind-review bundle
- `blind-benchmark-report.md` — this synthesis
