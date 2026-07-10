# Finding Discovery Worker Output: shard_05_interfaces_oracle

scan_id: 351c58eb-604e-4d06-91a4-9a0d6e65626b
target: /Users/dudesahn/Documents/GitHub/codex/review/steth-accumulator-strategy
scope: production code only
assigned_files:
- src/interfaces/IBaseLSTAccumulator.sol
- src/interfaces/IStrategyInterface.sol
- src/interfaces/IStrategy4626Interface.sol
- src/periphery/StrategyAprOracle.sol

## Full-file receipts

- src/interfaces/IBaseLSTAccumulator.sol: read lines 1-43 in full. Evidence: interface imports IBaseHealthCheck at line 4, extends it at line 6, exposes view state getters at lines 16-26, management setters at lines 28-35, and manual/keeper-style LST operations at lines 37-42.
- src/interfaces/IStrategyInterface.sol: read lines 1-14 in full. Evidence: interface extends IBaseLSTAccumulator at lines 4-6 and adds stETH referral/manual-claim surface at lines 9-13.
- src/interfaces/IStrategy4626Interface.sol: read lines 1-15 in full. Evidence: interface extends IStrategyInterface at lines 4-8 and exposes vault/wstETH views plus emergency-style manual redeem/unwrap functions at lines 9-14.
- src/periphery/StrategyAprOracle.sol: read lines 1-34 in full. Evidence: oracle inherits AprOracleBase at lines 4-7 and implements aprAfterDebtChange at lines 28-32 by ignoring both parameters and returning the constant 4e16.

## Supporting code inspected

- src/BaseLSTAccumulator.sol: inspected role gates and accounting/report interactions for interface methods. Management setters and manual fund movement are onlyManagement at lines 198-245; manualStake is onlyManagement at lines 250-253; initiateLSTWithdrawal is onlyManagement and increments pendingRedemptions at lines 259-263; claimLSTWithdrawal is onlyKeepers and decrements pendingRedemptions at lines 269-272; clearPendingRedemptions is onlyManagement at lines 279-280; harvest/report requires pendingRedemptions == 0 at lines 146-147; normal withdrawals are limited to liquid asset at lines 133-143.
- src/Strategy.sol: inspected stETH-specific request/claim implementation. _initiateLSTWithdrawal receives uint256[] requestIds from the Lido queue at line 97 and returns abi.encode(requestIds) at line 99; _claimLSTWithdrawal decodes the bytes as a single uint256 at line 105 and passes it to claimWithdrawal at line 108; manualClaimWithdrawals is onlyEmergencyAuthorized at lines 116-120; setReferral is onlyManagement at lines 128-129.
- src/Strategy4626.sol: inspected ERC4626 helper exposure and value functions. availableDepositLimit respects vault.maxDeposit at lines 55-62; valueOfWstETH uses local wstETH plus vault.convertToAssets(balanceOf shares) at lines 69-70; valueOfLST includes stETH plus wstETH value at lines 73-74; _freeStETH redeems vault shares up to previewWithdraw/maxRedeem and unwraps wstETH at lines 77-95; manualRedeem and manualUnwrap are onlyEmergencyAuthorized at lines 103-114.
- src/interfaces/IQueue.sol: inspected Lido queue wrapper signatures. requestWithdrawals returns uint256[] requestIds at lines 5-7; claimWithdrawal accepts a scalar uint256 at line 8; batch claim accepts arrays at line 10.
- lib/tokenized-strategy-periphery/src/AprOracle/AprOracleBase.sol: inspected imported API contract because StrategyAprOracle directly inherits it. aprAfterDebtChange is defined as a strategy- and delta-sensitive expected APR hook at lines 16-33.
- lib/tokenized-strategy-periphery/src/AprOracle/AprOracle.sol: inspected direct periphery consumer behavior. getStrategyApr forwards _strategy and _debtChange to the registered oracle at lines 61-84; setOracle can be called by AprOracle governance or the strategy management at lines 113-121.

## Coverage rows

| family | disposition | evidence | notes |
|---|---|---|---|
| External interface exposure for management setters | suppressed | IBaseLSTAccumulator.sol:28-35 declares setters; BaseLSTAccumulator.sol:198-235 implements them onlyManagement | No public/unguarded implementation found for assigned setter surface. |
| External interface exposure for manual stake/swap/redemption initiation | suppressed | IBaseLSTAccumulator.sol:37-42 declares manual operations; BaseLSTAccumulator.sol:241-263 implements swap/stake/initiate onlyManagement | Sensitive LST movement is privileged. Claim-data mismatch is tracked separately because it affects correctness after a privileged initiation. |
| Keeper claim helper exposure | reportable | IBaseLSTAccumulator.sol:40-41 pairs initiate return bytes with claim bytes; Strategy.sol:97-105 encodes uint256[] but decodes uint256 | See candidate CS-351C58EB-S05-001. |
| Emergency helper exposure | suppressed | IStrategyInterface.sol:12-13 declares manualClaimWithdrawals; Strategy.sol:116-120 gates it onlyEmergencyAuthorized; IStrategy4626Interface.sol:13-14 declares manualRedeem/manualUnwrap; Strategy4626.sol:103-114 gates both onlyEmergencyAuthorized | No untrusted caller can invoke these helpers from the inspected implementations. Operational footguns remain privileged. |
| Interface mismatch that can mislead production callers | reportable | IBaseLSTAccumulator.sol:40-41, BaseLSTAccumulator.sol:259-272, Strategy.sol:97-105, IQueue.sol:5-10 | Returned claim data from initiation is not in the format consumed by claimLSTWithdrawal. See candidate CS-351C58EB-S05-001. |
| Oracle semantics and debt-allocation risk | deferred | StrategyAprOracle.sol:28-32 returns constant 4e16; AprOracleBase.sol:16-33 expects strategy/delta-sensitive APR; AprOracle.sol:61-84 forwards per-strategy debt change to registered oracle | Plausible if registered for production debt allocation, but no in-repo deployment/registration evidence was found. See candidate CS-351C58EB-S05-002. |
| Static APR behavior | deferred | StrategyAprOracle.sol:28-32 ignores _strategy and _delta | Candidate-local proof gap is whether this example oracle is deployed/registered for production allocators. |
| ERC4626 manual helper/unit exposure through interface | suppressed | IStrategy4626Interface.sol:9-14 declares views/manual helpers; Strategy4626.sol:55-74 shows value conversion views; Strategy4626.sol:103-114 gates manualRedeem/manualUnwrap | No missing access control or caller-controlled sink in assigned interface surface. Amount-unit ambiguity for manualRedeem is emergency-only. |
| Standard deposit/withdraw exposure through inherited interfaces | suppressed | BaseLSTAccumulator.sol:126-143 gates deposits with openDeposits/allowed/depositLimit and normal withdrawals to balanceOfAsset | No assigned-file evidence of unguarded deposit opening or automatic LST unstaking through public withdrawals. |

## Raw candidates

### Candidate CS-351C58EB-S05-001

candidate_id: CS-351C58EB-S05-001
title: Lido withdrawal initiation returns encoded request-id array but keeper claim decodes a scalar request id

Affected locations:
- entrypoint/wrapper: src/interfaces/IBaseLSTAccumulator.sol:40-41 declares initiateLSTWithdrawal(uint256) returns bytes and claimLSTWithdrawal(bytes), making the initiation return data the natural input for the keeper claim.
- entrypoint/wrapper: src/BaseLSTAccumulator.sol:259-263 onlyManagement initiateLSTWithdrawal clamps the amount, increments pendingRedemptions, and returns _initiateLSTWithdrawal(_amount).
- sink/state-control: src/BaseLSTAccumulator.sol:269-272 onlyKeepers claimLSTWithdrawal calls _claimLSTWithdrawal(_claimData) and decrements pendingRedemptions only after a redeemed amount is returned.
- concrete_implementation/root_control: src/Strategy.sol:97-99 receives uint256[] requestIds from requestWithdrawals and returns abi.encode(requestIds).
- concrete_implementation/root_control/sink: src/Strategy.sol:104-108 decodes the supplied bytes as uint256 and passes that scalar to IQueue.claimWithdrawal.
- impact amplifier: src/BaseLSTAccumulator.sol:146-147 harvest/report requires pendingRedemptions == 0.
- fallback control: src/Strategy.sol:116-125 exposes manualClaimWithdrawals only to emergency-authorized accounts and can optionally zero pendingRedemptions.
- fallback control: src/BaseLSTAccumulator.sol:279-280 allows management to clear pendingRedemptions, with nearby comments at lines 275-278 warning that doing so can realize losses during the next report.

instance_key: interface-mismatch:src/Strategy.sol:99
attacker-controlled or privileged source: privileged management initiates an LST withdrawal; keeper later supplies claim bytes to claimLSTWithdrawal. The immediate source is privileged/operator-controlled rather than untrusted, but the bug is in the production interface contract between management initiation and keeper claiming.
broken control/sink: ABI format mismatch between the bytes returned by initiation and the bytes consumed by claiming. abi.encode(uint256[]) is later abi.decode(..., (uint256)), so normal reuse of returned bytes decodes the dynamic-array offset word, not the actual request id.
impact: Normal keeper claim flow can claim the wrong request id or revert, leaving pendingRedemptions nonzero. Because _harvestAndReport requires pendingRedemptions == 0, reports can remain blocked until emergency/manual intervention; incorrect manual clearing can realize losses or hide unsettled redemptions.
closest control and why incomplete: claimLSTWithdrawal is onlyKeepers, so untrusted users cannot trigger arbitrary claims; however, the role gate does not validate that _claimData matches the format returned by initiateLSTWithdrawal. manualClaimWithdrawals and clearPendingRedemptions are fallback controls, but they require emergency/management action and can desynchronize or realize losses.
candidate-local validation evidence:
- IQueue.requestWithdrawals returns uint256[] requestIds (src/interfaces/IQueue.sol:5-7).
- Strategy._initiateLSTWithdrawal stores the returned array and returns abi.encode(requestIds) (src/Strategy.sol:97-99).
- Strategy._claimLSTWithdrawal decodes the bytes as a scalar uint256 (src/Strategy.sol:104-105) and calls claimWithdrawal(_requestId) (src/Strategy.sol:108).
- BaseLSTAccumulator increments pendingRedemptions before returning the encoded data (src/BaseLSTAccumulator.sol:259-263) and only decrements after _claimLSTWithdrawal succeeds (src/BaseLSTAccumulator.sol:269-272).
- Reports are blocked while pendingRedemptions is nonzero (src/BaseLSTAccumulator.sol:146-147).
candidate-local counterevidence:
- The claim function is keeper-gated, not public (src/BaseLSTAccumulator.sol:269).
- Emergency-authorized accounts can batch-claim with explicit request ids/hints (src/Strategy.sol:116-120) and management can clear pendingRedemptions (src/BaseLSTAccumulator.sol:279-280).
- No in-repo production caller was found that automatically pipes the returned bytes into claimLSTWithdrawal; the issue is inferred from the public interface contract and implementation pair.
proof gaps:
- No fork/runtime PoC was executed in this worker pass.
- Exact Lido queue revert behavior for a wrong scalar request id was not inspected beyond the local IQueue signature.
attack-path facts:
- If a single Lido request id N is returned, abi.encode(uint256[](1)[N]) begins with the dynamic offset word 0x20. abi.decode(returnData, (uint256)) therefore yields 32 rather than N.
- A keeper following the interface-level bytes handoff will call claimWithdrawal(32) instead of the newly created request id.
- On revert or zero progress, pendingRedemptions remains nonzero and blocks harvest/report.
validation recommended: yes
CWE: [CWE-704]

### Candidate CS-351C58EB-S05-002

candidate_id: CS-351C58EB-S05-002
title: StrategyAprOracle returns a constant 4% APR for any strategy and debt delta

Affected locations:
- root_control: src/periphery/StrategyAprOracle.sol:28 implements aprAfterDebtChange(address _strategy, int256 _delta).
- sink: src/periphery/StrategyAprOracle.sol:29-32 ignores _strategy and _delta and always returns 4e16.
- imported API expectation: lib/tokenized-strategy-periphery/src/AprOracle/AprOracleBase.sol:16-33 documents aprAfterDebtChange as the expected APR at the current timestamp after a signed debt change.
- imported consumer: lib/tokenized-strategy-periphery/src/AprOracle/AprOracle.sol:61-84 forwards _strategy and _debtChange to a registered oracle from getStrategyApr.
- imported registration control: lib/tokenized-strategy-periphery/src/AprOracle/AprOracle.sol:113-121 allows AprOracle governance or strategy management to register the custom oracle.

instance_key: oracle-static-apr:src/periphery/StrategyAprOracle.sol:28
attacker-controlled or privileged source: privileged AprOracle governance or strategy management can register this oracle for a strategy in the Yearn periphery; allocators or off-chain systems can then consume the reported APR. No untrusted caller can change the returned APR.
broken control/sink: APR calculation ignores both the strategy address and debt delta even though the periphery API passes those values specifically to model expected APR after allocation changes.
impact: If this contract is registered for production debt allocation, it can overstate or understate strategy yield and cause debt allocators or dashboards to allocate capital based on a hard-coded 4% value instead of actual stETH/vault conditions. The direct impact is misleading allocator signals and possible opportunity loss or excess exposure rather than direct theft from this strategy.
closest control and why incomplete: AprOracle.setOracle is restricted to governance or strategy management, but that only controls registration authority. Once registered, getStrategyApr trusts the custom oracle response and forwards it to consumers without sanity-checking strategy-specific or delta-specific semantics.
candidate-local validation evidence:
- StrategyAprOracle.aprAfterDebtChange receives _strategy and _delta but does not reference either parameter (src/periphery/StrategyAprOracle.sol:28-32).
- The inherited API says the hook should return expected APR after a signed debt change and can be called during non-view functions (lib/tokenized-strategy-periphery/src/AprOracle/AprOracleBase.sol:16-33).
- The periphery AprOracle returns IOracle(oracle).aprAfterDebtChange(_strategy, _debtChange) for a registered oracle (lib/tokenized-strategy-periphery/src/AprOracle/AprOracle.sol:82-84).
candidate-local counterevidence:
- The constructor name is "Strategy Apr Oracle Example" (src/periphery/StrategyAprOracle.sol:7), suggesting placeholder/example intent.
- No script or production source in this repository registers StrategyAprOracle with AprOracle; local search found no StrategyAprOracle usage outside its own file.
- Oracle registration in the imported periphery is privileged (lib/tokenized-strategy-periphery/src/AprOracle/AprOracle.sol:113-121).
proof gaps:
- Need deployment/config evidence that this oracle is actually registered or intended for production debt allocation.
- Need allocator consumer behavior to quantify loss/exposure from a stale constant APR.
attack-path facts:
- A privileged registrant sets this oracle for a strategy in the periphery AprOracle.
- getStrategyApr for that strategy routes to this contract and receives 4e16 regardless of current strategy, current yield, available capacity, vault state, or positive/negative debt change.
- Debt allocation or monitoring based on getStrategyApr can rank this strategy incorrectly against dynamic strategies.
validation recommended: yes, but only if production registration/usage is in scope
CWE: [CWE-682]

## No-additional-candidate notes

- No plausible missing-access-control candidate was found in the assigned interface surface. Every sensitive method declared by the interfaces that was inspected in first-party implementation is gated by onlyManagement, onlyKeepers, or onlyEmergencyAuthorized.
- No direct untrusted external caller path was found for manualRedeem/manualUnwrap or manualClaimWithdrawals; their residual risks are privileged emergency-operation risks.
- No candidate was opened for Strategy4626 view functions or vault/wstETH getters because the assigned interface only exposes read methods, and the inspected implementation's value accounting concerns belong to Strategy4626 logic rather than an interface/oracle mismatch in this shard.
