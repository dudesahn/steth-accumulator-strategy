# Lane 03 — Destination protocol due diligence and external-state assumptions

## Scope, provenance, and evidence grade

- Review object: detached `4580174c60ccac4658d97b02f0951aec92b218b2` in `/Users/dudesahn/.codex/worktrees/8c5a/steth-accumulator-strategy`.
- The root orchestrator proved the worktree clean and pinned before review. At this lane's first status check, `git rev-parse HEAD` returned the exact commit and `git status --short --branch` showed only `?? .review-output/`, the shared output directory created after that proof. No sibling lane artifact was read.
- Exact inherited gitlinks inspected only as needed: `tokenized-strategy@82806289f967590c4efbf6bc3d237e4e7f0a0966` and `tokenized-strategy-periphery@fc1b1d4ab5c9a0b65b7ac785734c404d3742317a`.
- Blind boundary preserved: no parent checkout, other worktree, branch/history/reflog/stash, audit artifact, manual report, issue comment, prior finding, live deployment, or later deployment evidence was inspected.
- Destination evidence grade: `bounded_dd`. Exact strategy source and tests were inspected. Official Lido and ERC-4626 specifications were used only for protocol mechanics. No current balances, liquidity, roles, implementations, proxy slots, queue state, or downstream-vault configuration were queried.
- Test evidence: source-inspected tests plus one pure ABI reproduction. No fork test was run because this phase explicitly excludes live deployment state.

## Mechanics and trust boundary

`WETH asset -> ETH -> (Curve ETH/stETH if quoted output > input, otherwise Lido submit) -> stETH -> wstETH -> constructor-supplied ERC-4626 vault shares`.

Principal may therefore exist as:

1. loose WETH/ETH;
2. loose rebasing stETH;
3. loose non-rebasing wstETH;
4. downstream ERC-4626 shares representing wstETH; or
5. an `unstETH` ERC-721 withdrawal request while Lido redemption is pending.

The normal strategy ERC-4626 withdrawal path exposes only loose WETH (`BaseLSTAccumulator.availableWithdrawLimit`, lines 123-134); management/emergency operators must first free principal through the downstream vault and Curve or through Lido's asynchronous queue.

Source anchors:

- Lido stETH: `0xae7a...e84`, `src/Strategy.sol:31-33`.
- wstETH: `0x7f39...2Ca0`, `src/Strategy4626.sol:16`.
- Lido WithdrawalQueueERC721: `0x889e...F9B1`, `src/Strategy.sol:20-23`.
- Curve ETH/stETH pool: `0xDC24...022`, `src/Strategy.sol:23-27`.
- Downstream ERC-4626 vault: arbitrary immutable constructor argument whose only constructor check is `vault.asset() == wstETH`, `src/Strategy4626.sol:18-27`. The factory is permissionless and can instantiate one child per supplied vault, `src/Strategy4626Factory.sol:43-61`.
- One committed example/test target is `0xE73b2561309Bed1035D2145275BCA1aEcf85A8F7`, named in `script/Deploy4626.s.sol:12-18` and `src/test/utils/Setup4626.sol:20-27`; its implementation and external positions are not included in this repository.

## Findings table

| ID | Classification | Severity (Impact x Likelihood) | Summary | Stop/go effect |
| --- | --- | --- | --- | --- |
| DD-V1 | validated | Medium (`High x Low`) | A keeper can deploy all idle/recovered WETH back through Lido/wstETH/the downstream vault after shutdown; `stakeAsset`, `depositLimit`, and shutdown do not bound `_tend`. | Require code fix or an explicit keeper-revocation/shutdown runbook before relying on emergency recovery. |
| DD-V2 | validated | Low (`Medium x Low`) | `initiateLSTWithdrawal` returns `abi.encode(uint256[])`, while the normal claim path decodes its bytes as one `uint256`; directly forwarding the returned data deterministically selects request id `32`. | Fix the API or make the required decode/re-encode operation explicit and tested. |
| DD-C1 | plausible/conditional | Medium conditional (`High x Low`) | The generic ERC-4626 integration has no minimum-shares bound, gives the vault an unlimited wstETH allowance, and values shares with gross `convertToAssets`; safety is wholly dependent on the exact vault implementation and admins. | Block each child until exact vault source, admin/config, fee, donation/inflation, and exit-liquidity review is complete. |
| DD-C2 | plausible/conditional | Low (`Low x Medium`) | The strategy checks only Lido's pause flag, not its current stake-rate limit; direct-submit deposits/reports can revert when the limit is below the attempted amount. | Operational recheck; add current stake-limit awareness or bounded fallback. |
| DD-C3 | plausible/conditional | Low (`Low x Low`) | Converting downstream `maxDeposit` into stETH/WETH capacity can overshoot when the selected Curve route returns more than 1 stETH per ETH. | Test and leave headroom near downstream caps. |

## Detailed validated findings

### DD-V1 — Keeper can restore destination exposure after shutdown

Impact: High. Likelihood: Low. Severity: Medium.

Evidence and path:

1. Inherited `TokenizedStrategy.tend()` remains callable by management or keeper and passes the strategy's entire loose asset balance to the strategy callback (`lib/tokenized-strategy/src/TokenizedStrategy.sol:1314-1319`). The inherited shutdown documentation explicitly says `tend` and `report` remain available after shutdown (`TokenizedStrategy.sol:1326-1331`), and `emergencyWithdraw` only requires shutdown (`TokenizedStrategy.sol:1356-1364`).
2. `BaseLSTAccumulator._tend` unconditionally calls `_stake(_totalIdle)` and checks neither shutdown, `stakeAsset`, nor `_depositLimit()` (`src/BaseLSTAccumulator.sol:158-160`).
3. `stakeAsset` guards only deposit-time `_deployFunds` (`BaseLSTAccumulator.sol:102-106`). The repository even codifies that report bypasses this flag in `src/test/StethSpecific.t.sol:332-353`.
4. In `Strategy4626`, `_stake` converts WETH to stETH, wraps the entire stETH balance, and deposits the entire wstETH balance into the downstream vault (`src/Strategy4626.sol:29-42`; `src/Strategy.sol:48-68`).

Consequences:

- During an incident, emergency admin can shut down and free funds, but a still-authorized or compromised keeper can call `tend()` and re-expose all recovered WETH to Lido, wstETH, and the downstream vault.
- `setStakeAsset(false)` and `setDepositLimit(0)` do not stop this `_tend` path. Emergency admin cannot change the keeper; only management can (`TokenizedStrategy.sol:1528-1544`).
- The keeper cannot redirect funds to itself, so the direct impact is renewed illiquidity/trapping and a delayed emergency exit rather than theft. Blast radius is the full loose WETH balance, especially material if the downstream vault is paused or illiquid.

Recommended invariant: once shutdown is true, no keeper-only call may increase stETH, wstETH, or downstream-vault share balances. Make `_tend` return when shutdown or `!stakeAsset`, and cap it by `_depositLimit()`. Operationally, revoke the keeper before or atomically with shutdown until code enforces the invariant.

### DD-V2 — Withdrawal request return bytes are not valid normal-claim bytes

Impact: Medium. Likelihood: Low. Severity: Low.

Evidence and path:

1. `_initiateLSTWithdrawal` receives a `uint256[] requestIds` and returns `abi.encode(requestIds)` (`src/Strategy.sol:90-99`).
2. `_claimLSTWithdrawal` decodes supplied bytes as a scalar `(uint256)` (`src/Strategy.sol:103-108`).
3. The public base API describes the latter as claim data from the withdrawal request (`src/BaseLSTAccumulator.sol:72-81,239-255`), making direct composition a reasonable interpretation.
4. ABI encoding a one-element dynamic array starts with the offset `0x20`; decoding those bytes as a scalar produces `32`, not the request id.

Reproduction (pure ABI; no chain state):

```text
$ cast --version
cast Version: 1.5.1-stable
$ cast abi-encode 'f(uint256[])' '[12345]'
0x000...020000...001000...3039
$ cast abi-decode 'f()(uint256)' 0x000...020000...001000...3039
32
```

The existing tests avoid the bug by decoding the returned array and re-encoding `requestIds[0]` before claim (`src/test/WithdrawalQueue.t.sol:70-80,104-117,133-147`). Directly forwarding `returnData` normally reverts because the strategy does not own request 32; if it does own an eligible request 32, it can claim the wrong request. Funds still return to the strategy, and the emergency batch-claim path remains available, which lowers severity.

Recommended change: use typed APIs (`uint256[]` return, `uint256 requestId` claim), or make claim decode `uint256[]` and explicitly select/iterate. Add a regression that passes the initiation result exactly as documented and proves the created request is the one claimed.

## Plausible / conditional concerns and deployment gates

### DD-C1 — Exact ERC-4626 vault is the dominant unresolved trust surface

Source facts:

- The only constructor validation is `asset() == wstETH`; no implementation hash, factory provenance, proxy admin, fee model, or vault behavior is constrained (`src/Strategy4626.sol:20-27`).
- The vault receives an unlimited wstETH allowance (`Strategy4626.sol:25-26`).
- `_stake` calls `vault.deposit(allWstETH, this)` and ignores returned shares; there is no minimum-shares/slippage assertion (`Strategy4626.sol:37-42`).
- Accounting uses `vault.convertToAssets(vault.balanceOf(this))` (`Strategy4626.sol:71-76`). EIP-4626 defines this as an idealized estimate that excludes fees and current exit conditions; it is not proof of realizability.
- Exit caps `previewWithdraw(...)` by `maxRedeem(this)` and redeems that many shares (`Strategy4626.sol:79-98`). This handles partial liquidity mechanically, but reported value can remain gross while immediately redeemable value is zero or fee-discounted.

The [ERC-4626 specification](https://eips.ethereum.org/EIPS/eip-4626) expressly warns that permissionless integrations must review the concrete implementation, that `convertToAssets` need not equal realizable assets, and that integrations may need explicit slippage bounds. Therefore this is not a source-proven exploit for the intended vault, but it is a hard per-child gate. A conforming vault with deposit rounding/inflation exposure, withdrawal fees, manipulable previews, mutable allocation, upgrade authority, or malicious code can lose or trap all deposited wstETH.

Required proof before any child is funded:

- exact vault implementation/proxy/admin and source parity;
- all strategies/markets holding its wstETH and their loss/illiquidity paths;
- deposit/withdrawal fees and `previewDeposit`/`previewRedeem` deltas;
- empty-vault/donation/inflation behavior and minimum minted shares;
- `maxDeposit`, `maxRedeem`, pause/shutdown, queue, debt, and emergency states;
- ability of management/guardian/allocator to upgrade, pause, add strategies, change debt, or move assets;
- bounded loss if `convertToAssets > previewRedeem` or `maxRedeem == 0`.

The committed tests are not that proof. `Setup4626` creates a local mock and immediately overwrites it with the fixed external address (`src/test/utils/Setup4626.sol:20-24`), then impersonates the downstream vault's management to allowlist the new strategy (`lines 41-42`). The production factory does not perform that allowlisting, so downstream `setAllowed(child,true)` is also an explicit attachment gate.

### DD-C2 — Lido's current stake limit is omitted

`Strategy._depositLimit` checks only `isStakingPaused()` (`src/Strategy.sol:37-42`), and `ISTETH` does not expose `getCurrentStakeLimit()` (`src/interfaces/ISTETH.sol:6-9`). If Curve is not quoting more than 1:1, `_stake` chooses `Lido.submit` for the full amount (`Strategy.sol:56-68`).

Official [Lido contract documentation](https://docs.lido.fi/contracts/lido/) defines a mutable per-block current stake limit distinct from the pause flag. When the attempted amount exceeds the available limit, the direct route can revert even though `availableDepositLimit` advertises capacity. This can block deposits, tend, or report until capacity regenerates or Curve becomes the selected route. No principal is lost because the transaction reverts.

### DD-C3 — Downstream cap can be exceeded by the positive Curve route

`vault.maxDeposit(this)` is denominated in wstETH; the adapter converts it to stETH value and exposes that number as WETH deposit capacity (`src/Strategy4626.sol:55-60`). But `_stake` deliberately selects Curve only when Curve returns more stETH than the WETH input (`src/Strategy.sol:56-64`). At the exact advertised cap, the resulting stETH wraps into more wstETH than `maxDeposit`, so `vault.deposit` may revert. This is a near-cap liveness issue, not a loss: retain headroom or derive the WETH limit from a conservative Curve/Lido output bound.

### Lido queue residual assumptions

Official [WithdrawalQueueERC721 documentation](https://docs.lido.fi/contracts/withdrawal-queue-erc721/) establishes that:

- each request must be between 100 wei and 1000 stETH;
- requests are asynchronous ERC-721 `unstETH` claims;
- finalization depends on ETH availability, time, oracle-selected share rate, and can occur below 1:1 after a sufficiently large protocol loss;
- `PAUSE_ROLE`, `RESUME_ROLE`, `FINALIZE_ROLE`, and `ORACLE_ROLE` affect request placement/finalization, while already-finalized claims remain available.

The strategy creates only one request per call and does not chunk amounts above 1000 stETH (`Strategy.sol:90-98`), so large exits require multiple management calls. `pendingRedemptions` is increased by requested stETH but decreased by actual ETH claimed (`BaseLSTAccumulator.sol:242-255`; `Strategy.sol:103-111`); a below-1:1 finalization leaves a nonzero residual and blocks reports until management deliberately clears it. `clearPendingRedemptions` is the explicit escape hatch and warns that the next report may realize loss (`BaseLSTAccumulator.sol:258-264`). These are operational constraints rather than unmitigated bugs, but they need monitoring and a loss-approval runbook.

## Destination instance matrix

| Instance | Principal / exit form | Mutable or privileged surface | Reviewed state |
| --- | --- | --- | --- |
| Lido stETH `0xae7a...e84` | ETH becomes rebasing stETH; value changes with oracle reports/slashing | staking pause/rate controls; oracle/accounting; proxy/governance surface | Mechanics only; current roles/rate/oracle state not checked. |
| wstETH `0x7f39...2Ca0` | stETH locked for non-rebasing wstETH; unwrap returns current stETH share value | Depends on canonical stETH accounting | Mechanics only; official docs confirm wrap/unwrap denomination. |
| Lido WithdrawalQueueERC721 `0x889e...F9B1` | stETH becomes transferrable unstETH NFT, then claimable ETH | pause/resume/finalize/oracle roles; proxy upgrade surface; queue ETH availability | Mechanics only; queue/finalization/bunker state not checked. |
| Curve ETH/stETH `0xDC24...022` | ETH <-> stETH synchronous exchange | pool liquidity/price and unresolved admin/pause controls | Source route only; balances, admin and exit depth not checked. |
| Constructor-supplied ERC-4626 vault | wstETH becomes vault shares; redeem returns wstETH | arbitrary vault admin, proxy, allocator/strategy, pause/cap/fee/accounting controls | Unresolved. Example address is named, but its source/config/state were deliberately not inspected. |

## Fund-control surface

| Actor | Power affecting Yearn funds | Bound / mitigation | Confidence |
| --- | --- | --- | --- |
| Strategy management | Set `stakeAsset`, deposit cap, report buffer, keeper/emergency admin; manually stake/swap; initiate queue; clear pending losses | Privileged; `manualSwapToAsset` caller supplies min-out. Management can set buffer to 100%, so operational policy must bound it. | Source-confirmed. |
| Strategy keeper | Report, tend, and claim single queue requests; management is also treated as keeper | Can re-deploy all idle funds via `tend`; see DD-V1. | Source-confirmed. |
| Strategy emergency admin | Shutdown, Curve emergency exit, manual downstream redeem/unwrap, batch queue claim | Cannot revoke keeper or change caps; downstream liquidity still controls success. | Source-confirmed. |
| Downstream vault management/admin/guardian/allocator | Potentially pause deposits/redeems, change allocations/fees/caps, upgrade code, or impair/reprice shares | No source-side restriction beyond `asset() == wstETH`; must be resolved per child. | Unresolved. |
| Lido governance/proxy/role actors | Can affect staking availability, core/queue code, finalization timing/share rate and pause state | Two exits exist (Curve and queue), but both can be impaired simultaneously by market/protocol stress. | Mechanic confirmed; exact reviewed-era holders/delays unverified. |
| Curve pool governance/admin and LP state | Can affect synchronous exit availability and slippage | Management min-out/report buffer; Lido queue is async alternative. | Unresolved. |

## Tests, invariants, and evidence gaps

Inspected relevant tests:

- `src/test/Strategy4626.t.sol` covers happy-path deposit, gross report value, vault redeem on manual swap, and vault redeem before queue initiation.
- `src/test/WithdrawalQueue.t.sol` uses an etched mock queue; it covers request, transformed scalar claim data, pending-report blocking, clear, and manual batch claim.
- `src/test/StethSpecific.t.sol` covers route selection and explicitly proves report bypasses `stakeAsset`.
- No test executed against live state. Existing Strategy4626 tests depend on a fixed external vault address with no pinned fork block in `foundry.toml`/Makefile, so their present green status was not claimed.

Missing high-value checks:

1. invariant: shutdown cannot increase stETH/wstETH/vault-share balances under `report` or `tend`;
2. direct composition of initiation return bytes into normal claim;
3. downstream `maxRedeem == 0`, partial liquidity, paused redeem, withdrawal fee, and `convertToAssets > previewRedeem`;
4. empty/donated/inflated vault and a deposit that mints zero/negligible shares;
5. downstream allowlist absent, management changed, cap changed between view and deposit, and vault upgrade/admin mutation;
6. Lido staking unpaused but current limit 0 or below attempted deposit;
7. Curve positive quote at the downstream max-deposit boundary;
8. queue request at 99 wei, 100 wei, 1000 ETH, and 1000 ETH + 1; multiple outstanding NFTs; below-1:1 claim; paused/finalization-delayed state;
9. Curve unavailable plus queue paused/delayed and downstream `maxRedeem == 0`;
10. fixed-block fork tests for exact intended vault code/config, only in the later deployment-aware phase.

## Rejected or downgraded leads

- **Factory permissionlessness does not grant attacker strategy management.** `BaseStrategy` initially assigns roles to the deployer, which is the factory; the factory then installs its configured keeper/emergency roles and pending management. An arbitrary caller can trigger deterministic configuration for a vault but does not receive control. This remains an operational deployment/front-run nuisance, not a theft path.
- **No stETH/wstETH unit mismatch found in gross valuation.** Vault assets and loose wstETH are added in wstETH units before `getStETHByWstETH` converts them; loose stETH is then added in stETH units (`Strategy4626.sol:67-76`).
- **Curve deposit routing has a hard 1:1 minimum.** The quote selects the route, but `exchange` sets minimum stETH output to the WETH/ETH input (`Strategy.sol:56-64`), so the positive-route decision alone does not permit principal slippage below 1:1.
- **Queue claim uses actual returned ETH.** The normal claim measures the ETH balance delta and wraps the actual amount (`Strategy.sol:103-111`); it does not assume the requested amount was returned. Residual pending bookkeeping after a haircut is handled separately above.
- **`manualRedeem` may revert under partial downstream liquidity.** It caps by owned shares rather than `maxRedeem` (`Strategy4626.sol:105-110`), but emergency operators can query/call a smaller amount and `_freeStETH` uses `maxRedeem`; downgraded to an operational footgun.
- **`wstETH.unwrap(0)` can revert when the downstream vault reports value but `maxRedeem == 0`.** This makes a max-sized emergency call fail rather than free zero/only loose stETH; granular operator calls can still swap loose stETH, and locked vault funds are not actually retrievable in that state. Downgraded to an illiquidity-handling edge case.

## Stop/go and open questions

Lane status: `source_replay_complete_not_deployment_ready`.

The source mechanics are reviewable, but production attachment should remain blocked until the exact downstream ERC-4626 child is identified and its code, nested positions, privileges, allowlist, fees, caps, and exit state are verified. DD-V1 should be fixed or covered by a concrete atomic shutdown/keeper-revocation procedure. DD-V2 should be made type-safe before queue automation relies on the returned bytes.

Questions for the later comparison/deployment-aware phase:

1. Is `0xE73b...A8F7` the sole intended destination vault or only an example? What exact source commit/implementation and nested positions back it?
2. Who controls that vault's management, emergency admin, allocator/strategies, proxy, and allowlist, and what delays apply?
3. Is the strategy child allowlisted before deposits/debt are enabled, and is that transaction part of the deployment checklist?
4. Is the keeper revoked atomically on shutdown, or is post-shutdown tend intentionally accepted?
5. What automation transforms `uint256[]` initiation return data into scalar claim data, and is it regression-tested?
6. What report buffer and manual Curve min-out policy is required at the expected TVL?
7. What maximum strategy size is intended relative to Lido's 1000-stETH per-request queue bound and downstream/Curve exit depth?

## Training extraction notes

- `blind_agent_found`: post-shutdown maintenance permissions must be traced to the first external action; a generic “shutdown stops deposits” invariant does not prevent keeper re-exposure.
- `blind_agent_found`: typed async claims should be followed end-to-end through return encoding, automation handoff, and claim decoding.
- `production_caveat`: an ERC-4626 `asset()` check proves denomination only, not implementation safety, realizable value, or admin/exitability.
- `external_protocol_review`: hardcoded proxies and queues preserve interface addresses while governance, implementation, pause, oracle, and finalization behavior can change underneath the strategy.
