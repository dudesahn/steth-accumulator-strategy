# Validation Worker Output: CS-351C58EB-004 and CS-351C58EB-005

Scan id: `351c58eb-604e-4d06-91a4-9a0d6e65626b`

Target repo: `/Users/dudesahn/Documents/GitHub/codex/review/steth-accumulator-strategy`

Method used: static code understanding plus bounded production adjacency search. I did not create PoC files or modify the target repo. I also did not rerun Forge tests because this worker was instructed to write only this assigned output file; parent-provided test evidence was checked against `src/test/Oracle.t.sol`.

## Validation Rubric

- [x] The assigned candidate has an exact source/control/sink tuple in production-scoped code or an exact proof gap explaining why it cannot be closed.
- [x] The candidate's affected line is reachable from a production surface named by the threat model, or counterevidence/proof gap identifies missing deployment/registration reachability.
- [x] Nearby safe patterns are used only as controls, not as suppression for the assigned instance.
- [x] Imported dependency API behavior needed for the claim is verified at the directly imported dependency boundary.
- [x] Disposition is calibrated to the threat model: operator deployment footguns and misleading allocator signals are generally Medium or lower unless untrusted theft/loss is proven.

## Candidate CS-351C58EB-004

Finding title: Standalone Strategy4626 deployment logs intended management but leaves deployer-controlled defaults

Instance key: `deployment-config:script/Deploy4626.s.sol:18`

Ledger row ids: `WL-009`, `HIF-009`

Root-control file:line: `script/Deploy4626.s.sol:18`

Affected locations from discovery: `script/Deploy4626.s.sol:12`, `script/Deploy4626.s.sol:18-20`, `script/Deploy4626.s.sol:26-28`

Entrypoint/source: trusted operator running `script/Deploy4626.s.sol`

Sink/control: `new Strategy4626(WETH, name, vault)` inherits Yearn `BaseStrategy` initialization with `msg.sender` as management, performance fee recipient, and keeper; no post-deploy setters are called in this script.

Disposition: `reportable`

Confidence: high static confidence, `0.80`

Validation method: static trace through deployment script, `Strategy4626` constructor inheritance, and directly imported TokenizedStrategy API; nearby deployment/factory scripts used as negative controls.

Rubric checklist:

- [x] Exact production surface exists: `script/Deploy4626.s.sol` is a deployment script in scope per the threat model.
- [x] Missing control is exact: the script deploys at line 18 and then stops broadcast at line 20 without calling role/fee/unlock setters.
- [x] Dependency default behavior is verified: `BaseStrategy` initializes TokenizedStrategy with `msg.sender` for management, performance fee recipient, and keeper.
- [x] Impact is bounded to deployment/operational risk, not untrusted runtime theft.
- [x] Nearby safe controls show the intended setup pattern and do not defeat this direct script instance.

Evidence observed:

- `script/Deploy4626.s.sol:12-18` defines a `management` address and deploys `new Strategy4626(WETH, name, vault)`.
- `script/Deploy4626.s.sol:20` stops broadcast immediately after deployment.
- `script/Deploy4626.s.sol:22-28` logs the intended management and says management must call `acceptManagement()`, but there is no preceding `setPendingManagement(management)` call, so the logged note is misleading for this script.
- `lib/tokenized-strategy/src/BaseStrategy.sol:138-150` calls `ITokenizedStrategy.initialize(_asset, _name, msg.sender, msg.sender, msg.sender)` during construction.
- `lib/tokenized-strategy/src/TokenizedStrategy.sol:453-470` sets default `profitMaxUnlockTime = 10 days`, `performanceFeeRecipient = _performanceFeeRecipient`, `performanceFee = 1000`, `management = _management`, and `keeper = _keeper`.
- `lib/tokenized-strategy/src/TokenizedStrategy.sol:333-338` authorizes emergency actions only for `emergencyAdmin` or `management`; `initialize` does not set `emergencyAdmin`.
- `script/Deploy.s.sol:23-28` is a safe direct-deploy control: after `new Strategy(...)`, it calls `setPendingManagement`, `setKeeper`, `setEmergencyAdmin`, and `setPerformanceFeeRecipient`.
- `src/Strategy4626Factory.sol:52-64` is a safe factory control: after `new Strategy4626(...)`, it calls `setPerformanceFeeRecipient`, `setKeeper`, `setPendingManagement`, `setEmergencyAdmin`, `setPerformanceFee(0)`, and `setProfitMaxUnlockTime(0)`.
- `script/Deploy4626Factory.s.sol:9-18` supplies management, fee recipient, keeper, emergency admin, and asset to the factory constructor rather than relying on the standalone strategy defaults.

Counterevidence:

- No evidence shows an untrusted caller can exploit this at runtime. The source is a trusted operator/deployer action.
- The deployer remains initial management, so a careful deployer could manually repair settings after broadcast. That mitigates exploitability but does not fix the script's encoded production sequence or misleading acceptance note.
- Factory-based deployment is safer, but it does not suppress the standalone script because `script/Deploy4626.s.sol` is a separate production deployment surface.

Remaining uncertainty:

- I did not inspect broadcast artifacts because the scope excludes broadcast/cache output. Therefore this validates the production script hazard, not a confirmed already-deployed on-chain misconfiguration.

Minimal next step if more proof is needed:

- If the final report needs concrete on-chain impact, inspect the actual deployment transaction or deployed strategy storage out of band and confirm management, pendingManagement, keeper, emergencyAdmin, performanceFeeRecipient, performanceFee, and profitMaxUnlockTime immediately after the `Deploy4626` broadcast.

Closure:

This candidate survives validation as a reportable deployment footgun. The script logs an intended management handoff but never calls the required setter, while the inherited constructor gives role and fee defaults to the broadcaster. Severity should be calibrated as Medium/operational unless on-chain deployment evidence shows funds were managed under the bad defaults.

## Candidate CS-351C58EB-005

Finding title: StrategyAprOracle returns a constant 4% APR for any strategy and debt delta

Instance key: `oracle-static-apr:src/periphery/StrategyAprOracle.sol:28`

Ledger row ids: `WL-005`, `HIF-010`

Root-control file:line: `src/periphery/StrategyAprOracle.sol:28`

Affected locations from discovery: `src/periphery/StrategyAprOracle.sol:28-32`

Entrypoint/source: any periphery/allocator consumer that calls `aprAfterDebtChange(address _strategy, int256 _delta)` after the oracle is deployed/registered.

Sink/control: oracle APR returned to allocator/periphery consumers; implementation ignores both `_strategy` and `_delta`.

Disposition: `deferred`

Confidence: medium static confidence for deferred disposition, `0.65`

Validation method: static trace of oracle implementation and directly imported `AprOracleBase` API, plus bounded production search for deployment/registration evidence.

Rubric checklist:

- [x] Exact behavior is present: the function always returns `4e16`.
- [x] Expected API semantics are verified: the inherited interface expects APR for a strategy after a signed debt change.
- [x] Existing test coverage is checked and does not validate debt-change behavior.
- [x] Production adjacency search was bounded and found no in-repo registration/deploy path.
- [ ] Reportable impact path is not complete because no production allocator registration or deployment evidence was found.

Evidence observed:

- `src/periphery/StrategyAprOracle.sol:28-32` implements `aprAfterDebtChange(address _strategy, int256 _delta)` and returns `4e16` unconditionally.
- `src/periphery/StrategyAprOracle.sol:24-26` documents `_strategy` and `_delta` as inputs to the expected APR calculation.
- `lib/tokenized-strategy-periphery/src/AprOracle/AprOracleBase.sol:16-33` defines the same method as the expected APR after a debt change and explicitly includes `_strategy` and `_delta`.
- Production search over `src`, `script`, `foundry.toml`, and `README.md`, excluding tests and mocks, found `StrategyAprOracle` only in `src/periphery/StrategyAprOracle.sol`; no production deploy script, registry call, or allocator registration was found.
- `src/test/Oracle.t.sol:20-24` only asserts the returned APR is greater than zero and less than 100%.
- `src/test/Oracle.t.sol:26-36` leaves TODO/commented assertions that APR should go up/down for negative/positive debt changes.
- `src/test/Oracle.t.sol:62` leaves a TODO to test multiple strategies with different assets.

Counterevidence:

- The contract identifies itself as `"Strategy Apr Oracle Example"` in `src/periphery/StrategyAprOracle.sol:7`.
- No production code path in this repository deploys or registers this oracle with an allocator/periphery consumer.

Remaining uncertainty:

- The incorrect oracle semantics are confirmed, but the security impact depends on an external or omitted production registration path. The current repository evidence does not prove that allocators consume this oracle in production.
- Absence of an in-repo registration path is not a complete safety control because deployment/registration can occur outside this repository.

Minimal next step if more proof is needed:

- Check deployment/allocator configuration outside this repo for an active `StrategyAprOracle` address registered for this strategy, or add a production deploy/registration artifact proving it is intended to be used by allocators.

Closure:

This candidate should remain deferred, not reportable yet. The implementation is a confirmed static-placeholder APR oracle, but the reportable source-to-impact tuple is incomplete without production registration or allocator consumption evidence. It should be suppressed only if maintainers confirm this file is example-only and never deployed or registered.

## Validation Closure Table

| ledger row id | instance key | advisory/source reference | seed anchor file:line | root-control file:line | entrypoint/source | sink/control | disposition | counterevidence or proof gap | survives |
|---|---|---|---|---|---|---|---|---|---|
| `WL-009`, `HIF-009` | `deployment-config:script/Deploy4626.s.sol:18` | none | n/a | `script/Deploy4626.s.sol:18` | trusted operator running standalone 4626 deployment script | direct deployment inherits deployer-controlled TokenizedStrategy defaults and omits role/fee/unlock setters | `reportable` | no confirmed on-chain broadcast inspected; runtime issue is a deployment footgun, not untrusted caller exploit | yes |
| `WL-005`, `HIF-010` | `oracle-static-apr:src/periphery/StrategyAprOracle.sol:28` | none | n/a | `src/periphery/StrategyAprOracle.sol:28` | allocator/periphery consumer if oracle is deployed and registered | `aprAfterDebtChange` ignores strategy and debt delta and returns constant 4% | `deferred` | confirmed bad semantics, but no production deploy/registration/consumer path found in repo | uncertain |
