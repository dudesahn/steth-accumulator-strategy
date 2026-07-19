# Test and PoC Results

All fork commands used the configured `ETH_RPC_URL`; its value is intentionally not copied into this artifact. Tests that depend on the reproduced below-peg Curve state were pinned to mainnet block `25533225`.

## Environment

```text
forge Version: 1.5.1-stable
Commit SHA: b0a9dd9ceda36f63e2326ce530c10e6916f4b8a2
ETH_RPC_URL=set
```

## Full committed suite

Initial sandboxed attempt:

```text
forge test -vv --fork-url "$ETH_RPC_URL"
exit: 134
Foundry panic: system-configuration-0.6.1 attempted to create a NULL object while constructing the macOS proxy matcher.
```

The same command was rerun outside the restricted sandbox after approval:

```text
forge test -vv --fork-url "$ETH_RPC_URL"
exit: 1
45 passed; 1 failed; 0 skipped; 46 total
failure: src/test/StethSpecific.t.sol:StethSpecificTest::test_depositLimit()
observed assertion: available deposit limit was 1 wei, expected 0 ("Limit not exhausted")
```

Focused confirmation:

```text
forge test --match-test test_depositLimit -vvvv --fork-url "$ETH_RPC_URL"
exit: 1
2 passed; 1 failed; 0 skipped
same deterministic 1-wei failure in test_depositLimit(); the substring match also ran the two other deposit-limit tests.
```

This is not a green suite. The failure is a dust-level exact-equality assumption caused by stETH share rounding at the forked live state; it does not by itself prove a material security issue. It does prove the checked-in suite is not currently clean and is not block-pinned.

## Isolated claim-data regression

Source: `../poc/ClaimDataMismatch.t.sol`

```text
env FOUNDRY_TEST=.review-output/blind-benchmark-4580174/poc \
  forge test --match-contract ClaimDataMismatchPoC -vv --fork-url "$ETH_RPC_URL"
exit: 0
1 passed; 0 failed; 0 skipped
test_directForwardOfReturnedClaimDataUsesWrongRequestId: PASS
```

The PoC proves that directly forwarding `initiateLSTWithdrawal()`'s returned bytes to `claimLSTWithdrawal()` decodes ABI offset `32` rather than the returned request ID. The committed tests only succeed after decoding the array and re-encoding one scalar ID.

## Isolated emergency and cap regressions

Source: `../poc/EmergencyAndCap.t.sol`

```text
env FOUNDRY_TEST=.review-output/blind-benchmark-4580174/poc \
  forge test --match-contract EmergencyAndCapPoC -vv \
  --fork-url "$ETH_RPC_URL" --fork-block-number 25533225
exit: 0
4 passed; 0 failed; 0 skipped
```

Passing regressions:

- `test_defaultEmergencyBufferRevertsAtPinnedBelowPegCurveState`
- `test_keeperCanTendRecoveredFundsAfterShutdownDespiteConfigStops`
- `test_pendingQueuePrincipalReopensAndBypassesDepositCap`
- `test_reportRedeploysRecoveredFundsAfterShutdownWhenStakeFlagIsFalse`

Independent fixed-block quote used by the default-buffer regression:

```text
cast call 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022 \
  "get_dy(int128,int128,uint256)(uint256)" 1 0 1000000000000000000 \
  --block 25533225 --rpc-url "$ETH_RPC_URL"
999797856520084312
```

## Isolated deployment-role regression

Source: `../poc/DeploymentConfig.t.sol`

```text
env FOUNDRY_TEST=.review-output/blind-benchmark-4580174/poc \
  forge test --match-contract DeploymentConfigPoC -vv \
  --fork-url "$ETH_RPC_URL" --fork-block-number 25533225
exit: 0
1 passed; 0 failed; 0 skipped
test_directDeploymentDoesNotConfigureAdvertisedManagementOrRoles: PASS
```

The direct-constructor path used by `script/Deploy4626.s.sol` leaves the broadcaster as management, keeper, and performance-fee recipient, leaves `pendingManagement` and `emergencyAdmin` zero, and causes the management address printed by the script to revert on `acceptManagement()`.

## Final PoC-only verification

```text
env FOUNDRY_TEST=.review-output/blind-benchmark-4580174/poc \
  forge test \
  --match-contract '^(ClaimDataMismatchPoC|EmergencyAndCapPoC|DeploymentConfigPoC)$' \
  -vv --fork-url "$ETH_RPC_URL" --fork-block-number 25533225
exit: 0
6 passed; 0 failed; 0 skipped
```

## Lane-focused runs

The blind lane artifacts preserve their own exact focused commands. The token-movement lane reports 22 passing focused tests across Strategy4626, manual swap, shutdown, withdrawal queue, and factory subsets. These focused successes do not override the one failure in the full suite.

## Missing hard tests in the committed repository

- no project-level stateful invariant suite
- no post-shutdown `report` or `tend` no-redeployment invariant
- no default-buffer below-peg emergency regression
- no two-user liquidation-loss allocation regression
- no direct-forward withdrawal claim-data regression
- no pending-redemption-inclusive deposit-cap invariant
- no deployment-script role/config postcondition test
- no malicious/upgraded downstream-vault allowance or exit-liquidity test
