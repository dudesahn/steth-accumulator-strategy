# Finding discovery worker output: shard_03_4626_factory

scanId: 351c58eb-604e-4d06-91a4-9a0d6e65626b
scope: production code only
assigned_files:
- src/Strategy4626.sol
- src/Strategy4626Factory.sol

## Summary

Reviewed both assigned files in full. One technically plausible candidate was found: `CS-351c58eb-S03-001`, a bounded ERC4626 maxDeposit griefing path where donated loose stETH/wstETH can make `_stake` attempt to deposit more wstETH than the downstream vault currently accepts, reverting report/deposit/tend flows until operator cleanup or vault capacity returns.

Factory deployment uniqueness, role propagation, management acceptance, `setAddresses` authorization, and `isDeployedStrategy` were reviewed with supporting TokenizedStrategy access-control evidence. Those rows were closed as suppressed or not applicable because the observed controls are privileged/two-step or only prove factory provenance, not vault safety.

## Full-file receipts

| File | Lines read | Receipt evidence |
|---|---:|---|
| `src/Strategy4626.sol` | 1-116 | Full file read with line numbers. Evidence covered canonical `wstETH` constant and immutable `vault` at lines 16-18, constructor asset check and approvals at lines 20-27, `_stake` wrap/deposit flow at lines 29-42, `_swapLSTToAsset` and `_initiateLSTWithdrawal` free/availability logic at lines 44-53, `availableDepositLimit` at lines 55-63, wstETH/vault valuation at lines 65-75, `_freeStETH` previewWithdraw/maxRedeem/redeem/unwrap logic at lines 77-96, conversion helper at lines 98-100, and emergency-only manual redeem/unwrap at lines 103-115. |
| `src/Strategy4626Factory.sol` | 1-89 | Full file read with line numbers. Evidence covered stored role defaults and deployments mapping at lines 14-22, constructor role assignment at lines 24-36, permissionless `newStrategy4626` duplicate check/name/deployment/setter flow at lines 43-69, management-gated `setAddresses` at lines 72-83, and `isDeployedStrategy` vault-to-deployment check at lines 85-88. |

Supporting production/direct-import evidence inspected minimally:
- `src/Strategy.sol:49-68` shows `super._stake(0)` returns before stETH wrapping resumes in `Strategy4626._stake`, and nonzero staking mints/swaps stETH.
- `src/Strategy.sol:74-82` swaps stETH to WETH through Curve; `src/Strategy.sol:91-103` initiates Lido withdrawal claims after stETH is available.
- `src/BaseLSTAccumulator.sol:103-107` calls `_stake` during deposit deployment; `src/BaseLSTAccumulator.sol:146-154` calls `_stake(Math.min(balanceOfAsset(), availableDepositLimit(address(this))))` during reports; `src/BaseLSTAccumulator.sol:241-245` and `src/BaseLSTAccumulator.sol:259-263` show management-only manual swap and Lido withdrawal initiation.
- `src/BaseLSTAccumulator.sol:126-132` gates deposits by `openDeposits` or `allowed`; `src/BaseLSTAccumulator.sol:269-273` gates Lido claim to keepers.
- `lib/tokenized-strategy/src/BaseStrategy.sol:54-73` maps local modifiers to TokenizedStrategy role checks.
- `lib/tokenized-strategy/src/BaseStrategy.sol:130-153` initializes TokenizedStrategy roles to the deployer, which is the factory for factory deployments.
- `lib/tokenized-strategy/src/TokenizedStrategy.sol:306-337` enforces management, keeper-or-management, and emergency-authorized checks.
- `lib/tokenized-strategy/src/TokenizedStrategy.sol:433-475` initializes management/performance fee recipient/keeper and rejects zero management/performance fee recipient.
- `lib/tokenized-strategy/src/TokenizedStrategy.sol:1084-1097` shows `report()` is keeper-gated and calls `harvestAndReport`.
- `lib/tokenized-strategy/src/TokenizedStrategy.sol:1502-1517` makes management transfer a pending-management plus accept-management two-step.
- `lib/openzeppelin-contracts/contracts/interfaces/IERC4626.sol:73-81` defines `maxDeposit`; `lib/openzeppelin-contracts/contracts/interfaces/IERC4626.sol:101-111` requires `deposit` to revert if all assets cannot be deposited; `lib/openzeppelin-contracts/contracts/interfaces/IERC4626.sol:160-176` and `193-231` define previewWithdraw/maxRedeem/redeem semantics.

## Coverage rows

| Row id | High-impact family | Disposition | Evidence and closure |
|---|---|---|---|
| S03-ERC4626-UNITS-01 | ERC4626/wstETH unit conversions in accounting | suppressed | `valueOfWstETH` sums loose wstETH and `vault.convertToAssets(vault.balanceOf(address(this)))` then converts that wstETH-denominated amount to stETH through `_stETHValue` (`src/Strategy4626.sol:69-75`, `98-100`). This preserves the local wstETH-to-stETH unit boundary. The remaining WETH/stETH peg assumption is inherited from `BaseLSTAccumulator.estimatedTotalAssets` (`src/BaseLSTAccumulator.sol:176-178`) and the scan threat model, not a new assigned-file bug. |
| S03-ERC4626-MAXDEPOSIT-01 | ERC4626 maxDeposit-bounded availability | reportable | `availableDepositLimit` caps new deposits by `_stETHValue(vault.maxDeposit(address(this)))` (`src/Strategy4626.sol:55-63`), but `_stake` wraps all loose stETH and deposits the entire loose wstETH balance (`src/Strategy4626.sol:32-41`). Because ERC4626 `deposit` must revert if all assets cannot be deposited (`lib/openzeppelin-contracts/contracts/interfaces/IERC4626.sol:101-111`), attacker-donated loose stETH/wstETH can push the actual `vault.deposit` amount above current maxDeposit and revert report/deposit/tend flows. Raw candidate emitted as `CS-351c58eb-S03-001`. |
| S03-ERC4626-FREESTETH-01 | `_freeStETH` previewWithdraw/maxRedeem/redeem accounting | suppressed | `_freeStETH` only redeems up to `vault.maxRedeem(address(this))` after computing shares with `vault.previewWithdraw(...)` (`src/Strategy4626.sol:81-92`) and then unwraps available wstETH (`src/Strategy4626.sol:95`). If insufficient stETH is freed, `_initiateLSTWithdrawal` reverts on `balanceOfLST() >= _amount` (`src/Strategy4626.sol:49-52`), while `_swapLSTToAsset` swaps only `Math.min(_amount, balanceOfLST())` (`src/Strategy4626.sol:44-47`). This closes over-withdraw/over-accounting for the assigned path; remaining partial-swap behavior is management-controlled through `manualSwapToAsset` (`src/BaseLSTAccumulator.sol:241-245`). |
| S03-ERC4626-ROUNDING-01 | `_freeStETH` stETH/wstETH rounding | suppressed | The code adds two wei after `getWstETHByStETH(_amount - stethBalance)` to cover conversion and unwrap rounding (`src/Strategy4626.sol:81-82`), then exact Lido-withdrawal availability is enforced by `_initiateLSTWithdrawal` (`src/Strategy4626.sol:49-52`). No plausible untrusted over-credit or under-collateralized withdrawal path was found. |
| S03-VAULT-ASSET-01 | Downstream vault asset assumption | suppressed | Constructor requires `IERC4626(_vault).asset() == address(wstETH)` before saving the vault (`src/Strategy4626.sol:20-23`) and approves only LST-to-wstETH plus wstETH-to-vault (`src/Strategy4626.sol:25-26`). This does not prove vault economic safety, but vault selection is a deployment/management trust assumption; no untrusted runtime caller can change `vault` after construction. |
| S03-EMERGENCY-4626-01 | Emergency redeem/unwrap authorization | suppressed | `manualRedeem` and `manualUnwrap` are both `onlyEmergencyAuthorized` and clamp requested amounts to local balances (`src/Strategy4626.sol:103-115`). The modifier resolves to TokenizedStrategy's emergency-authorized check (`lib/tokenized-strategy/src/BaseStrategy.sol:72-73`; `lib/tokenized-strategy/src/TokenizedStrategy.sol:333-337`). No missing public fund-movement authorization was found. |
| S03-FACTORY-DUP-01 | Factory deployment uniqueness | suppressed | `newStrategy4626` reverts when `deployments[_vault]` is already set and records the deployed strategy for that exact vault after initialization (`src/Strategy4626Factory.sol:43-45`, `66-69`). This prevents duplicate deployments for the same vault address. Multiple distinct vault wrappers around wstETH are outside this exact uniqueness guarantee and remain deployment trust, not a bypass of this mapping. |
| S03-FACTORY-ROLES-01 | Factory role propagation and management acceptance | suppressed | BaseStrategy initializes management/performance fee recipient/keeper to the deployer (`lib/tokenized-strategy/src/BaseStrategy.sol:130-153`), so the factory can call setters immediately after construction (`src/Strategy4626Factory.sol:52-64`). Final management is installed through `setPendingManagement(management)` (`src/Strategy4626Factory.sol:58`) and TokenizedStrategy requires the pending manager to call `acceptManagement` (`lib/tokenized-strategy/src/TokenizedStrategy.sol:1502-1517`). No missing acceptance bypass was found. |
| S03-FACTORY-SETADDR-01 | `setAddresses` authorization and role-default mutation | suppressed | `setAddresses` requires `msg.sender == management` before mutating all factory role defaults (`src/Strategy4626Factory.sol:72-83`). Zero-address or wrong-address settings can break future deployments because TokenizedStrategy rejects zero pending management/performance fee recipient (`lib/tokenized-strategy/src/TokenizedStrategy.sol:433-475`, `1502-1504`), but that is privileged factory management behavior, not an untrusted caller path. |
| S03-FACTORY-TRUST-01 | `isDeployedStrategy` trust assumptions | suppressed | `isDeployedStrategy` derives `_vault` from the queried strategy and returns true only when `deployments[_vault] == _strategy` (`src/Strategy4626Factory.sol:85-88`). This proves factory deployment provenance for the exact vault mapping, not vault safety or management acceptance. No in-scope consumer was found that treats this view as an authorization oracle. |

## Raw candidate objects

```yaml
- candidate_id: CS-351c58eb-S03-001
  title: Donated loose stETH/wstETH can exceed downstream ERC4626 maxDeposit and revert strategy maintenance flows
  affected_locations:
    - label: root_control
      file: src/Strategy4626.sol
      lines: 55-63
      detail: availableDepositLimit caps the new deposit amount by vault.maxDeposit(address(this)) converted from wstETH to stETH units.
    - label: sink
      file: src/Strategy4626.sol
      lines: 29-41
      detail: _stake resumes after super._stake(_amount), wraps the entire loose stETH balance, then deposits the entire loose wstETH balance into the vault.
    - label: entrypoint/wrapper
      file: src/BaseLSTAccumulator.sol
      lines: 146-154
      detail: report-time harvest calls _stake(Math.min(balanceOfAsset(), availableDepositLimit(address(this)))) before returning estimated total assets.
    - label: entrypoint/wrapper
      file: src/BaseLSTAccumulator.sol
      lines: 103-107
      detail: deposit deployment also calls _stake for incoming assets when stakeAsset is enabled.
    - label: api_contract
      file: lib/openzeppelin-contracts/contracts/interfaces/IERC4626.sol
      lines: 101-111
      detail: ERC4626 deposit must revert if all assets cannot be deposited, including when a deposit limit is reached.
  instance_key: erc4626-maxdeposit-donation-dos:src/Strategy4626.sol:41
  attacker_controlled_or_privileged_source: Untrusted external accounts can directly transfer stETH or wstETH to the strategy address; depositors can also time deposits around current downstream vault maxDeposit capacity when deposits are open or allowlisted.
  broken_control_or_sink: The closest capacity control only limits the new asset amount returned by availableDepositLimit, but the sink deposits all loose wstETH, including balances created from prior direct token donations or existing loose balances, into a vault that may reject deposits above maxDeposit.
  impact: A griefing attacker can make keeper report, tend/deposit maintenance, or user deposits revert whenever the donated loose stETH/wstETH makes the actual vault.deposit amount exceed the downstream ERC4626 vault's current maxDeposit. This can delay accounting updates and maintenance until management swaps/withdraws the loose LST or vault capacity returns. The attacker loses the donated tokens, so the impact is availability/accounting grief rather than direct theft.
  closest_control_and_why_incomplete: src/Strategy4626.sol:55-63 checks vault.maxDeposit(address(this)) and returns a stETH-denominated limit for new deposits, but src/Strategy4626.sol:32-41 does not subtract existing loose stETH/wstETH before calling vault.deposit(wstETHBalance). The line-39 zero-balance guard only skips when wrapped balance is zero; it does not enforce maxDeposit on the actual sink amount.
  candidate_local_validation:
    evidence:
      - src/Strategy.sol:49-50 returns from super._stake when _amount is zero, after which Strategy4626._stake still continues at src/Strategy4626.sol:32.
      - src/Strategy4626.sol:32-41 wraps all balanceOfLST() and deposits all balanceOfWstETH(), not only the wstETH produced from _amount.
      - src/Strategy4626.sol:59-63 uses vault.maxDeposit(address(this)) as a limit but does not account for already-loose stETH/wstETH at the strategy address.
      - src/BaseLSTAccumulator.sol:146-154 calls _stake during report, so the revert can block keeper reporting before estimatedTotalAssets is returned.
      - lib/openzeppelin-contracts/contracts/interfaces/IERC4626.sol:101-111 says deposit must revert if all assets cannot be deposited due to a deposit limit.
    counterevidence:
      - src/Strategy4626.sol:60 bypasses the cap when maxDeposit is type(uint256).max, so unlimited vaults are not affected by this specific path.
      - The attacker must donate stETH/wstETH and cannot directly recover the donation through this path.
      - Management has cleanup options through manualSwapToAsset (src/BaseLSTAccumulator.sol:241-245), initiateLSTWithdrawal (src/BaseLSTAccumulator.sol:259-263 plus src/Strategy4626.sol:49-52), or emergency-only manualRedeem/manualUnwrap (src/Strategy4626.sol:103-115), so the condition is not necessarily permanent.
    proof_gaps:
      - Needs dynamic reproduction against a compliant ERC4626 vault with a finite or zero maxDeposit that reverts when deposit assets exceed that limit.
      - Needs severity calibration for realistic configured downstream vaults: exploit cost scales with the current maxDeposit headroom unless maxDeposit is zero or very small.
  attack_path_facts:
    - Preconditions: downstream vault maxDeposit(address(strategy)) is finite and lower than the actual loose wstETH amount that _stake will deposit.
    - Step 1: attacker transfers enough stETH or wstETH directly to the strategy address to create loose LST/wstETH above the downstream vault's remaining deposit capacity.
    - Step 2: a keeper report, tend/deposit flow, or user deposit causes _stake to run.
    - Step 3: _stake wraps loose stETH, computes the full loose wstETH balance, and calls vault.deposit(wstETHBalance, address(this)).
    - Step 4: the ERC4626 vault reverts because all assets cannot be deposited under its current maxDeposit, blocking the maintenance/deposit call.
  cwe:
    - CWE-754
  validation_recommended: true
```
