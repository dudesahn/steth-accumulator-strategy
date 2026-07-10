# Economics and Composability Lane

## Coverage

Reviewed the economics / flash-loan / DeFi-composability surface for:

- Curve ETH/stETH route selection and min-output behavior in `Strategy._stake` and `_swapLSTToAsset` (`src/Strategy.sol:51-81`).
- stETH/wstETH/ERC4626 accounting in `Strategy4626`, especially vault capacity, `convertToAssets`, `previewWithdraw`, and `maxRedeem` usage (`src/Strategy4626.sol:29-96`).
- Deposit-limit, `reportBuffer`, public deposit gating, liquid-only withdrawal semantics, report/tend flows, and manual exit paths (`src/BaseLSTAccumulator.sol:96-178`, `src/BaseLSTAccumulator.sol:198-281`).
- Factory permissionlessness and default Strategy4626 configuration (`src/Strategy4626Factory.sol:43-68`).
- Inherited Yearn V3 share accounting, deposits, withdrawals, reports, profit locking, and tend behavior (`lib/tokenized-strategy/src/TokenizedStrategy.sol:487-635`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:836-1044`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:1081-1247`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:1314-1364`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:1596-1617`).

No CRITICAL or HIGH economics/flash-composability issue was identified from this lane. The concrete leads below are MEDIUM/LOW and are mostly conditional on public deposits, keeper/report timing, or use of a manipulable ERC4626 vault.

## Candidates

### HP-ECO-01: Public deposits can re-stake idle WETH withdrawal liquidity

Severity: MEDIUM (Impact: Medium, Likelihood: Medium when deposits are open or the caller is allowlisted)

`TokenizedStrategy._deposit` transfers the depositor's WETH, then calls `deployFunds` with the strategy's entire loose WETH balance, not just the newly deposited amount (`lib/tokenized-strategy/src/TokenizedStrategy.sol:963-969`). The local `_deployFunds` stakes that whole amount whenever `stakeAsset == true` and the balance exceeds `ASSET_DUST` (`src/BaseLSTAccumulator.sol:109-112`). Because withdrawals are intentionally liquid-only (`_freeFunds` is a no-op at `src/BaseLSTAccumulator.sol:115-123`, and `availableWithdrawLimit` is just `balanceOfAsset()` at `src/BaseLSTAccumulator.sol:133-143`), a small public/allowlisted deposit can convert WETH that management had left available for withdrawals back into stETH or wstETH/vault exposure.

Attack shape:

1. Management or a completed queue claim leaves WETH idle so users can withdraw.
2. Deposits are open, or an allowed account can deposit (`src/BaseLSTAccumulator.sol:126-130`, `src/BaseLSTAccumulator.sol:216-224`).
3. Attacker deposits a small amount that mints nonzero shares.
4. The deposit path stakes the full idle WETH balance through Lido/Curve (`src/Strategy.sol:51-69`) and, for Strategy4626, wraps/deposits the resulting stETH into the ERC4626 vault (`src/Strategy4626.sol:29-42`).
5. `maxWithdraw` drops because loose WETH is gone, forcing users back into management-mediated swaps or Lido withdrawal queue timing.

This does not directly steal funds, but it is an externally triggered liquidity grief that is especially relevant because the strategy explicitly does not free funds on user withdrawals.

### HP-ECO-02: Factory-created Strategy4626 deployments disable profit locking, enabling report-front-run dilution when deposits are public

Severity: MEDIUM (Impact: Medium, Likelihood: Medium if deposits are public and reports are predictable; Low if deposits stay closed/allowlisted)

The factory sets `profitMaxUnlockTime` to zero for every deployed Strategy4626 (`src/Strategy4626Factory.sol:62-64`). In Yearn V3, deposits mint shares against the last recorded `totalAssets` (`lib/tokenized-strategy/src/TokenizedStrategy.sol:505-510`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:836-851`) and only add the depositor's `assets` to recorded `totalAssets` after deployment (`lib/tokenized-strategy/src/TokenizedStrategy.sol:971-975`). Unreported gains from the ERC4626 vault are only incorporated when `report()` calls `harvestAndReport` and updates `S.totalAssets` (`lib/tokenized-strategy/src/TokenizedStrategy.sol:1095-1117`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:1245-1247`).

When `profitMaxUnlockTime != 0`, new profit is locked by minting shares to the strategy (`lib/tokenized-strategy/src/TokenizedStrategy.sol:1164-1183`). With the factory's zero unlock setting, that branch is skipped, so a positive report immediately increases PPS. A depositor who front-runs a keeper report can mint at stale pre-profit accounting and share in the immediately recognized vault/Curve/reportBuffer-release profit that economically belonged to pre-existing shareholders.

The report source for Strategy4626 includes `vault.convertToAssets(vault.balanceOf(address(this)))` converted back through wstETH (`src/Strategy4626.sol:69-75`), so this is most relevant when the underlying vault has accrued yield or when a vault/accounting value changes shortly before a report. Extraction still depends on future liquidity because withdrawals are liquid-only, but the share dilution occurs at report time.

### HP-ECO-03: Strategy4626 trusts external ERC4626 accounting for NAV, deposit capacity, and freeing funds

Severity: MEDIUM, deployment-conditional (Impact: High if an endorsed vault is malicious/manipulable, Likelihood: Low for vetted Yearn-style vaults)

`Strategy4626` only checks that the external vault's `asset()` is wstETH in the constructor (`src/Strategy4626.sol:20-23`). After that, core accounting and limits trust the vault:

- `availableDepositLimit` trusts `vault.maxDeposit(address(this))` (`src/Strategy4626.sol:55-63`).
- NAV trusts `vault.convertToAssets(vault.balanceOf(address(this)))` (`src/Strategy4626.sol:69-75`).
- stETH freeing trusts `vault.previewWithdraw`, `vault.maxRedeem`, and `vault.redeem` (`src/Strategy4626.sol:77-96`).

A malicious or flash-manipulable ERC4626 vault can therefore overstate NAV before report to create false profit, understate NAV to admit deposits past the intended gross cap, or make `previewWithdraw`/`maxRedeem` prevent full exits. Health checks can bound large profit/loss reports (`lib/tokenized-strategy-periphery/src/Bases/HealthCheck/BaseHealthCheck.sol:136-159`), but management can disable the next check (`lib/tokenized-strategy-periphery/src/Bases/HealthCheck/BaseHealthCheck.sol:109-110`), and factory-created strategies also remove profit-lock smoothing as noted in HP-ECO-02.

Factory permissionlessness alone does not make this immediately exploitable: new Strategy4626 instances start with deposits closed by default, and the factory sets pending management to the configured management address (`src/Strategy4626Factory.sol:54-64`, `src/BaseLSTAccumulator.sol:44-46`, `src/BaseLSTAccumulator.sol:126-130`). This becomes a real user-risk only if management endorses/opens a strategy for an untrusted or economically manipulable ERC4626 vault.

### HP-ECO-04: Loss-realizing manual swaps can create a withdrawal race before the next report

Severity: LOW (Impact: Medium, Likelihood: Low due management-only trigger)

Management can manually swap stETH to WETH through Curve with a chosen `_minOut` (`src/BaseLSTAccumulator.sol:241-245`, `src/Strategy.sol:74-81`). This creates loose WETH immediately, while any loss versus the strategy's prior recorded accounting is not incorporated until a later `report()` (`lib/tokenized-strategy/src/TokenizedStrategy.sol:1081-1247`). Withdrawals that can be satisfied from idle WETH do not call `_freeFunds`; they burn shares and transfer WETH against the current recorded `totalAssets` (`lib/tokenized-strategy/src/TokenizedStrategy.sol:1008-1044`).

If management realizes a loss-making manual swap and does not report in the same operational bundle, faster withdrawers can exit against stale accounting and leave a larger share of the eventual loss to remaining holders. This is not publicly triggerable without a management action, but liquid-only withdrawals make the post-swap/pre-report window economically sensitive.

## Non-Findings / Rejected Ideas

- Curve route-selection manipulation was not a loss vector in the WETH->stETH direction. `_stake` only uses Curve when `get_dy(ETH, stETH, amount) > amount`, and the actual `exchange` uses `_min_to_amount = amount` (`src/Strategy.sol:57-65`). A flash/sandwich manipulation can make the deposit revert or miss a premium, but not accept below-1:1 stETH output.
- Same-transaction public `deposit -> report -> withdraw` is not directly drainable without pre-existing/introduced loose WETH because deposits stake the full loose WETH balance (`lib/tokenized-strategy/src/TokenizedStrategy.sol:963-969`, `src/BaseLSTAccumulator.sol:109-112`) and withdrawals are capped to `balanceOfAsset()` (`src/BaseLSTAccumulator.sol:133-143`).
- Public factory deployment is not itself endorsement of a vault. Anyone can call `newStrategy4626` for a wstETH ERC4626 vault (`src/Strategy4626Factory.sol:43-68`), but deposits are closed until management configures/open deposits (`src/BaseLSTAccumulator.sol:44-46`, `src/BaseLSTAccumulator.sol:126-130`). UIs/integrators should still avoid treating `NewStrategy4626` as a vault-quality signal.
- Raw ETH donations to `receive()` (`src/Strategy.sol:36`) are not an extractable flash-loan path by themselves. Later swaps/claims wrap the whole ETH balance to WETH (`src/Strategy.sol:80-81`, `src/Strategy.sol:111-112`), which benefits the strategy unless paired with a separate stale-accounting/front-run sequence.
- `reportBuffer` is management-only. It intentionally discounts `valueOfLST()` in `estimatedTotalAssets` (`src/BaseLSTAccumulator.sol:177-179`) and therefore also affects `_depositLimit()` (`src/BaseLSTAccumulator.sol:96-103`). A nonzero buffer can let gross assets exceed the nominal deposit cap by the haircut amount, and a value above `MAX_BPS` can make views/reports revert, but this is a configuration risk rather than a public flash/composability exploit (`src/BaseLSTAccumulator.sol:198-200`).

## Suggested PoCs

### PoC sketch for HP-ECO-01

Create a Foundry test that:

1. Opens deposits and has Alice deposit enough WETH to receive shares.
2. Has management make WETH idle, either by `manualSwapToAsset` in a fork test or by directly placing WETH in the strategy in a unit-style test.
3. Records Alice's `maxWithdraw`.
4. Has an attacker deposit a small amount that mints nonzero shares.
5. Asserts `asset.balanceOf(strategy)` and Alice's `maxWithdraw` fall because the deposit re-staked the entire idle WETH balance.

Suggested command:

```bash
forge test --match-test test_depositRestakesIdleWithdrawalLiquidity -vv --skip 'src/test/*PoC*.t.sol'
```

### PoC sketch for HP-ECO-02

Create a Strategy4626 test with a mock wstETH ERC4626 vault whose `convertToAssets` increases before report:

1. Deploy through `Strategy4626Factory` so `profitMaxUnlockTime() == 0`.
2. Open deposits and let Alice deposit first.
3. Increase the vault's apparent assets/yield without calling `report`.
4. Attacker deposits immediately before keeper `report`.
5. Assert the attacker receives shares at stale pre-profit accounting and participates in the immediate PPS increase after report.

Suggested command:

```bash
forge test --match-test test_frontRunReportCapturesUnlocked4626Profit -vv --skip 'src/test/*PoC*.t.sol'
```

### PoC sketch for HP-ECO-03

Create a malicious/mock ERC4626 vault with `asset() == wstETH` and switchable `convertToAssets`/`previewWithdraw` behavior:

1. Let Strategy4626 deposit wstETH into the vault.
2. Inflate `convertToAssets` for a keeper report and assert false profit is recorded.
3. Restore/decrease `convertToAssets` and report again to show the loss is shifted to current holders.
4. Optionally set `maxRedeem` below needed shares to show manual exits/withdrawal-queue initiation can be griefed.

Suggested command:

```bash
forge test --match-test test_malicious4626FalseProfitThenLoss -vv --skip 'src/test/*PoC*.t.sol'
```
