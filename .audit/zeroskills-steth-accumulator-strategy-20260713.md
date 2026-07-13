# ZeroSkills audit — steth-accumulator-strategy

- Date: 2026-07-13
- Audited commit: `4580174c60ccac4658d97b02f0951aec92b218b2`
- Requested branch context: `review-sol-update`; the audited commit is an ancestor of that branch, whose tip was `f5f547278a398ee0b8edd1d24daab9877186178e` at audit start
- Audit worktree: detached clean worktree at `/tmp/zeroskills-steth-accumulator-strategy-4580174`
- Methodologies: ZeroSkills `code-sleuth` and `symmetry-sniper` only
- Report path: `.audit/zeroskills-steth-accumulator-strategy-20260713.md`

## Executive summary

The audit identified four validated symmetry findings: one Medium and three Low. The `code-sleuth` lane found no validated storage-integrity vulnerability. One queue-accounting behavior remains a plausible, externally dependent lead.

| ID | Severity | Status | Lane | Title |
|---|---|---|---|---|
| ZS-01 | Medium | Validated | symmetry-sniper | Automatic stake paths can reverse intentional and emergency liquidity releases |
| ZS-02 | Low | Validated | symmetry-sniper | Withdrawal initiation output is not valid input to its paired claim |
| ZS-03 | Low | Validated | symmetry-sniper | Pending queue claims disappear from the cumulative deposit cap |
| ZS-04 | Low | Validated | symmetry-sniper | Loose wstETH can exceed nested-vault capacity and block reports |
| ZS-L1 | Informational | Plausible/conditional | both | A discounted queue payout can leave a persistent redemption residue |

Severity uses qualitative Impact x Likelihood. Findings were kept below Medium unless they demonstrate material loss, durable fund unavailability, or a realistic emergency-control failure. No direct theft or permissionless value extraction was demonstrated.

## Clean-room boundaries and provenance

Discovery used normal repository source, interfaces, tests, README, Foundry/build configuration, dependency manifests, and only the pinned dependency code needed to resolve inherited behavior. It excluded prior audit reports, prior findings, memory, `.audit/`, `.scratchpad/`, synthesis files, broadcast output, generated review artifacts, Git history, and later commits as evidence.

No Plamen, Codex Security, sc-auditor, SolidityGuard, solskill, Slither, or other audit framework/scanner was run.

The initial worktree was verified at the exact commit and clean. Four declared submodules were initialized at their pinned revisions:

- `forge-std`: `fc560fa34fa12a335a50c35d92e55a6628ca467c`
- `openzeppelin-contracts`: `bd325d56b4c62c9c5c1aff048c37c6bb18ac0290`
- `tokenized-strategy`: `82806289f967590c4efbf6bc3d237e4e7f0a0966`
- `tokenized-strategy-periphery`: `fc1b1d4ab5c9a0b65b7ac785734c404d3742317a`

After verification, the temporary regression harness was removed and the audit worktree was reverified clean at `4580174c60ccac4658d97b02f0951aec92b218b2`.

## Validated findings

### ZS-01 — Automatic stake paths can reverse intentional and emergency liquidity releases

- Severity: Medium
- Impact: Medium
- Likelihood: Medium for stale/compromised keeper automation after shutdown; Low to Medium for the allowed-depositor path
- Affected contracts: `Strategy`, `Strategy4626`
- Duplicate handling: post-shutdown maintenance and dust-deposit variants are merged because both break the same stake/free invariant by re-locking WETH deliberately made liquid

#### Evidence

- `BaseLSTAccumulator._freeFunds` intentionally performs no automatic unstaking, and withdrawals are limited to loose WETH: `src/BaseLSTAccumulator.sol:108-117` and `:123-134`.
- Management and queue claims create withdrawable WETH through `manualSwapToAsset` and `_claimLSTWithdrawal`: `src/BaseLSTAccumulator.sol:222-229`; `src/Strategy.sol:101-112`.
- Emergency unwind swaps deployed LST back to WETH: `src/BaseLSTAccumulator.sol:148-156`; the wrapper first frees the nested position at `src/Strategy4626.sol:62-65`.
- The inherited implementation deliberately leaves `report` and `tend` callable after shutdown: `lib/tokenized-strategy/src/TokenizedStrategy.sol:1081-1096`, `:1295-1318`, and `:1325-1337`.
- The inherited base explicitly warns that `_harvestAndReport` must avoid redeploying after shutdown: `lib/tokenized-strategy/src/BaseStrategy.sol:334-355`, especially `:342-350`.
- This implementation has no shutdown guard. `_harvestAndReport` and `_tend` call `_stake` at `src/BaseLSTAccumulator.sol:136-145` and `:158-160`.
- `Strategy._stake` consumes the passed WETH at `src/Strategy.sol:50-68`; `Strategy4626._stake` additionally wraps all loose stETH and deposits all loose wstETH at `src/Strategy4626.sol:29-41`.
- On every deposit, inherited `_deposit` passes the strategy's entire loose WETH balance—not only the new deposit—to `deployFunds`: `lib/tokenized-strategy/src/TokenizedStrategy.sol:954-975`, especially `:963-969`.
- Deposit reachability is receiver-based through `BaseHealthCheck.availableDepositLimit`: `lib/tokenized-strategy-periphery/src/Bases/HealthCheck/BaseHealthCheck.sol:172-179`.

#### Exploit or failure path

Post-shutdown variant:

1. Emergency admin shuts down and calls `emergencyWithdraw`, producing loose WETH for users.
2. A stale or compromised keeper calls `report` or `tend`, which remain authorized after shutdown.
3. The strategy converts the WETH back to stETH; `Strategy4626` returns it to the nested vault.
4. `availableWithdrawLimit` and user `maxRedeem` fall toward zero.
5. The keeper can repeat this after each emergency unwind until automation/access is stopped.

Allowed-depositor variant:

1. Management swaps LST or a queue claim creates a loose-WETH withdrawal buffer.
2. While deposits are open, or using an allowed receiver, an attacker deposits a small nonzero amount before users redeem.
3. Inherited `_deposit` invokes `deployFunds` with the complete WETH balance.
4. The new deposit and the pre-existing withdrawal buffer are re-staked.
5. Users lose immediate withdrawal liquidity until management frees funds again.

#### Verification

A temporary Foundry regression reproduced both paths at the pinned commit:

- `test_poc_reportRestakesAfterShutdown` passed: after shutdown and full emergency unwind, a keeper report reduced WETH to zero, restored stETH, and reduced `availableWithdrawLimit` to zero.
- `test_poc_dustDepositRestakesWithdrawalBuffer` passed: a 1,001-wei allowed deposit consumed a previously freed roughly 10-WETH buffer and reduced victim withdrawal liquidity to zero.
- Existing `test_harvestStakesBypassesStakeAssetFlag` also passed and confirms report-side staking ignores `stakeAsset=false`: `src/test/StethSpecific.t.sol:332-354`.
- Existing shutdown tests passed 3/3 but do not interleave `report` or `tend` after emergency unwind: `src/test/Shutdown.t.sol:18-144`.

#### Assumptions, mitigations, and fix direction

- The public path is unavailable while deposits are closed and no attacker-selected receiver is allowed. Because the gate is on `receiver`, a caller can still deposit on behalf of a known allowed receiver.
- Setting `stakeAsset=false` before creating a buffer mitigates deposit-time re-staking but does not mitigate report/tend, which ignore the flag.
- If the keeper is trusted against emergency-admin intent, downgrade the shutdown variant. The explicit inherited warning and role split support including stale/compromised keeper behavior.
- Guard report/tend deployment when `TokenizedStrategy.isShutdown()` is true. Make all automatic stake paths consistently respect an explicit preserve-idle mode, or otherwise reserve liquidity freed for withdrawals.

### ZS-02 — Withdrawal initiation output is not valid input to its paired claim

- Severity: Low
- Impact: Low to Medium operational liveness failure; funds are recoverable
- Likelihood: Medium for automation treating the paired `bytes` values as opaque
- Affected contracts: `Strategy`, `Strategy4626`

#### Evidence

- `_initiateLSTWithdrawal` returns `abi.encode(requestIds)` where `requestIds` is `uint256[]`: `src/Strategy.sol:90-99`.
- `_claimLSTWithdrawal` decodes its bytes as a scalar `uint256`: `src/Strategy.sol:101-108`.
- The base interface exposes these as an initiation `bytes returnData` and a paired claim `bytes _claimData`: `src/BaseLSTAccumulator.sol:239-255`.
- `Strategy4626` forwards the incompatible initiation payload unchanged: `src/Strategy4626.sol:49-53`.
- Tests work around the mismatch by decoding the returned array and re-encoding `requestIds[0]`: `src/test/WithdrawalQueue.t.sol:70-80`, `:103-117`, and `:133-147`.
- A nonzero pending value blocks reporting: `src/BaseLSTAccumulator.sol:136-138`.

#### Failure path

1. Management calls `initiateLSTWithdrawal` and stores its opaque returned bytes.
2. Keeper passes those bytes directly to `claimLSTWithdrawal`.
3. Scalar ABI decoding reads the dynamic-array head offset, `32`, as the request ID.
4. The desired request remains queued; the call normally reverts, or could target an unintended strategy-owned request 32.
5. Reports remain blocked until automation decodes/re-encodes the correct ID or uses emergency recovery.

#### Verification

`cast abi-encode 'f(uint256[])' '[123]'` produced a payload beginning with `0x20`. Decoding the payload as `uint256` with `cast abi-decode 'f()(uint256)' ...` returned `32`. The withdrawal suite passed 7/7 only because every single-claim test transforms the payload first.

#### Assumptions and fix direction

- Suppress if all supported integrations are explicitly required and documented to decode the array and re-encode its first element. No such repo-level contract documentation was found.
- Return `abi.encode(requestIds[0])` for the single-request API, or decode `uint256[]` consistently in the claim path. Document the exact encoding.

### ZS-03 — Pending queue claims disappear from the cumulative deposit cap

- Severity: Low
- Impact: Medium risk-cap violation; no unbacked shares or direct theft demonstrated
- Likelihood: Low
- Affected contracts: `BaseLSTAccumulator`, `Strategy`, `Strategy4626`

#### Evidence

- `_depositLimit` computes remaining capacity as `depositLimit - estimatedTotalAssets()`: `src/BaseLSTAccumulator.sol:86-96`.
- `estimatedTotalAssets` counts only loose WETH and current LST value, omitting `pendingRedemptions`: `src/BaseLSTAccumulator.sol:171-173`.
- Initiation adds to `pendingRedemptions`, then the queue takes the LST: `src/BaseLSTAccumulator.sol:239-247`; `src/Strategy.sol:87-99`; the mock transfer is explicit at `src/test/mocks/MockWithdrawalQueue.sol:10-22`.
- Pending redemptions block reports but not deposits/mints or `availableDepositLimit`: `src/BaseLSTAccumulator.sol:119-145`.
- Deposit/mint enforce the understated result through `_maxDeposit`/`_maxMint`: `lib/tokenized-strategy/src/TokenizedStrategy.sol:487-535` and `:869-892`.
- Tests establish cumulative-TVL intent: `src/test/StethSpecific.t.sol:204-247` and `:361-390`.

#### Exploit or failure path

1. The strategy holds assets equal to a finite `depositLimit`.
2. Management queues amount `X`; LST leaves the strategy but the claim remains economically controlled.
3. Apparent deposit capacity reopens by approximately `X`.
4. An open/allowed depositor fills the apparent capacity and receives normally backed shares.
5. Economic assets become approximately `depositLimit + X`, violating the configured cumulative cap.

#### Verification

Temporary `test_poc_pendingQueueReopensFiniteDepositCap` passed. It filled a 10-WETH cap, queued essentially all stETH, observed approximately 10 WETH of reopened capacity, deposited that amount, and confirmed both stored `totalAssets` and `pendingRedemptions + estimatedTotalAssets()` exceeded the cap.

#### Assumptions and fix direction

- The setter comment at `src/BaseLSTAccumulator.sol:204-207` conflicts with implementation/tests by describing a per-harvest staking maximum. If governance confirms queued claims are intentionally outside the risk cap, downgrade to informational.
- The path requires finite cap plus open/allowed deposit reachability during a pending window.
- Either return zero deposit capacity while `pendingRedemptions != 0`, or include pending claims in the value used only for cap enforcement without double-counting them in report accounting.

### ZS-04 — Loose wstETH can exceed nested-vault capacity and block reports

- Severity: Low
- Impact: Low report/tend/deposit liveness failure; privileged recovery is available
- Likelihood: Low and conditional on finite/zero nested-vault capacity
- Affected contract: `Strategy4626`

#### Evidence

- `_depositLimit` queries and converts `vault.maxDeposit(address(this))`: `src/Strategy4626.sol:55-60`.
- `_stake(_amount)` uses `_amount` only for the WETH-to-stETH super call, then wraps all loose stETH and deposits all loose wstETH: `src/Strategy4626.sol:29-42`.
- Report calls `_stake` even when its requested amount is zero: `src/BaseLSTAccumulator.sol:136-145`.
- The pinned nested tokenized strategy enforces `assets <= _maxDeposit(...)` and reverts with `ERC4626: deposit more than max`: `lib/tokenized-strategy/src/TokenizedStrategy.sol:487-503`.
- The repository's wrapper setup uses an allowlisted nested vault and can set its strategy allowance: `src/test/utils/Setup4626.sol:20-43`.

#### Exploit or failure path

1. The nested vault reports zero or finite remaining capacity, for example after shutdown or allowlist removal.
2. An attacker transfers loose wstETH to `Strategy4626`, exceeding that capacity.
3. The next report may call `_stake(0)`, but `_stake` still attempts to deposit the full loose wstETH balance.
4. The nested vault reverts, blocking report; deposit and tend paths can fail similarly.
5. Privileged operators must reopen capacity or convert the loose wrapper token through emergency/manual paths.

#### Verification

Temporary `test_poc_looseWstethRevertsWhenNestedCapacityIsZero` passed against the pinned fork setup. After the nested vault removed the outer strategy from its allowlist, `maxDeposit` returned zero; a simulated one-wei wstETH transfer made the next keeper report revert with `ERC4626: deposit more than max`.

#### Assumptions and fix direction

- Suppress if every supported nested vault always accepts unlimited deposits. The pinned repository test setup demonstrates a supported finite/zero-capacity state.
- Cap the actual `vault.deposit` amount by the current `maxDeposit`, leave excess wstETH loose, and skip the call when capacity is zero.

## Plausible lead needing more evidence

### ZS-L1 — A discounted queue payout can leave a persistent redemption residue

- Status: Plausible/conditional, not validated
- Candidate severity: Informational/Low
- Impact: Low to Medium report liveness failure requiring management reconciliation
- Likelihood: Unknown/Low

Initiation adds the requested stETH amount to `pendingRedemptions` at `src/BaseLSTAccumulator.sol:239-247`. Claim measures the actual ETH balance delta at `src/Strategy.sol:101-111`, and the base subtracts that ETH amount from the nominal stETH accumulator at `src/BaseLSTAccumulator.sol:249-255`. Any residual blocks report at `src/BaseLSTAccumulator.sol:136-138`; management can recover through `clearPendingRedemptions` at `:258-264`.

Conditional path: if a fully consumed request for `X` stETH pays `X-d` ETH, persistent pending state becomes `d` even though no claim remains. The shipped mock always pays the exact request at `src/test/mocks/MockWithdrawalQueue.sol:25-32`, so the passing tests do not establish or refute live queue haircut/rounding behavior.

Validation was deferred because authoritative pinned Lido settlement semantics were not present in the permitted repo evidence. Suppress if the live queue guarantees payout is always at least the exact requested integer amount.

## Lane results

### `code-sleuth`

#### Scope reviewed

- Repo contracts: `src/BaseLSTAccumulator.sol`, `src/Strategy.sol`, `src/Strategy4626.sol`, `src/Strategy4626Factory.sol`, `src/periphery/StrategyAprOracle.sol`, and storage-relevant interfaces.
- Pinned inherited storage behavior: `BaseHealthCheck.sol`, `BaseStrategy.sol`, `TokenizedStrategy.sol`, `AprOracleBase.sol`, and `Governance.sol` only where needed.
- Tests/config: README, Foundry/package config, queue/factory/storage-writer tests.

#### Storage inventory and result

- `Strategy` and `Strategy4626` ordinary state occupies compiler-managed slots 0-8: health-check flags/allowlist/ratios, `stakeAsset`, limits, `pendingRedemptions`, and `referral`.
- Tokenized accounting uses the fixed namespace `bytes32(uint256(keccak256("yearn.base.strategy.storage")) - 1)` in `lib/tokenized-strategy/src/TokenizedStrategy.sol:365-409`.
- The constructor writes a separate fixed EIP-1967 marker at `lib/tokenized-strategy/src/BaseStrategy.sol:152-161`; runtime dispatch ignores that slot and delegates to a compile-time constant at `:485-500`.
- `Strategy4626Factory` uses slots 0-4 for four addresses and `deployments`; `StrategyAprOracle` has only simple inherited governance/name state.
- Concrete validated findings: none.
- Plausible lead: ZS-L1 above.

#### False positives, suppressed leads, and assumptions

- Outbound memory arrays in `_initiateLSTWithdrawal` are not copies of persistent storage and have no omitted write-back.
- `_vault` and user addresses are intended Solidity mapping keys, not attacker-selected raw storage slots.
- Fallback calldata is attacker-controlled, but the delegatecall target and storage namespace are fixed and privileged writers retain role checks.
- The EIP-1967 marker resembles upgradeability, but no upgrade method or storage-loaded implementation target exists.
- `manualClaimWithdrawals(..., false)` intentionally retains pending state; tests assert that behavior.
- No `StrategyData memory` mutation, persistent-array `push`/`pop`, attacker-selected `sstore`, custom slot arithmetic, upgrade collision, diamond collision, bitmap mask, or stale delete/index pair was found.
- `StrategyAprOracle` did not satisfy Gate 2 for deeper storage-risk analysis.

#### Verification

- `forge inspect` confirmed the layouts above.
- Queue/factory writer tests passed 12/12.
- The full suite was 45/46; the sole failure was the non-security 1-wei deposit-cap assertion described below.

### `symmetry-sniper`

#### Scope reviewed

- All repo production contracts and interfaces listed above.
- Operation tests for deposits, withdrawals, shutdown, queue lifecycle, wrapper behavior, factory behavior, and rounding.
- Only inherited tokenized-strategy/health-check sections required to resolve the paired call paths.

#### Pair map and concrete results

| Pair | Result |
|---|---|
| Deposit/mint | Shared conservative path; no finding |
| Withdraw/redeem | Shared conservative path; documented default `maxLoss` difference suppressed |
| Stake/free and emergency unwind/post-shutdown maintenance | ZS-01 |
| Initiate/claim | ZS-02 and ZS-L1 |
| Queue pending state/deposit cap | ZS-03 |
| Wrapper vault deposit/redeem | ZS-04; no value-extracting round trip |
| Single claim/emergency batch claim | Deliberate emergency-only difference; no public bypass |
| Factory deploy/registry check | Consistent for conforming deployments; no inverse/batch operation |
| APR positive/negative delta | Constant example output; informational/non-applicable |

#### False positives, suppressed leads, and assumptions

- Inherited ERC-4626 rounding is conservative: deposit down, mint up, withdraw up, redeem down; no profitable round trip was found.
- Automatic deploy versus no automatic free is documented. Only concrete re-locking interleavings are reported in ZS-01.
- Emergency batch claim can optionally zero aggregate pending state, but it is explicit and emergency-authorized.
- `_freeStETH` unwraps the complete loose wstETH balance, but outer paths cap consumption; no extraction was found.
- `reportBuffer` discounts valuation and sets minimum emergency output in the same conservative direction.
- `manualSwapToAsset(..., 0)` is management-selected slippage behavior, not a public bypass.
- `Strategy4626Factory.isDeployedStrategy` can revert for nonconforming input, but is view-only with no security-critical in-repo consumer.
- `StrategyAprOracle` ignores debt delta but is explicitly an example estimator with no in-repo value-moving consumer.
- No public batch deposit/mint/withdraw/redeem path or authorization mismatch enabling untrusted asset theft was found.

## Informational notes

### One-wei deposit-limit assertion

The full fork suite repeatedly observed `availableDepositLimit == 1` where `test_depositLimit` expects zero at `src/test/StethSpecific.t.sol:204-246`. The calculation uses live LST value at `src/BaseLSTAccumulator.sol:89-96` and `:171-185`; the one wei is conversion/rounding capacity, not storage corruption or a material symmetry break. Classification: Informational/test fragility.

### Fixed storage domains

Compiler layout, the fixed tokenized-strategy hash namespace, and the EIP-1967 marker are separated. The delegatecall target is immutable and no upgrade path exists. Classification: Informational, not a collision finding.

## Verification summary

- `forge build`: successful.
- Storage layouts: successful for `Strategy`, `Strategy4626`, `Strategy4626Factory`, and oracle/inherited state checks.
- Full baseline fork suite: 45 passed, 1 failed, 0 skipped. Sole failure: repeatable 1-wei `test_depositLimit` assertion.
- Focused baseline rerun: same 1-wei failure reproduced; the two related deposit-limit tests passed.
- Code-sleuth targeted writer suites: 12 passed, 0 failed.
- Symmetry existing targeted suites: WithdrawalQueue 7/7, Strategy4626 5/5, Shutdown 3/3, report-stake flag test 1/1.
- Temporary regression harness: 4 passed, 0 failed. It was removed after execution.
- ABI shape check: array encoding decoded as scalar returned 32.

## Commands run and blockers

Principal exact commands, all against the pinned worktree unless noted:

```sh
git worktree add --detach /tmp/zeroskills-steth-accumulator-strategy-4580174 4580174c60ccac4658d97b02f0951aec92b218b2
git submodule update --init --recursive
sed -n '1,400p' /Users/dudesahn/Documents/GitHub/codex/skill-research/ZeroSkills/code-sleuth/SKILL.md
sed -n '1,400p' /Users/dudesahn/Documents/GitHub/codex/skill-research/ZeroSkills/symmetry-sniper/SKILL.md
rg --files -g '!**/.audit/**' -g '!**/.scratchpad/**' -g '!**/broadcast/**' -g '!**/cache/**'
rg -n '\b(memory|storage|calldata)\b|assembly|sstore|sload|delegatecall|StorageSlot|bytes32|mapping\(' src -g '*.sol' -g '!src/test/**'
rg -n 'pendingRedemptions|manualClaimWithdrawals|initiateLSTWithdrawal|claimLSTWithdrawal|clearPendingRedemptions' src/test -g '*.sol'
rg -n 'modifier only|function report|function tend|function shutdownStrategy|function emergencyWithdraw|function setOpen|function setAllowed|function availableDepositLimit|function availableWithdrawLimit|maxDeposit|maxMint|maxWithdraw|maxRedeem' lib/tokenized-strategy/src/TokenizedStrategy.sol lib/tokenized-strategy/src/BaseStrategy.sol lib/tokenized-strategy-periphery/src/Bases/HealthCheck/BaseHealthCheck.sol
nl -ba src/BaseLSTAccumulator.sol
nl -ba src/Strategy.sol
nl -ba src/Strategy4626.sol
nl -ba src/Strategy4626Factory.sol
nl -ba src/periphery/StrategyAprOracle.sol
nl -ba lib/tokenized-strategy/src/BaseStrategy.sol
nl -ba lib/tokenized-strategy/src/TokenizedStrategy.sol
nl -ba lib/tokenized-strategy-periphery/src/Bases/HealthCheck/BaseHealthCheck.sol
forge build
forge inspect src/Strategy.sol:Strategy storageLayout
forge inspect src/Strategy4626.sol:Strategy4626 storageLayout
forge inspect src/Strategy4626Factory.sol:Strategy4626Factory storageLayout
env ETH_RPC_URL=https://ethereum.publicnode.com forge test -vv --fork-url https://ethereum.publicnode.com
env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-test test_depositLimit -vv --fork-url https://ethereum.publicnode.com
forge test --match-contract 'WithdrawalQueueTest|Strategy4626FactoryTest' --fork-url https://ethereum.publicnode.com -vv
forge test --match-contract WithdrawalQueueTest -vv --fork-url https://ethereum.publicnode.com
forge test --match-contract Strategy4626Test -vv --fork-url https://ethereum.publicnode.com
forge test --match-contract ShutdownTest -vv --fork-url https://ethereum.publicnode.com
forge test --match-test test_harvestStakesBypassesStakeAssetFlag -vv --fork-url https://ethereum.publicnode.com
cast abi-encode 'f(uint256[])' '[123]'
cast abi-decode 'f()(uint256)' 0x000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000000007b
env ETH_RPC_URL=https://ethereum.publicnode.com FOUNDRY_OUT=/tmp/zeroskills-regression-out FOUNDRY_CACHE_PATH=/tmp/zeroskills-regression-cache forge test --match-path src/test/ZeroSkillsRegression.t.sol --match-test test_poc_ -vv --fork-url https://ethereum.publicnode.com
git rev-parse HEAD
git status --short --branch
git submodule status
```

Blockers and environmental issues:

- Sandboxed `git worktree add` and first submodule initialization could not write `.git/worktrees/...`; both succeeded when retried with approval-aware access.
- The first temporary regression fork run compiled, then Foundry panicked in macOS `system-configuration` before test execution. The identical command succeeded outside the sandbox: 4/4 passed.
- Foundry emitted non-blocking cache read/write warnings under `~/.foundry/cache`; tests otherwise ran.
- The full-suite green baseline is blocked by the repeatable one-wei assertion mismatch. Targeted security regressions are green.
- ZS-L1 remains blocked on authoritative live queue settlement semantics or a real below-request payout case.

## Files written

Durable repo-local output:

- `.audit/zeroskills-steth-accumulator-strategy-20260713.md`

Audit scratch outputs:

- `/tmp/zeroskills-code-sleuth-lane.md`
- `/tmp/zeroskills-symmetry-sniper-lane.md`
- Temporary `src/test/ZeroSkillsRegression.t.sol` in the detached audit worktree; removed after 4/4 tests passed
- Temporary Foundry output/cache under `/tmp/zeroskills-regression-out` and `/tmp/zeroskills-regression-cache`

No production source or permanent test file was changed. An unrelated existing modification to `.audit/synthesis/deduped-findings-report.md` in the persistent worktree was preserved and excluded from discovery and this report.

## Final audit accounting

- New validated findings: 4 — one Medium, three Low.
- Plausible/deferred leads: 1 — queue payout denomination/rounding residue.
- Informational notes: 2 principal notes — fixed storage-domain safety and the one-wei baseline assertion.
- Non-applicable/suppressed checks: storage lost-write/raw-slot/upgrade families, conservative inherited ERC-4626 rounding, explicit emergency batch behavior, documented no-auto-free behavior without a concrete re-locking path, and view-only/example periphery differences.
- Audit worktree final state: clean detached HEAD at `4580174c60ccac4658d97b02f0951aec92b218b2`.
