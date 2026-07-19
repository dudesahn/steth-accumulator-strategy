# stETH Accumulator 4626 — Comment-Aware Replay

## 1. Purpose and isolation boundary

This is a separate second-pass delta over the completed blind review. It reads the body, comments, responses, lifecycle, linked base review, and locally available fix commits associated with Yearn [Issue #765](https://github.com/yearn/yearn-strategies/issues/765). It does **not** replace or edit `blind-benchmark-report.md`.

The user's manual review report was not supplied, opened, searched, or inferred. The later manual-report comparison remains pending.

| Field | Value |
| --- | --- |
| Exact source revalidated | `4580174c60ccac4658d97b02f0951aec92b218b2` |
| Source state | detached `HEAD`; production source unchanged |
| Issue-body target | `68f946ac9044cf91a7e30c6fe128301e77c07d14` |
| Comment sources | Issue #765 and its explicitly linked base review, Issue #714 |
| External-known-findings search | none |
| Manual report | not read |
| Added evidence | this replay, `evidence/comment-aware-results.md`, and `poc/CommentAwareEdges.t.sol` |

## 2. Executive delta

The comments materially improve provenance but do not clear the pinned generation:

- F-01 remains High. Shutdown/report redeployment was previously noticed and explicitly treated as intended, but the response's proposed deposit-limit control does not constrain direct `tend()`. The blind pass independently extended the known report behavior into an emergency-recovery sequence and a direct-tend bypass.
- F-02 remains High. The reviewer correctly flagged the zero emergency minimum. The fix replaced it with `reportBuffer`, but the default buffer is still zero, only management can change it, and no deployment path initializes it. This is a residual defect introduced by an incomplete fix, not a brand-new review topic.
- F-03 (conditional High) and F-04 (Medium) remain blind-only relative to the issue feedback reviewed here.
- F-05 is downgraded from a novel incompatibility to a known, intentional off-chain adapter convention with a residual Low integration/documentation footgun. The base issue had already identified it.
- The replay validates one additional Low operational defect, CA-01: when an ERC-4626 destination reports `maxRedeem == 0`, `_freeStETH()` can reach `wstETH.unwrap(0)` and revert before selling already-liquid stETH. Management can retry with an exact smaller amount, limiting impact.
- The factory-size concern is resolved at the pinned commit: runtime size is 18,214 bytes with 6,362 bytes of EIP-170 margin.

## 3. Review and fix chronology

| Time | Event | Meaning |
| --- | --- | --- |
| 2026-06-29 14:42:04 -06:00 | `68f946a` `chore: updates` | commit named in Issue #765 body |
| 2026-06-29 15:11:23 -06:00 | `521fff2` `build: factory` | factory added after issue-body anchor |
| 2026-07-06 16:18:53 UTC | reviewer comment | first 4626-specific review feedback |
| 2026-07-08 16:12:25 UTC | author response | claimed fixes and accepted behaviors |
| 2026-07-08 12:27:25 -06:00 | `c242082` `hcore review` | source changes made after the response |
| 2026-07-08 12:35:43 -06:00 | `4580174` `add back factory` | exact benchmark commit; factory restored and optimizer enabled |

`68f946a` is an ancestor of `4580174`. Issue #765's timeline contains two comments and administrative events only: no linked fix commit, approval, LGTM, closure, or deployment event. The issue remains open with review-completion boxes unchecked and no deployed addresses.

## 4. Comment-by-comment source resolution

### Issue #765

| Reviewer point | Response / claimed disposition | Pinned-source result | Classification |
| --- | --- | --- | --- |
| reuse BaseHealthCheck allowlist | updated | custom `openDeposits` path removed; inherited `open/allowed` used | fixed |
| storage-pack `openDeposits` | added/updated | variable was removed, making the packing point moot | fixed by redesign |
| bound `reportBuffer` | added | setter requires `<= MAX_BPS` | fixed |
| emergency swap used `minOut = 0` | use `reportBuffer` | formula added, but default `reportBuffer == 0` still demands exact 1:1 and is management-only | incomplete; F-02 |
| cap withdrawal initiation | external function caps it | cap to owned position is present; Lido min/max protocol bounds remain caller responsibility | balance cap fixed; protocol bounds unresolved |
| Lido paused/pass-limit state | deposit limit should catch; added tend trigger | `_depositLimit` checks `isStakingPaused()` only; no current stake-limit check; direct `tend()` does not use `_depositLimit` | incomplete |
| queue request min/max | management should handle | no source bounds, chunking, preflight, or named runbook | accepted operator dependency |
| referral event | added | `ReferralUpdated` emitted | fixed |
| unnecessary WETH Curve approval | removed | no constructor WETH approval remains | fixed |
| emergency did not free wstETH/vault shares | added | `_emergencyWithdraw` calls `_freeStETH` first | fixed, subject to destination liquidity and CA-01 |
| harvest/tend ignored vault max deposit | harvest already checks; tend fixed | report uses `availableDepositLimit`; trigger checks `_depositLimit`; direct callable `_tend` stakes full idle amount | incomplete; folded into F-01 |
| report re-stakes WETH on shutdown | “thats fine” | behavior remains; base review also records it as intended | known/accepted design, still F-01 |
| `_freeStETH` unwraps zero / whole balance | thought unreachable / over-unwrap accepted | zero unwrap is reachable and fork PoC passes; whole-balance unwrap remains deliberate | CA-01 validated; over-unwrap accepted |
| factory oversized | optimizer fixed | runtime 18,214 bytes; 6,362-byte margin | fixed |

### Linked base review, Issue #714

The base review supplies two important novelty corrections:

1. On 2026-03-25, a reviewer explicitly reported the `uint256[]` initiation return versus scalar claim decode. The author explained that off-chain tooling should unpack the array and pass one scalar. F-05 therefore remains a real non-composable API behavior but is not new and is intentional.
2. The same reviewer reported that `stakeAsset = false` does not stop report staking. The author said this is intentional because the flag protects permissionless deposit swaps while report is expected to use protected execution. Earlier feedback also asked whether shutdown should stop reinvestment; the answer was no, with `depositLimit` proposed as the stop.

Issue #714 received `LGTM` and later `Deployed code LGTM` for base-generation deployment `0x470e0e048F85CFD72EEf325895e02c8D297E7435`. Those approvals do not establish approval, deployment parity, or live configuration for `Strategy4626`, its factory, or commit `4580174`.

## 5. Findings delta against the blind report

| Blind ID | Comment-aware status | Severity | Novelty / disposition |
| --- | --- | --- | --- |
| F-01 | validated, known behavior with incomplete mitigation | High | report restaking was human-known and accepted; blind pass added the emergency sequence and direct `tend()` bypass, which defeats `stakeAsset=false`, `depositLimit=0`, and shutdown |
| F-02 | validated residual after partial fix | High | reviewer found zero min-out; response changed the mechanism but left default/config/role liveness failure |
| F-03 | unchanged | High conditional | not raised or resolved in reviewed issue feedback; standalone script still logs but never installs management/roles |
| F-04 | unchanged | Medium | no comment addresses pending-claim omission from the deposit-cap basis |
| F-05 | source behavior validated; vulnerability status downgraded | Low residual | human-found in #714 and intentional; retain as an integration/documentation footgun, not a novel defect |

### CA-01 — Zero unwrap blocks an otherwise possible partial manual recovery

**Severity: Low — Impact Low/Medium x Likelihood Low. Status: validated operational liveness defect, comment-guided.**

`Strategy4626._freeStETH` computes a needed wstETH amount, caps redemption by `vault.maxRedeem`, conditionally redeems only when shares are nonzero, and then unconditionally calls `wstETH.unwrap(wrappedBalance)` (`src/Strategy4626.sol:79-98`). If the destination is temporarily illiquid and reports `maxRedeem(address(strategy)) == 0`, `wrappedBalance` can remain zero.

The passing fixed-block PoC establishes a vault position, donates loose stETH, sets destination `maxRedeem` to zero, requests more stETH than is liquid, and observes canonical wstETH's `zero amount unwrap not allowed` revert. Without that call, `_swapLSTToAsset` is explicitly prepared to sell `Math.min(requested, balanceOfLST())`, so already-liquid stETH could otherwise be partially recovered (`src/Strategy4626.sol:44-47`).

Impact is limited because management can retry with the exact loose stETH amount or wait for vault liquidity. Add `if (wrappedBalance > 0)`, and test zero/partial `maxRedeem`, partial liquidity, and emergency behavior.

## 6. Comment-guided corroboration and unresolved context

| Topic | Result after source replay |
| --- | --- |
| Lido staking pause | checked in deposit-limit view; still a liveness revert for direct manual stake and direct tend paths depending on Curve route |
| Lido current stake limit | not checked; source calls `submit` directly when Curve is not above 1:1 |
| Lido queue min/max | no on-chain bounds or chunking; accepted as management responsibility without an operational specification |
| vault max deposit | report and trigger consult it; direct tend does not |
| downstream exit liquidity | emergency now attempts to free nested positions, but `maxRedeem == 0` and redemption failure remain explicit trust assumptions |
| over-unwrap | source unwraps all loose wstETH, not only the needed amount; author explicitly accepted this behavior |
| shutdown restaking | explicitly accepted in two review generations; no atomic keeper-revocation or safe-report procedure is named |

## 7. Misleading, stale, or insufficient review statements

- **“Fixed for tend” is incomplete.** Only `_tendTrigger` was limited. `tend()` remains callable by keepers and passes all idle WETH to `_tend`, which stakes it without checking shutdown, `stakeAsset`, `depositLimit`, Lido pause, or vault max deposit.
- **“The deposit limit should catch it” is path-dependent.** It constrains deposit/report capacity and trigger signaling, not the direct tend execution path or `manualStake`.
- **“Don't think we should ever hit unwrap 0” is contradicted by an executable state.** A standards-compliant ERC-4626 can advertise zero redeemable shares during temporary illiquidity.
- **“That's fine” records intent, not a complete accepted-risk control.** It does not identify who revokes keeper, whether that revocation is atomic with shutdown, how a loss is reported without redeployment, or the allowed re-exposure bound.
- The base-generation LGTM and deployed-code LGTM are scoped to Issue #714 and its deployed address. Treating them as approval of the 4626 generation would be a provenance error.

## 8. Tests and reproducible evidence

| Command / check | Outcome |
| --- | --- |
| comment-aware PoCs at block `25533225` with configured RPC | **2 passed, 0 failed** |
| combined blind + comment-aware PoCs at block `25533225` | **8 passed, 0 failed** |
| `forge build --sizes` | exit 0; factory runtime 18,214 bytes |
| first public-node PoC attempt | infrastructure failure: endpoint returned 403 for archive storage; no test result claimed |

The two added tests are:

- `test_directTendIgnoresShutdownStakeFlagAndDepositLimit`
- `test_zeroUnwrapBlocksOtherwisePossiblePartialManualRecovery`

Exact commands and concise output are preserved in `evidence/comment-aware-results.md`.

## 9. Updated stop/go and residual-risk view

**Status: `comment_replay_complete_not_approved_for_4626_deployment`.**

Issue context confirms that several risky behaviors are intentional, but it does not demonstrate bounded acceptance or operational controls. The source-level stop conditions remain F-01, F-02, and conditional F-03. F-04 remains a material cap-accounting defect. CA-01 is a smaller recovery-liveness edge. Destination-vault code/admin/fees/liquidity, deployed parity, accepted management, downstream allowlisting, live roles, and exact buffer/cap values remain evidence gaps.

No #765 LGTM, deployed address, closure, or deployed-code validation exists in the reviewed timeline.

## 10. Training-extraction notes

1. Preserve a byte-stable blind artifact, then write comment-aware work as an append-only delta.
2. Separate the issue's named review commit from the later fix generation; replay both chronology and exact diff before crediting a fix.
3. A trigger fix is not an execution-path fix. Test the externally callable path directly.
4. Treat “intentional” as a novelty/severity input, not as proof of safety; accepted risk needs actor, action, timing, bounds, and residual blast radius.
5. Follow explicitly linked base-review context before labeling a finding novel.
6. Scope LGTM and deployed-code evidence to the exact contract generation and address it actually covers.
7. Comments that dispute reachability are high-value PoC prompts.

## 11. Questions before the later manual-report comparison

1. Is the standalone `Deploy4626` script obsolete, or must it be treated as a supported production path alongside the factory?
2. Is post-shutdown report/tend redeployment formally accepted for the 4626 strategy, and if so, what atomic keeper and loss-reporting runbook bounds it?
3. What emergency `reportBuffer` is approved, who must be able to change it, and is it installed before debt?
4. Is the array-to-scalar withdrawal adapter documented in the actual keeper automation?
5. Should CA-01 be fixed in source or recorded as an operator retry condition?
6. Which exact wstETH ERC-4626 destination implementation and control plane should be reviewed for deployment applicability?
7. When the manual report is supplied, should the final benchmark preserve three explicit columns—blind, comment-aware, and manual—or also add a fourth deployment-aware column?

## 12. Manual-report comparison placeholder

| Comparison field | Status |
| --- | --- |
| User manual report read | no |
| Blind-to-comments delta | complete in this artifact |
| Blind-to-manual overlap | pending |
| Comment-sparked-to-manual overlap | pending |
| Manual-only findings and rationale | pending |
| Final training labels | pending |
