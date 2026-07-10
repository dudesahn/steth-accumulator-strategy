# Recon and Invariants Lane

## Coverage

- Reviewed the allowed Human Pages files: `contract_brief.md`, `entry_points.md`, `invariants.md`, and `static_analysis.md`.
- Checked local production entry points in `src/BaseLSTAccumulator.sol`, `src/Strategy.sol`, `src/Strategy4626.sol`, `src/Strategy4626Factory.sol`, and `src/periphery/StrategyAprOracle.sol`.
- Checked the relevant inherited Yearn surfaces in `lib/tokenized-strategy/src/BaseStrategy.sol`, `lib/tokenized-strategy/src/TokenizedStrategy.sol`, `lib/tokenized-strategy-periphery/src/Bases/HealthCheck/BaseHealthCheck.sol`, `lib/tokenized-strategy-periphery/src/AprOracle/AprOracleBase.sol`, and `lib/tokenized-strategy-periphery/src/utils/Governance.sol`.
- The entry-point map is mostly accurate for the main strategy contracts. Corrections:
  - `StrategyAprOracle` inherits `transferGovernance(address)` through `AprOracleBase -> Governance`; this is a state-changing inherited surface missing from the map (`src/periphery/StrategyAprOracle.sol:6`, `lib/tokenized-strategy-periphery/src/AprOracle/AprOracleBase.sol:6`, `lib/tokenized-strategy-periphery/src/utils/Governance.sol:35`).
  - `TokenizedStrategy.initialize(...)` is technically reachable through the strategy fallback, but the one-time guard prevents successful reinitialization after construction (`lib/tokenized-strategy/src/BaseStrategy.sol:485`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:433`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:443`).
  - `TokenizedStrategy.permit(...)` is a state-changing inherited ERC20 approval surface; the map's generic "permit methods" row covers it, but the exact line is `lib/tokenized-strategy/src/TokenizedStrategy.sol:1965`.

## Candidates

### MEDIUM - shutdown does not prevent keeper report/tend from re-staking emergency-freed WETH

The shutdown state machine is weaker than described. Yearn shutdown blocks new `deposit`/`mint`, but explicitly still allows `tend` and `report` (`lib/tokenized-strategy/src/TokenizedStrategy.sol:1329`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:1331`). This strategy's `tend` callback unconditionally stakes idle WETH (`src/BaseLSTAccumulator.sol:165`), and the report path also stakes loose WETH before accounting (`src/BaseLSTAccumulator.sol:146`, `src/BaseLSTAccumulator.sol:152`). Because the constructor whitelists `address(this)` (`src/BaseLSTAccumulator.sol:64`), `availableDepositLimit(address(this))` stays nonzero even when the inherited strategy is shutdown (`src/BaseLSTAccumulator.sol:126`).

This contradicts the Yearn base guidance for shutdown reports: if reporting after emergency withdrawal, `_harvestAndReport` should check shutdown so it does not redeploy freed funds (`lib/tokenized-strategy/src/BaseStrategy.sol:342`, `lib/tokenized-strategy/src/BaseStrategy.sol:345`). Impact is that after `shutdownStrategy()` and `emergencyWithdraw()`, a keeper or management `tend()` or `report()` can move WETH back into stETH, wstETH, or the external vault (`src/Strategy.sol:51`, `src/Strategy4626.sol:29`), undermining emergency unwind and liquid-only withdrawal expectations.

### MEDIUM - Lido withdrawal queue return data is encoded as `uint256[]` but claim decodes `uint256`

`BaseLSTAccumulator.initiateLSTWithdrawal` increments `pendingRedemptions` and returns child `returnData` (`src/BaseLSTAccumulator.sol:259`, `src/BaseLSTAccumulator.sol:262`). The stETH implementation requests withdrawals through an interface returning `uint256[]` (`src/interfaces/IQueue.sol:5`) and returns `abi.encode(requestIds)` (`src/Strategy.sol:97`, `src/Strategy.sol:99`). The claim implementation then decodes the caller-supplied bytes as a single `uint256` (`src/Strategy.sol:104`, `src/Strategy.sol:105`).

For normal ABI encoding, `abi.decode(abi.encode(uint256[](1)), (uint256))` reads the array head offset, `32`, not `requestIds[0]`. A keeper that uses the documented return bytes from initiation will call `claimWithdrawal(32)` instead of the real request id (`src/Strategy.sol:107`, `src/Strategy.sol:108`). The strategy then remains stuck with `pendingRedemptions`, causing future reports to revert (`src/BaseLSTAccumulator.sol:146`, `src/BaseLSTAccumulator.sol:147`). Recovery is possible by manually passing `abi.encode(requestId)` or using emergency/manual clearing paths, so this is an operational DoS/state-machine issue rather than direct theft.

### MEDIUM - Strategy4626 deposit capacity invariant ignores pre-existing loose WETH

`Strategy4626.availableDepositLimit` caps a new depositor by the external vault's current `maxDeposit(address(this))`, converted through wstETH/stETH units (`src/Strategy4626.sol:55`, `src/Strategy4626.sol:59`, `src/Strategy4626.sol:62`). However, inherited `_deposit` does not deploy only the newly accepted `assets`; after transferring from the depositor, it calls `deployFunds(_asset.balanceOf(address(this)))`, i.e. the full loose WETH balance already sitting in the strategy (`lib/tokenized-strategy/src/TokenizedStrategy.sol:963`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:967`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:968`). `Strategy4626._stake` then wraps all stETH and deposits the entire wstETH balance into the external vault without rechecking `maxDeposit` (`src/Strategy4626.sol:32`, `src/Strategy4626.sol:37`, `src/Strategy4626.sol:41`).

An external WETH donation, previous `stakeAsset=false` idle balance, or other loose WETH can make a subsequent otherwise-valid deposit attempt push more into the ERC4626 vault than `availableDepositLimit` allowed. With a finite-capacity vault this can revert at `vault.deposit`, allowing a low-cost deposit DoS if the attacker only needs to push loose WETH above remaining vault capacity. Management can mitigate by disabling `stakeAsset` or clearing idle balance, but the stated Strategy4626 capacity invariant is false as written.

### LOW - report buffer has no upper bound and can brick views/reports by underflow

`estimatedTotalAssets` computes `MAX_BPS - reportBuffer` (`src/BaseLSTAccumulator.sol:177`, `src/BaseLSTAccumulator.sol:178`), but `setReportBuffer` accepts any management-supplied value (`src/BaseLSTAccumulator.sol:198`, `src/BaseLSTAccumulator.sol:199`). If set above `MAX_BPS`, `estimatedTotalAssets`, `_depositLimit`, and report paths can revert. This is role-restricted misconfiguration rather than an external attack, but INV-RPT-3 is not enforced.

### LOW - factory one-per-vault invariant can be bypassed by malicious vault reentrancy during deployment

`newStrategy4626` checks `deployments[_vault]` once, then makes external calls before writing the deployment marker: `ERC20(_vault).symbol()` before deployment (`src/Strategy4626Factory.sol:43`, `src/Strategy4626Factory.sol:48`) and `IERC4626(_vault).asset()` inside the new strategy constructor (`src/Strategy4626.sol:20`, `src/Strategy4626.sol:21`). The mapping is written only after post-deploy setter calls and the event (`src/Strategy4626Factory.sol:52`, `src/Strategy4626Factory.sol:66`, `src/Strategy4626Factory.sol:68`).

A malicious vault can reenter `newStrategy4626(_vault)` before the marker is set and cause duplicate strategy deployments/events for the same vault, with only the last written address recorded. No direct funds are at risk because deployment is public and strategies still need users/management to trust them, but INV-FAC-1 is stronger than the implementation.

### INFO - APR oracle inherited governance mutator omitted from entry map

`StrategyAprOracle` inherits `AprOracleBase`, which inherits `Governance` (`src/periphery/StrategyAprOracle.sol:6`, `lib/tokenized-strategy-periphery/src/AprOracle/AprOracleBase.sol:6`). `Governance.transferGovernance(address)` mutates the oracle's `governance` field and is gated by current governance (`lib/tokenized-strategy-periphery/src/utils/Governance.sol:17`, `lib/tokenized-strategy-periphery/src/utils/Governance.sol:35`, `lib/tokenized-strategy-periphery/src/utils/Governance.sol:37`). This is an entry-map miss, not a concrete strategy-fund risk, because the oracle's APR output is constant (`src/periphery/StrategyAprOracle.sol:28`, `src/periphery/StrategyAprOracle.sol:32`).

## Non-Findings / Rejected Ideas

- Public deposit/mint gating appears correctly inherited: shutdown and `receiver == address(this)` are blocked in `_maxDeposit`/`_maxMint` (`lib/tokenized-strategy/src/TokenizedStrategy.sol:870`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:875`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:885`).
- Third-party withdraw/redeem authorization appears correctly inherited: receiver is nonzero, `maxLoss` is bounded, and allowance is spent when `msg.sender != owner` (`lib/tokenized-strategy/src/TokenizedStrategy.sol:997`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:998`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:1001`).
- Liquid-only withdrawals match the stated design: `_freeFunds` intentionally does nothing and `availableWithdrawLimit` returns only loose WETH (`src/BaseLSTAccumulator.sol:115`, `src/BaseLSTAccumulator.sol:122`, `src/BaseLSTAccumulator.sol:133`, `src/BaseLSTAccumulator.sol:143`).
- Curve WETH-to-stETH routing can be manipulated for route selection, but the actual Curve exchange uses `_min_to_amount = _amount`, so it should revert rather than accept below-1:1 stETH output (`src/Strategy.sol:57`, `src/Strategy.sol:60`, `src/Strategy.sol:64`).
- `Strategy4626._freeStETH` unwraps all loose wstETH after any vault redemption (`src/Strategy4626.sol:77`, `src/Strategy4626.sol:91`, `src/Strategy4626.sol:95`). This can change exposure more than the requested amount, but it preserves strategy-owned value and is only reached from management/emergency flows in this design.
- `receive()` accepts arbitrary ETH (`src/Strategy.sol:36`), and swap/claim paths wrap the full ETH balance into WETH (`src/Strategy.sol:80`, `src/Strategy.sol:112`, `src/Strategy.sol:125`). Pre-existing ETH donations are not counted as newly redeemed in `_claimLSTWithdrawal` because `preBalance` is sampled before the queue claim (`src/Strategy.sol:107`, `src/Strategy.sol:109`).
- Factory zero-address setters are governance/management hygiene issues. `TokenizedStrategy.initialize` and `setPerformanceFeeRecipient` guard critical zero/self values for deployed strategies (`lib/tokenized-strategy/src/TokenizedStrategy.sol:457`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:467`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:1575`), while factory `setAddresses` can still brick future deployment configuration if management misuses it (`src/Strategy4626Factory.sol:72`, `src/Strategy4626Factory.sol:78`).

## Suggested PoCs

1. Shutdown restake PoC for the first MEDIUM:
   - Deploy or use existing setup for `Strategy`.
   - Deposit WETH and allow it to stake.
   - As emergency admin or management, call `shutdownStrategy()` then `emergencyWithdraw(type(uint256).max)` or otherwise create loose WETH in the shutdown strategy.
   - As keeper, call `tend()` and assert `asset.balanceOf(strategy)` decreases while `stETH`/`wstETH`/vault exposure increases despite `isShutdown() == true`.
   - Suggested command after adding a PoC test: `forge test --match-path src/test/ShutdownRestakePoC.t.sol --match-test test_shutdown_tend_or_report_restakes_idle_weth -vvv --fork-url $ETH_RPC_URL`

2. Claim data mismatch PoC for the second MEDIUM:
   - Construct `uint256[] memory ids = new uint256[](1); ids[0] = 12345;`.
   - Set `bytes memory returnData = abi.encode(ids);`.
   - Assert `abi.decode(returnData, (uint256)) == 32`, not `12345`.
   - In an integration-style variant, have `initiateLSTWithdrawal` return this bytes blob and assert `claimLSTWithdrawal(returnData)` attempts `claimWithdrawal(32)` or leaves `pendingRedemptions` uncleared.
   - Suggested command after adding a PoC test: `forge test --match-path src/test/WithdrawalQueueClaimDataPoC.t.sol --match-test test_initiate_return_data_decodes_to_offset_not_request_id -vvv`

3. Strategy4626 capacity DoS PoC for the third MEDIUM:
   - Use a mock ERC4626 vault whose `asset()` is wstETH and whose `maxDeposit(address(this))` is finite.
   - Directly transfer WETH to the Strategy4626 so loose WETH is already above the vault's remaining capacity.
   - Have an allowed user deposit a small amount that is less than `availableDepositLimit(user)`.
   - Assert the deposit reverts when `_deployFunds` tries to deposit the entire loose balance into the vault.
   - Suggested command after adding a PoC test: `forge test --match-path src/test/Strategy4626CapacityPoC.t.sol --match-test test_donated_idle_weth_can_make_next_deposit_exceed_vault_capacity -vvv`
