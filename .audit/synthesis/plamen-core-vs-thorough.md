# Plamen Core vs Thorough Comparison

## Purpose

This comparison measures whether the clean Plamen Thorough run added useful
security coverage beyond the earlier clean Plamen Core run. It is not a strict
A/B benchmark because the runs audited different commits and the Core run used
an exceptional Recon routing workaround.

The comparison uses final reports, checkpoints, cost ledgers, verification
manifests, run notes, and the production-source diff. Raw candidate counts are
not treated as findings, and fuzzer counterexamples are not treated as
proof-backed vulnerabilities unless they survived final verification with an
executed evidence tag.

## Run provenance

| Dimension | Core | Thorough |
| --- | --- | --- |
| Audited commit | `521fff28ad978a37115be8995a1d631611fa1d3d` | `4580174c60ccac4658d97b02f0951aec92b218b2` |
| Commit relationship | Ancestor | Descendant of Core baseline |
| Mode | `core` | `thorough` |
| Backend | Codex | Codex |
| Driver result | Exit 0; 54 phase slots handled | Exit 0; 73 phase slots handled |
| Wall time | 3:13:56 | 7:25:49 |
| Ledger cost | $170.9076 | $495.8428 |
| Final body | 8 Medium | 22 actual sections: 15 Medium, 7 Low |
| Final body evidence | 2 `POC-PASS`, 6 `CODE-TRACE` | 1 `POC-PASS`, 21 `CODE-TRACE` |
| Mechanical verifier rows | 22: 3 PASS, 1 FAIL, 18 NO_TEST_FILE | 117: 2 PASS, 15 FAIL, 100 NO_TEST_FILE |
| Invariant fuzzing | No dedicated invariant-fuzz worker | 17 properties executed; 14 counterexamples, 3 passes |
| Medusa | Not selected by Core | Harness compiled; deployment reverted, no campaign executed |

Thorough used 2.30 times the wall time and 2.90 times the recorded model cost.
It produced 2.75 times as many body sections and 5.32 times as many verifier
rows, but fewer final body findings with proof-grade evidence.

## Commit-difference control

`521fff28...` is the merge base and an ancestor of `4580174c...`. The later
snapshot changes five production files:

| File | Insertions | Deletions | Comparison impact |
| --- | ---: | ---: | --- |
| `BaseLSTAccumulator.sol` | 8 | 25 | Removes local deposit whitelist, composes inherited capacity, bounds `reportBuffer`, and replaces zero emergency `minOut` with a buffer-derived floor |
| `Strategy.sol` | 4 | 4 | Adds a referral event and removes an unused constructor approval |
| `Strategy4626.sol` | 8 | 6 | Reworks capacity plumbing and adds vault-aware emergency freeing |
| `Strategy4626Factory.sol` | 6 | 14 | Primarily naming and formatting; role-default and one-shot registry behavior remains |
| `IBaseLSTAccumulator.sol` | 0 | 6 | Removes declarations for the deleted local whitelist |

The material version confounders are:

- Core M-05 covers the old Strategy4626 emergency path that skipped vault-held
  assets. That exact defect is fixed at `4580174c...`; Thorough L-03, L-04,
  and L-09 instead cover edge cases in the replacement freeing helper.
- Core M-08 covers the old zero-output emergency swap floor. The later commit
  closes that condition and introduces the buffer-coupled floor examined by
  Thorough M-10 and canonical DF-14.
- The later commit bounds `reportBuffer`, fixing canonical DF-08. Valid
  in-range buffers still interact with capacity accounting, which is the
  separate Thorough M-08 / canonical DF-19 mechanism.
- Test fixtures also changed. They are verification infrastructure, not primary
  finding scope, but they can affect which PoCs initialize successfully.

All other Thorough-only mechanisms listed below arise from behavior that is
substantively present at both commits, so they are reasonable recall signals
rather than obvious consequences of the source delta.

## Pipeline coverage difference

Thorough added 19 checkpoint slots beyond Core:

- re-scan preparation and execution;
- semantic-invariant pass 2;
- attention repair, exploration skeptic, and axis coverage;
- chain iteration 2 applicability;
- post-verification extraction and skeptic review;
- ten Low-severity verification shards.

The depth worker pool also expanded from 10 workers in Core to 18 in Thorough.
The added roles covered event completeness, semantic consistency, specification
compliance, design stress, perturbation, skill-execution completeness, Foundry
invariant fuzzing, and Medusa.

Two important confounders remain:

- Core Recon ran as one combined Terra worker after a temporary routing
  workaround, rather than the canonical EVM Recon fan-out. That likely reduced
  Core recall and makes the measured Thorough lift larger than a normal
  Core-vs-Thorough comparison would show.
- Core made Slither importable through a temporary Python path. Thorough had a
  visible Slither CLI but could not import its Python module and used the
  source-graph fallback. Neither run had OpenGrep. Tooling therefore did not
  uniformly favor Thorough. OpenGrep was installed only after these runs, so
  it should improve the next comparison but cannot be credited here.

Both runs used the same Codex model families
(`gpt-5.6-terra`, `gpt-5.6-sol`, and `gpt-5.6-luna`), but routing differed:
Core used Terra for Breadth, chain, and most verification; Thorough routed those
high-volume phases primarily to Sol.

## Core-to-Thorough semantic mapping

| Core result | Thorough counterpart | Assessment |
| --- | --- | --- |
| M-01 arbitrary-vault approval and valuation | M-15, M-16, M-17 | Same broad trust boundary split into minimum-share, realizable-value, and arbitrary-vault subfamilies. Core had the stronger executed malicious-vault PoC. |
| M-02 constant APR | M-07 appendix and FUZZ-1 | Same mechanism. Core had the stronger final `POC-PASS`; Thorough calibrated it out of the client body because no production consumer was shown. |
| M-03 nominal request vs actual queue proceeds | M-02 plus absorbed M-13 | Same root, with Thorough adding stale-NAV and stale-withdrawal consequences. Both final reports kept the production-loss trigger conditional. |
| M-04 initiation/claim ABI mismatch | M-03 | Same root and decode-offset evidence. |
| M-05 emergency exit skips vault-held assets | L-03, L-04, L-09 | Not an exact repeat: the later commit fixes Core's path and creates replacement-helper edge cases. |
| M-06 shutdown-insensitive staking | M-06 | Same report/tend configuration bypass; Thorough also produced an invariant counterexample but retained final code-trace evidence. |
| M-07 loose-wstETH capacity mismatch | M-04 and L-08 | Same root split into terminal sink enforcement and advertised-capacity mismatch. |
| M-08 zero emergency minimum | M-10 | Version-shifted slippage trade-off: zero floor at Core commit versus strict/stale buffer-derived floor at Thorough commit. |
| Core appendix I-01 zero profit unlock | M-14 | Same conditional mechanism. Thorough confirmed only the zero-unlock configuration, not the claimed cohort loss. |

Thorough therefore retained or re-expressed every Core report family, although
two families changed with the audited code and one moved between body and
appendix.

## Thorough-only recall

The following Thorough body results were not independently represented in the
Core final report:

| Thorough item | Same behavior present at Core commit? | Canonical treatment | Value added |
| --- | --- | --- | --- |
| M-01 queued rights omitted from the cap | Yes | DF-05 | High-value evidence lift: adds the only final Thorough `POC-PASS` and a 256-case fuzz variant to an existing canonical family |
| M-05 factory role rotation does not revoke deployed roles | Yes | DF-11 | Useful operational expansion; no executed harm and no new family |
| M-08 report haircut recursively reopens capacity | Yes for valid in-range buffers | New DF-19 | New canonical configuration-dependent Medium family |
| M-09 aggregate clearing while queue rights remain | Yes | DF-16 | Useful per-request-accounting extension; final shareholder loss remains contested |
| M-11 nominal one-to-one LST valuation | Yes | DF-01 context | Conditional valuation premise; no live impairment or new terminal path proved |
| M-12 keeper claim ID is not bound to tracked rights | Yes | DF-16 | Useful request-binding extension; no end-to-end cohort loss |
| L-01 factory callback can orphan a strategy | Yes | Rejected | No benefit: conflicts with the existing adversarial callback test, which found the relevant metadata calls execute under static context |
| L-02 queue requests are not bounded or split | Yes | New DF-20 | New Low operational family; live queue bounds were not executed |
| L-07 direct Lido capacity is omitted | Yes | New DF-21 | New Low external-state family; live stake-limit exhaustion was not executed |
| L-10 native ETH remains temporarily unaccounted | Yes | DF-18 conditional variant | Useful residual-value variant, but contested and no inherited share-pricing PoC |

Net integration result:

- 3 new canonical families: DF-19 through DF-21;
- 1 meaningful proof upgrade to existing DF-05;
- 5 useful expansions or corroborations of existing families;
- 1 rejected Thorough body finding;
- remaining extra body count comes from finer splitting of Core families or
  commit-dependent replacement behavior.

## Verification-quality comparison

Core had higher final proof density:

- M-01 and M-02 were final `POC-PASS` findings.
- Its bounded queue-settlement postcondition also executed, although the final
  M-03 tag stayed `CODE-TRACE`.
- Three of 22 verifier rows mechanically passed.

Thorough had much broader dynamic exploration:

- Foundry executed 17 stateful invariants at 256 runs and depth 25, minimizing
  14 counterexamples.
- Only the queue-cap family survived final reporting as `POC-PASS`.
- Several counterexamples established local invariant violations but did not
  prove external deployment assumptions or end-to-end shareholder harm.
- Medusa never executed a property because the harness constructor reverted.
- A missing archive RPC and HTTP 403 blocked at least one intended fork PoC.
- Two verifier skip reasons were mechanically invalid.

The extra Thorough spend therefore bought recall and mechanism decomposition,
not a proportional increase in proof-backed vulnerabilities.

## Conclusion

Thorough provided real incremental benefit, but the benefit was narrower than
the raw 22-versus-8 body count suggests.

The strongest gains were:

1. discovering the report-buffer/cap recursion family;
2. adding executable proof to the queued-rights capacity family;
3. exposing two additional external-capacity/liveness assumptions;
4. decomposing broad Core trust and capacity findings into more actionable
   submechanisms.

The main costs and limitations were:

- 2.90 times the model cost and 2.30 times the wall time;
- lower final proof density;
- one rejected body finding;
- several low-confidence, external-state-dependent additions;
- Medusa non-execution and fork-RPC failure;
- report-count and title-quality regressions after final deduplication.

For this repository, Core remains a strong default discovery pass. Thorough is
worth the additional spend when maximum recall, per-contract decomposition, and
stateful invariant exploration matter, but it should be paired with a reliable
archive RPC, working Slither/OpenGrep, and a post-dedup report QA step.

## Recommended controlled comparison

For a defensible future A/B test:

1. Pin both runs to the same commit and identical recursive submodule SHAs.
2. Use sibling clean worktrees with identical scope, docs, backend, and model
   routing.
3. Preflight OpenGrep, Slither's Python import, Forge, Medusa harness
   deployment, and the same archive RPC.
4. Run Core and Thorough independently without sharing target-specific output.
5. Normalize results into root-cause families before comparing recall.
6. Compare final proof-backed families, contested families, false positives,
   runtime, cost, retries, and verification coverage—not raw candidate counts.
7. Repeat each mode if measuring model variance rather than a single-run
   operational outcome.
