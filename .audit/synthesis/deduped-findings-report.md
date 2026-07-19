# Deduplicated Security Findings

## Synthesis Scope

This report consolidates the committed tool outputs under `.audit/` on `review`, the four 5.6 Sol model-run bundles committed on `review-sol-update`, the preserved clean-worktree Plamen Core and Thorough runs, the clean-worktree ZeroSkills run, the controlled strategy-review-agent blind benchmark plus comment-aware replay, and the dedicated adversarial test-suite campaign into canonical finding families. It is a synthesis of prior evidence, not a new audit pass.

- Baseline production snapshot: `521fff28ad978a37115be8995a1d631611fa1d3d` on `review`
- 5.6 Sol run snapshot: `4580174c60ccac4658d97b02f0951aec92b218b2` on `review-sol-update`
- Plamen Core run snapshot: `521fff28ad978a37115be8995a1d631611fa1d3d`, from a dedicated clean detached worktree
- Plamen Thorough run snapshot: `4580174c60ccac4658d97b02f0951aec92b218b2`, from a dedicated clean detached worktree
- ZeroSkills run snapshot: `4580174c60ccac4658d97b02f0951aec92b218b2`, from a dedicated clean detached worktree
- Strategy-review-agent benchmark snapshot: `4580174c60ccac4658d97b02f0951aec92b218b2`, first reviewed blind in a dedicated clean detached worktree and then replayed separately against Issue #765 comments and linked Issue #714 context; the user's manual report remained unread
- Extended adversarial-test snapshot: `4580174c60ccac4658d97b02f0951aec92b218b2`, from the dedicated `codex/improve-test-suite-4580174` worktree; production source was unchanged and all additions were tests, mocks, test tooling, or documentation
- Branch relationship: `4580174c...` descends from `521fff28...` through two source-changing commits
- Audit-artifact branch head: `f5f547278a398ee0b8edd1d24daab9877186178e`; no production source changes occur between `4580174c...` and that branch head
- Repository `HEAD` at this synthesis integration: `36d7b21d5ce35dd6ecf0723b769013f6f32773db`; its production source still matches the baseline snapshot
- Scope: first-party production contracts, interfaces, and relevant deployment scripts covered by the committed tool runs
- Excluded from independent vote counts: x-ray orientation, duplicated Nemesis subpass summaries, raw candidates rejected by a tool's own finalizer, and generated PoC/build artifacts

The evidence sources are:

| Source | Canonical input | Final output shape |
| --- | --- | --- |
| Codex Security | `.audit/codex-security/351c58eb-604e-4d06-91a4-9a0d6e65626b/report.md` and `findings.json` | 2 final report findings; candidate validation artifacts retained separately |
| dot-context | `.audit/dot-context/outputs/1/audit-report.md` and `findings.json` | 4 Medium and 2 Low findings |
| Human Pages | `.audit/human-pages/findings.md`, `findings.jsonl`, and `poc_results.md` | 2 validated, 3 conditional, plus downgraded and rejected notes |
| dot-context-sol | `review-sol-update@f5f5472:.audit/dot-context/outputs/1/audit-report.md` and `findings.json` | 1 Medium and 3 Low findings against `4580174c...` |
| human-pages-sol | `review-sol-update@f5f5472:.audit/human-pages/findings.md`, `findings.jsonl`, and `poc_results.md` | 5 validated, 2 plausible, and 1 rejected hypothesis against `4580174c...` |
| Nemesis | `.audit/findings/nemesis-verified.md` | 3 verified Low findings; Feynman and state-inconsistency files are subpasses of the same run |
| x-ray + solidity-auditor | `.audit/solidity-auditor-521fff2/validated-findings-and-leads.md` | 3 validated findings and 5 validated leads; x-ray is orientation only |
| Plamen Core baseline | `../steth-accumulator-strategy-plamen-core-521fff2/.audit/plamen-runs/core-baseline-2026-07-13-521fff2/{AUDIT_REPORT.md,run_notes.md,.scratchpad/mechanical_verify_manifest.json}` | 8 Medium body findings and 1 appendix observation against `521fff28...`; 2 body findings carry final `POC-PASS` tags |
| Plamen Thorough | `../steth-accumulator-strategy-plamen-thorough-4580174-20260713/.audit/plamen-runs/thorough-baseline-2026-07-13-4580174/{AUDIT_REPORT.md,provenance.md,.scratchpad/verdict_manifest.json}` | 22 actual post-disposition body sections against `4580174c...` (15 Medium, 7 Low), plus 4 quality observations; 1 body finding carries a final `POC-PASS` tag. The generated executive summary says 23 because its M-13-to-M-02 merge was not propagated to the header and priority list. |
| ZeroSkills (`code-sleuth` + `symmetry-sniper`) | `.audit/zeroskills-steth-accumulator-strategy-20260713.md` | 4 validated findings (1 Medium, 3 Low), 1 plausible conditional lead, and no validated storage-integrity finding against `4580174c...` |
| strategy-review-agent benchmark | `.review-output/blind-benchmark-4580174/{blind-benchmark-report.md,comment-aware-replay.md,evidence/,poc/}` | Blind pass: 5 validated findings and 5 conditional concerns. Comment-aware replay: no new canonical family, one sharper DF-17 variant, fix/intent chronology, and severity reconciliation. The combined fixed-block PoC run passed 8/8; the committed full suite remained 45/46 because of the known one-wei assertion. |
| Extended adversarial test suite | `../steth-accumulator-strategy-test-suite-4580174/{docs/ADVERSARIAL_TESTING.md,src/test/unit/,src/test/adversarial/,src/test/invariant/,src/test/mocks/ProtocolMocks.sol}` | 80 deterministic security-model tests: 53 enforced properties and 27 executable counterexample or assumption tests; 14 stateful invariants passed at 256 runs and depth 64, including seeds `0x1`, `0x2`, and `0x3`; production coverage reached 205/205 lines, 50/50 functions, and 34/34 branches; all 46 legacy fork tests passed through PublicNode. |
| 5.6 Sol Codex Security run | `review-sol-update@2539bb0:.audit/codex-security/b28ae933-e033-4054-aabb-a11a84937880/report.md` and `findings.json` | 9 final findings against `4580174c...` |
| 5.6 Sol solidity-auditor run | `review-sol-update@2539bb0:.audit/pashov-4580174-20260710T112356Z/synthesis/validated-findings-and-leads.md` | 9 validated findings and 11 validated or conditional leads against `4580174c...`; x-ray remained orientation only |

Final and verified outputs take precedence over raw agent notes. A source-traced disagreement is retained in the canonical finding instead of being hidden by a simple vote count.

## Executive Summary

No Critical or High finding was reported by the committed tool runs.

Counts and table severities use the highest reconciled severity applicable to either reviewed snapshot. Version-specific downgrades and fixes are stated in each finding.

The synthesis yields:

- 4 confirmed Medium findings
- 3 deployment- or configuration-conditional Medium findings, including one mechanism now confirmed by an executable deterministic model
- 12 Low findings or operational weaknesses
- 2 conditional trust-boundary or informational findings

The Plamen Core delta does not add a nineteenth family. Six of its eight body mechanisms remain present at `4580174c...`; its Strategy4626 emergency-exit item is the baseline-only DF-07 defect fixed by that later snapshot, and its contested zero-minimum emergency-swap item describes the baseline side of the slippage trade-off later represented by DF-14. Plamen's appendix-only profit-unlock observation failed its attempted PoC and adds no proof beyond DF-04's existing production-fork evidence.

The Plamen Thorough delta adds three canonical families: DF-19 for report-buffer-discounted capacity, DF-20 for unbounded single-request Lido exits, and DF-21 for omitted direct-Lido live capacity. At the end of that run, all three were final code-trace findings without an executed end-to-end PoC. The later extended test campaign upgrades DF-19 with deterministic execution; DF-20 and DF-21 remain code-trace-only and their external-state applicability is stated explicitly below. Thorough also upgrades DF-05 with the run's sole final `POC-PASS`, expands DF-11 and DF-16 with role-lifecycle and per-request-accounting variants, and supplies additional code-trace corroboration elsewhere. Thorough L-01 is not promoted because the existing human-pages-sol adversarial callback test rejected the same reentrant factory-deployment hypothesis. The direct Core-vs-Thorough comparison, including commit and routing confounders, is recorded in `.audit/synthesis/plamen-core-vs-thorough.md`.

The ZeroSkills delta also adds no new family or count change. Its merged liquidity-relocking finding separates into DF-02's post-shutdown keeper path and DF-12's ordinary-depositor path under the canonical taxonomy; its other validated findings map directly to DF-03, DF-05, and DF-06. Its sole conditional queue-settlement lead is already represented by DF-16.

The strategy-review-agent benchmark also adds no new canonical family or count change. Its blind F-01 through F-05 map to DF-02, DF-14, the existing downgraded direct-deployment footgun, DF-05, and DF-06 respectively. Its conditional concerns map to DF-01, DF-09, DF-10, DF-13, DF-16, DF-20, and DF-21. The comment-aware replay maps its zero-unwrap partial-recovery scenario to DF-17 and confirms that the Issue #765 tend and emergency-slippage fixes were incomplete. The benchmark contributes independent fixed-block PoCs and stronger source-report severity ratings for DF-02, DF-05, DF-14, and the downgraded deployment-script issue; those rating differences are preserved below without changing the reconciled canonical severities.

The extended adversarial test suite likewise adds no new canonical family or count change. Its strongest delta is an executable deterministic model PoC for DF-19: a 1% report buffer on a fully utilized 10 WETH cap reopened 0.1 WETH of capacity, accepted that deposit, and caused the next report to record a 0.101 WETH accounting loss shared across the existing and new users. The campaign also strengthens DF-01, DF-02, DF-03, DF-05, DF-06, DF-10, DF-16, and DF-17 with exact regression, fuzz, and stateful evidence. Wrong-asset deployment, factory zero-role configuration, arbitrary-token recovery, and direct-Lido underdelivery remain configuration-hardening or external-assumption notes rather than new canonical vulnerabilities.

| ID | Severity | Status | Applicability | Canonical finding |
| --- | --- | --- | --- | --- |
| DF-01 | Medium | Confirmed | Both snapshots | Loss-producing unwinds expose WETH before share accounting records the loss |
| DF-02 | Medium | Confirmed | Both snapshots | Report and tend can re-stake shutdown liquidity or bypass the staking disable state |
| DF-03 | Medium | Confirmed | Both snapshots | Strategy4626 deposits its full loose wstETH balance without enforcing live vault capacity |
| DF-04 | Medium | Confirmed, conditional | Both snapshots | Zero profit locking allows pre-report deposits to capture accrued yield |
| DF-05 | Low | Confirmed | Both snapshots | Pending Lido redemptions are omitted from deposit-limit accounting |
| DF-06 | Low | Confirmed | Both snapshots | Lido withdrawal initiation and claim use incompatible ABI shapes |
| DF-07 | Low | Confirmed operational weakness | Baseline only; fixed at `4580174c...` | Strategy4626 emergency withdrawal does not unwind its normal vault-held position |
| DF-08 | Low | Confirmed configuration footgun | Baseline only; fixed at `4580174c...` | `reportBuffer > MAX_BPS` underflows valuation and report paths |
| DF-09 | Low | Deployment-conditional | Both snapshots | StrategyAprOracle returns a constant APR independent of strategy state and debt delta |
| DF-10 | Conditional | Trust boundary | Both snapshots | Strategy4626 fully trusts the selected ERC4626 vault without local output or NAV guards |
| DF-11 | Informational | Operational | Both snapshots | Permissionless factory deployment can populate one-shot registry state for unreviewed vaults |
| DF-12 | Medium | Confirmed | Both snapshots | A small accepted deposit can redeploy WETH prepared for existing-holder withdrawals |
| DF-13 | Medium | Confirmed, conditional | Both snapshots with a fee-bearing vault | Fee-exclusive nested-vault valuation can overstate realizable assets |
| DF-14 | Low | Confirmed operational weakness | `4580174c...` snapshot only | The exact-peg emergency minimum can block separated-role recovery |
| DF-15 | Low | Confirmed configuration footgun | Both snapshots | Restoring the report buffer can mint fee shares without an economic gain |
| DF-16 | Low | Confirmed, market-conditional | Both snapshots | Queue accounting mixes nominal request value with actual claim proceeds |
| DF-17 | Low | Confirmed operational weakness | `4580174c...` snapshot only | The Strategy4626 unwind helper is not amount-safe across edge states |
| DF-18 | Low | Confirmed | Both snapshots | Zero-supply residual assets can be captured by the next depositor |
| DF-19 | Medium | Executable model PoC, configuration-conditional | Both snapshots | Report-buffer haircuts recursively reopen deposit capacity |
| DF-20 | Low | Code-trace-only, external-limit-conditional | Both snapshots | Lido withdrawal requests are not bounded or split to the queue's accepted range |
| DF-21 | Low | Code-trace-only, external-state-conditional | Both snapshots | Advertised capacity ignores Lido's live direct-staking limit |

## Confirmed and Reportable Findings

### DF-01: Loss-producing unwinds expose WETH before share accounting records the loss

- Severity: Medium
- Confidence: High
- Status: Confirmed by executable PoC and independent source trace

`manualSwapToAsset()` and the emergency unwind path can convert stETH-side value into less WETH than the previously recorded nominal value. The resulting WETH immediately increases `availableWithdrawLimit()`, while TokenizedStrategy's stored `totalAssets` and share price remain unchanged until the next report. A user who redeems in that interval receives value using stale pre-loss pricing and shifts a disproportionate share of the loss to remaining shareholders.

The path requires management or emergency-role action to create the WETH and a user withdrawal before the loss-recording report. The privileged first step reduces likelihood but does not remove the permissionless loss-shifting exit once liquid WETH is exposed.

The extended adversarial suite also exercised the two authorized-loss extremes on `4580174c...`. Management can pass `_minOut = 0` to `manualSwapToAsset()` and accept a zero-output conversion, while setting `reportBuffer = MAX_BPS` makes the emergency minimum zero and permits the emergency role to do the same. These variants do not create a separate family because they share DF-01's privileged loss-production root, but they show that the later snapshot's buffer bound still permits the baseline zero-floor condition to be recreated through valid configuration.

Affected paths:

- `src/BaseLSTAccumulator.sol`: `availableWithdrawLimit`, `_harvestAndReport`, `_emergencyWithdraw`, `manualSwapToAsset`
- `src/Strategy.sol`: LST-to-WETH swap implementation
- inherited TokenizedStrategy withdrawal accounting

Provenance:

- dot-context `M-02` — Medium, PoC-backed
- solidity-auditor `F-01` — Medium, validated trace
- Human Pages downgraded note, "Management manual swaps can create stale-accounting withdrawal windows" — same mechanics, calibrated as trusted sequencing risk
- human-pages-sol `HP-V6` — Medium, production-fork PoC confirmed that the first of two equal holders can exit at stale value after a lossy Curve unwind
- Plamen Core baseline `M-08` — contested, code-trace-only confirmation that the baseline emergency path supplied zero as Curve's output floor; no forked sandwich or realized loss was executed, so it is retained only as a DF-01 loss/slippage amplifier rather than independent proof
- Plamen Thorough `M-11` — contested code trace of the adjacent nominal one-to-one LST valuation premise; no live impairment or separate cohort-loss sequence was executed, so it adds context rather than a new family
- extended adversarial properties `CONV-03` and `CONV-05` — deterministic counterexamples `test_exposes_managementCanAuthorizeUnboundedManualSwapLoss` and `test_exposes_reportBufferCanAuthorizeTotalEmergencyLoss` consumed the entire modeled stETH position for zero WETH under valid role and parameter calls

Recommended remediation:

- Prevent newly unwound WETH from increasing the withdrawal limit until accounting is refreshed.
- Prefer an atomic unwind-and-report operation, or set a stale-accounting flag cleared only by a successful report.
- Require bounded slippage for emergency conversions where operationally possible.

### DF-02: Report and tend can re-stake shutdown liquidity or bypass the staking disable state

- Severity: Medium
- Confidence: High
- Status: Confirmed for the shutdown path; flag-only variant has intent ambiguity

TokenizedStrategy permits reporting and tending after shutdown. `_harvestAndReport()` and `_tend()` can still call `_stake()` without checking shutdown. As a result, WETH freed for emergency withdrawals can be converted back to stETH or downstream-vault exposure, reducing user `maxRedeem` and undoing incident recovery.

The same call sites also ignore `stakeAsset == false`. Codex Security treated that as a Low management-versus-keeper control bypass, while the solidity-auditor and Nemesis runs observed that an existing test explicitly expects report-time staking with the flag disabled. The synthesis therefore treats shutdown re-staking as the reportable Medium issue and retains the flag-only behavior as an intent/documentation variant, not a separate finding.

Both 5.6 Sol runs calibrated the shutdown report/tend variants as Low because the trigger is keeper-gated. The synthesis retains Medium as the highest applicable severity because the baseline PoCs demonstrate that the action can reverse emergency recovery and remove immediately withdrawable liquidity.

The strategy-review-agent blind benchmark rated the same root High after reproducing both report and direct-tend redeployment following shutdown. Its Strategy4626-specific tend regression additionally set `stakeAsset = false` and `depositLimit = 0`, proving that those configuration stops and the tend-trigger fix do not constrain a direct keeper call. The synthesis retains Medium after reconciliation because the harmful call remains keeper-gated and the new test sharpens, but does not expand, the already demonstrated blast radius.

Affected paths:

- `src/BaseLSTAccumulator.sol`: `_harvestAndReport`, `_tend`, `setStakeAsset`
- `src/Strategy.sol` and `src/Strategy4626.sol`: staking implementations
- inherited TokenizedStrategy shutdown/report/tend behavior

Provenance:

- dot-context `M-03` — Medium, PoC-backed
- Human Pages `HP-M-01` — Medium, PoC-backed
- Codex Security `csf_aade44b3010a30d567b45109` — Low, focused fork-test confirmation of the `stakeAsset` variant
- solidity-auditor demoted trail, "stakeAsset not honored by report/tend" — treated as intended when isolated from shutdown
- 5.6 Sol Codex Security `csf_d9b4fe4044f8f96d22efd58a` and `csf_c5a9e2a967e22583d8780558` — separate report and tend findings, both Low due keeper gating
- 5.6 Sol solidity-auditor `VL-02` — conditional lead due the same trusted-role precondition
- dot-context-sol `M-01` — Medium, mainnet-fork PoC showed report consuming more than 99% of emergency-freed idle WETH while shutdown remained active
- human-pages-sol `HP-V1` — Medium, production-fork PoCs independently confirmed both tend and report variants
- Plamen Core baseline `M-06` — Medium in the source report, but code-trace-only and unexecuted; corroborates that report and tend remain shutdown-insensitive
- ZeroSkills `ZS-01` — Medium; a pinned-fork disposable regression confirmed that a post-shutdown report re-stakes emergency-freed WETH and reduces withdrawal liquidity to zero
- Plamen Thorough `M-06` — final code trace of the same staking-disable and capacity bypass; its Foundry invariant campaign separately minimized a one-call `stakeAsset=false` counterexample without promoting it to end-to-end harm proof
- strategy-review-agent blind `F-01` plus comment-aware replay — source-rated High; fixed-block PoCs independently confirmed report redeployment and direct tend after shutdown, including the `stakeAsset=false` and `depositLimit=0` bypass. Issue #714 and #765 context confirms report restaking was intentional, while the claimed tend mitigation changed only trigger signaling.
- extended adversarial properties `DEPLOY-02` through `DEPLOY-05` — deterministic regressions covered report and direct-tend bypass of `stakeAsset`, direct tend with zero configured capacity, direct-tend failure while Lido is paused, and post-shutdown redeployment into both direct stETH and nested-vault exposure; the shutdown and flag variants map here, while the pause-only behavior remains a liveness extension

Recommended remediation:

- Skip `_stake()` from report when shutdown.
- Make tend a no-op or revert when shutdown.
- Clarify whether `stakeAsset` is deposit-only; otherwise apply it consistently or introduce a separate explicit maintenance-staking switch.

### DF-03: Strategy4626 deposits its full loose wstETH balance without enforcing live vault capacity

- Severity: Medium
- Confidence: High for the donation path; Medium for capacity variants
- Status: Confirmed by disposable PoC and independent trace

`Strategy4626._stake()` wraps loose stETH and then deposits the strategy's entire loose wstETH balance into the downstream ERC4626 vault. `availableDepositLimit()` checks `vault.maxDeposit(address(this))` only when calculating new WETH intake; the actual `vault.deposit()` sink is not capped by the vault's current remaining capacity.

An unauthenticated account can donate wstETH to the strategy. If the downstream vault has little or no capacity, a later report, tend, user deposit deployment, or manual stake attempts to deposit the donated balance and reverts. Related variants arise when pre-existing loose WETH is swept with a new deposit or a favorable Curve fill produces more wstETH than the precomputed limit anticipated.

The 5.6 Sol runs calibrated these availability paths as Low, while the baseline Codex Security and solidity-auditor runs rated the permissionless donation path Medium. The table retains Medium as the highest applicable rating and records the 5.6 Sol calibration here.

Affected paths:

- `src/Strategy4626.sol`: `_stake`, `availableDepositLimit`
- `src/BaseLSTAccumulator.sol`: `_harvestAndReport`, deposit-limit plumbing
- inherited TokenizedStrategy deposit sweep of loose WETH

Provenance:

- Codex Security `csf_7dc94802bf292fbeefd70a6f` — Medium, disposable Foundry PoC
- solidity-auditor `F-03` — Medium, validated forced-wstETH path
- solidity-auditor `L-02` — favorable-fill capacity variant
- Human Pages `HP-C-01` — pre-existing loose-WETH capacity variant
- 5.6 Sol Codex Security `csf_5236c2f55c0be4d5a012af25` — live-cap overshoot after route surplus or balance aggregation
- 5.6 Sol Codex Security `csf_2908870927c06eae78c8a5a4` — amount-scoped staking sweeps unrelated loose balances
- 5.6 Sol solidity-auditor `VF-03` and `VL-03` — final-deposit and direct-tend capacity variants
- dot-context-sol `L-01` — Low after PoC calibration; donated loose wstETH exceeded a mutable downstream live cap by one wei and repeatedly blocked reports
- Plamen Core baseline `M-07` — Medium in the source report, but final evidence remained code-trace-only after its integration harness failed to initialize; maps to the same zero-capacity loose-wstETH deposit path
- ZeroSkills `ZS-04` — Low; a pinned-fork disposable regression removed nested-vault capacity, donated one wei of wstETH, and reproduced `ERC4626: deposit more than max` on the next report
- Plamen Thorough `M-04` and `L-08` — split the same root into terminal sink enforcement and advertised-capacity accounting; a local invariant minimized the zero-capacity-plus-one-wei branch, while the final findings remained `CODE-TRACE`
- extended adversarial property `V4626-03` — `test_exposes_looseWstethMakesAdvertisedDepositUnexecutable` advertised 5 WETH of room while 1 WETH of loose wstETH already consumed the downstream vault's remaining capacity, then reproduced an atomic deposit revert

Recommended remediation:

- Immediately before `vault.deposit`, read `vault.maxDeposit(address(this))` and cap the actual wstETH amount.
- Skip the vault deposit when capacity is zero and leave surplus wstETH loose and accounted.
- Subtract already-loose deployable balances from intake limits, or deploy only the amount attributable to the current deposit.

### DF-04: Zero profit locking allows pre-report deposits to capture accrued yield

- Severity: Medium when deposits are open and unreported gains are material
- Confidence: High on mechanics; Medium on deployment likelihood
- Status: Confirmed mechanism with deployment conditions

`Strategy4626Factory.newStrategy4626()` sets `profitMaxUnlockTime` to zero. Deposits mint shares against the last reported accounting value. A depositor who enters immediately before a predictable positive report receives shares before accrued stETH or vault yield is recognized, then participates in the entire immediate PPS increase. Existing holders are diluted by yield that accrued before the new deposit.

The extraction requires open deposits, material unreported gains, and timing around a report. Those conditions should be confirmed for each deployment before final severity is fixed.

Affected paths:

- `src/Strategy4626Factory.sol`: `newStrategy4626`
- `src/BaseLSTAccumulator.sol`: report accounting
- `src/Strategy4626.sol`: vault-value reporting
- inherited TokenizedStrategy deposit and profit-locking logic

Provenance:

- dot-context `M-01` — Medium, PoC-backed
- Human Pages `HP-C-02` — conditional Medium, source-traced
- human-pages-sol `HP-V7` — Medium, production-fork PoC quantified about 9 WETH of captured preexisting yield for a 900 WETH pre-report deposit against 100 WETH of incumbent assets
- Plamen Core baseline appendix `I-01` — contested and mechanically demoted after `POC-FAIL`; mapped for source completeness only and not counted as corroborating proof
- Plamen Thorough `M-14` — contested; a fork test confirmed only the zero profit-unlock configuration, not the late-depositor capture sequence, so it adds no proof beyond `HP-V7`

Recommended remediation:

- Preserve a non-zero profit-unlock period by default.
- If zero unlock is intentional, close deposits around material reports or report immediately before reopening deposits.

## Confirmed Queue-Cap Finding

### DF-05: Pending Lido redemptions are omitted from deposit-limit accounting

- Severity: Low
- Confidence: High
- Status: Confirmed by both 5.6 Sol runs against `4580174c...`, including a temporary lifecycle check

`estimatedTotalAssets()` counts loose WETH and directly held LST value but not `pendingRedemptions`. Initiating a Lido withdrawal transfers stETH out and increments the scalar pending amount. Until the request is claimed, the strategy can appear to have unused capacity even though the queued value remains economically attributable to it. New deposits can fill that temporary apparent headroom and cause total exposure to exceed the configured `depositLimit` after the queued withdrawal is claimed.

The strategy-review-agent blind benchmark rated this Medium after demonstrating a full-cap position, queue transfer, reopened capacity, refill, and held-plus-pending exposure above the cap. The synthesis retains Low because initiating and repeating the queue transition requires management and the control is a risk/TVL cap rather than share-price accounting; the stronger source rating is retained as a severity disagreement.

Provenance:

- baseline solidity-auditor `F-02` — Low/Medium, validated source trace
- 5.6 Sol Codex Security `csf_7f9d7622a90752f126134dd1` — Low, final report finding
- 5.6 Sol solidity-auditor `VF-08` — Low; a temporary lifecycle check filled a 100 WETH cap, queued the full LST balance, observed reopened room, refilled it, and confirmed held-plus-pending exposure above the cap
- ZeroSkills `ZS-03` — Low; a disposable regression independently filled a 10 WETH cap, queued essentially all LST, refilled the reopened room, and confirmed both stored and economic assets above the cap
- Plamen Thorough `M-01` — final `POC-PASS`; a 100-unit boundary test and 256-case fuzz variant independently reopened and refilled capacity until economic exposure reached twice the configured cap
- strategy-review-agent blind `F-04` — source-rated Medium; a fixed-block PoC independently reproduced the full-cap queue/refill lifecycle and asserted pending-plus-active economic exposure above the configured cap
- extended adversarial property `QUEUE-08` — `test_exposes_pendingWithdrawalReopensDepositCapacity` reproduced the same omission in the deterministic request-NFT model, with 4 WETH of queued principal reopening 4 WETH of capacity

Recommended remediation:

- Include `pendingRedemptions` in cap-side asset accounting, or return zero deposit capacity while a redemption is pending.

## Low-Severity Findings and Operational Weaknesses

### DF-06: Lido withdrawal initiation and claim use incompatible ABI shapes

- Severity: Low
- Confidence: High
- Status: Confirmed by PoC and multiple independent traces

The initiation path returns `abi.encode(uint256[] requestIds)`, while the claim path decodes the supplied bytes as a scalar `uint256`. Passing the initiation bytes directly to claim decodes the dynamic-array offset `0x20` as request id `32`. The current tests and a knowledgeable keeper can work around the mismatch by decoding the array and re-encoding its first element, but the natural bytes handoff is not round-trippable. A failed handoff leaves `pendingRedemptions` nonzero and blocks reports until corrected.

Provenance:

- dot-context `L-01`
- Human Pages `HP-M-02` — PoC-backed Medium before synthesis calibration
- Nemesis `NEM-002`
- solidity-auditor `L-01`
- Codex Security candidate `CS-351C58EB-001` — validation summary marked reportable, but it was not included in the final `findings.json`
- 5.6 Sol solidity-auditor `VF-02` — direct-replay validation and ABI checks
- Plamen Core baseline `M-04` — code-trace finding with a passing ABI-decoding check; no external queue lifecycle was executed
- Plamen Thorough `M-03` — final code trace of the same initiation/claim shape mismatch; its generated unit check exercised local decode behavior but not the external queue lifecycle
- ZeroSkills `ZS-02` — Low; `cast` confirmed that direct array-as-scalar decoding returns request id 32, while all seven queue tests passed only through explicit decode/re-encode handling
- strategy-review-agent blind `F-05` plus comment-aware replay — Low; a direct-forward PoC reproduced request id 32 and then succeeded through the hidden decode/re-encode adapter. Issue #714 shows that the shape mismatch was previously reported and intentionally retained for off-chain handling, so this is corroboration and integration-documentation risk rather than a novel defect.
- extended adversarial property `QUEUE-01` — `test_exposes_initiationResponseClaimsDifferentRequestNft` created request IDs 32 and 33, forwarded the second initiation response directly, and proved that the scalar decoder claimed request 32 while leaving the intended request NFT live

Severity reconciliation: Low is retained because the path is privileged and operators can transform the data or use emergency/manual recovery. The interface mismatch itself is fully demonstrated.

Recommended remediation:

- Return scalar-encoded claim data when only one request is supported, or make both sides use a typed `uint256[]` shape.
- Add a regression test that passes initiation return data directly to the claim function.

### DF-07: Strategy4626 emergency withdrawal does not unwind its normal vault-held position

- Severity: Low
- Confidence: High on mechanics
- Status: Confirmed operational weakness; downgraded because manual recovery exists

The inherited emergency withdrawal path only checks directly held stETH. A normal Strategy4626 position is primarily held as downstream ERC4626 shares or loose wstETH, so the standard callback can complete without materially freeing the deployed position. Emergency-authorized operators can still call `manualRedeem()` and `manualUnwrap()` before swapping, making this a multi-step runbook hazard rather than an unrecoverable fund lock.

Provenance:

- dot-context `M-04` — PoC-backed Medium
- Human Pages downgraded note, "Strategy4626 emergencyWithdraw only handles loose stETH/dust" — PoC-backed Low operational note
- solidity-auditor `L-03`
- Plamen Core baseline `M-05` — code-trace-only baseline corroboration; no integration PoC was executed

Severity reconciliation: the PoC confirms the standard emergency callback is ineffective, but explicit manual recovery helpers materially reduce impact and justify Low unless deployment runbooks assume a one-call unwind.

Version note: `4580174c...` adds a Strategy4626 emergency-withdraw override, fixing this exact baseline defect. Distinct edge cases in the replacement helper are tracked as DF-17.

Recommended remediation:

- Override Strategy4626 emergency withdrawal to redeem and unwrap enough vault-held value before invoking the base swap, or formally document and test the required manual sequence.

### DF-08: `reportBuffer > MAX_BPS` underflows valuation and report paths

- Severity: Low
- Confidence: High
- Status: Confirmed management configuration footgun

`setReportBuffer()` accepts any `uint256`, but `estimatedTotalAssets()` calculates `MAX_BPS - reportBuffer`. Values above 10,000 revert under Solidity checked arithmetic and can break valuation, deposit-limit, and report calls until management corrects the setting.

Provenance:

- Nemesis `NEM-001`
- solidity-auditor `L-05`
- Human Pages factory/configuration downgraded note

Version note: `4580174c...` adds `require(_reportBuffer <= MAX_BPS)`, fixing this exact underflow footgun on `review-sol-update`.

Recommended remediation:

- Require `reportBuffer <= MAX_BPS`, with a tighter maximum if only small valuation discounts are intended.

### DF-09: StrategyAprOracle returns a constant APR independent of strategy state and debt delta

- Severity: Low if deployed in allocation infrastructure; otherwise Informational
- Confidence: High on implementation, Medium-Low on integration impact
- Status: Deployment-conditional

`aprAfterDebtChange(address,int256)` ignores both inputs and always returns `4e16`. If used by production allocation tooling, it can advertise a positive 4% APR for shutdown, capacity-constrained, or unsupported strategies and for arbitrary debt deltas. No in-repo value-moving consumer or confirmed production registration was identified.

Provenance:

- dot-context `L-02`
- Nemesis `NEM-003`
- solidity-auditor demoted trail, "Fixed StrategyAprOracle APR"
- Codex Security candidate `CS-351C58EB-005` — deferred because production registration was not established
- 5.6 Sol solidity-auditor `VF-07` — Low at confidence 75 after repository-consumer searches found no local allocator integration
- Plamen Core baseline `M-02` — executable property test confirmed that distinct strategies and opposite debt deltas both return `4e16`; production registration remains unproven
- Plamen Thorough `M-07` appendix and invariant `FUZZ-1` — reconfirmed constant output across state changes, but found no production consumer and did not promote the issue into the client report body

Recommended remediation:

- Mark the oracle as non-production, or implement capacity-, state-, and delta-aware APR behavior with zero returns for unavailable strategies.

## Conditional Trust-Boundary Findings

### DF-10: Strategy4626 fully trusts the selected ERC4626 vault without local output or NAV guards

- Severity: Conditional; Medium for arbitrary or manipulable vaults, Low/Informational for vetted vaults
- Confidence: Medium-Low
- Status: Trust boundary, not proven against a configured production vault

Strategy4626 verifies that the downstream vault's asset is wstETH but otherwise trusts `deposit`, `convertToAssets`, `previewWithdraw`, `maxRedeem`, and `redeem`. The deposit path ignores returned shares and has no local minimum-share check. A malicious or non-standard selected vault could donate principal, distort reported NAV, or block exits.

The extended campaign adds a standards-compatible donation/virtual-share variant rather than relying only on a deliberately hostile vault. After a direct donation inflated the downstream vault's assets-per-share, a report redeposited loose wstETH and reduced the strategy's recoverable value by exactly 32,687,008,448 wei in the minimized fixture. This proves local value drift from an ordinary ERC-4626 rounding mechanism, but it does not establish the same parameters against the configured production vault or show an economically profitable attack. Separate zero-share-mint and short-return mocks deliberately violate normal vault behavior and remain trust-boundary stress tests.

Provenance:

- Human Pages `HP-C-03`
- 5.6 Sol solidity-auditor `VL-08` and `VL-11` — zero-share and arbitrary-vault variants
- human-pages-sol `HP-V4` — conditional mock PoCs demonstrated both fee-socialized loss and a non-migratable zero-redemption-capacity lock; no claim was made about the scripted vault's current behavior
- Plamen Core baseline `M-01` — local malicious-vault unit PoC demonstrated unlimited wstETH allowance use and attacker-controlled `convertToAssets()` valuation after permissionless factory deployment; impact still requires funds to reach that attacker-selected strategy
- Plamen Thorough `M-15` and `M-17` — final code traces split the same trust boundary into ignored deposit output and arbitrary-vault deployment variants; neither executed a new funded-vault exploit
- extended adversarial properties `V4626-02`, `V4626-07`, and `V4626-09` — executable zero-share, short-return, and standards-compatible donation/virtual-share counterexamples; only `V4626-09` avoids deliberately noncompliant vault behavior, and none establishes the configured production vault's susceptibility or attacker profitability

Recommended remediation:

- Restrict deployment to reviewed vaults or per-vault adapters.
- Check returned shares against a minimum and test zero-share deposits, manipulated NAV, and zero-redeem-capacity behavior.

### DF-11: Permissionless factory deployment can populate one-shot registry state for unreviewed vaults

- Severity: Informational
- Confidence: High on behavior, Low on security impact
- Status: Operational and indexing risk

Anyone can call `newStrategy4626()` for a vault whose asset is wstETH. The caller does not gain strategy privileges, and management must still accept the strategy, but the factory immediately records a single deployment using the current role defaults. Later changes to those factory defaults do not rotate roles on existing strategies. Off-chain consumers must not interpret the factory mapping or event as management endorsement of the underlying vault, and operators must treat deployed role assignments as independent lifecycle state.

Provenance:

- solidity-auditor `L-04`
- 5.6 Sol solidity-auditor `VL-10` and `VL-11` — stale role-snapshot and arbitrary-vault registry variants
- Plamen Core baseline `M-01` — corroborates permissionless arbitrary-vault deployment, but does not show that factory registration alone transfers funds or constitutes management endorsement
- Plamen Thorough `M-05` and `M-17` — code-trace role-snapshot and arbitrary-vault variants; no unauthorized action or registry-to-funding path was executed

Recommended remediation:

- Add a management allowlist or reservation step, or expose a separate endorsement state that indexers and allocators can distinguish from permissionless creation.
- Provide an explicit existing-strategy role-rotation workflow and verify post-deployment assignments independently of mutable factory defaults.

## 5.6 Sol Run Additions

### DF-12: A small accepted deposit can redeploy WETH prepared for existing-holder withdrawals

- Severity: Medium
- Confidence: High
- Status: Confirmed with an ordinary-depositor trigger and focused fork test

The inherited deposit path calls the strategy deployment hook with the full post-transfer WETH balance, not only the assets received from the current depositor. `_deployFunds()` forwards that aggregate balance to `_stake()` when staking is enabled. A small open-mode or allowlisted deposit can therefore re-stake a much larger WETH balance that management or a keeper had left liquid for existing-holder withdrawals.

This differs from DF-02 because no post-shutdown keeper action is required. It also differs from DF-03 because the primary impact is consumption of reserved withdrawal liquidity, not downstream-vault capacity failure. The same inherited full-balance callback exists in both reviewed snapshots.

Provenance:

- 5.6 Sol solidity-auditor `VF-01` — Medium at confidence 75; access-control and 256-run withdrawal-limit checks passed
- 5.6 Sol Codex Security `csf_07fb06eefe8dd302ec047d0d` — Low; focused fork test reproduced a tiny accepted deposit re-staking prepared WETH
- ZeroSkills `ZS-01` — Medium source finding merged both liquidity-relocking variants; its ordinary-depositor regression showed a 1,001-wei deposit consuming a pre-existing roughly 10 WETH withdrawal buffer

Recommended remediation:

- Scope deposit-time deployment to the newly received amount or preserve an explicit idle-liquidity reserve.
- Add regression tests where a small deposit arrives after WETH has been prepared for withdrawals.

### DF-13: Fee-exclusive nested-vault valuation can overstate realizable assets

- Severity: Medium when a fee-bearing downstream vault is accepted
- Confidence: High on mechanics; deployment-conditional
- Status: Confirmed with a fee-bearing harness; not observed for the configured Yearn vault

Strategy4626 values downstream shares using `convertToAssets()` and carries that gross figure into `estimatedTotalAssets()` and report accounting. A standards-compatible vault may charge an exit fee such that realizable redemption proceeds are lower than the ideal conversion value. If such a vault is selected and funded, the strategy can commit overstated shareholder value and only recognize the shortfall during redemption, deferring or shifting the loss.

The configured Yearn vault used by the solidity-auditor checks returned equal `convertToAssets` and `previewRedeem` values at the pinned block. The Codex Security harness independently reproduced a 100-to-90 fee gap, report commitment, and insufficient-buffer case. This remains conditional on actual vault selection.

Provenance:

- 5.6 Sol Codex Security `csf_46d2a8b0062d1f2a0e5d1795` — Medium, four focused fee-valuation tests
- 5.6 Sol solidity-auditor `VL-09` — conditional lead because the configured vault was fee-free at the checked block
- human-pages-sol `HP-V4` — conditional Medium mechanism; an interface-valid 10% fee vault caused gross booking and socialized loss in the verifier harness
- Plamen Thorough `M-16` — final code trace of gross `convertToAssets()` valuation without a realizable-redemption guard; no fee-bearing production vault was identified

Recommended remediation:

- Value downstream shares using a fee-aware realizable-redemption preview or a vetted per-vault adapter.
- Enforce vault-selection invariants and test fee-bearing ERC4626 implementations before deposits are enabled.

### DF-14: The exact-peg emergency minimum can block separated-role recovery

- Severity: Low
- Confidence: High
- Status: Confirmed on the `4580174c...` snapshot reviewed by the 5.6 Sol runs

Compared with the baseline snapshot, `4580174c...` uses a minimum derived from `reportBuffer` in `_emergencyWithdraw()`. Because the buffer defaults to zero, the emergency swap initially requires nominal one-for-one stETH output. When Curve quotes below par, a distinct emergency administrator can enter the recovery path but cannot relax the management-only buffer, so recovery reverts until management cooperates or market conditions improve.

The same shared parameter has the opposite unsafe extreme: the extended suite set `reportBuffer` to the permitted maximum and executed a zero-output emergency conversion. The default-zero liveness failure remains the canonical DF-14 issue, while the maximum-buffer loss case maps to DF-01 and reinforces the recommendation to separate accounting conservatism from a tightly bounded emergency-slippage control.

This mechanism does not apply to the baseline `521fff28...` snapshot, whose emergency swap uses a zero minimum. It is introduced by the `4580174c...` emergency-slippage change.

Plamen Core baseline `M-08` examined the opposite extreme: the baseline's zero floor. It confirmed that value is forwarded in source but did not execute a forked sandwich or prove searcher profit. The later commit therefore closes the zero-floor condition while introducing the exact-peg recovery-liveness trade-off captured here.

Provenance:

- 5.6 Sol Codex Security `csf_2fb78692d339540f18df9133` — Low; focused production-linked harness reproduced failure at 99% output and success after a 100-basis-point buffer
- 5.6 Sol solidity-auditor `VL-01` — conditional lead due emergency-role gating
- dot-context-sol `L-03` — Low; source and repository-test configuration confirmed the default exact-par requirement
- human-pages-sol `HP-V2` — conditional Medium at the source level; production-fork verification observed a below-par quote, default unwind failure, emergency-role access failures, and management-assisted recovery
- Plamen Thorough `M-10` — final code trace of the same buffer-derived floor and separated-role recovery dependency; its intended fork execution was blocked, so it adds corroboration rather than new proof
- strategy-review-agent blind `F-02` plus comment-aware replay — source-rated High; at mainnet block `25533225`, Curve quoted `0.999797856520084312` ETH per stETH and the default-buffer emergency regression reverted. Comment chronology confirms the reviewer-requested slippage fix left a zero default, management-only configuration, and no deployment initialization.

Severity reconciliation: the strategy-review-agent benchmark rated the separated-role outage High and human-pages-sol rated it Medium under management loss, while the other 5.6 Sol sources retained Low because no attacker is required or profits and a healthy management key or later market recovery restores the path. The synthesis retains Low and records the stronger conditional impact here.

Recommended remediation:

- Give the emergency path a separately bounded slippage parameter that the emergency role can use within a management-approved ceiling.
- Set a non-zero safe default during deployment and test below-peg emergency recovery with separated roles.

### DF-15: Restoring the report buffer can mint fee shares without an economic gain

- Severity: Low
- Confidence: High
- Status: Confirmed management configuration footgun

`reportBuffer` directly discounts reported LST value. Raising it records an accounting loss; restoring it later records an apparent profit even when no assets moved. If performance fees are enabled, inherited report accounting can mint fee shares against that synthetic recovery and dilute holders without an economic gain.

The mechanism exists in both snapshots. The bound present at `4580174c...` fixes the out-of-range underflow in DF-08 but still permits management to cycle valid in-range buffer values.

Provenance:

- 5.6 Sol solidity-auditor `VF-09` — Low; a temporary fork check used a 10% performance fee, moved no assets between reports, and observed fee-recipient shares after restoring the buffer

Recommended remediation:

- Treat buffer changes as valuation-policy changes that cannot generate fee-bearing profit.
- Reset or separately account for the synthetic valuation delta when the buffer changes.

### DF-16: Queue accounting mixes nominal request value with actual claim proceeds

- Severity: Low
- Confidence: High on accounting mechanics; market-conditional on discounted proceeds
- Status: Confirmed mechanism with conditional production trigger

Queue initiation adds nominal requested stETH to `pendingRedemptions`, while claim completion subtracts the actual native-asset payout. If actual proceeds are below nominal, a residual remains and blocks report, but the received WETH is immediately exposed through `availableWithdrawLimit()`. A shareholder can redeem using stale pre-loss share pricing and shift part of the queue haircut to remaining holders.

The same aggregate ledger creates adjacent recovery hazards: management can clear pending state before a later principal recovery, a partial manual claim batch can zero the whole aggregate, and later proceeds can be measured as profit. Those variants require additional role actions or health-check changes and remain conditional extensions of the canonical nominal-versus-actual mismatch.

Provenance:

- 5.6 Sol Codex Security `csf_e74ae140bceefd722ddf44dc` — Low; offline model reproduced a 100-for-90 claim and asymmetric holder outcomes
- 5.6 Sol solidity-auditor `VL-04` and `VL-05` — residual-pending and stale-withdrawal variants
- 5.6 Sol solidity-auditor `VL-06` and `VL-07` — early-clear and partial-batch conditional variants
- dot-context-sol `L-02` — Low; source validation confirmed that actual claim proceeds can leave a report-blocking remainder
- human-pages-sol `HP-V6` — Medium for the broader stale-loss exit-ordering root; its queue under-settlement variant is treated here as an amplifier of the same nominal-versus-actual mismatch
- Plamen Core baseline `M-03` — final report evidence tag remained `CODE-TRACE`; its focused unit harness passed for a 100 nominal / 99 received postcondition and report revert, but no external loss-bearing queue settlement was executed
- Plamen Thorough `M-02`, `M-09`, and `M-12`, including the absorbed `M-13` trail — final code traces extend the same root through stale withdrawal pricing, aggregate clearing, and unbound request identifiers; no end-to-end external discounted settlement was executed
- ZeroSkills `ZS-L1` — Informational/Low conditional lead only; source tracing confirmed the nominal-versus-actual subtraction, but the exact-payout repo mock could not establish a live discounted settlement
- extended adversarial properties `QUEUE-03`, `QUEUE-04`, and `QUEUE-07` — a fuzzed discounted full claim left only the haircut as stale pending state, while empty and subset batch claims proved that authorized callers can clear aggregate accounting without consuming every live request NFT

Recommended remediation:

- Track each request's nominal amount and settlement status separately from actual proceeds.
- Reconcile the loss before claim proceeds become withdrawable and prevent aggregate clearing unless every live request is accounted for.

### DF-17: The Strategy4626 unwind helper at `4580174c...` is not amount-safe across edge states

- Severity: Low
- Confidence: High on source mechanics
- Status: Confirmed operational weaknesses on the `4580174c...` snapshot reviewed by the 5.6 Sol runs

The `4580174c...` snapshot includes a Strategy4626 emergency override and `_freeStETH()` helper, fixing DF-07 relative to the baseline. That path has three distinct amount-handling defects:

- a large emergency request against mixed loose stETH and wrapped exposure can unwind only part of the wrapped position in one call;
- when vault redemption room and loose wstETH are both zero, execution still calls production `wstETH.unwrap(0)`, which reverts;
- for a small shortfall, the helper unwraps the entire loose wstETH balance rather than only the calculated requirement.

These paths are privileged and recoverable, so they remain Low, but they complicate emergency runbooks and make an amount-scoped helper transform more exposure than requested.

The extended suite sharpened the first case in two ways. A full emergency request left downstream vault shares solely because one extra unit of loose stETH already satisfied the helper's local target, and `manualRedeem(type(uint256).max)` reverted without progress when the vault exposed only partial redemption capacity. Both are additional manifestations of the existing amount-safety and recovery-progress root.

Provenance:

- 5.6 Sol solidity-auditor `VF-04` — mixed-balance partial unwind
- 5.6 Sol solidity-auditor `VF-05` — pinned production call confirmed `unwrap(0)` reverts
- 5.6 Sol solidity-auditor `VF-06` — full-loose-balance unwrap instead of shortfall
- human-pages-sol `HP-V4` — a blocked-redemption vault harness independently reached the zero-amount unwrap revert and confirmed that the immutable vault shares remained trapped
- Plamen Thorough `L-03`, `L-04`, and `L-09` — final code traces independently split the replacement helper into partial-unwind, full-loose-balance, and zero-amount-call edge cases
- strategy-review-agent comment-aware `CA-01` — Low; a fixed-block test established a vault position, added already-liquid stETH, forced `maxRedeem == 0`, and reproduced canonical wstETH's zero-unwrap revert before the caller's partial-recovery `Math.min` branch could sell the liquid balance
- extended adversarial properties `V4626-05` and `V4626-08` — `test_exposes_manualRedeemIgnoresPartialVaultLiquidity` proved the manual helper does not cap to live redemption room, and `test_exposes_fullEmergencyUnwindLeavesVaultSharesWithLooseSteth` proved a nominal full unwind can leave the vault layer deployed

Recommended remediation:

- Compute the total target once across loose stETH, loose wstETH, and redeemable vault shares.
- Skip zero-amount wrapper calls and unwrap only the exact bounded shortfall.
- Add mixed-balance, zero-capacity, and excess-loose-balance emergency tests.

### DF-18: Zero-supply residual assets can be captured by the next depositor

- Severity: Low
- Confidence: High
- Status: Confirmed with a production-fork PoC; rare multi-party sequence

TokenizedStrategy converts assets to shares one-for-one when effective supply is zero without checking whether the strategy still controls residual assets. A conservative report can let all existing shares redeem their cached value while a favorable manual unwind leaves additional loose WETH behind. Once supply and cached `totalAssets` both reach zero, the next depositor becomes the sole shareholder; a later report assigns the orphaned WETH to that depositor.

The human-pages-sol verifier created the full sequence without storage mutation: a 5% buffered 100 WETH position was unwound near par, all old shares redeemed, and more than 3 WETH remained at zero supply and zero cached assets. A subsequent 10 WETH depositor captured more than half of that residual after report. The conditional gain is material, but the need for a conservative report, favorable settlement, a complete prior exit, a new deposit, and keeper reporting keeps likelihood Low.

The zero-supply conversion branch comes from the same pinned TokenizedStrategy implementation, and the conservative-report/manual-unwind sequence exists in both reviewed snapshots. The `4580174c...` source changes do not introduce or remove this root.

Affected paths:

- inherited TokenizedStrategy zero-supply share conversion and deposit accounting
- `src/BaseLSTAccumulator.sol`: buffered valuation and report accounting
- `src/Strategy.sol`: manual LST-to-WETH unwind

Provenance:

- human-pages-sol `HP-V8` — Low, production-fork PoC with a measurable orphan and next-depositor capture
- Plamen Thorough `L-10` — contested code-trace variant involving temporarily unaccounted native ETH; no inherited share-pricing or capture sequence was executed

Recommended remediation:

- Reject zero-supply deposits while any strategy-controlled asset remains.
- Alternatively, reconcile or sweep residual value to a defined beneficiary before minting the new initial supply.

## Plamen Thorough Run Additions

### DF-19: Report-buffer haircuts recursively reopen deposit capacity

- Severity: Medium when `depositLimit` is intended as a hard gross-exposure cap
- Confidence: High on arithmetic and deterministic execution; Medium on deployment impact
- Status: Confirmed by executable model PoC; configuration intent remains conditional

`estimatedTotalAssets()` discounts LST-side value by `reportBuffer`, and Strategy4626 derives remaining deposit room by subtracting that discounted value from `_depositLimit`. Depositing and staking therefore increases measured exposure by less than the accepted deposit whenever the buffer is nonzero. Repeating the cycle can drive gross economic exposure toward `depositLimit / (1 - reportBuffer)`; at the maximum permitted 100% buffer, the cap no longer constrains LST-side exposure at all.

The extended suite converted this from an unexecuted code trace into a deterministic model PoC. Starting from a fully utilized 10 WETH limit, setting a 1% buffer reduced measured exposure to 9.9 WETH and reopened 0.1 WETH of advertised capacity. A second user filled that room; the next report recorded a 0.101 WETH loss, leaving the original user's shares worth 9.9 WETH and the second user's shares worth 0.099 WETH. The test proves both gross-cap overshoot and user-level allocation of the artificial accounting loss, while production intent and live configuration remain deployment questions.

This differs from baseline-only DF-08: the later snapshot correctly rejects out-of-range buffers, but every valid nonzero buffer still participates in this recursive capacity calculation. Impact depends on whether the limit is intended to cap gross deployed exposure rather than conservative reported NAV.

Provenance:

- Plamen Thorough `M-08` — final code trace with algebraic and bounded-cycle analysis; the intended production-linked PoC did not execute because local dependencies lacked code and the fallback RPC returned HTTP 403
- extended adversarial properties `CONFIG-04` and `USER-02` — `test_exposes_reportBufferReopensCapacityAndSocializesAccountingLoss` executed the 10 WETH / 1% buffer sequence above and asserted the exact 0.101 WETH report loss and per-user post-report values

Recommended remediation:

- Enforce the risk limit against undiscounted gross exposure and reserve `reportBuffer` for report/NAV conservatism.
- If the discounted-cap policy is intentional, document the effective gross bound and enforce a much tighter maximum buffer.
- Add repeated deposit/stake tests across nonzero buffer values, including the maximum allowed setting.

### DF-20: Lido withdrawal requests are not bounded or split to the queue's accepted range

- Severity: Low
- Confidence: High on source mechanics; Low on current external bounds
- Status: Code-trace-only operational weakness; external-limit applicability unverified

The queue path submits the full requested amount as a one-element array without checking the withdrawal queue's live per-request minimum or maximum and without splitting oversized exits. A strategy exit that is otherwise valid locally can therefore revert at the external queue boundary and require management to retry with manually partitioned requests. Funds remain controlled, so the primary impact is exit and reporting liveness rather than loss.

Provenance:

- Plamen Thorough `L-02` — final code trace; the run did not execute live Lido queue-boundary calls or establish the applicable production limits

Recommended remediation:

- Query or configure accepted queue bounds, reject sub-minimum requests explicitly, and split oversized requests into a bounded array.
- Cover boundary, multi-request, and later-claim accounting in an integration test.

### DF-21: Advertised capacity ignores Lido's live direct-staking limit

- Severity: Low
- Confidence: High on source mechanics; Medium-Low on external-state applicability
- Status: Code-trace-only operational weakness; external-state applicability unverified

The strategy's advertised deposit room considers its local limit and Lido's paused flag but not Lido's live direct-staking capacity. When direct staking is selected and the protocol-level staking limit is exhausted, a deposit can pass the local capacity check and later revert in `submit()`. This is a liveness and integrator-accuracy issue: value is not lost, but advertised capacity can exceed executable capacity until Lido's external state changes or an alternate route becomes viable.

Provenance:

- Plamen Thorough `L-07` — final code trace; no live exhausted-stake-limit transaction was executed

Recommended remediation:

- Incorporate Lido's current direct-staking allowance into advertised capacity when the direct route can be selected.
- Add an external-limit-exhaustion test and specify whether callers should retry through Curve or wait for capacity restoration.

## Source-to-Canonical Mapping

| Source item | Canonical result | Synthesis treatment |
| --- | --- | --- |
| Codex Security `csf_7dc94802bf292fbeefd70a6f` / candidate `CS-351C58EB-003` | DF-03 | Core confirmed path |
| Codex Security `csf_aade44b3010a30d567b45109` / candidate `CS-351C58EB-002` | DF-02 | Flag-only variant; shutdown path controls final severity |
| Codex candidate `CS-351C58EB-001` | DF-06 | Validated candidate absent from final `findings.json` |
| Codex candidate `CS-351C58EB-004` | Downgraded note | Direct deployment handoff/process issue; not promoted |
| Codex candidate `CS-351C58EB-005` | DF-09 | Deferred integration-dependent issue |
| dot-context `M-01` | DF-04 | Core confirmed path |
| dot-context `M-02` | DF-01 | Core confirmed path |
| dot-context `M-03` | DF-02 | Core confirmed shutdown path |
| dot-context `M-04` | DF-07 | Mechanics confirmed; severity reduced |
| dot-context `L-01` | DF-06 | Corroboration |
| dot-context `L-02` | DF-09 | Corroboration |
| Human Pages `HP-M-01` | DF-02 | Core confirmed shutdown path |
| Human Pages `HP-M-02` | DF-06 | Mechanics confirmed; severity reduced |
| Human Pages `HP-C-01` | DF-03 | Existing-loose-WETH capacity variant |
| Human Pages `HP-C-02` | DF-04 | Conditional corroboration |
| Human Pages `HP-C-03` | DF-10 | Retained as trust boundary |
| Human Pages manual-swap downgraded note | DF-01 | Severity disagreement retained |
| Human Pages emergency-withdraw downgraded note | DF-07 | Controls final severity calibration |
| Human Pages factory/configuration note | DF-08 plus downgraded notes | Buffer issue promoted; zero-address/event concerns not promoted |
| Human Pages direct-deployment-script note | Downgraded note | Operational handoff issue; not promoted |
| dot-context-sol `M-01` | DF-02 | Core confirmed shutdown-report path |
| dot-context-sol `L-01` | DF-03 | Donation/live-cap variant; mechanics confirmed and severity reduced |
| dot-context-sol `L-02` | DF-16 | Report-blocking nominal-versus-actual remainder |
| dot-context-sol `L-03` | DF-14 | Exact-par emergency floor corroboration |
| human-pages-sol `HP-V1` | DF-02 | Independently confirms both post-shutdown keeper paths |
| human-pages-sol `HP-V2` | DF-14 | Stronger conditional severity retained as a reconciliation note |
| human-pages-sol `HP-V3` | Downgraded note | Deployment handoff mechanics validated; operational likelihood keeps it below the canonical table |
| human-pages-sol `HP-V4` | DF-10 / DF-13 / DF-17 | Immutable-vault trust, fee-booking, and zero-capacity exit variants |
| human-pages-sol `HP-V5` | Rejected | Factory metadata calls execute under static context and block the proposed nested deployment |
| human-pages-sol `HP-V6` | DF-01 / DF-16 | Core stale-loss ordering path plus queue under-settlement amplifier |
| human-pages-sol `HP-V7` | DF-04 | Core zero-unlock pre-report capture path |
| human-pages-sol `HP-V8` | DF-18 | New zero-supply residual-capture family |
| Nemesis `NEM-001` | DF-08 | Core confirmed path |
| Nemesis `NEM-002` | DF-06 | Corroboration |
| Nemesis `NEM-003` | DF-09 | Corroboration |
| solidity-auditor `F-01` | DF-01 | Core confirmed path |
| solidity-auditor `F-02` | DF-05 | Baseline discovery, later independently confirmed |
| solidity-auditor `F-03` | DF-03 | Core confirmed path |
| solidity-auditor `L-01` | DF-06 | Corroboration |
| solidity-auditor `L-02` | DF-03 | Favorable-fill capacity variant |
| solidity-auditor `L-03` | DF-07 | Operational corroboration |
| solidity-auditor `L-04` | DF-11 | Retained as Informational |
| solidity-auditor `L-05` | DF-08 | Corroboration |
| solidity-auditor demoted `stakeAsset` trail | DF-02 | Intent caveat retained |
| solidity-auditor demoted fixed-APR trail | DF-09 | Integration caveat retained |
| Plamen Core baseline `M-01` | DF-10 / DF-11 | Executed malicious-vault mechanism; funding and endorsement conditions retained |
| Plamen Core baseline `M-02` | DF-09 | Executed constant-output property; integration impact remains conditional |
| Plamen Core baseline `M-03` | DF-16 | Unit postcondition passed; external loss-bearing queue lifecycle not executed |
| Plamen Core baseline `M-04` | DF-06 | ABI mismatch corroboration; no queue end-to-end PoC |
| Plamen Core baseline `M-05` | DF-07 | Baseline-only code trace; exact defect fixed at `4580174c...` |
| Plamen Core baseline `M-06` | DF-02 | Shutdown-insensitive maintenance corroboration; code trace only |
| Plamen Core baseline `M-07` | DF-03 | Zero-capacity loose-wstETH deposit variant; integration harness did not complete |
| Plamen Core baseline `M-08` | DF-01 / DF-14 context | Contested baseline zero-floor amplifier; no sandwich PoC and no new family |
| Plamen Core baseline appendix `I-01` | DF-04 | `POC-FAIL`; source-coverage mapping only, not added proof |
| Plamen Thorough `M-01` | DF-05 | Final `POC-PASS` and 256-case fuzz proof upgrade for the existing queue-cap family |
| Plamen Thorough `M-02` plus absorbed `M-13` | DF-16 | Stale-pricing and queue-settlement consequences; external discounted lifecycle not executed |
| Plamen Thorough `M-03` | DF-06 | Initiation/claim ABI mismatch corroboration |
| Plamen Thorough `M-04` and `L-08` | DF-03 | Terminal sink-capacity and advertised-capacity split of the existing root |
| Plamen Thorough `M-05` | DF-11 | Existing-strategy roles do not follow later factory-default rotation |
| Plamen Thorough `M-06` | DF-02 / DF-03 | Staking-disable and downstream-capacity bypass variants |
| Plamen Thorough appendix `M-07` | DF-09 | Constant-output property retained as deployment-conditional appendix material |
| Plamen Thorough `M-08` | DF-19 | New report-buffer/cap recursion family |
| Plamen Thorough `M-09` and `M-12` | DF-16 | Aggregate-clearing and unbound-request extensions |
| Plamen Thorough `M-10` | DF-14 | Buffer-derived emergency-floor corroboration; intended fork check did not execute |
| Plamen Thorough `M-11` | DF-01 context | Nominal LST valuation premise only; no independent loss-shifting lifecycle proved |
| Plamen Thorough `M-14` | DF-04 | Zero-unlock configuration confirmed; late-depositor capture not executed |
| Plamen Thorough `M-15` | DF-10 | Ignored downstream deposit-output variant |
| Plamen Thorough `M-16` | DF-13 | Gross-versus-realizable downstream-vault valuation variant |
| Plamen Thorough `M-17` | DF-10 / DF-11 | Arbitrary-vault trust and permissionless-registry variant |
| Plamen Thorough `L-01` | Rejected | Existing adversarial callback test showed the relevant metadata calls execute under static context |
| Plamen Thorough `L-02` | DF-20 | New external queue-boundary liveness family |
| Plamen Thorough `L-03`, `L-04`, and `L-09` | DF-17 | Replacement-helper amount-safety variants |
| Plamen Thorough `L-05` and `L-06` | Downgraded note | Missing factory events and one-step management transfer retained as operational hardening only |
| Plamen Thorough `L-07` | DF-21 | New external direct-staking-capacity liveness family |
| Plamen Thorough `L-10` | DF-18 context | Contested native-ETH residual variant; no capture sequence executed |
| ZeroSkills `ZS-01` | DF-02 / DF-12 | Source merged the common liquidity-relocking invariant; canonical report keeps shutdown-keeper and ordinary-depositor triggers separate |
| ZeroSkills `ZS-02` | DF-06 | ABI-shape mismatch corroboration with direct decode result 32 |
| ZeroSkills `ZS-03` | DF-05 | Queue-cap lifecycle independently reproduced |
| ZeroSkills `ZS-04` | DF-03 | One-wei loose-wstETH zero-capacity report DoS independently reproduced |
| ZeroSkills `ZS-L1` | DF-16 | Conditional nominal-versus-actual settlement lead; no additional live-queue proof |
| strategy-review-agent blind `F-01` | DF-02 | Source-rated High; fixed-block report and tend PoCs corroborate shutdown redeployment, with a direct-tend configuration-bypass variant |
| strategy-review-agent blind `F-02` | DF-14 | Source-rated High; fixed-block below-par Curve quote and default-buffer emergency revert corroborate the separated-role liveness root |
| strategy-review-agent blind `F-03` | Downgraded note | Source-rated High conditional; independently validates the existing direct `Deploy4626.s.sol` role-handoff footgun without proving production use or lasting key loss |
| strategy-review-agent blind `F-04` | DF-05 | Source-rated Medium; fixed-block queue/refill PoC independently confirms held-plus-pending exposure above the configured cap |
| strategy-review-agent blind `F-05` | DF-06 | Direct-forward PoC reproduces request id 32; comment replay confirms the off-chain adapter convention was intentional and previously reviewed |
| strategy-review-agent blind `C-01` | DF-01 / DF-16 | Conditional stale-loss redistribution concern; queue shortfall is an amplifier of the existing accounting window |
| strategy-review-agent blind `C-02` | DF-01 context | Caller-supplied zero or stale-low manual Curve minimum retained as a slippage amplifier, not a separate family |
| strategy-review-agent blind `C-03` | DF-10 / DF-13 | Arbitrary ERC4626 control, allowance, gross-NAV, fee, and exitability trust boundary |
| strategy-review-agent blind `C-04` | DF-16 | Nominal request minus actual proceeds can leave a report-blocking residual after a haircut |
| strategy-review-agent blind `C-05` | DF-09 / DF-20 / DF-21 | Fixed APR, queue-boundary, and direct-Lido live-capacity operational concerns |
| strategy-review-agent comment-aware `CA-01` | DF-17 | Already-liquid stETH plus `maxRedeem == 0` sharpens the existing zero-unwrap partial-recovery path |
| extended adversarial `CONV-03` and `CONV-05` | DF-01 / DF-14 context | Executed caller-zero-minimum and maximum-buffer zero-output conversions; same privileged loss/slippage-control root, not a new family |
| extended adversarial `DEPLOY-02` through `DEPLOY-05` | DF-02 / DF-03 / DF-21 context | Executed staking-disable, zero-capacity, Lido-pause, and post-shutdown maintenance variants; actual live Lido capacity remains unverified |
| extended adversarial `QUEUE-01`, `QUEUE-03`, `QUEUE-04`, `QUEUE-07`, and `QUEUE-08` | DF-05 / DF-06 / DF-16 | Executed direct-response misdecode, per-request clearing, discounted settlement, orphaned-NFT accounting, and cap-reopening variants |
| extended adversarial `V4626-02`, `V4626-03`, `V4626-05`, and `V4626-07` through `V4626-09` | DF-03 / DF-10 / DF-17 | Executed sink-capacity, output-trust, partial-liquidity, layered-unwind, and standards-compatible virtual-share variants |
| extended adversarial `CONFIG-04` and `USER-02` | DF-19 | Upgrades the recursive report-buffer capacity root from code trace to executable model PoC with exact per-user loss assertions |
| extended adversarial `CONV-01`, `FUNDS-03`, `CONFIG-02`, and `CONFIG-03` | Downgraded or assumption notes | Direct-Lido underdelivery depends on a deliberately weakened external mock; arbitrary-token recovery and deployment misconfiguration lack an attacker-to-funded-production impact path |
| 5.6 Sol Codex Security `csf_46d2a8b0062d1f2a0e5d1795` | DF-13 | Fee-bearing-vault realization gap |
| 5.6 Sol Codex Security `csf_d9b4fe4044f8f96d22efd58a` | DF-02 | Post-shutdown report variant |
| 5.6 Sol Codex Security `csf_c5a9e2a967e22583d8780558` | DF-02 | Post-shutdown tend variant |
| 5.6 Sol Codex Security `csf_7f9d7622a90752f126134dd1` | DF-05 | Independently confirms queue-cap omission |
| 5.6 Sol Codex Security `csf_2fb78692d339540f18df9133` | DF-14 | `4580174c...` exact-peg emergency floor |
| 5.6 Sol Codex Security `csf_07fb06eefe8dd302ec047d0d` | DF-12 | Ordinary deposit re-stakes prepared liquidity |
| 5.6 Sol Codex Security `csf_5236c2f55c0be4d5a012af25` | DF-03 | Final nested-vault amount exceeds checked capacity |
| 5.6 Sol Codex Security `csf_2908870927c06eae78c8a5a4` | DF-03 | Amount-scoped staking sweeps ambient balances |
| 5.6 Sol Codex Security `csf_e74ae140bceefd722ddf44dc` | DF-16 | Discounted claim leaves stale-priced liquidity |
| 5.6 Sol solidity-auditor `VF-01` | DF-12 | Core ordinary-depositor path |
| 5.6 Sol solidity-auditor `VF-02` | DF-06 | ABI mismatch corroboration |
| 5.6 Sol solidity-auditor `VF-03` | DF-03 | Capacity translation and sink mismatch |
| 5.6 Sol solidity-auditor `VF-04` | DF-17 | Mixed-balance partial unwind |
| 5.6 Sol solidity-auditor `VF-05` | DF-17 | Zero-amount wrapper revert |
| 5.6 Sol solidity-auditor `VF-06` | DF-17 | Excess loose-wrapped balance unwrap |
| 5.6 Sol solidity-auditor `VF-07` | DF-09 | Constant APR corroboration |
| 5.6 Sol solidity-auditor `VF-08` | DF-05 | Queue-cap lifecycle confirmation |
| 5.6 Sol solidity-auditor `VF-09` | DF-15 | Synthetic buffer-recovery fees |
| 5.6 Sol solidity-auditor `VL-01` | DF-14 | Emergency-role liveness variant |
| 5.6 Sol solidity-auditor `VL-02` | DF-02 | Shutdown maintenance variant |
| 5.6 Sol solidity-auditor `VL-03` | DF-03 | Direct-tend capacity variant |
| 5.6 Sol solidity-auditor `VL-04` | DF-16 | Lower-proceeds pending remainder |
| 5.6 Sol solidity-auditor `VL-05` | DF-16 | Stale-priced claim proceeds |
| 5.6 Sol solidity-auditor `VL-06` | DF-16 | Early-clear later-recovery accounting variant |
| 5.6 Sol solidity-auditor `VL-07` | DF-16 | Partial-batch aggregate-clear variant |
| 5.6 Sol solidity-auditor `VL-08` | DF-10 | Zero-share accepted-vault variant |
| 5.6 Sol solidity-auditor `VL-09` | DF-13 | Fee-bearing-vault dependency |
| 5.6 Sol solidity-auditor `VL-10` | DF-11 | Old role-snapshot deployment variant |
| 5.6 Sol solidity-auditor `VL-11` | DF-10 / DF-11 | Arbitrary-vault trust and registry variant |

Nemesis `FF-*` and `SI-*` identifiers map to `NEM-001` through `NEM-003`; they are internal subpasses and are not counted as independent corroborating tools. X-ray findings and invariants are orientation artifacts and are not used as standalone security findings.

## Downgraded or Rejected Families

The following items remain below the reportable threshold unless deployment facts add impact:

- Factory and `setAddresses()` zero-address validation and missing events: management-only configuration hardening. The extended suite proved that an existing manager can set factory management to zero and permanently disable future `setAddresses()` calls. It also showed that zero keeper and emergency-admin defaults leave a new strategy dependent on its pending manager accepting management before ordinary report and emergency operations become available. These are concrete deployment and key-redundancy hazards, but no unauthorized action or funded-production path was demonstrated.
- Non-WETH asset construction: `Strategy` and `Strategy4626Factory` accept an arbitrary ERC-20 asset even though staking later calls WETH-specific methods. The extended suite deployed a strategy over mock stETH and reproduced an atomic deposit revert; the user's tokens and shares remained unchanged, and the repository deployment scripts pin canonical mainnet WETH. Retain as constructor hardening unless an alternate deployment path can fund a misconfigured instance.
- Arbitrary ERC-20 recovery: an unrelated token donated to the strategy remained stuck because production code exposes no generic rescue function. This is an accidental-transfer recovery gap rather than theft of a supported position token; any rescue function must prohibit withdrawal of WETH, stETH, wstETH, downstream-vault shares, and strategy shares.
- Direct-Lido underdelivery: a fuzz test confirmed that the strategy has no post-`submit()` output floor if an external Lido model mints less stETH than ETH supplied. The mock deliberately permits behavior outside the expected integration invariant, so this remains an external-protocol assumption rather than a current Lido vulnerability.
- Direct `Deploy4626.s.sol` role-handoff behavior: human-pages-sol `HP-V3` and strategy-review-agent blind `F-03` both validated the script-shaped deployment and failed acceptance by the logged address. The benchmark rated it High conditional, but lasting harm still requires this path to be production-supported, poor broadcaster-key handling, and later funding, so the canonical synthesis retains it as a deployment runbook/process footgun.
- Factory duplicate-deployment reentrancy: human-pages-sol `HP-V5` rejected the hypothesis with an adversarial callback test because relevant vault metadata calls execute under static context.
- Plamen Thorough `L-01` is rejected for the same reason: its callback-based orphan hypothesis did not account for the static context already demonstrated by `HP-V5`.
- Plamen Thorough `L-05` missing factory events and `L-06` one-step management transfer remain operational hardening recommendations without a demonstrated unauthorized-action path.
- `isDeployedStrategy()` reverting on arbitrary non-strategy input: brittle helper with no demonstrated security consumer.
- `setReferral(0)`, generic ERC777/fee-on-transfer behavior, and generic WETH token quirks: non-applicable to the intended integration.
- The baseline run's earlier demotion of excess loose-wstETH unwrapping is superseded for `4580174c...` by the more complete DF-17 amount-safety evidence.
- Plamen Core baseline appendix `I-01` was capped from Medium to Informational after `POC-FAIL`; it remains subsumed by DF-04 and contributes no additional proof.

## Verification Record

The synthesis relies on the run-local evidence sources listed below. The extended campaign independently reran both its deterministic security model and the pre-existing fork suite:

- dot-context: four focused PoCs passed; final baseline reported 46 passed, 0 failed, 0 skipped.
- Human Pages: baseline reported 46 passed; three focused `.audit`-resident PoCs passed.
- dot-context-sol: the shutdown PoC passed 1/1, the mutable-cap ERC4626 PoCs passed 2/2, and the live-head baseline reported 45 passed and 1 rounding-sensitive failure out of 46.
- human-pages-sol: all eight canonical hypotheses were tested; the final isolated verifier suite passed 10/10, the native shutdown baseline passed 3/3, and `findings.jsonl` validated as eight unique schema-conforming records.
- Codex Security: production build passed, focused existing tests passed, and the disposable max-deposit donation PoC passed.
- Nemesis: withdrawal-queue, Strategy4626, operation, and full fork suites passed as recorded; promoted issues were trace-verifiable Low findings.
- solidity-auditor: targeted `WithdrawalQueueTest` and `Strategy4626Test` suites passed.
- Plamen Core baseline: mechanical verification recorded 3 PASS, 18 NO_TEST_FILE, and 1 FAIL across 22 verifier records. The generated unit/property harnesses for `M-01`, `M-02`, and the bounded `M-03` postcondition passed; only `M-01` and `M-02` received final report `POC-PASS` evidence tags. `M-08` was unexecuted and appendix `I-01` was demoted after `POC-FAIL`.
- Plamen Thorough: mechanical verification recorded 2 PASS, 15 FAIL, and 100 NO_TEST_FILE outcomes across 117 verifier rows. The Foundry invariant campaign executed 17 properties, minimized 14 counterexamples, and passed 3; only `M-01` retained a final body `POC-PASS` tag. The Medusa harness compiled but reverted during deployment, so no Medusa property campaign executed. Two verifier skip reasons were mechanically invalid, and the generated report header retained a 23-versus-22 post-dedup count mismatch.
- ZeroSkills: the clean `4580174c...` worktree built successfully; the full baseline was 45/46 with only the known one-wei deposit-limit assertion; code-sleuth writer suites passed 12/12; symmetry-targeted existing suites passed 16/16; the disposable four-case regression passed 4/4; and the ABI array-as-scalar check returned 32. The temporary regression file was removed and the audit worktree was clean at handoff.
- strategy-review-agent benchmark: provenance pinned a clean detached worktree to `4580174c...` before source review and preserved the blind report by checksum before opening comments. The committed full suite remained 45/46 with only the known one-wei deposit-limit assertion; six blind PoCs passed 6/6 at block `25533225`; two comment-aware PoCs passed 2/2; and the final combined isolated run passed 8/8. `forge build --sizes` passed with a Strategy4626Factory runtime size of 18,214 bytes. One preliminary public-RPC attempt executed no tests because the endpoint rejected archive storage with HTTP 403; the configured-RPC run succeeded.
- extended adversarial test suite: `make test-security-model` passed 80 deterministic tests, separated into 53 enforced-property tests and 27 `test_exposes_*` counterexample or external-assumption tests. Fourteen stateful invariants passed at 256 runs and depth 64 and were repeated with seeds `0x1`, `0x2`, and `0x3`. `make coverage-production` reported 205/205 production lines, 50/50 functions, and 34/34 branches. `ETH_RPC_URL=https://ethereum.publicnode.com make test-fork-legacy` passed all 46 pre-existing fork tests. Six independent review passes then rechecked coverage honesty, invariant reachability, queue-NFT accounting, conversion loss controls, ERC-4626 recovery, and role/configuration behavior. No production source file changed.
- 5.6 Sol Codex Security: production contracts built with pinned Vyper 0.3.7; focused offline, fork, and model-based validations are recorded per finding.
- 5.6 Sol solidity-auditor: nine findings survived validation; temporary queue-cap and buffer-fee checks passed, all five Strategy4626 tests passed at the pinned block, ABI direct-replay checks passed, and fixed-block calls established the quoted vault/wrapper behavior.

Deployment facts should be collected for DF-04, DF-09, DF-10, DF-11, DF-13, DF-16, DF-19, DF-20, and DF-21 so their final severity and applicability can be fixed. The extended campaign reran the test commands recorded above; statements for the other sources remain grounded in their run-local receipts and repo-local reports.
