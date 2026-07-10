# Pashov X-Ray + Solidity Auditor Synthesis

Commit: `521fff28ad978a37115be8995a1d631611fa1d3d`
Branch: `review`
Date: `2026-07-08`
Run root: `.audit/`

## Scope

The review covered first-party production contracts:

- `src/BaseLSTAccumulator.sol`
- `src/Strategy.sol`
- `src/Strategy4626.sol`
- `src/Strategy4626Factory.sol`
- `src/periphery/StrategyAprOracle.sol`

Tests, interfaces, and vendored libraries were used for context and validation only.

## Run Layout

- X-ray artifacts: `.audit/pashov-xray-521fff2/`
- Solidity auditor bundles: `.audit/solidity-auditor-521fff2/bundles/`
- Solidity auditor wave 1: `.audit/solidity-auditor-521fff2/wave-1/`
- Solidity auditor wave 2: `.audit/solidity-auditor-521fff2/wave-2/`
- Validated results: `.audit/solidity-auditor-521fff2/validated-findings-and-leads.md`

This mirrors the useful ytranche pattern: keep each tool run distinct, use x-ray as orientation only, run all Solidity auditor lanes independently, then synthesize with provenance rather than blending raw outputs into later agents.

## X-Ray Orientation

X-ray classified the protocol as a Yearn V3 TokenizedStrategy that accepts WETH, accumulates stETH, and optionally wraps/deposits exposure into a downstream wstETH ERC4626 vault.

Most important x-ray surfaces:

- `pendingRedemptions` blocks reports while Lido queue redemptions are outstanding.
- Normal withdrawals are idle-WETH-only.
- Strategy4626 trusts downstream vault capacity and conversion semantics.
- Factory deployments are permissionless and one-shot per vault.
- `reportBuffer` is an intended basis-point haircut but has no on-chain upper bound.

X-ray artifacts were copied into `.audit/pashov-xray-521fff2/` after generation. The stock `enumerate.sh` output is archived as `enumerate.raw.txt`; it hit macOS BSD `grep -P` compatibility errors, so x-ray enumeration was completed manually from repo-local source and tests. `forge coverage` compiled but was not usable as a coverage artifact because the repo's fork-oriented setup failed without RPC setup and Foundry then panicked in coverage finalization; raw output is archived as `coverage.raw.txt`.

## Solidity Auditor Run

The all-lane run used 12 independent lanes in two waves:

- Wave 1: math precision, access control, economic security, execution trace, invariant, periphery.
- Wave 2: first principles, asymmetry, boundary, numerical gap, trust gap, flow gap.

Each agent received a lane-specific bundle and wrote only to its assigned output file. X-ray artifacts were included only as orientation. No agent was asked to read another lane's output.

Raw lane result summary:

- Agents with no finding blocks: 1, 2, 6, 7, 9, 10.
- Agents with raw finding blocks: 3, 4, 5, 8, 11, 12.
- Repeated clusters: queue claim-data shape mismatch, pending-redemption cap bypass, Strategy4626 vault-capacity sweep, stale accounting after manual liquidity creation, factory permissionless deployment/trust stamping.

## Validation Result

Validated findings:

- F-01 Medium: Manual or emergency unwinds expose idle WETH before accounting records the unwind loss.
- F-02 Low/Medium: Pending Lido redemptions are excluded from deposit-limit accounting.
- F-03 Medium: Forced loose wstETH can DoS Strategy4626 reports when the downstream vault has no capacity.

Validated leads:

- L-01: Lido request return data and claim data use incompatible ABI shapes.
- L-02: Strategy4626 can advertise an executable max deposit that becomes too large after a favorable Curve fill.
- L-03: Strategy4626 emergency withdrawal does not reach vault-held value by itself.
- L-04: Permissionless factory deployment stamps live role defaults and one-shot vault registry state.
- L-05: `reportBuffer` has no `MAX_BPS` bound.

Rejected or demoted:

- Factory duplicate deployment through reentrancy was rejected because the relevant vault calls are view/static calls.
- `stakeAsset` being bypassed by report/tend was demoted because the behavior is explicitly tested.
- `isDeployedStrategy()` reverting on arbitrary input was demoted to a brittle view-helper issue.
- The fixed APR oracle was demoted because no in-repo value-moving consumer uses it.

The detailed post-validation write-up is in `.audit/solidity-auditor-521fff2/validated-findings-and-leads.md`.

## Validation Commands

```sh
env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-contract WithdrawalQueueTest -vv --fork-url https://ethereum.publicnode.com
env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-contract Strategy4626Test -vv --fork-url https://ethereum.publicnode.com
```

Results:

- `WithdrawalQueueTest`: 7 passed, 0 failed.
- `Strategy4626Test`: 5 passed, 0 failed.

## Future Efficiency Notes

To make this faster and reduce orchestration/tool-calling next time:

1. Provide a one-screen run manifest up front: commit, branch, exact source scope, artifact root, desired lanes, and validation threshold.
2. Keep reusable pashov run scaffolding in the repo or a personal script: create `.audit/<tool>-<shortsha>/`, copy x-ray artifacts, build 12 lane bundles, and launch two waves.
3. Pre-authorize the fork test command family and RPC URL if fork tests are expected.
4. Decide before the run whether role-gated operational bugs should be promoted as findings or kept as validated leads. That avoids a second classification pass.
5. Give the expected final artifact shape, for example `validated-findings-and-leads.md` plus `synthesis/<run>.md`, so I do not spend calls inferring report format.
6. For pashov x-ray on macOS, either run with GNU grep installed or use the already-generated x-ray artifacts as input; the bundled shell enumerator expects `grep -P`.

