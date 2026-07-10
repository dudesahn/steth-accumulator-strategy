# Security Review: steth-accumulator-strategy

## Scope

Production-code-only repository scan of first-party Solidity contracts and deploy scripts. Tests, mocks, vendored dependencies, build output, prior audit artifacts, scanner reports, and cached analysis were excluded from scan input.

- Scan mode: repository
- Target kind: git_revision
- Target ID: 521fff28ad978a37115be8995a1d631611fa1d3d
- Revision: 521fff28ad978a37115be8995a1d631611fa1d3d
- Inventory strategy: custom
- Included paths: src/BaseLSTAccumulator.sol, src/Strategy.sol, src/Strategy4626.sol, src/Strategy4626Factory.sol, src/periphery/StrategyAprOracle.sol, src/interfaces/IBaseLSTAccumulator.sol, src/interfaces/IStrategyInterface.sol, src/interfaces/IStrategy4626Interface.sol, src/interfaces/ICurve.sol, src/interfaces/IQueue.sol, src/interfaces/ISTETH.sol, src/interfaces/IWETH.sol, src/interfaces/IWstETH.sol, script/Deploy.s.sol, script/Deploy4626.s.sol, script/Deploy4626Factory.s.sol
- Excluded paths: src/test/\*\*, test/\*\*, mocks/\*\*, lib/\*\*, out/\*\*, cache/\*\*, broadcast/\*\*, .audit/\*\*, x-ray/\*\*, scanner reports, cached analysis
- Runtime or test status: Production contracts compiled with `forge build`; targeted fork tests and one disposable PoC passed. No missing test dependency such as `vyper` was required.
- Artifacts reviewed: artifacts/01_context/threat_model.md, artifacts/02_discovery/deep_review_input.jsonl, artifacts/02_discovery/finding_discovery_report.md, artifacts/03_coverage/repository_coverage_ledger.md, artifacts/04_reconciliation/deduped_candidates.jsonl, artifacts/05_findings/validation_summary.md, artifacts/05_findings/attack_path_analysis_report.md
- Scan context: The scan was anchored to git revision 521fff28ad978a37115be8995a1d631611fa1d3d. Existing untracked `.audit/` material was excluded from scan input and used only as a final mirror destination.

Limitations and exclusions:
- Vendored Yearn, OpenZeppelin, Lido, Curve, WETH, wstETH, and ERC4626 implementations were treated as out of scope except for first-party integration semantics.
- No live production deployment or registry state was used to prove external `StrategyAprOracle` registration.
- Severity for ERC4626 headroom issues depends on the downstream vault selected at deployment time.
- Excluded src/test/\*\*, test/\*\*, mocks/\*\*: Tests and mocks were excluded as scan input; targeted tests were used only for validation.
- Excluded lib/\*\*: Vendored dependencies were excluded except when directly relied on for API semantics.
- Excluded out/\*\*, cache/\*\*, broadcast/\*\*: Build artifacts and cached Foundry output were excluded.
- Excluded .audit/\*\*, x-ray/\*\*, scanner reports, cached analysis: Prior audit artifacts and scanner output were excluded from scan input.

### Scan Summary

| Field | Value |
| --- | --- |
| Reportable findings | 2 |
| Severity mix | medium: 1, low: 1 |
| Confidence mix | high: 2 |
| Coverage | complete |
| Validation mode | Independent discovery shards, targeted validation, counterevidence review, and attack-path policy calibration. |

Canonical artifacts: `scan-manifest.json`, `findings.json`, and `coverage.json`. This report is a deterministic projection of those files.

## Threat Model

The repository implements Yearn V3 TokenizedStrategy contracts that accept WETH, stake or swap into stETH, optionally wrap into wstETH and deposit into a downstream ERC4626 vault, and rely on management, keeper, and emergency roles for risk controls and maintenance. The main security objectives are preserving asset/share accounting, preventing unauthorized fund movement, preventing untrusted griefing of reports/tends/deposits, and keeping deployment role configuration consistent.

### Assets

- Deposited WETH, stETH, wstETH, ERC4626 vault shares, pending Lido withdrawal claims, Yearn strategy shares, and privileged role authority.
- Allocator APR signals when periphery oracle code is deployed and registered.

### Trust Boundaries

- Depositors and vault allocators are outside the operator boundary and interact through inherited ERC4626 strategy entrypoints.
- Management controls risk parameters, deposit gates, role defaults, manual routes, and deployment setup.
- Keepers can report, tend, and claim withdrawals but should not bypass management-only risk decisions.
- Emergency authorized accounts can perform sensitive recovery actions.
- External protocols such as Lido, Curve, WETH, wstETH, and downstream ERC4626 vaults are external dependencies whose live limits and rates affect safety.

### Attacker Capabilities

- Call public or inherited strategy entrypoints when deposits are open or the caller is allowed.
- Transfer stETH, wstETH, WETH, or ETH directly to strategy addresses.
- Influence public timing around Curve pricing, Lido queue state, and keeper/report execution.
- Compromise or act as a lower-trust keeper for keeper-scoped attack paths.

### Security Objectives

- Only authorized roles may move funds or change risk parameters.
- Management risk switches must gate the operational callbacks they are documented to control.
- Direct token donations must not make maintenance flows revert or over-report value.
- ERC4626 vault interactions must respect live capacity and unit conversions at the actual sink.
- Deployment scripts must not silently leave strategies under unintended roles.

### Assumptions

- Yearn TokenizedStrategy and periphery base contracts enforce their documented role checks and share-accounting semantics.
- Canonical WETH, stETH, wstETH, Lido withdrawal queue, and Curve contracts behave according to their public APIs.
- Management and emergency roles are trusted; harmful behavior requiring only those roles is generally not a final security finding unless it creates a clear privilege delta.
- Downstream ERC4626 vaults used by `Strategy4626` have wstETH as `asset()` but may have finite live deposit capacity.

## Findings

| Finding | Severity | Confidence |
| --- | --- | --- |
| [Loose wstETH donations can exceed the downstream vault maxDeposit and block maintenance](#finding-1) | medium | high |
| [Keeper report and tend paths bypass the management stakeAsset disable switch](#finding-2) | low | high |

### Confidence Scale

| Label | Meaning |
| --- | --- |
| high | Direct evidence supports the finding with no material unresolved blocker. |
| medium | Evidence supports a plausible issue, but material runtime or reachability proof remains. |
| low | Evidence is incomplete and the item is retained only for explicit follow-up. |

<a id="finding-1"></a>

### [1] Loose wstETH donations can exceed the downstream vault maxDeposit and block maintenance

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Direct source tracing plus a disposable Foundry PoC against copied target code confirmed the maxDeposit revert; remaining uncertainty is deployment-specific vault headroom. |
| Category | Donation griefing / ERC4626 limit bypass |
| CWE | CWE-400: Uncontrolled Resource Consumption |
| Affected lines | src/Strategy4626.sol:41, src/Strategy4626.sol:55-63, src/BaseLSTAccumulator.sol:146-153 |

#### Summary

`Strategy4626._stake` wraps any loose stETH and deposits the strategy's entire loose wstETH balance into the downstream ERC4626 vault. `availableDepositLimit` consults `vault.maxDeposit(address(this))`, but that cap is applied only to new WETH intake, not to the actual loose wstETH amount sent to `vault.deposit`. An unauthenticated token donor can therefore make the next report, tend, deposit deployment, or manual stake revert when the downstream vault has little or no remaining deposit capacity.

#### Root Cause

The violated invariant is that every downstream ERC4626 `deposit` amount must be bounded by the vault's current `maxDeposit`. The implementation checks `maxDeposit` only while calculating how much new WETH can enter, but the later sink deposits the strategy's full loose wstETH balance, including balances created by direct token transfers.

**maxDeposit only reduces the advertised new deposit limit** — `src/Strategy4626.sol:55-63`

The vault cap is used to limit new WETH deposits, but it is not re-applied to the actual loose wstETH balance deposited by `_stake`.

```solidity
function availableDepositLimit(address _owner) public view virtual override returns (uint256) {
    uint256 superLimit = super.availableDepositLimit(_owner);
    if (superLimit == 0) return 0;

    uint256 maxDeposit = vault.maxDeposit(address(this));
    if (maxDeposit == type(uint256).max) return superLimit;

    return Math.min(superLimit, _stETHValue(maxDeposit));
}
```

**Stake deposits the entire loose wstETH balance** — `src/Strategy4626.sol:29-42`

`_stake` deposits `balanceOfWstETH()` after wrapping all loose stETH, so direct donations are included in the amount sent to the downstream vault.

```solidity
function _stake(uint256 _amount) internal virtual override {
    super._stake(_amount);

    uint256 stethBalance = balanceOfLST();
    if (stethBalance > 0) {
        wstETH.wrap(stethBalance);
    }

    uint256 wstETHBalance = balanceOfWstETH();
    // Can round to 0 if stethBalance is too small
    if (wstETHBalance == 0) return;

    vault.deposit(wstETHBalance, address(this));
}
```

#### Validation

Validation copied the target code into a disposable scan artifact, donated loose wstETH to the strategy, bounded a mock ERC4626 vault's deposit capacity, and observed the expected `ERC4626: deposit more than max` revert.

Validation method: static source trace plus disposable Foundry PoC

**Stake deposits the entire loose wstETH balance** — `src/Strategy4626.sol:29-42`

`_stake` deposits `balanceOfWstETH()` after wrapping all loose stETH, so direct donations are included in the amount sent to the downstream vault.

```solidity
function _stake(uint256 _amount) internal virtual override {
    super._stake(_amount);

    uint256 stethBalance = balanceOfLST();
    if (stethBalance > 0) {
        wstETH.wrap(stethBalance);
    }

    uint256 wstETHBalance = balanceOfWstETH();
    // Can round to 0 if stethBalance is too small
    if (wstETHBalance == 0) return;

    vault.deposit(wstETHBalance, address(this));
}
```

**maxDeposit only reduces the advertised new deposit limit** — `src/Strategy4626.sol:55-63`

The vault cap is used to limit new WETH deposits, but it is not re-applied to the actual loose wstETH balance deposited by `_stake`.

```solidity
function availableDepositLimit(address _owner) public view virtual override returns (uint256) {
    uint256 superLimit = super.availableDepositLimit(_owner);
    if (superLimit == 0) return 0;

    uint256 maxDeposit = vault.maxDeposit(address(this));
    if (maxDeposit == type(uint256).max) return superLimit;

    return Math.min(superLimit, _stETHValue(maxDeposit));
}
```

Evidence:
- `env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-path src/test/MaxDepositDonationPoC.t.sol -vv --fork-url https://ethereum.publicnode.com` passed 1/1 in the disposable validation copy.
- The original production build also succeeded with `forge build`.

Counterevidence and remaining uncertainty:
- The attacker sacrifices donated token value and still needs a keeper, management, deposit, or manual-stake trigger to hit the revert.
- Emergency roles may be able to unwind some stuck balances, so the direct impact is availability and intervention cost.

#### Dataflow

direct token transfer to strategy -\> `balanceOfLST` or `balanceOfWstETH` -\> `_stake` wraps/reads loose balance -\> `vault.deposit(wstETHBalance, address(this))` -\> ERC4626 maxDeposit revert

- **Source:** permissionless direct stETH or wstETH transfer to the strategy address

- **Sink:** `vault.deposit(wstETHBalance, address(this))`

- **Outcome:** maintenance call reverts while the loose balance exceeds downstream vault deposit headroom

**Stake deposits the entire loose wstETH balance** — `src/Strategy4626.sol:29-42`

`_stake` deposits `balanceOfWstETH()` after wrapping all loose stETH, so direct donations are included in the amount sent to the downstream vault.

```solidity
function _stake(uint256 _amount) internal virtual override {
    super._stake(_amount);

    uint256 stethBalance = balanceOfLST();
    if (stethBalance > 0) {
        wstETH.wrap(stethBalance);
    }

    uint256 wstETHBalance = balanceOfWstETH();
    // Can round to 0 if stethBalance is too small
    if (wstETHBalance == 0) return;

    vault.deposit(wstETHBalance, address(this));
}
```

**Keeper report calls the staking path** — `src/BaseLSTAccumulator.sol:146-153`

A normal keeper report can reach `_stake`, where donated loose wstETH is deposited without its own maxDeposit cap.

```solidity
function _harvestAndReport() internal virtual override returns (uint256 _totalAssets) {
    require(pendingRedemptions == 0, "Pending redemptions");

    _claimAndSellRewards();

    // Stake any loose asset
    _stake(Math.min(balanceOfAsset(), availableDepositLimit(address(this))));
```

#### Reachability

The attacker cannot call `_stake` directly, but direct token transfers are permissionless and normal keeper, management, or deposit workflows provide the trigger.

- **Attacker:** external token donor

- **Entry point:** direct stETH or wstETH transfer followed by report, tend, deposit deployment, or manual stake

- **Outcome:** availability griefing and operator intervention for affected vault configurations

Preconditions:
- The downstream ERC4626 vault has finite or temporarily exhausted `maxDeposit` for the strategy.
- A subsequent authorized maintenance flow reaches `_stake`.

#### Severity

**Medium** — The issue is externally reachable because anyone can transfer stETH or wstETH directly to the strategy, and the PoC confirmed the revert when loose wstETH exceeds a bounded ERC4626 `maxDeposit`. The consequence is availability and operator-intervention risk rather than direct theft, so medium impact with high likelihood yields medium severity.

Severity would rise if a production downstream vault commonly reaches zero headroom with meaningful strategy debt and no practical emergency recovery, and would fall if `_stake` capped the actual deposit amount or if the integrated vault always returns unlimited `maxDeposit`.

#### Remediation

Before calling `vault.deposit`, cap the actual wstETH amount by `vault.maxDeposit(address(this))` and leave surplus wstETH idle or route it through an explicit recovery path. Apply the cap after wrapping loose stETH and before the ERC4626 call, and avoid reverting the whole report/tend path when only donated surplus exceeds vault headroom.

Tests:
- Add a bounded ERC4626 mock test where donated loose wstETH exceeds `maxDeposit` and assert report/tend does not revert.
- Add a zero-headroom test that leaves donated wstETH idle while still reporting correctly.

Preventive controls:
- Treat direct token transfers as attacker-controlled balances in all token-flow reviews.
- For every ERC4626 integration, assert the actual `deposit` amount is no greater than live `maxDeposit` at the sink.

<a id="finding-2"></a>

### [2] Keeper report and tend paths bypass the management stakeAsset disable switch

| Field | Value |
| --- | --- |
| Severity | low |
| Confidence | high |
| Confidence rationale | Static tracing and an existing focused fork test confirmed report staking after `stakeAsset=false`; remaining uncertainty is intended semantics. |
| Category | Privilege boundary bypass / operational control bypass |
| CWE | CWE-284: Improper Access Control |
| Affected lines | src/BaseLSTAccumulator.sol:152, src/BaseLSTAccumulator.sol:165-166, src/BaseLSTAccumulator.sol:203-206 |

#### Summary

`setStakeAsset(false)` is the management-controlled switch that disables automatic staking in `_deployFunds`, but keeper-triggered report and tend callbacks still call `_stake` without the same guard. A keeper can therefore move idle WETH into stETH or the downstream vault after management disables staking, crossing the intended management risk-control boundary.

#### Root Cause

The violated invariant is that the management staking switch should gate all automatic staking paths, not only deposit deployment. The implementation applies the guard in `_deployFunds` but omits it from report and tend callbacks.

**_deployFunds honors the stakeAsset flag** — `src/BaseLSTAccumulator.sol:109-112`

The deposit deployment path treats `stakeAsset` as a guard before staking WETH.

```solidity
function _deployFunds(uint256 _amount) internal virtual override {
    if (stakeAsset && _amount > ASSET_DUST) {
        _stake(_amount);
    }
}
```

**Report stakes idle WETH without checking stakeAsset** — `src/BaseLSTAccumulator.sol:146-153`

`_harvestAndReport` can be reached by keeper reporting and calls `_stake` even when management has set `stakeAsset` to false.

```solidity
function _harvestAndReport() internal virtual override returns (uint256 _totalAssets) {
    require(pendingRedemptions == 0, "Pending redemptions");

    _claimAndSellRewards();

    // Stake any loose asset
    _stake(Math.min(balanceOfAsset(), availableDepositLimit(address(this))));
```

**Tend stakes idle WETH without checking stakeAsset** — `src/BaseLSTAccumulator.sol:165-166`

`_tend` delegates the idle amount directly to `_stake` without applying the same guard.

```solidity
function _tend(uint256 _totalIdle) internal virtual override {
    _stake(_totalIdle);
}
```

**Only management can set stakeAsset** — `src/BaseLSTAccumulator.sol:203-206`

The switch is management-controlled and its notice describes harvest staking, so keeper-triggered report/tend bypasses the management risk control.

```solidity
/// @notice Set whether the strategy will stake asset to LST during harvest
function setStakeAsset(bool _stakeAsset) external virtual onlyManagement {
    stakeAsset = _stakeAsset;
    emit StakeAssetUpdated(_stakeAsset);
}
```

#### Validation

Validation traced the flag from `setStakeAsset` to all staking callbacks and used the existing focused fork test to confirm report can stake idle WETH after `stakeAsset` is disabled.

Validation method: static source trace and focused fork test

**Report stakes idle WETH without checking stakeAsset** — `src/BaseLSTAccumulator.sol:146-153`

`_harvestAndReport` can be reached by keeper reporting and calls `_stake` even when management has set `stakeAsset` to false.

```solidity
function _harvestAndReport() internal virtual override returns (uint256 _totalAssets) {
    require(pendingRedemptions == 0, "Pending redemptions");

    _claimAndSellRewards();

    // Stake any loose asset
    _stake(Math.min(balanceOfAsset(), availableDepositLimit(address(this))));
```

**Tend stakes idle WETH without checking stakeAsset** — `src/BaseLSTAccumulator.sol:165-166`

`_tend` delegates the idle amount directly to `_stake` without applying the same guard.

```solidity
function _tend(uint256 _totalIdle) internal virtual override {
    _stake(_totalIdle);
}
```

Evidence:
- `env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-test test_harvestStakesBypassesStakeAssetFlag -vv --fork-url https://ethereum.publicnode.com` passed 1/1.
- `forge build` succeeded for the production contracts.

Counterevidence and remaining uncertainty:
- The path is keeper-gated and not reachable by arbitrary depositors.
- The state variable comment mentions deposits, which leaves some intent ambiguity, but the setter notice explicitly mentions harvest staking.

#### Dataflow

`setStakeAsset(false)` -\> keeper report/tend -\> `_harvestAndReport` or `_tend` -\> `_stake` -\> Lido/Curve/4626 staking side effect

- **Source:** keeper-triggered report or tend

- **Sink:** `_stake` conversion of WETH into LST or downstream vault exposure

- **Outcome:** management-disabled staking still occurs

**Report stakes idle WETH without checking stakeAsset** — `src/BaseLSTAccumulator.sol:146-153`

`_harvestAndReport` can be reached by keeper reporting and calls `_stake` even when management has set `stakeAsset` to false.

```solidity
function _harvestAndReport() internal virtual override returns (uint256 _totalAssets) {
    require(pendingRedemptions == 0, "Pending redemptions");

    _claimAndSellRewards();

    // Stake any loose asset
    _stake(Math.min(balanceOfAsset(), availableDepositLimit(address(this))));
```

**Tend stakes idle WETH without checking stakeAsset** — `src/BaseLSTAccumulator.sol:165-166`

`_tend` delegates the idle amount directly to `_stake` without applying the same guard.

```solidity
function _tend(uint256 _totalIdle) internal virtual override {
    _stake(_totalIdle);
}
```

**Only management can set stakeAsset** — `src/BaseLSTAccumulator.sol:203-206`

The switch is management-controlled and its notice describes harvest staking, so keeper-triggered report/tend bypasses the management risk control.

```solidity
/// @notice Set whether the strategy will stake asset to LST during harvest
function setStakeAsset(bool _stakeAsset) external virtual onlyManagement {
    stakeAsset = _stakeAsset;
    emit StakeAssetUpdated(_stakeAsset);
}
```

#### Reachability

The attacker position is a keeper or compromised keeper. That is privileged, but it is lower-trust than management for changing staking risk controls.

- **Attacker:** keeper role

- **Entry point:** inherited report or tend callback

- **Outcome:** idle WETH becomes staked after management disabled staking

Preconditions:
- Management has set `stakeAsset` to false.
- The strategy holds idle WETH or receives idle amount from the inherited callback.

#### Severity

**Low** — The effect can reintroduce LST/vault exposure and reduce liquidity after management disables staking, but exploitation requires the keeper role and does not let arbitrary users steal funds. The management-vs-keeper privilege delta keeps it reportable while the trusted role precondition lowers severity.

Severity would rise if keeper access is permissionless or broadly delegated and management uses `stakeAsset=false` as an emergency stop, and would fall if the project documents separate deposit-only semantics for the flag.

#### Remediation

Apply the `stakeAsset` guard consistently in `_harvestAndReport` and `_tend`, or split the configuration into explicitly documented deposit-staking and keeper-maintenance-staking controls. If staking is disabled, report should skip `_stake` and tend should return without moving idle WETH.

Tests:
- Add tests that set `stakeAsset=false` and assert `report` does not call the Lido/Curve staking path.
- Add tests that set `stakeAsset=false` and assert `tend` leaves idle WETH unchanged.

Preventive controls:
- Require every management risk switch to have callback coverage tests across deposit, report, tend, and manual paths.
- Document whether keepers are allowed to override each management-controlled staking mode.

## Reviewed Surfaces

| Surface | Risk Area | Outcome | Notes |
| --- | --- | --- | --- |
| Strategy4626 ERC4626 integration | Token-flow and downstream vault capacity | Reported | Loose stETH/wstETH donation can make `_stake` exceed live downstream `maxDeposit`; final finding CS-351C58EB-003. Evidence: artifacts/03_coverage/repository_coverage_ledger.md, artifacts/05_findings/CS-351C58EB-003/candidate_ledger.jsonl, artifacts/05_findings/CS-351C58EB-003/validation_report.md, artifacts/05_findings/CS-351C58EB-003/attack_path_analysis_report.md |
| BaseLSTAccumulator staking control | Keeper versus management trust boundary | Reported | Keeper report and tend paths bypass the management `stakeAsset` switch; final finding CS-351C58EB-002. Evidence: artifacts/03_coverage/repository_coverage_ledger.md, artifacts/05_findings/CS-351C58EB-002/candidate_ledger.jsonl, artifacts/05_findings/CS-351C58EB-002/validation_report.md, artifacts/05_findings/CS-351C58EB-002/attack_path_analysis_report.md |
| Lido withdrawal queue initiation and claim data | Asynchronous redemption accounting | Rejected | ABI mismatch is validated, but final policy suppressed it because the path is management/keeper workflow-only and existing tests use the safe scalar re-encoding. Evidence: artifacts/03_coverage/repository_coverage_ledger.md, artifacts/05_findings/CS-351C58EB-001/candidate_ledger.jsonl, artifacts/05_findings/CS-351C58EB-001/validation_report.md, artifacts/05_findings/CS-351C58EB-001/attack_path_analysis_report.md |
| Deployment scripts and factory role setup | Deployment role configuration | Rejected | `Deploy4626.s.sol` omits direct post-deploy role setup, but the precondition is trusted deployer misuse; factory and non-4626 deploy paths apply setup. Evidence: artifacts/03_coverage/repository_coverage_ledger.md, artifacts/05_findings/CS-351C58EB-004/candidate_ledger.jsonl, artifacts/05_findings/CS-351C58EB-004/validation_report.md, artifacts/05_findings/CS-351C58EB-004/attack_path_analysis_report.md, artifacts/02_discovery/worker_outputs/shard_06_deploy.md |
| StrategyAprOracle APR output | Allocator signal integrity | Rejected | Constant 4 percent APR behavior is confirmed, but no production deploy or registration path was found and the constructor labels it an example oracle. Evidence: artifacts/03_coverage/repository_coverage_ledger.md, artifacts/05_findings/CS-351C58EB-005/candidate_ledger.jsonl, artifacts/05_findings/CS-351C58EB-005/validation_report.md, artifacts/05_findings/CS-351C58EB-005/attack_path_analysis_report.md |
| Strategy4626Factory deployment uniqueness and role propagation | Factory deployment provenance | No issue found | One strategy per vault mapping, role propagation, and management-gated address updates were reviewed with no surviving issue. Evidence: artifacts/03_coverage/repository_coverage_ledger.md, artifacts/02_discovery/worker_outputs/shard_03_4626_factory.md |
| Curve, Lido staking, and stETH-to-WETH swap routes | External protocol routing and slippage | No issue found | Curve staking path uses a 1:1 minimum when selected, manual unwind slippage is caller-controlled, and no untrusted forced unwind path survived. Evidence: artifacts/03_coverage/repository_coverage_ledger.md, artifacts/02_discovery/worker_outputs/shard_02_strategy.md |
| RCE, injection, deserialization, SSRF, file, and web sink families | Generic application security sink classes | Not applicable | The production Solidity/deploy surface exposes no process, query, parser, filesystem, HTTP, redirect, template, upload, or deserialization sinks. Evidence: artifacts/03_coverage/repository_coverage_ledger.md |

## Open Questions And Follow Up

- If `StrategyAprOracle` is intended for production registration outside this repository, it needs a targeted oracle-consumer review.
  - Follow-up prompt: Review the external deployment or registry transaction for `src/periphery/StrategyAprOracle.sol` and determine whether constant `aprAfterDebtChange` can influence debt allocation.
