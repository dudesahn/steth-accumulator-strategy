# Validation: CS-351C58EB-003

## Finding

Donated loose stETH/wstETH can exceed downstream ERC4626 `maxDeposit` and revert maintenance flows.

- candidate id: `CS-351C58EB-003`
- instance key: `erc4626-maxdeposit-donation-dos:src/Strategy4626.sol:41`
- ledger row id: `HIF-004` (`WL-003` coverage row also references this candidate)
- root-control: `src/Strategy4626.sol:41`
- affected locations from discovery: `src/Strategy4626.sol:29-41`, `src/Strategy4626.sol:55-63`, `src/BaseLSTAccumulator.sol:146-154`
- additional validated maintenance entrypoint: `src/BaseLSTAccumulator.sol:165-166`
- recommended disposition: `reportable`
- confidence: high (`0.88`)

## Validation Rubric

- [x] Attacker-controlled source: an untrusted actor can directly transfer/donate canonical stETH or wstETH to the strategy address, and the threat model explicitly includes donation/direct token transfers as attacker-controlled inputs.
- [x] Reachable maintenance interface: a real keeper/management maintenance entrypoint reaches `_stake()` after the donation (`report()` via `_harvestAndReport()`, `tend()`, or management `manualStake()`).
- [x] Broken control: the downstream vault `maxDeposit(address(this))` is used only to cap new WETH deposit availability, not the full loose wstETH balance actually sent to `vault.deposit()`.
- [x] Vulnerable sink: `_stake()` deposits the entire loose wstETH balance into the downstream ERC4626 vault, and standard ERC4626 implementations revert when `assets > maxDeposit(receiver)`.
- [ ] Production severity calibration complete: the exact donation cost and likelihood depend on the chosen downstream wstETH vault's live `maxDeposit` behavior and headroom.

## Evidence Observed

Source/control/sink trace:

- `Strategy4626._stake()` calls `super._stake(_amount)`, then wraps the full loose stETH balance if any, then reads the full loose wstETH balance and calls `vault.deposit(wstETHBalance, address(this))` without bounding `wstETHBalance` by `vault.maxDeposit(address(this))` (`src/Strategy4626.sol:29-41`).
- `Strategy4626.availableDepositLimit()` reads `vault.maxDeposit(address(this))` and caps only the externally advertised/new WETH deposit limit by `_stETHValue(maxDeposit)` (`src/Strategy4626.sol:55-63`). This does not subtract or otherwise account for already-loose donated stETH/wstETH held by the strategy.
- `BaseLSTAccumulator._harvestAndReport()` reaches `_stake(Math.min(balanceOfAsset(), availableDepositLimit(address(this))))` during keeper/management `report()` (`src/BaseLSTAccumulator.sol:146-154`). Even if the new WETH amount is bounded, `Strategy4626._stake()` subsequently deposits all loose wstETH.
- `BaseLSTAccumulator._tend()` directly calls `_stake(_totalIdle)` (`src/BaseLSTAccumulator.sol:165-166`), and TokenizedStrategy `tend()` is a real permissioned keeper/management entrypoint that passes the current loose asset balance (`lib/tokenized-strategy/src/TokenizedStrategy.sol:1295-1318`).
- TokenizedStrategy `report()` is likewise keeper/management gated and calls `harvestAndReport()` (`lib/tokenized-strategy/src/TokenizedStrategy.sol:1081-1096`).
- The imported OpenZeppelin ERC4626 implementation enforces `require(assets <= maxDeposit(receiver), "ERC4626: deposit more than max")` in `deposit()` (`lib/openzeppelin-contracts/contracts/token/ERC20/extensions/ERC4626.sol:152-157`).

PoC evidence:

- Existing validation artifact: `/private/var/folders/s_/3h_wvzqx385frkp70gr8cpdc0000gn/T/codex-security-scans-HMBJE7/steth-accumulator-strategy/521fff28ad978a37115be8995a1d631611fa1d3d_20260708T164548Z_sqevo7au/artifacts/05_findings/CS-351C58EB-003/validation_artifacts/repro/src/test/MaxDepositDonationPoC.t.sol`
- The PoC creates a bounded ERC4626 wstETH vault with `maxDeposit() == 1 ether`, deploys `Strategy4626` against it, donates `2 ether` of canonical mainnet wstETH to the strategy with `deal(WSTETH, address(strategy), 2 ether)`, then calls `strategy.tend()` and expects `ERC4626: deposit more than max`.
- Parent-provided execution result for `env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-path src/test/MaxDepositDonationPoC.t.sol -vv --fork-url https://ethereum.publicnode.com`: compiled 62 files and passed 1/1, proving the wstETH donation path through the real `tend()` entrypoint against the copied target code.

## Counterevidence and Scope Limits

- This is not direct theft: the attacker must donate stETH/wstETH value to trigger the condition, and the failure blocks maintenance rather than extracting funds.
- The affected external maintenance calls are keeper/management-gated, not public. The untrusted portion is the token donation state that the later trusted maintenance call consumes.
- If the configured downstream vault returns `type(uint256).max` or otherwise has enough `maxDeposit` headroom for the strategy's loose wstETH, this specific revert does not trigger.
- Emergency/management actions may be able to clear the donated loose balance, for example by unwrapping wstETH and swapping/withdrawing stETH through privileged flows. That is a recovery path, not a control that prevents the initial keeper/report DoS.
- The supplied PoC dynamically proves the loose wstETH donation path. The loose stETH variant is supported by code inspection of the same `_stake()` function because loose stETH is wrapped before the full wstETH balance is deposited, but it was not separately executed in the supplied PoC.

## What Was Tested

I inspected the candidate, threat model, coverage ledger, production `Strategy4626`/`BaseLSTAccumulator` paths, directly imported TokenizedStrategy keeper/report entrypoints, the imported ERC4626 deposit API, and the existing disposable PoC. I did not create additional artifacts or rerun forge in this worker, to preserve the instruction to write only the assigned output file; the parent-supplied PoC run and existing compile artifacts were used as dynamic evidence and were checked against the source trace.

## Remaining Uncertainty

The vulnerability is validated for any supported downstream wstETH ERC4626 vault whose `maxDeposit(address(strategy))` can be lower than donated loose wstETH. Severity still needs final calibration against the intended production vault(s): live max-deposit policy, current headroom, whether cap reductions to zero are plausible, and the minimum donation needed to block maintenance.

## Minimal Next Step

For final reporting, quantify the griefing cost against the intended production downstream vault by comparing `vault.maxDeposit(strategy)` to possible donated loose wstETH/stETH balances. A focused remediation check should bound the deposit amount by current capacity and leave excess loose wstETH/stETH recoverable instead of reverting the entire maintenance call.

## Validation Closure

| ledger row id | instance key | advisory/source reference | seed anchor file:line | root-control file:line | entrypoint/source | sink/control | disposition | counterevidence or proof gap | survives |
|---|---|---|---|---|---|---|---|---|---|
| `HIF-004` | `erc4626-maxdeposit-donation-dos:src/Strategy4626.sol:41` | discovery candidate `CS-351C58EB-003` / raw id `CS-351c58eb-S03-001` | `src/Strategy4626.sol:29-41` | `src/Strategy4626.sol:41` | untrusted direct stETH/wstETH donation, then keeper/management `tend()` or `report()` | `vault.deposit(wstETHBalance, address(this))` uses full loose wstETH while `availableDepositLimit()` only caps new WETH deposit availability | `reportable` | no theft and keeper call is permissioned; severity depends on actual downstream vault cap/headroom; wstETH path dynamically reproduced, stETH path statically follows wrapping branch | yes |
