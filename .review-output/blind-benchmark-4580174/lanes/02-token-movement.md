# Lane 2 — Token Movement, Approvals, Callbacks, and Principal Custody

## Scope and clean-room provenance

- Lane: token movement, Curve swaps, Lido withdrawal queue, approvals, callbacks, protected-token behavior, and principal custody only.
- Reviewed repository: `/Users/dudesahn/.codex/worktrees/8c5a/steth-accumulator-strategy`.
- Reviewed commit: `4580174c60ccac4658d97b02f0951aec92b218b2`.
- `git rev-parse HEAD`: `4580174c60ccac4658d97b02f0951aec92b218b2`.
- Git state observed before source inspection: detached (`## HEAD (no branch)`). The root orchestrator recorded the fresh worktree as clean before review output was created. At this lane's first check, the only dirt was the shared untracked `.review-output/` directory; no tracked changes were present.
- Exact initialized dependency gitlinks used for inherited behavior:
  - `lib/tokenized-strategy`: `82806289f967590c4efbf6bc3d237e4e7f0a0966` (`v3.0.4`).
  - `lib/tokenized-strategy-periphery`: `fc1b1d4ab5c9a0b65b7ac785734c404d3742317a` (`v3.0.4`).
  - `lib/openzeppelin-contracts`: `bd325d56b4c62c9c5c1aff048c37c6bb18ac0290` (`v4.9.5`).
- No parent checkout, other worktree, branches, reflogs, stashes, issue comments, prior review artifacts, manual report, historical findings, or other lane outputs were inspected.
- Evidence grade: exact pinned source plus focused mainnet-fork tests. Live production configuration, destination-vault control surface, and operations/relay evidence were intentionally not established in this lane.

## Lane summary

The strategy has no auction, swapper, reward-sale, generic sweep/rescue/recover, or user-selectable callback surface. Principal follows:

`WETH -> ETH -> stETH -> wstETH -> downstream ERC4626 shares`

It exits either synchronously through:

`ERC4626 shares -> wstETH -> stETH -> Curve ETH -> WETH`

or asynchronously through:

`ERC4626 shares -> wstETH -> stETH -> Lido withdrawal request -> ETH -> WETH`.

The fixed Curve and Lido queue approvals are exact-amount approvals. The wstETH wrapper and downstream ERC4626 vault receive permanent maximum approvals. The inherited TokenizedStrategy callbacks are `onlySelf`, and the externally callable TokenizedStrategy deposit/withdraw/report/tend/emergency entrypoints involved here are non-reentrant.

No unconditional public principal-movement vulnerability was validated. Two source-proven but condition-dependent concerns remain: the management-only Curve unwind can be submitted with no effective price floor, and the downstream ERC4626 vault retains pull authority over loose wstETH even after a manual redeem.

## Token movement matrix

| Token / position | Holder | Mover / receiver | Role | Counted in `estimatedTotalAssets()`? | Movable paths | Protection source | Failure if misclassified |
| --- | --- | --- | --- | --- | --- | --- | --- |
| WETH (`asset`) | Strategy while idle | TokenizedStrategy receives from depositor; strategy unwraps through canonical WETH; user receives on withdraw | Vault asset / principal | Yes, by `balanceOfAsset()` | deposit, `manualStake`, tend/report stake, user withdrawal | No generic sweep; TokenizedStrategy withdrawal accounting; role-gated manual stake | Direct loss of liquid principal or incorrect withdrawal capacity |
| Native ETH | Strategy transiently | Canonical WETH, Curve, Lido submit/queue | Transient principal / donation form | Not directly; wrapped to WETH on swap/claim | WETH unwrap; Curve/Lido value call; `receive()`; WETH wrap of entire native balance | No external send function; only fixed destinations; empty `receive()` | ETH stranded or redirected before conversion |
| stETH | Strategy while loose | wstETH, Curve pool, Lido withdrawal queue | Principal LST | Yes, at stETH units less `reportBuffer` | wrap; manual/emergency Curve sale; queue request | Fixed counterparties; management/emergency roles; exact approvals to Curve/queue | Principal sold, queued, or pulled without bounds |
| wstETH | Strategy while loose | Downstream ERC4626 vault or canonical wstETH unwrap | Wrapped principal | Yes, converted back to stETH units | automatic vault deposit; internal/manual unwrap | Fixed wrapper; emergency-authorized manual unwrap; no generic sweep | Loose principal pulled via persistent vault allowance |
| Downstream ERC4626 shares | Strategy | Downstream vault redemption | Tokenized principal receipt | Yes, via `vault.convertToAssets` then wstETH->stETH conversion | `_freeStETH`, `manualRedeem` | Strategy is share owner; redemption receiver fixed to strategy | External vault impairment traps or misvalues principal |
| Lido withdrawal request / queue claim | Queue/NFT state for strategy | Fixed Lido queue pays ETH to strategy | Pending principal claim | Deliberately excluded while `pendingRedemptions != 0`; reports revert | management initiates; keeper/management claims; emergency batch claim | Fixed owner `address(this)` at request; role gates; report lock | Request transfer/claim semantics could trap or redirect pending principal |
| Strategy ERC4626 shares | Users/vaults | TokenizedStrategy ERC20 logic | Accounting claim on WETH principal | N/A | transfer, redeem, withdraw | Standard pinned TokenizedStrategy allowance and non-reentrancy | Unauthorized share transfer or withdrawal |

Source evidence: `src/BaseLSTAccumulator.sol:102-117,136-185,222-264`; `src/Strategy.sol:48-81,87-125`; `src/Strategy4626.sol:20-52,62-117`; `lib/tokenized-strategy/src/BaseStrategy.sol:40-82,355-440`; `lib/tokenized-strategy/src/TokenizedStrategy.sol:283-295,487-570,940-1040,1081-1096,1314-1364`.

## Approval and receiver ledger

| Owner token | Spender | Amount / lifetime | Created at | Consumed / revoked | Custody observation |
| --- | --- | --- | --- | --- | --- |
| stETH | Curve ETH/stETH pool `0xDC24316b9AE028F1497c275EB9192a3Ea0f67022` | Exact swap amount | `src/Strategy.sol:73-77` | Normally consumed by `exchange`; no explicit zeroing | Fixed principal-sale route; min-out is caller/report-buffer dependent |
| stETH | Lido withdrawal queue `0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1` | Exact queued amount | `src/Strategy.sol:90-98` | Normally consumed by `requestWithdrawals`; no explicit zeroing | Request owner is fixed to strategy |
| stETH | canonical wstETH `0x7f39...2Ca0` | `type(uint256).max` | `src/Strategy4626.sol:20-26` | Never revoked | Wrapper can pull any loose stETH; treated as canonical Lido trust surface |
| wstETH | constructor-supplied ERC4626 vault | `type(uint256).max` | `src/Strategy4626.sol:20-27` | Never revoked | Vault retains pull authority over all loose wstETH, including balances produced by `manualRedeem` |

The exact pinned strategy/base/periphery source has no `protectedTokens`, `sweep`, `rescue`, `recover`, auction, or swapper function. Command:

```text
git grep -n -E 'protectedTokens|function (sweep|rescue|recover)|setAuction|setSwapper|kickAuction|auctionTrigger|enableAuctionToken' HEAD -- src lib/tokenized-strategy/src lib/tokenized-strategy-periphery/src/Bases/HealthCheck
```

Result: exit code `1`, no matches. Principal is therefore structurally protected from generic token-moving periphery in this generation, rather than protected by a token allow/deny list.

## Findings table

| ID | Classification | Severity | Impact x Likelihood | Title | Stop/go |
| --- | --- | --- | --- | --- | --- |
| C-01 | Plausible / conditional concern | Medium | High x Low | Full-principal manual Curve unwind can have no effective price floor | Warn; require bounded execution evidence |
| C-02 | Plausible / conditional concern | Medium | High x Low | Permanent downstream-vault allowance extends custody to loose emergency wstETH | Warn; destination trust and recovery design must be explicit |

No unconditional validated finding was established in this lane.

## C-01 — Full-principal manual Curve unwind can have no effective price floor

**Classification:** plausible/conditional concern; source behavior validated, harmful production use not proven.
**Severity:** Medium (High impact x Low likelihood).

`manualSwapToAsset` is management-only, but it clamps the requested amount to the entire `valueOfLST()` and forwards `_minOut` unchanged (`src/BaseLSTAccumulator.sol:222-229`). In the 4626 strategy this can first redeem the downstream principal position (`src/Strategy4626.sol:44-47,79-98`). The concrete Curve call then executes `exchange(stETH, ETH, amount, _minOut)` (`src/Strategy.sol:71-80`). There is no on-chain oracle/TWAP floor, lot limit, or requirement that `_minOut` be economically meaningful.

The committed tests repeatedly exercise the principal route with `_minOut = 0`: `src/test/StethSpecific.t.sol:167-201,249-269`, `src/test/Strategy4626.t.sol:41-52`, and `src/test/Operation.t.sol:54-63,108-118,252-266`. Focused mainnet-fork runs confirmed that zero is accepted, but did not simulate hostile liquidity or mempool ordering.

**Conditional harm path:** management (or a compromised/misconfigured management executor) submits a large public-mempool unwind with zero or stale-low min-out; an adversary moves Curve price before the swap and restores it afterward; the strategy realizes avoidable principal loss. The blast radius is the caller-selected amount, potentially the full stETH-denominated position.

**Why not elevated to an unconditional finding:** only management can invoke the route, a safe caller-supplied `_minOut` fully prevents the hypothesized fill, and no evidence in this blind lane establishes the production transaction builder, private relay, lot sizing, or actual use of zero. A bare `require(_minOut > 0)` would not be a meaningful fix.

**Recommended bound:** derive/enforce a maximum-slippage floor from a defensible price source, cap per-transaction lot size, and record whether execution is private. At minimum, make the operator payload/runbook reject zero or stale-low min-out and test manipulated-liquidity behavior.

**Smallest missing regression:** seed/manipulate the Curve fork around a large `manualSwapToAsset` call and assert that the strategy either reverts outside the configured loss bound or loses no more than the stated maximum.

## C-02 — Permanent downstream-vault allowance extends custody to loose emergency wstETH

**Classification:** plausible/conditional concern; source behavior validated, malicious/upgraded destination not established here.
**Severity:** Medium (High impact x Low likelihood).

The constructor verifies only that `_vault.asset()` is canonical wstETH, then grants that vault an unlimited wstETH allowance for the strategy lifetime (`src/Strategy4626.sol:20-27`). Normal staking deposits all loose wstETH to the vault (`src/Strategy4626.sol:29-42`). The emergency-authorized `manualRedeem` can later convert vault shares into loose wstETH, while `manualUnwrap` is a separate transaction and no allowance-revoke function exists (`src/Strategy4626.sol:105-117`). The factory accepts any caller-supplied vault meeting the asset check (`src/Strategy4626Factory.sol:43-60`), though production management acceptance and deposit gating remain separate protections.

**Conditional harm path:** the selected vault is malicious, upgraded, or compromised; emergency authorization redeems shares through `manualRedeem`; before a separate `manualUnwrap`, the vault uses `transferFrom` under its retained maximum allowance to pull the recovered wstETH. Any other loose wstETH or dust is similarly within the vault's pull authority without a strategy-initiated deposit.

**Why not elevated to an unconditional finding:** the vault already custodies the deposited principal position, normal `_freeStETH` redeems and unwraps in the same transaction, and this lane did not establish whether the intended vault is upgradeable or has a credible hostile-control path. The incremental blast radius is primarily recovered/loose wstETH during degraded-state operations.

**Recommended bound:** approve only the exact deposit amount and clear the allowance afterward, add an emergency allowance-revoke action, and provide an atomic redeem-and-unwrap fallback. Deployment gates should treat the `_vault` address and its control/upgrade surface as principal-custody configuration, not merely an ERC4626 compatibility check.

**Smallest missing regression:** use a mock ERC4626 vault that attempts `wstETH.transferFrom(strategy, ...)` after `manualRedeem`; prove either the pull fails or the recovery flow unwraps atomically before the vault can exercise residual authority.

## Callback and reentrancy review

- The inherited strategy callbacks `deployFunds`, `freeFunds`, `harvestAndReport`, `tendThis`, and `shutdownWithdraw` are all `onlySelf`; `_onlySelf` requires `msg.sender == address(this)` (`lib/tokenized-strategy/src/BaseStrategy.sol:40-82,355-440`). Forged direct callback entry was rejected.
- Pinned TokenizedStrategy deposit/mint/withdraw/redeem, report, tend, and emergency-withdraw paths use the shared non-reentrancy guard (`lib/tokenized-strategy/src/TokenizedStrategy.sol:283-295,487-570,1081-1096,1314-1364`).
- Strategy-specific manual operations are role-gated (`onlyManagement`, `onlyKeepers`, or `onlyEmergencyAuthorized`). External protocols cannot satisfy those checks unless configured into those roles.
- The only native-ETH callback is an empty `receive()` (`src/Strategy.sol:35`). Curve and Lido claim flows wrap `address(this).balance` into WETH after receipt (`src/Strategy.sol:73-81,103-125`); this also converts donated/forced ETH into the vault asset rather than sending it to a caller.
- No reward claim/sale callback exists: `_claimAndSellRewards` is empty in the base and not overridden in this generation (`src/BaseLSTAccumulator.sol:83-84`).

## Rejected / downgraded leads

| Lead | Disposition | Evidence / reason |
| --- | --- | --- |
| Public caller can forge TokenizedStrategy callbacks and move principal | Rejected | All five inherited callbacks are `onlySelf`; direct callers fail `msg.sender == address(this)` |
| Permissionless deposit Curve leg can accept less than 1:1 stETH | Rejected | Curve is selected only when `get_dy > amount`, and `exchange` uses `_minOut = amount` (`src/Strategy.sol:56-64`) |
| Generic sweep/rescue/auction can sell stETH, wstETH, or vault shares | Rejected for pinned generation | Exact pinned source search found no such function or periphery |
| Keeper can redirect Lido withdrawal claim | Rejected from strategy source | Claim receiver is determined by fixed queue/request ownership; strategy passes no receiver and immediately wraps received ETH (`src/Strategy.sol:103-112`) |
| `pendingRedemptions` is incremented before queue request and can remain inflated on request failure | Rejected | A revert from the external request reverts the preceding state increment atomically (`src/BaseLSTAccumulator.sol:242-247`) |
| Wrapping the entire native balance after a swap/claim steals donated ETH | Rejected | WETH is the strategy asset; converted ETH remains in strategy custody and becomes reportable principal/profit |
| Permanent wstETH allowance alone lets an arbitrary factory caller steal a production strategy | Downgraded to C-02 | Each factory child is closed by default and awaits configured management acceptance; destination selection/attachment is a production gate |
| Factory `symbol()` callback can reenter before `deployments[_vault]` is written | Downgraded/out of lane | A malicious vault could challenge one-deployment registry semantics, but no direct principal harm was established; factory/registry integrity belongs in roles/deployment synthesis |

## Focused tests executed

Only the following focused suites/tests are claimed; no full-suite claim is made. All ran against `https://ethereum.publicnode.com` from the pinned checkout after exact gitlink initialization.

1. Command:

   ```text
   forge test --match-path src/test/Strategy4626.t.sol -vv --fork-url https://ethereum.publicnode.com
   ```

   Result: exit `0`; 5 passed, 0 failed, 0 skipped. Covered wrap/deposit custody, reporting the receipt position, manual Curve exit from the vault, and queue initiation from the vault.

2. Command:

   ```text
   forge test --match-path src/test/StethSpecific.t.sol --match-test 'test_(manualStakeAndSwap|curvePoolSwap)' -vv --fork-url https://ethereum.publicnode.com
   ```

   Result: exit `0`; 2 passed, 0 failed, 0 skipped. Confirmed management manual staking and the Curve sale path accept the test's zero min-out.

3. Command:

   ```text
   forge test --match-path src/test/Shutdown.t.sol -vv --fork-url https://ethereum.publicnode.com
   ```

   Result: exit `0`; 3 passed, 0 failed, 0 skipped. Covered full and partial emergency Curve exits using the configured 50-bps `reportBuffer` floor.

4. Command:

   ```text
   forge test --match-path src/test/WithdrawalQueue.t.sol -vv --fork-url https://ethereum.publicnode.com
   ```

   Result: exit `0`; 7 passed, 0 failed, 0 skipped. Covered request, claim, pending-report lock, manual claim, manual pending clear, and multiple request behavior. These tests replace the fixed queue code with a mock and therefore do not prove real Lido NFT/claim authorization or loss behavior.

5. Command:

   ```text
   forge test --match-path src/test/Strategy4626Factory.t.sol -vv --fork-url https://ethereum.publicnode.com
   ```

   Result: exit `0`; 5 passed, 0 failed, 0 skipped. Covered factory child initialization, duplicate deployment check, wrong-asset rejection, and role-address updates; no malicious-vault callback case is present.

No new PoC source was created because this lane was restricted to a single assigned output file.

## Missing evidence and residual risks

- No adversarial Curve price/MEV test, route-depth evidence, sale-size bound, transaction-builder policy, private-relay proof, or operator runbook was available for C-01.
- No malicious/upgraded ERC4626 mock test, allowance-revocation test, or atomic degraded-state recovery test exists for C-02.
- Exact downstream-vault upgrade/admin/control surface and live allowance state were not reviewed here; they belong to destination-protocol and live-config due diligence.
- The real Lido withdrawal-request NFT ownership/transfer rules, claim authorization, queue pause state, and slash/discount behavior were not established by the repo mock.
- There is no invariant asserting that WETH, stETH, wstETH, ERC4626 shares, and withdrawal claims can move only to their enumerated destinations after future dependency or strategy changes.
- There is no callback/reentrancy test using a hostile ERC4626 vault.
- The factory's external `symbol()` call occurs before its deployment mapping is written and is not covered by a hostile-vault reentrancy test; no direct fund impact was proven in this lane.

## Lane stop/go assessment

**`warn / ready only with rechecks`** for this lane. The pinned source does not expose an unconditional public principal drain, generic sweep, unsafe external callback, or unbounded automatic deposit swap. Production readiness still depends on (1) bounded/private manual Curve unwind operations, (2) explicit acceptance of the downstream vault's permanent allowance and control surface or tighter approvals, and (3) real destination/queue live-state verification outside this lane.
