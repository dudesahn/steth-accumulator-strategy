# Validation worker output: CS-351C58EB-001 and CS-351C58EB-002

Scope: production code only, with tests and imported dependency APIs used only as validation evidence.

Assigned candidates:

- `CS-351C58EB-001`: Lido withdrawal return data encodes a request-id array but the normal claim path decodes a scalar id.
- `CS-351C58EB-002`: `stakeAsset` disable switch is bypassed by keeper report and tend paths.

## Validation rubric

- [x] Source/control/sink tuple is complete for the exact candidate instance.
- [x] Production reachability is established through first-party `src/` code and directly imported TokenizedStrategy APIs where needed.
- [x] Realistic interface behavior is checked against externally callable strategy functions and role gates.
- [x] Existing dynamic evidence or a read-only local probe supports or falsifies the suspected behavior.
- [x] Counterevidence, recovery controls, and remaining proof gaps are separated from the disposition.

## CS-351C58EB-001

Title: Lido withdrawal return data encodes a request-id array but the normal claim path decodes a scalar id.

Candidate id: `CS-351C58EB-001`

Instance key: `queue-claim-data-shape:src/Strategy.sol:99`

Ledger rows: `HIF-002`; coverage links `WL-002`, `WL-006`, `WL-007`

Root-control and affected locations:

- `src/interfaces/IQueue.sol:5-7`: `requestWithdrawals` returns `uint256[] memory requestIds`.
- `src/Strategy.sol:97-99`: `_initiateLSTWithdrawal` receives `requestIds` and returns `abi.encode(requestIds)`.
- `src/Strategy.sol:104-108`: `_claimLSTWithdrawal` decodes `_claimData` as a scalar `uint256` and calls `claimWithdrawal(_requestId)`.
- `src/BaseLSTAccumulator.sol:259-263`: management initiates the Lido withdrawal and increments `pendingRedemptions`.
- `src/BaseLSTAccumulator.sol:269-271`: keeper/management claim path decrements `pendingRedemptions` only after `_claimLSTWithdrawal` succeeds and returns an amount.
- `src/BaseLSTAccumulator.sol:146-147`: reports revert while `pendingRedemptions != 0`.

Validation method: static source/control/sink trace, parent fork-test evidence, and read-only ABI probe with `cast`.

Rubric checklist:

- [x] Claimed source identified: management receives `bytes returnData` from `initiateLSTWithdrawal`, and keeper/management later supplies `bytes _claimData` to `claimLSTWithdrawal`.
- [x] Claimed control/sink identified: no adapter converts the returned `uint256[]` payload into the scalar `uint256` expected by `_claimLSTWithdrawal`; sink is Lido queue `claimWithdrawal(_requestId)`.
- [x] Production reachability identified: both functions are external production functions, gated by `onlyManagement` and `onlyKeepers` respectively.
- [x] Realistic interface checked: raw returned bytes are not directly usable as claim data; tests show successful usage only after decoding the array and re-encoding `requestIds[0]`.
- [x] Counterevidence and recovery controls checked: no public/untrusted caller reaches the claim path; emergency `manualClaimWithdrawals` and management `clearPendingRedemptions` can recover operationally.

Evidence observed:

- Production interface shape mismatch is direct: `IQueue.requestWithdrawals` returns `uint256[]`, while `_claimLSTWithdrawal` decodes `bytes` as `uint256`.
- Local ABI probe confirms the mismatch. `cast abi-encode "f(uint256[])" "[123]"` produced dynamic-array encoded bytes beginning with offset word `0x20`; decoding that payload as `uint256` with `cast decode-abi "f()(uint256)" ...` returned `32`, not `123`. Scalar encoding of `123` is the single word `0x...007b`.
- Parent validation evidence reports `env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-path src/test/WithdrawalQueue.t.sol -vv --fork-url https://ethereum.publicnode.com` passed 7/7. The tests decode `returnData` as `uint256[]` and then call `claimLSTWithdrawal(abi.encode(requestIds[0]))`, which confirms the successful path requires caller-side reshaping instead of raw return-data reuse.
- Test evidence in `src/test/WithdrawalQueue.t.sol:49-80`, `106-117`, `136-147`, and `225-235` consistently decodes `returnData` as `uint256[]` before single-claim use or passes the decoded array to the emergency batch claim helper.

Counterevidence:

- This is not a direct public exploit. `initiateLSTWithdrawal` is management-gated and `claimLSTWithdrawal` is keeper/management-gated through TokenizedStrategy's keeper authorization.
- The normal single-claim path can succeed when the operator decodes `returnData` as `uint256[]` and re-encodes the first request id as a scalar.
- Emergency authorized accounts can call `manualClaimWithdrawals(uint256[] calldata _requestIds, uint256[] calldata _hints, bool _zeroRedemptions)` and management can call `clearPendingRedemptions`, so the issue is recoverable with privileged/operator intervention.

Proof gaps:

- No production keeper bot or operations runbook was available to prove that operators actually pass the raw `returnData` directly into `claimLSTWithdrawal`.
- I did not rerun fork tests in this worker because the worker instruction permits writing only to the assigned output file and forge may touch local build/cache artifacts; I used the supplied passing test evidence and read-only ABI verification instead.

Disposition: `reportable`

Confidence: `0.74`

Rationale: The ABI/data-shape bug is confirmed by exact production code and read-only ABI behavior. The security impact is lower-confidence than the code bug because it depends on operator workflow, and the role gates plus emergency/manual recovery defeat a direct public exploit narrative. It remains reportable as a realistic liveness/accounting-risk bug: using the returned bytes as documented claim data can claim the wrong request id or fail to claim, leaving `pendingRedemptions` nonzero and blocking reports.

Minimal next step if more proof is needed: inspect the production keeper/operations script that consumes `initiateLSTWithdrawal` return data and confirm whether it passes raw `returnData` or reshapes it before claiming.

Artifacts created: this worker output only.

## CS-351C58EB-002

Title: `stakeAsset` disable switch is bypassed by keeper report and tend paths.

Candidate id: `CS-351C58EB-002`

Instance key: `stake-control:src/BaseLSTAccumulator.sol:152`

Ledger rows: `HIF-003`; coverage link `WL-001`

Root-control and affected locations:

- `src/BaseLSTAccumulator.sol:109-112`: `_deployFunds` checks `stakeAsset` before staking deposit-time asset.
- `src/BaseLSTAccumulator.sol:146-153`: `_harvestAndReport` stakes loose asset with `_stake(Math.min(balanceOfAsset(), availableDepositLimit(address(this))))` without checking `stakeAsset`.
- `src/BaseLSTAccumulator.sol:165-166`: `_tend` stakes all `_totalIdle` without checking `stakeAsset`.
- `src/BaseLSTAccumulator.sol:203-206`: `setStakeAsset` is management-gated and its notice says it controls whether the strategy stakes asset during harvest.
- Imported TokenizedStrategy API: `report()` and `tend()` are `onlyKeepers`, and dispatch to `harvestAndReport()` / `tendThis()` hooks.

Validation method: static source/control/sink trace plus parent focused fork-test evidence.

Rubric checklist:

- [x] Claimed source identified: management-controlled `stakeAsset=false` state plus idle WETH balance, followed by keeper/management `report()` or `tend()`.
- [x] Claimed control/sink identified: `_deployFunds` is guarded by `stakeAsset`, but report and tend staking sinks call `_stake` without the same guard.
- [x] Production reachability identified: inherited TokenizedStrategy `report()` and `tend()` are external keeper-gated functions that reach `_harvestAndReport` and `_tend`.
- [x] Realistic interface checked: parent test exercises the real strategy surface by setting `stakeAsset=false`, depositing idle WETH, and calling `report()` as keeper.
- [x] Counterevidence and limitations checked: keeper is trusted, report path is still bounded by available deposit limit, but tend has no `stakeAsset` or deposit-limit check.

Evidence observed:

- `stakeAsset` is initialized to true and is management-controlled by `setStakeAsset`. The state variable comment says deposit staking, but the setter notice says "during harvest"; at minimum, the codebase's own wording makes the report path part of the intended control surface.
- `_deployFunds` respects `stakeAsset`, so the flag can leave newly deposited WETH idle.
- `_harvestAndReport` ignores `stakeAsset` and stakes loose WETH during report if `pendingRedemptions == 0` and `availableDepositLimit(address(this))` permits it.
- `_tend` ignores `stakeAsset` and stakes `_totalIdle` directly.
- Imported TokenizedStrategy code confirms `report()` and `tend()` are callable by keepers/management and dispatch into the strategy hooks.
- Parent validation evidence reports `env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-test test_harvestStakesBypassesStakeAssetFlag -vv --fork-url https://ethereum.publicnode.com` passed 1/1. The test sets `stakeAsset=false`, deposits WETH that remains idle, then a keeper `report()` stakes it into stETH.
- Test source `src/test/StethSpecific.t.sol:332-351` matches that behavior: after `setStakeAsset(false)`, deposit leaves WETH, then keeper `report()` results in stETH balance greater than zero and WETH balance zero.

Counterevidence:

- This is not a public depositor-controlled direct theft path. `report()` and `tend()` are keeper/management-gated by TokenizedStrategy.
- The report path still applies `availableDepositLimit(address(this))`, so management can reduce report-time staking by setting a tight deposit limit. However, this is indirect and not the advertised `stakeAsset` control; `_tend` has no equivalent deposit-limit bound.
- One state-variable comment says `stakeAsset` controls staking "during deposits", which weakens certainty if the maintainers intended the flag to be deposit-only. The setter notice and test expectation point the other way for harvest/report behavior.

Proof gaps:

- No external design document or operations runbook was available to conclusively state whether `stakeAsset=false` was meant to halt all automatic staking or only deposit-time staking.
- I did not rerun fork tests in this worker because the worker instruction permits writing only to the assigned output file and forge may touch local build/cache artifacts; I used the supplied passing test evidence and static trace instead.

Disposition: `reportable`

Confidence: `0.82`

Rationale: The bypass is confirmed by exact production code and focused dynamic evidence from the parent run. The impact is bounded by keeper trust and operational recovery, but it violates a management-controlled risk switch in at least the report path and definitely in the tend path, allowing a keeper to move liquid WETH into stETH/Lido exposure after management disables deposit-time staking.

Minimal next step if more proof is needed: ask maintainers whether `stakeAsset=false` is intended to block only deposit-time staking or every automatic staking path; if all automatic staking is intended, add the same guard to `_harvestAndReport` and `_tend`.

Artifacts created: this worker output only.

## Validation closure table

| ledger row id | instance key | advisory/source reference | seed anchor file:line | root-control file:line | entrypoint/source | sink/control | disposition | counterevidence or proof gap | survives |
|---|---|---|---|---|---|---|---|---|---|
| `HIF-002` | `queue-claim-data-shape:src/Strategy.sol:99` | none provided | none distinct | `src/Strategy.sol:99`, `src/Strategy.sol:105` | management `initiateLSTWithdrawal` return data; keeper/management `claimLSTWithdrawal(bytes)` claim data | `abi.encode(uint256[])` returned, but `_claimLSTWithdrawal` decodes `uint256` and calls `IQueue.claimWithdrawal` | `reportable` | not public; works if operator decodes array and re-encodes scalar; emergency/manual recovery exists; production keeper workflow not proven | yes |
| `HIF-003` | `stake-control:src/BaseLSTAccumulator.sol:152` | none provided | none distinct | `src/BaseLSTAccumulator.sol:152`, `src/BaseLSTAccumulator.sol:166` | management sets `stakeAsset=false`; keeper/management calls `report()` or `tend()` with idle WETH | `_harvestAndReport` and `_tend` call `_stake` without checking `stakeAsset` | `reportable` | keeper-gated not public; report path deposit-limit bounded; design intent for flag is slightly ambiguous due state-variable comment | yes |
