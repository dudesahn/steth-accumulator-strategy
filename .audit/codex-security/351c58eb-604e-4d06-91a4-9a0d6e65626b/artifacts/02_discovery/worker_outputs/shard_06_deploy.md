# shard_06_deploy finding discovery

scan_id: 351c58eb-604e-4d06-91a4-9a0d6e65626b

scope: production deploy scripts only; tests, mocks, cached/audit artifacts, build output, and broad vendored review excluded. Vendored Yearn TokenizedStrategy lines were consulted only for the directly imported constructor/setter behavior needed to validate deployment configuration effects.

summary: 1 technically plausible deployment-configuration candidate found. The standalone `Deploy4626` script deploys a `Strategy4626` but never applies its hardcoded management/keeper/emergency/performance-fee configuration, so the logged management and acceptance note do not match on-chain state. Other assigned deploy paths were closed by explicit setter/constructor coverage or constructor checks.

## full-file receipts

| file | line range read | concise evidence |
|---|---:|---|
| `script/Deploy.s.sol` | 1-42 | Direct `Strategy` deployment uses canonical WETH constant at line 10, hardcoded management/keeper/emergency/performance-fee recipient at lines 14-18, deploys `new Strategy(WETH, name)` at line 23, then applies `setPendingManagement`, `setKeeper`, `setEmergencyAdmin`, and `setPerformanceFeeRecipient` at lines 25-28. It logs the configured values at lines 32-38 and notes that pending management must call `acceptManagement()` at line 40. |
| `script/Deploy4626.s.sol` | 1-30 | Direct `Strategy4626` deployment uses WETH at line 9, hardcoded management and vault at lines 12-14, deploys `new Strategy4626(WETH, name, vault)` at line 18, stops broadcasting at line 20, and only logs the hardcoded management plus an `acceptManagement()` note at lines 26-28. No post-deploy setter is called. |
| `script/Deploy4626Factory.s.sol` | 1-29 | Factory deployment hardcodes management, performance-fee recipient, keeper, emergency admin, and asset at lines 9-13, passes all five values into `new Strategy4626Factory(...)` at lines 17-18, then logs the same values at lines 22-27. |

Supporting code consulted:

- `src/Strategy4626.sol:20-27`: constructor requires `IERC4626(_vault).asset() == address(wstETH)`, stores the vault, and grants stETH/wstETH approvals.
- `src/Strategy4626Factory.sol:24-36`: factory constructor stores role defaults and immutable asset from deploy-script inputs.
- `src/Strategy4626Factory.sol:52-64`: factory-created strategies call `setPerformanceFeeRecipient`, `setKeeper`, `setPendingManagement`, `setEmergencyAdmin`, `setPerformanceFee(0)`, and `setProfitMaxUnlockTime(0)`.
- `lib/tokenized-strategy/src/BaseStrategy.sol:138-149`: direct strategy construction initializes TokenizedStrategy storage with `msg.sender` for management, performance-fee recipient, and keeper.
- `lib/tokenized-strategy/src/TokenizedStrategy.sol:445-470`: initialization sets default 10-day profit unlock, 10% performance fee, performance-fee recipient, management, and keeper from constructor parameters.
- `lib/tokenized-strategy/src/TokenizedStrategy.sol:1502-1517`: `acceptManagement()` only succeeds for the current `pendingManagement`, which is set by `setPendingManagement`.
- `lib/tokenized-strategy/src/TokenizedStrategy.sol:1528-1580`: keeper, emergency admin, performance fee, and performance-fee recipient setters are management-only.
- `src/BaseLSTAccumulator.sol:198-245`: management-only setters and manual fund-movement paths demonstrate why a wrong management role is security-relevant.

## coverage rows

| family | disposition | exact evidence | closure |
|---|---|---|---|
| hardcoded asset constants | suppressed | `script/Deploy.s.sol:10`, `script/Deploy4626.s.sol:9`, and `script/Deploy4626Factory.s.sol:13` all use canonical mainnet WETH; constructors pass the configured asset through at `script/Deploy.s.sol:23`, `script/Deploy4626.s.sol:18`, and `script/Deploy4626Factory.s.sol:17-18`. | No concrete mismatched asset path in assigned scripts. Cross-chain misuse remains an operator review concern, not a production-code candidate from these files. |
| hardcoded ERC4626 vault constant | suppressed | `script/Deploy4626.s.sol:13` hardcodes a vault; `src/Strategy4626.sol:20-23` requires the vault `asset()` to be canonical wstETH before storing it. | The unit/domain control exists in the constructor. The selected vault address is operator-controlled and needs deployment review, but no attacker-controlled bypass appears in the script. |
| post-deploy role setter coverage, direct `Strategy` | suppressed | `script/Deploy.s.sol:25-28` sets pending management, keeper, emergency admin, and performance-fee recipient immediately after `new Strategy(...)` at line 23. | Setter coverage matches logged role values; two-step management acceptance is correctly surfaced at line 40. |
| post-deploy role setter coverage, direct `Strategy4626` | reportable | `script/Deploy4626.s.sol:18` deploys the strategy, but lines 19-20 stop without any `setPendingManagement`, `setKeeper`, `setEmergencyAdmin`, or `setPerformanceFeeRecipient`; lines 26-28 still log management and an acceptance note. | Candidate `CS-351c58eb-S06-001`. |
| post-deploy role setter coverage, factory deployment | suppressed | `script/Deploy4626Factory.s.sol:17-18` passes role defaults into the factory; `src/Strategy4626Factory.sol:31-35` stores them; `src/Strategy4626Factory.sol:54-64` applies them to each factory-created strategy. | Factory-created strategy setup has the intended role/fee/unlock setter sequence. |
| missing management acceptance | suppressed for `Deploy.s.sol`; reportable for `Deploy4626.s.sol`; not_applicable for factory contract deployment itself | `script/Deploy.s.sol:25` sets pending management and line 40 notes acceptance; `lib/tokenized-strategy/src/TokenizedStrategy.sol:1502-1517` confirms the two-step flow. `script/Deploy4626.s.sol:28` prints the same note without line 18 being followed by `setPendingManagement`. | Direct `Deploy4626` acceptance note is false because pending management is never set. |
| mismatched logged-vs-set roles | reportable for `Deploy4626.s.sol`; suppressed for the other two scripts | `script/Deploy4626.s.sol:12` defines management and line 26 logs it, but no setter installs it; inherited construction instead uses `msg.sender` via `lib/tokenized-strategy/src/BaseStrategy.sol:145-149`. `Deploy.s.sol` logs values it set at lines 25-28; `Deploy4626Factory.s.sol` logs values passed into the factory at lines 17-18. | Candidate `CS-351c58eb-S06-001`. |
| factory/direct deployment differences | reportable | Direct `Deploy4626` only calls `new Strategy4626` at `script/Deploy4626.s.sol:18`; factory-created strategies additionally set role/fee/unlock parameters at `src/Strategy4626Factory.sol:54-64`. | Candidate `CS-351c58eb-S06-001`. |

## raw candidate objects

```yaml
- candidate_id: "CS-351c58eb-S06-001"
  title: "Standalone Strategy4626 deployment logs intended management but leaves deployer-controlled defaults"
  affected_locations:
    - label: "configuration_source"
      file: "script/Deploy4626.s.sol"
      line: 12
      detail: "Hardcoded intended management address is assigned to a local variable."
    - label: "root_control"
      file: "script/Deploy4626.s.sol"
      line: 18
      detail: "Script deploys `new Strategy4626(WETH, name, vault)` directly."
    - label: "broken_control"
      file: "script/Deploy4626.s.sol"
      line: 20
      detail: "Broadcast stops with no post-deploy role, fee-recipient, fee, or unlock-time setter calls."
    - label: "misleading_operator_output"
      file: "script/Deploy4626.s.sol"
      lines: "26-28"
      detail: "Script logs the hardcoded management address and says it must call `acceptManagement()`, but no pending management was set."
    - label: "inherited_sink"
      file: "lib/tokenized-strategy/src/BaseStrategy.sol"
      lines: "145-149"
      detail: "Direct construction delegates initialization with `msg.sender` as management, performance-fee recipient, and keeper."
    - label: "inherited_sink"
      file: "lib/tokenized-strategy/src/TokenizedStrategy.sol"
      lines: "445-470"
      detail: "Initialization stores default 10-day profit unlock, 10% performance fee, performance-fee recipient, management, and keeper."
  instance_key: "deployment-config:script/Deploy4626.s.sol:18"
  attacker_controlled_or_privileged_source: "Privileged deployment operator/broadcast signer controls `msg.sender`; the hardcoded management/vault constants are developer/operator-controlled, not attacker-controlled at runtime."
  broken_control_or_sink: "The deploy script omits the management-only post-deploy setters needed to replace constructor defaults with the intended production roles and fee settings."
  impact: "A production deployment made with this script would leave management, keeper, and performance-fee recipient as the broadcast signer rather than the logged management address. The logged management address cannot finalize ownership because `pendingManagement` was never set. Emergency admin remains unset except for management fallback, and factory-specific zero performance fee / zero profit unlock settings are not applied. If a hot deployer key is used, compromised, or simply unavailable, privileged strategy controls and keeper/report liveness can be lost or misdirected, and performance fees can accrue to the wrong account."
  closest_control:
    control: "TokenizedStrategy exposes `setPendingManagement`, `setKeeper`, `setEmergencyAdmin`, `setPerformanceFeeRecipient`, `setPerformanceFee`, and `setProfitMaxUnlockTime`; `Deploy.s.sol` uses role setters and `Strategy4626Factory.newStrategy4626` uses the full role/fee/unlock setup."
    why_incomplete: "`Deploy4626.s.sol` does not call those setters. The `acceptManagement()` note is incomplete because `TokenizedStrategy.acceptManagement()` requires `msg.sender == pendingManagement`, and `pendingManagement` is only populated by `setPendingManagement`."
  candidate_local_validation:
    evidence:
      - "`script/Deploy4626.s.sol:18-20` deploys and stops broadcasting with no setter calls."
      - "`script/Deploy4626.s.sol:26-28` logs the hardcoded management and an acceptance note despite no pending-management setup."
      - "`lib/tokenized-strategy/src/BaseStrategy.sol:145-149` passes `msg.sender` for management, fee recipient, and keeper during direct construction."
      - "`lib/tokenized-strategy/src/TokenizedStrategy.sol:1502-1517` shows acceptance requires a previously set pending management."
      - "`src/Strategy4626Factory.sol:54-64` is a nearby safe pattern: factory-created strategies set fee recipient, keeper, pending management, emergency admin, performance fee, and profit unlock."
    counterevidence:
      - "The issue is not attacker-triggerable after deployment by an unprivileged user; it depends on broadcasting the production script without an additional manual setup transaction."
      - "The deployer remains actual management and can still correct the deployment before funds are deposited, if the deployer key is retained and the omission is noticed."
      - "`src/Strategy4626.sol:20-23` validates the vault's asset is wstETH, so the candidate is not a vault unit-mismatch issue."
    proof_gaps:
      - "No broadcast artifact or deployed address was reviewed in this shard, so no live deployment is proven misconfigured."
      - "Operational intent for using the direct `Deploy4626` script instead of the factory was not provided."
    validation_recommended: true
  attack_path_facts:
    - "Operator broadcasts `script/Deploy4626.s.sol`; the strategy constructor runs with the broadcast signer as `msg.sender`."
    - "BaseStrategy delegates TokenizedStrategy initialization using `msg.sender` as management, performance-fee recipient, and keeper."
    - "The script does not set pending management, keeper, emergency admin, performance-fee recipient, performance fee, or profit unlock after construction."
    - "The hardcoded management address sees logs instructing it to call `acceptManagement()`, but `acceptManagement()` reverts because `pendingManagement` is zero."
    - "Any subsequent production deposits or reports rely on the deployer-controlled default roles until a separate corrective transaction is sent by the deployer."
  cwe:
    - "CWE-665"
    - "CWE-284"
```

No additional plausible candidates were found in the assigned files. Closed rows are supported by explicit setter coverage in `Deploy.s.sol`, constructor/factory role propagation in `Deploy4626Factory.s.sol` and `Strategy4626Factory.sol`, and the `Strategy4626` vault asset check.
