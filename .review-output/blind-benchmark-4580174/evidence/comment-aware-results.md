# Comment-Aware Replay Evidence

## Boundary and source

```text
worktree: /Users/dudesahn/.codex/worktrees/8c5a/steth-accumulator-strategy
HEAD: 4580174c60ccac4658d97b02f0951aec92b218b2
state: detached HEAD
production source: unchanged
manual report: not read
```

Authenticated GitHub reads were limited to Issue #765, its timeline, and the explicitly linked base review Issue #714. No unrelated issue/PR search or known-finding search was performed.

## Issue source ledger

```text
gh issue view 765 --repo yearn/yearn-strategies --json ...
exit: 0
state: OPEN
body commit: 68f946ac9044cf91a7e30c6fe128301e77c07d14
comments: 2
reviewer comment: 2026-07-06T16:18:53Z
author response: 2026-07-08T16:12:25Z
deployed addresses: none
```

```text
gh api repos/yearn/yearn-strategies/issues/765/timeline --paginate ...
exit: 0
material events: reviewer comment, author response
no linked commit, LGTM, closure, or deployment event
```

```text
gh issue view 714 --repo yearn/yearn-strategies --json ...
exit: 0
relevant context:
- array/scalar claim-data mismatch was reported and intentionally retained
- report staking despite stakeAsset=false was reported and intentionally retained
- base generation received LGTM and deployed-code LGTM
- deployed base address: 0x470e0e048F85CFD72EEf325895e02c8D297E7435
```

Primary comment URLs:

- https://github.com/yearn/yearn-strategies/issues/765#issuecomment-4895087535
- https://github.com/yearn/yearn-strategies/issues/765#issuecomment-4916828494
- https://github.com/yearn/yearn-strategies/issues/714#issuecomment-4128831111
- https://github.com/yearn/yearn-strategies/issues/714#issuecomment-4139824038
- https://github.com/yearn/yearn-strategies/issues/714#issuecomment-4148072124
- https://github.com/yearn/yearn-strategies/issues/714#issuecomment-4154011982

## Commit chronology

```text
68f946ac9044cf91a7e30c6fe128301e77c07d14|2026-06-29T14:42:04-06:00|chore: updates
521fff28ad978a37115be8995a1d631611fa1d3d|2026-06-29T15:11:23-06:00|build: factory
c242082278a86c52ab7eb7ab4e321767babd2856|2026-07-08T12:27:25-06:00|hcore review
4580174c60ccac4658d97b02f0951aec92b218b2|2026-07-08T12:35:43-06:00|add back factory
```

`git merge-base --is-ancestor 68f946a 4580174` exited 0.

Diff summaries:

```text
68f946a..c242082: 10 files changed, 42 insertions, 50 deletions
c242082..4580174: 4 files changed, 193 insertions, 1 deletion
```

## Comment-aware PoCs

Source: `../poc/CommentAwareEdges.t.sol`

First attempt with a public archive endpoint:

```text
env FOUNDRY_TEST=.review-output/blind-benchmark-4580174/poc \
  forge test --match-contract CommentAwareEdgesPoC -vv \
  --fork-url https://ethereum.publicnode.com --fork-block-number 25533225
exit: 1
result: no tests executed; RPC returned HTTP 403 for an archive storage request
```

This is an infrastructure failure, not a test or source failure.

Successful run using the configured RPC, whose value is not copied into evidence:

```text
env FOUNDRY_TEST=.review-output/blind-benchmark-4580174/poc \
  forge test --match-contract CommentAwareEdgesPoC -vv \
  --fork-url "$ETH_RPC_URL" --fork-block-number 25533225
exit: 0
2 passed; 0 failed; 0 skipped
test_directTendIgnoresShutdownStakeFlagAndDepositLimit: PASS
test_zeroUnwrapBlocksOtherwisePossiblePartialManualRecovery: PASS
```

## Combined PoC verification

```text
env FOUNDRY_TEST=.review-output/blind-benchmark-4580174/poc \
  forge test \
  --match-contract '^(ClaimDataMismatchPoC|EmergencyAndCapPoC|DeploymentConfigPoC|CommentAwareEdgesPoC)$' \
  -vv --fork-url "$ETH_RPC_URL" --fork-block-number 25533225
exit: 0
8 passed; 0 failed; 0 skipped
```

Passing tests:

- `test_directDeploymentDoesNotConfigureAdvertisedManagementOrRoles`
- `test_directForwardOfReturnedClaimDataUsesWrongRequestId`
- `test_directTendIgnoresShutdownStakeFlagAndDepositLimit`
- `test_zeroUnwrapBlocksOtherwisePossiblePartialManualRecovery`
- `test_defaultEmergencyBufferRevertsAtPinnedBelowPegCurveState`
- `test_keeperCanTendRecoveredFundsAfterShutdownDespiteConfigStops`
- `test_pendingQueuePrincipalReopensAndBypassesDepositCap`
- `test_reportRedeploysRecoveredFundsAfterShutdownWhenStakeFlagIsFalse`

## Factory-size verification

```text
forge build --sizes
exit: 0
Strategy4626 runtime:        13,064 bytes
Strategy4626Factory runtime: 18,214 bytes
factory EIP-170 margin:       6,362 bytes
```

Compiler/lint warnings were emitted, but no build error occurred. Foundry also warned that it could not write its signature cache outside the sandbox; this did not affect the successful build or size output.
