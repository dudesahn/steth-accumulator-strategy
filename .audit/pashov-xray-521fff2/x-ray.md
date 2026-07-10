# X-Ray Report

> stETH Accumulator Strategy | 390 in-scope nSLOC | 521fff2 (`review`) | Foundry | 08/07/26

---

## 1. Protocol Overview

**What it does:** A Yearn V3 TokenizedStrategy that accepts WETH, accumulates stETH, and optionally wraps/deposits stETH exposure into a wstETH ERC4626 vault.

- **Users**: ERC4626 depositors enter and exit through TokenizedStrategy functions delegated by the strategy fallback.
- **Core flow**: WETH deposits are staked into stETH through Lido or swapped through Curve when Curve is better than 1:1.
- **Key mechanism**: liquid withdrawals are limited to idle WETH; management/keeper/emergency paths free or claim LST-side liquidity.
- **Token model**: WETH is the strategy asset; stETH/wstETH/external ERC4626 shares are the yield-side positions.
- **Admin model**: TokenizedStrategy management configures parameters, keepers report/tend/claim, emergency authorized roles can shutdown and manually free positions.

For a visual overview of the protocol's architecture, see the [architecture diagram](architecture.svg).

### Contracts in Scope

| Subsystem | Key Contracts | nSLOC | Role |
|-----------|--------------|------:|------|
| Strategy core | BaseLSTAccumulator, Strategy | 242 | WETH/stETH accounting, staking, Curve swaps, Lido queue handling |
| ERC4626 extension | Strategy4626 | 81 | Wraps stETH to wstETH and deposits into a downstream ERC4626 vault |
| Deployment | Strategy4626Factory | 59 | Permissionless one-per-vault deployment with factory-configured roles |
| Periphery | StrategyAprOracle | 8 | Fixed illustrative APR oracle |

### How It Fits Together

The core trick: the strategy reports WETH-equivalent value across idle WETH, stETH, wstETH, and vault shares while only promising idle WETH for normal user exits.

### Deposit and stake

```text
TokenizedStrategy.deposit()/mint()
└─ BaseStrategy.deployFunds()
   └─ BaseLSTAccumulator._deployFunds()
      └─ Strategy._stake()
         ├─ Curve.exchange(ETH -> stETH) when get_dy > amount
         └─ Lido.submit() otherwise
```

### Report

```text
TokenizedStrategy.report()
└─ BaseHealthCheck.harvestAndReport()
   └─ BaseLSTAccumulator._harvestAndReport()
      ├─ require pendingRedemptions == 0
      ├─ _claimAndSellRewards()
      ├─ _stake(min(idle WETH, availableDepositLimit(address(this))))
      └─ estimatedTotalAssets()
```

### Manual unwind

```text
manualSwapToAsset()
└─ Strategy._swapLSTToAsset()
   ├─ Curve.exchange(stETH -> ETH)
   └─ WETH.deposit()
```

### ERC4626 vault layer

```text
Strategy4626._stake()
├─ Strategy._stake()
├─ wstETH.wrap(stETH)
└─ vault.deposit(wstETH, strategy)
```

### Lido withdrawal queue

```text
initiateLSTWithdrawal()
├─ pendingRedemptions += amount
└─ Strategy._initiateLSTWithdrawal()
   └─ LidoWithdrawalQueue.requestWithdrawals()
```

---

## 2. Threat & Trust Model

### Protocol Threat Profile

> Protocol classified as: **Yield Aggregator / Vault** with **Liquid Staking** characteristics

The code uses an ERC4626 TokenizedStrategy wrapper, strategy accounting callbacks, downstream vault deposits, and LST redemption/claim flows. The liquid-staking side comes from stETH/wstETH valuation and the Lido withdrawal queue.

### Actors & Adversary Model

| Actor | Trust Level | Capabilities |
|-------|-------------|--------------|
| Depositor | Untrusted | Calls inherited ERC4626 deposit/mint/withdraw/redeem; first-party custom deposit gating routes through `availableDepositLimit`. |
| Keeper | Bounded | Calls report/tend and `claimLSTWithdrawal`; cannot change parameters but can choose claim data. |
| Management | Trusted | Instant setters for strategy limits, report buffer, open/allowed deposits, manual staking/swaps, queue initiation, factory role defaults. |
| Emergency authorized | Trusted | Can shutdown through TokenizedStrategy and manually claim/redeem/unwrap or emergency-withdraw after shutdown. |
| Factory caller | Untrusted | Can deploy a Strategy4626 for any wstETH-backed ERC4626 vault not already registered. |
| External vault/Lido/Curve | External trust boundary | Supplies prices/capacity/conversion behavior used by staking, swapping, queueing, and valuation. |

**Adversary Ranking**

1. **Share/accounting boundary attacker** - relevant because user-facing ERC4626 accounting depends on strategy-reported WETH-equivalent value.
2. **External integration manipulator** - relevant because Lido, Curve, wstETH, and the downstream vault all feed core flows.
3. **Keeper timing attacker** - relevant because report/tend/claim timing controls when queued value becomes reportable.
4. **Compromised role holder** - relevant because management and emergency paths can manually move strategy liquidity with no timelock in this repo.

See [entry-points.md](entry-points.md) for the full permissionless entry point map.

### Trust Boundaries

- **TokenizedStrategy delegatecall boundary** - the strategy inherits ERC4626 accounting and role checks from the fixed implementation at `BaseStrategy.tokenizedStrategyAddress`.

- **LST valuation boundary** - `estimatedTotalAssets()` reads direct balances and wrapped/vault conversions; downstream conversion behavior is outside the first-party scope.

- **Manual liquidity boundary** - normal withdrawals are idle-WETH-only while management/emergency flows are responsible for moving value back from stETH/wstETH/vault positions.

- **Factory deployment boundary** - anyone can deploy for a vault, but role addresses and performance-fee settings come from mutable factory defaults.

### Key Attack Surfaces

- **Factory permissionless deployment role stamping** &nbsp;[[I-7](invariants.md#i-7)] - `newStrategy4626:43-69` deploys for user-chosen vaults and immediately applies factory role defaults; worth tracing role-default freshness and vault identity assumptions.

- **Report blocked by queued redemptions** &nbsp;[[I-3](invariants.md#i-3), [E-1](invariants.md#e-1)] - `pendingRedemptions` gates `_harvestAndReport`; worth checking every path that increments, claims, or clears it.

- **Report buffer arithmetic bound** &nbsp;[[I-4](invariants.md#i-4), [I-5](invariants.md#i-5)] - `estimatedTotalAssets:177-179` subtracts `reportBuffer` from `MAX_BPS`; worth checking management-set values around the basis-point boundary.

- **Idle-only normal withdraws** &nbsp;[[I-2](invariants.md#i-2), [X-3](invariants.md#x-3), [E-2](invariants.md#e-2)] - `_freeFunds` is a no-op and `availableWithdrawLimit` returns idle WETH; worth tracing UX and accounting around expected illiquidity.

- **ERC4626 vault unwind sizing** &nbsp;[[I-6](invariants.md#i-6), [X-1](invariants.md#x-1)] - `_freeStETH:77-96` combines wstETH conversion, `previewWithdraw`, `maxRedeem`, and a two-wei buffer; worth checking rounding and capacity edges.

- **Curve route and slippage split** - staking enforces 1:1 minimum when swapping ETH to stETH, while manual stETH-to-ETH swaps rely on management-provided `_minOut`.

### Protocol-Type Concerns

**As a Yield Aggregator / Vault:**
- `valueOfWstETH:69-71` uses downstream vault `convertToAssets`; capacity and conversion semantics deserve the same scrutiny as strategy accounting.
- `availableDepositLimit:55-63` maps vault maxDeposit in wstETH units back into stETH value; rounding direction matters at low amounts.

**As a Liquid Staking integration:**
- `initiateLSTWithdrawal:259-264` records pending before queue completion; queue accounting needs to stay aligned with actual claimable ETH.
- `Strategy._stake:51-69` branches between Curve and direct Lido staking; route choice depends on Curve `get_dy` at call time.

### Temporal Risk Profile

**Deployment & Initialization:**
- Factory-created strategies inherit factory defaults at deployment time; later factory changes do not mutate existing strategies.

**Market Stress:**
- Idle-only withdraw limits make the strategy explicitly liquidity-sensitive during stETH/vault withdrawal stress.

### Composability & Dependency Risks

**Dependency Risk Map:**

> **TokenizedStrategy** - via fallback/delegatecall
> - Assumes: fixed implementation address exposes the expected Yearn V3 accounting and role API.
> - Validates: implementation address is hard-coded in BaseStrategy.
> - Mutability: fixed in code for this strategy instance.
> - On failure: ERC4626 entry points and role checks revert or behave according to the implementation.

> **Lido stETH + withdrawal queue** - via `submit`, `requestWithdrawals`, `claimWithdrawal(s)`
> - Assumes: stETH queue claim data matches pending strategy accounting.
> - Validates: first-party code tracks pending amount and blocks reports while pending.
> - Mutability: external Lido contracts.
> - On failure: reports remain blocked or emergency clearing is needed.

> **Curve ETH/stETH pool** - via `get_dy` and `exchange`
> - Assumes: `get_dy` reflects a better-than-1:1 route when selected.
> - Validates: staking path sets min-out to `_amount`; manual unstake path uses caller `_minOut`.
> - Mutability: external Curve pool.
> - On failure: route reverts or manual slippage bounds decide execution.

> **wstETH + downstream ERC4626 vault** - via wrap/unwrap/deposit/redeem/conversion views
> - Assumes: vault asset is wstETH and conversion/max functions are internally consistent.
> - Validates: constructor checks `vault.asset() == wstETH`.
> - Mutability: external vault selected at factory deployment.
> - On failure: Strategy4626 deposit/unwind/report capacity diverges from assumptions.

---

## 3. Invariants

> ### Full invariant map: **[invariants.md](invariants.md)**
>
> A dedicated reference file contains the complete invariant analysis.
>
> - **8 Enforced Guards** (`G-1` ... `G-8`) - per-call preconditions with `Check` / `Location` / `Purpose`
> - **7 Single-Contract Invariants** (`I-1` ... `I-7`) - Conservation, Bound, Ratio, StateMachine, Temporal
> - **3 Cross-Contract Invariants** (`X-1` ... `X-3`) - caller/callee pairs that cross scope boundaries
> - **2 Economic Invariants** (`E-1` ... `E-2`) - higher-order properties deriving from `I-N` + `X-N`

---

## 4. Documentation Quality

| Aspect | Status | Notes |
|--------|--------|-------|
| README | Present | Generic Tokenized Strategy mix README plus testing/deployment notes |
| NatSpec | Present | Core contracts have title/notice and function-level comments; factory and oracle are thinner |
| Spec/Whitepaper | Missing | No protocol-specific design/spec doc beyond README |
| Inline Comments | Adequate | Key route choices, queue semantics, and Strategy4626 rounding buffer are commented |

---

## 5. Test Analysis

| Metric | Value | Source |
|--------|-------|--------|
| Test files | 11 | File scan |
| Test functions | 46 | Portable `rg` scan for `function test` |
| Line coverage | Unavailable - coverage run failed | Forge coverage compiled, then tests reverted/panicked; see `.audit/pashov-xray-521fff2/coverage.raw.txt` |
| Branch coverage | Unavailable - coverage run failed | Coverage tool requires passing tests |

### Test Depth

| Category | Count | Contracts Covered |
|----------|------:|-------------------|
| Unit / parameterized Foundry tests | 46 | Strategy, Strategy4626, factory, oracle, withdrawal queue, shutdown |
| Stateless Fuzz (`testFuzz` prefix) | 0 | none by x-ray naming heuristic; many tests are parameterized |
| Stateful Fuzz / Invariants | 0 | none detected |
| Formal Verification | 0 | none detected |

### Gaps

- No invariant, Echidna, Medusa, Halmos, HEVM, or Certora specs were detected for accounting and queue-state behavior.
- Coverage metrics are currently unavailable because the local coverage run does not complete successfully.

---

## 6. Developer & Git History

> Repo shape: normal_dev - 81 commits total, 23 source-touching commits over 1162 days on branch `review` at `521fff2`.

### Contributors

| Author | Source Lines (+/-) | % of Source Additions |
|--------|--------------------:|----------------------:|
| Schlagonia | +1285 / -1188 | 87.4% |
| Schlag | +180 / -94 | 12.2% |
| poolpitako | +5 / -5 | 0.3% |

### Review & Process Signals

| Signal | Value | Assessment |
|--------|-------|------------|
| Unique contributors | 9 total, 3 source-addition contributors | Source work is concentrated |
| Merge commits | 5 of 81 | Some PR-style history visible |
| Repo age | 2023-04-24 -> 2026-06-29 | Long-lived strategy mix lineage |
| Recent source activity (30d) | 2 commits | Factory and 4626 updates landed late |
| Test co-change rate | 69.6% | Git analysis measures co-modification, not coverage |

### File Hotspots

| File | Modifications | Note |
|------|--------------:|------|
| src/Strategy.sol | 17 | Route and Lido/Curve integration hotspot |
| src/periphery/StrategyAprOracle.sol | 9 | Periphery changed repeatedly |
| src/BaseLSTAccumulator.sol | 5 | Shared accounting/liquidity base |
| src/Strategy4626Factory.sol | 1 | Latest commit introduced factory surface |

### Security-Relevant Commits

| SHA | Date | Subject | Score | Key Signal |
|-----|------|---------|------:|------------|
| cb080ca | 2026-03-20 | fix: updates | 14 | guard, token transfer, and accounting changes |
| 457aaa8 | 2026-04-21 | fix: withdraws | 11 | focused Strategy4626 withdrawal/accounting change |
| a7fdbbd | 2025-09-10 | fix: reviews | 11 | accounting/fund-flow review changes |
| 8a686fa | 2024-03-22 | fix: move up available withdraw limit (#28) | 10 | withdraw-limit history without test co-change |
| 8dc8c81 | 2026-04-11 | build: 4626 | 9 | Strategy4626 addition with guards and tests |

### Dangerous Area Evolution

| Security Area | Commits | Key Files |
|---------------|--------:|-----------|
| fund_flows | 18 | BaseLSTAccumulator, Strategy, Strategy4626 |
| state_machines | 17 | Strategy, ISTETH |
| oracle_price | 5 | BaseLSTAccumulator, ICurve |
| access_control | 1 | Strategy4626Factory |

### Forked Dependencies

| Library | Path | Status | Notes |
|---------|------|--------|-------|
| OpenZeppelin | lib/openzeppelin-contracts | Submodule | Standard dependency tree |
| tokenized-strategy | lib/tokenized-strategy | Submodule | Provides inherited ERC4626 accounting and roles |
| tokenized-strategy-periphery | lib/tokenized-strategy-periphery | Submodule | Provides BaseHealthCheck |

### Technical Debt Markers

No TODO/FIXME/HACK/XXX markers were found in the scoped production files.

### Security Observations

- **Late factory surface** - `521fff2` adds `Strategy4626Factory`, the only current access-control dangerous-area hit.
- **Withdraw-limit history** - `8a686fa` is a high-scoring withdraw-limit fix and maps directly to the idle-only withdraw design.
- **Fund-flow churn** - 18 commits touched fund-flow areas, with current hot paths in BaseLSTAccumulator and Strategy4626.
- **Source concentration** - one author accounts for 87.4% of source additions in git analysis.

### Cross-Reference Synthesis

- **Factory is both newest and permissionless** - latest commit plus `newStrategy4626` public deployment makes factory initialization a priority orientation surface.
- **Withdraw-limit git history aligns with E-2** - prior withdraw-limit fixes and idle-only exits point review toward liquidity-bound ERC4626 behavior.
- **Pending-redemption state is the report checkpoint** - queue writes plus report guard make claim/clear paths central to report-cycle analysis.

---

## X-Ray Verdict

**FRAGILE** - roles and structural boundaries are clear, but coverage is unavailable locally and no invariant/formal test layer was detected for the accounting and queue-state surfaces.

**Structural facts:**
1. 390 in-scope nSLOC across five production contracts.
2. 46 Foundry `test*` functions were detected across 11 test files, but local coverage did not complete.
3. The latest commit `521fff2` adds the permissionless Strategy4626 factory.
4. Normal user withdrawals are structurally capped by idle WETH through `availableWithdrawLimit()`.
