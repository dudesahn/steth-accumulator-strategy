# Finding Discovery Worker Output: shard_01_base

ScanId: 351c58eb-604e-4d06-91a4-9a0d6e65626b
Target: /Users/dudesahn/Documents/GitHub/codex/review/steth-accumulator-strategy
Assigned file: src/BaseLSTAccumulator.sol
Threat model: /private/var/folders/s_/3h_wvzqx385frkp70gr8cpdc0000gn/T/codex-security-scans-HMBJE7/steth-accumulator-strategy/521fff28ad978a37115be8995a1d631611fa1d3d_20260708T164548Z_sqevo7au/artifacts/01_context/threat_model.md

## Full-File Receipt

| file | line range read | receipt evidence |
| --- | --- | --- |
| src/BaseLSTAccumulator.sol | 1-282 | Read in full. Reviewed state/config defaults, virtual LST hooks, deposit/withdraw/report/tend accounting, live asset/LST valuation, management setters, manual stake/swap/withdrawal queue operations, pendingRedemptions handling, and emergency withdrawal hook. |

## Minimal Supporting Code Read

| file | lines read | reason |
| --- | --- | --- |
| src/Strategy.sol | 1-131 | Concrete LST hook sinks for `_stake`, `_swapLSTToAsset`, `_initiateLSTWithdrawal`, `_claimLSTWithdrawal`, and emergency manual claim behavior. |
| src/Strategy4626.sol | 1-116 | Concrete ERC4626/wstETH hook behavior for `_stake`, `_swapLSTToAsset`, `_initiateLSTWithdrawal`, `valueOfLST`, and manual emergency redeem/unwrap helpers. |
| lib/tokenized-strategy/src/BaseStrategy.sol | 1-513 | Inherited role modifiers, callback-only hook entrypoints, and fallback/delegatecall mechanics needed to confirm external reachability. |
| lib/tokenized-strategy/src/TokenizedStrategy.sol | 250-340, 480-540, 790-850, 940-1245, 1290-1395 | Role checks, deposit/mint/withdraw/report/tend/emergency entrypoints, max deposit/withdraw calculations, and loss handling needed for candidate-local validation. |
| lib/tokenized-strategy-periphery/src/Bases/HealthCheck/BaseHealthCheck.sol | 1-161 | Health-check wrapper around report accounting and bounds checks. |

## High-Impact Coverage Rows

| row id | family / boundary | disposition | evidence and closure |
| --- | --- | --- | --- |
| HIF-BASE-01 | Access control on sensitive external operations | suppressed | Management setters and manual operations are role-gated in the assigned file: `setReportBuffer` src/BaseLSTAccumulator.sol:198, `setStakeAsset` :204, `setDepositLimit` :210, `setOpenDeposits` :216, `setAllowed` :222, tend config setters :228 and :234, `manualSwapToAsset` :241, `manualStake` :250, `initiateLSTWithdrawal` :259, and `clearPendingRedemptions` :279 all use `onlyManagement`; `claimLSTWithdrawal` :269 uses `onlyKeepers`. Inherited role checks resolve to TokenizedStrategy `requireManagement` lib/tokenized-strategy/src/TokenizedStrategy.sol:306, `requireKeeperOrManagement` :319, and `requireEmergencyAuthorized` :333. No untrusted public caller reaches these sensitive controls directly. |
| HIF-BASE-02 | Keeper/management boundary for staking control during report and tend | reportable | Candidate FD-351C58EB-BASE-001. The `stakeAsset` control is set by management at src/BaseLSTAccumulator.sol:204-206 and is enforced for deposit deployment at :109-112, but `_harvestAndReport` stakes loose assets without checking it at :146-153 and `_tend` stakes without checking it at :165-166. Keeper-reachable inherited entrypoints are `report` lib/tokenized-strategy/src/TokenizedStrategy.sol:1081 and `tend` :1314. |
| HIF-BASE-03 | Deposit gate and limit accounting | suppressed | External deposit/mint calls consult inherited `_maxDeposit` / `_maxMint` before minting shares, lib/tokenized-strategy/src/TokenizedStrategy.sol:487, :520, :870. The assigned file gates deposits to `openDeposits` or `allowed[_owner]` at src/BaseLSTAccumulator.sol:126-130 and computes remaining capacity from `estimatedTotalAssets()` versus `depositLimit` at :96-103. Depositing for an allowed receiver remains possible, but shares are minted to that allowed receiver and no unauthorized withdrawal or accounting sink is exposed from the assigned file. |
| HIF-BASE-04 | Withdrawal availability and loss realization | suppressed | The assigned file intentionally exposes only liquid asset withdrawals through `availableWithdrawLimit` at src/BaseLSTAccumulator.sol:133-144 and does no automatic unstaking in `_freeFunds` at :115-124. Inherited `_withdraw` will call `freeFunds` only when idle is short, then transfers only actual idle assets and applies maxLoss checks at lib/tokenized-strategy/src/TokenizedStrategy.sol:989-1043. This closes untrusted withdrawal-drain and forced-unstake rows for the assigned file. |
| HIF-BASE-05 | Report accounting, reportBuffer, donations, and rounding | suppressed | `_harvestAndReport` blocks reporting while `pendingRedemptions != 0` at src/BaseLSTAccumulator.sol:146-148, sells rewards then reports `estimatedTotalAssets()` at :149-155, and `estimatedTotalAssets` values liquid asset plus discounted LST at :177-179. Inherited report is keeper-gated at lib/tokenized-strategy/src/TokenizedStrategy.sol:1081-1085 and locks/fees profit through the standard report path at :1089-1242 with health-check validation through BaseHealthCheck :117-159. `setReportBuffer` has no <= MAX_BPS guard at src/BaseLSTAccumulator.sol:198-200, but the only source is management and the observed effect is a privileged self-brick/revert or deliberate discount, not an untrusted extraction path in this assigned file. |
| HIF-BASE-06 | pendingRedemptions and asynchronous Lido claim flow | suppressed | Management increments pending redemptions before the virtual withdrawal request at src/BaseLSTAccumulator.sol:259-263, reverting atomically if the child request fails. Keeper claim decrements by the redeemed amount and floors at zero at :269-272. Management-only `clearPendingRedemptions` can reduce the counter at :279-280 and the comment explicitly warns that this can realize losses at :275-278. No untrusted caller can inflate, clear, or claim pending redemptions from the assigned file. |
| HIF-BASE-07 | Manual swap/stake slippage and emergency withdrawal | suppressed | `manualSwapToAsset` is management-only and passes caller-provided `_minOut` to the virtual swap at src/BaseLSTAccumulator.sol:241-245; `manualStake` is management-only at :250-253. `_emergencyWithdraw` can swap with `_minOut = 0` at :158-163, but inherited `emergencyWithdraw` is emergency-authorized and only after shutdown at lib/tokenized-strategy/src/TokenizedStrategy.sol:1356. This is a privileged emergency slippage footgun, not an untrusted attack path under the supplied threat model. |
| HIF-BASE-08 | External protocol calls from assigned file | suppressed | The assigned file only defines virtual hooks at src/BaseLSTAccumulator.sol:71-88 and routes amounts to those hooks. Minimal concrete sinks were checked: `Strategy._stake` unwraps WETH and uses Curve/Lido at src/Strategy.sol:51-68, `_swapLSTToAsset` uses Curve then wraps ETH at :74-82, and `Strategy4626._stake` wraps/deposits through wstETH/vault at src/Strategy4626.sol:29-42. No untrusted arbitrary target, calldata, or recipient is selected in the assigned file. |
| HIF-BASE-09 | RCE, SQL/NoSQL/LDAP/XPath/template injection, unsafe deserialization, SSRF, path traversal, unsafe file upload, open redirect/header injection | not_applicable | src/BaseLSTAccumulator.sol is Solidity strategy code with no process execution, parser/deserializer, filesystem, HTTP/callback, header, redirect, SQL/NoSQL/LDAP/XPath, or template sinks. Reviewed full assigned file lines 1-282. |

## Raw Candidate Objects

```yaml
- candidate_id: FD-351C58EB-BASE-001
  title: "stakeAsset disable switch is bypassed by keeper report and tend paths"
  discovery_disposition: reportable
  affected_locations:
    - label: root_control
      location: "src/BaseLSTAccumulator.sol:204-206"
      evidence: "onlyManagement setStakeAsset writes the stakeAsset control."
    - label: control_applied
      location: "src/BaseLSTAccumulator.sol:109-112"
      evidence: "_deployFunds checks stakeAsset before staking deposit/loose asset during deposit deployment."
    - label: broken_control
      location: "src/BaseLSTAccumulator.sol:146-153"
      evidence: "_harvestAndReport stakes loose asset through _stake(Math.min(balanceOfAsset(), availableDepositLimit(address(this)))) without checking stakeAsset."
    - label: broken_control
      location: "src/BaseLSTAccumulator.sol:165-166"
      evidence: "_tend stakes the full _totalIdle without checking stakeAsset."
    - label: keeper_entrypoint
      location: "lib/tokenized-strategy/src/TokenizedStrategy.sol:1081-1085"
      evidence: "report is external, nonReentrant, and onlyKeepers."
    - label: keeper_entrypoint
      location: "lib/tokenized-strategy/src/TokenizedStrategy.sol:1314"
      evidence: "tend is external, nonReentrant, and onlyKeepers."
    - label: concrete_sink
      location: "src/Strategy.sol:51-68"
      evidence: "_stake unwraps WETH and routes value to Curve or Lido stETH."
    - label: concrete_sink
      location: "src/Strategy4626.sol:29-42"
      evidence: "4626 variant then wraps stETH to wstETH and deposits into the downstream vault."
    - label: impact_context
      location: "src/BaseLSTAccumulator.sol:115-124"
      evidence: "_freeFunds performs no automatic unstaking."
    - label: impact_context
      location: "src/BaseLSTAccumulator.sol:133-144"
      evidence: "availableWithdrawLimit advertises only liquid asset balance."
  instance_key: "access-control:src/BaseLSTAccumulator.sol:152"
  attacker_controlled_or_privileged_source: "A keeper or management address can call TokenizedStrategy.report/tend. The concerning path is a keeper call after management has set stakeAsset=false and idle WETH exists in the strategy."
  broken_control_or_sink: "The management-controlled stakeAsset flag is not enforced in the report/tend staking paths, so keeper-reachable maintenance can still move idle WETH into LST/vault positions."
  impact: "Bypasses a management risk-control switch and can force idle WETH into stETH/wstETH/vault exposure, reducing immediately withdrawable WETH because normal withdrawals only use liquid asset balance and BaseLSTAccumulator does not automatically unstake. This can create withdrawal illiquidity and expose funds to Lido/Curve/vault timing and queue risk despite staking being disabled."
  closest_control_and_why_incomplete: "stakeAsset exists and is enforced in _deployFunds, but report and tend call _stake without the same guard. depositLimit can be separately lowered and the keeper can be replaced, but neither is coupled to setStakeAsset(false); tendTrigger is only a trigger view and does not guard direct keeper tend()."
  candidate_local_validation:
    evidence:
      - "Static trace confirms setStakeAsset(false) only changes storage and event at src/BaseLSTAccumulator.sol:204-206."
      - "Deposit deployment honors the flag at src/BaseLSTAccumulator.sol:109-112."
      - "Report/tend omit the flag and call _stake at src/BaseLSTAccumulator.sol:152 and :166."
      - "Inherited keeper entrypoints reach those callbacks through report/tend at lib/tokenized-strategy/src/TokenizedStrategy.sol:1081-1085 and :1314."
      - "Concrete _stake implementations move WETH into external LST/vault positions at src/Strategy.sol:51-68 and src/Strategy4626.sol:29-42."
    counterevidence:
      - "The path is not public; report/tend require keeper or management through TokenizedStrategy.requireKeeperOrManagement at lib/tokenized-strategy/src/TokenizedStrategy.sol:319-322."
      - "Management can mitigate by setting depositLimit to block self-capacity, changing keeper, or manually swapping/redeeming later."
      - "Strategy._stake uses a 1:1 minimum for Curve or Lido submit, so the immediate sink is primarily unauthorized exposure/illiquidity rather than direct slippage theft."
    proof_gaps:
      - "No runtime PoC executed in this worker pass."
      - "Needs maintainer/design validation whether stakeAsset is intended to disable only deposit deployment or all staking; assigned-file comments conflict, with the state comment saying deposits and setStakeAsset saying harvest."
  attack_path_facts:
    preconditions:
      - "Management has set stakeAsset=false to avoid staking idle WETH."
      - "The strategy holds idle WETH, for example from deposits while staking is disabled, manual swap, claim, donation, or emergency operation."
      - "A keeper or compromised keeper calls report() or tend()."
    steps:
      - "report() reaches BaseHealthCheck.harvestAndReport and BaseLSTAccumulator._harvestAndReport, which calls _stake without checking stakeAsset."
      - "or tend() reaches BaseLSTAccumulator._tend, which calls _stake without checking stakeAsset."
      - "The concrete strategy converts WETH into stETH and, in Strategy4626, into wstETH/vault shares."
      - "Subsequent user withdrawals are limited to liquid WETH because _freeFunds is empty and availableWithdrawLimit returns balanceOfAsset()."
    severity_relevant_facts:
      - "Privileged keeper precondition reduces severity versus a public attack."
      - "The violated control is management-owned and explicitly exposed as a staking switch."
      - "Loss impact depends on LST/vault liquidity and timing; immediate effect is forced illiquidity/exposure."
  validation_recommended: true
  cwe:
    - "CWE-284"
    - "CWE-693"
```

