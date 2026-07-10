# Solidity Auditor Agent 8 - Asymmetry

Scope: BaseLSTAccumulator, Strategy, Strategy4626, Strategy4626Factory, StrategyAprOracle at commit 521fff28ad978a37115be8995a1d631611fa1d3d.

Orientation used: pashov x-ray, entry-points, invariants. Proof is from the lane bundle plus targeted out-of-scope context in interfaces, tests, and tokenized-strategy callbacks.

## Tool markers

[Feynman: BaseLSTAccumulator] This contract is the common machine that decides who may deposit, when idle WETH becomes stETH, how much liquid WETH users can withdraw, how pending Lido exits block reports, and which role can manually move value back and forth.
[Feynman: BaseLSTAccumulator._deployFunds] When a user deposit leaves WETH in the strategy, this stakes that WETH only if the staking flag is on and the amount is above dust.
[Feynman: BaseLSTAccumulator._freeFunds] When a normal user withdrawal asks the strategy to free money, this implementation intentionally does nothing.
[Feynman: BaseLSTAccumulator.availableDepositLimit] This lets a depositor in only if deposits are open or the receiver is whitelisted, then returns the remaining capacity.
[Feynman: BaseLSTAccumulator.availableWithdrawLimit] This tells users they can only withdraw the WETH already sitting idle in the strategy.
[Feynman: BaseLSTAccumulator._harvestAndReport] A keeper report refuses to run while queued Lido exits exist, then claims rewards, stakes idle WETH up to capacity, and reports WETH plus haircut LST value.
[Feynman: BaseLSTAccumulator._emergencyWithdraw] During shutdown, this tries to sell direct stETH back to WETH, but it first looks only at the direct stETH balance.
[Feynman: BaseLSTAccumulator._tend] A keeper tend stakes the idle WETH amount that TokenizedStrategy passes in.
[Feynman: BaseLSTAccumulator.estimatedTotalAssets] This reports idle WETH plus a buffered value for everything counted as LST exposure.
[Feynman: BaseLSTAccumulator.setters] Management setters change the knobs that decide deposit access, capacity, report haircut, tend threshold, gas threshold, and staking behavior.
[Feynman: BaseLSTAccumulator.manualSwapToAsset] Management can sell LST exposure for WETH with caller-provided slippage.
[Feynman: BaseLSTAccumulator.manualStake] Management can stake loose WETH.
[Feynman: BaseLSTAccumulator.initiateLSTWithdrawal] Management queues LST for Lido withdrawal and increments the pending-redemption counter before returning opaque claim data.
[Feynman: BaseLSTAccumulator.claimLSTWithdrawal] A keeper supplies claim data, the strategy claims ETH, wraps it to WETH, and reduces the pending-redemption counter by what was received.
[Feynman: BaseLSTAccumulator.clearPendingRedemptions] Management can manually lower the pending-redemption counter when the queue path needs emergency unsticking.
[Inversion: BaseLSTAccumulator.claimLSTWithdrawal] Try passing the raw bytes returned by initiate; try passing a stale but valid request id; try claiming less ETH than pending and then observe the report gate.

[Feynman: Strategy] This contract adapts the base machine to WETH, stETH, Curve, and Lido's withdrawal queue.
[Feynman: Strategy._depositLimit] This blocks new deposits when Lido staking is paused; otherwise it uses the base capacity rule.
[Feynman: Strategy._stake] This unwraps WETH to ETH, then either swaps through Curve if Curve gives more than direct staking or submits to Lido.
[Feynman: Strategy._swapLSTToAsset] This approves stETH to Curve, swaps stETH for ETH, then wraps all ETH on the contract back to WETH.
[Feynman: Strategy._initiateLSTWithdrawal] This approves stETH to Lido's queue, sends one requested amount, receives an array of request ids, and returns that array as bytes.
[Feynman: Strategy._claimLSTWithdrawal] This reads one request id from bytes, claims that one request from Lido, measures the ETH received, and wraps ETH to WETH.
[Feynman: Strategy.manualClaimWithdrawals] Emergency authorized callers can batch-claim queue requests with hints and optionally zero the pending-redemption counter.
[Feynman: Strategy.setReferral] Management changes the Lido referral address.
[Socratic: src/Strategy.sol:99 - why?] Why does the request side return bytes for an array while the claim side reads bytes as a single number? The implicit belief is that off-chain callers will transform the return payload before claiming.

[Feynman: Strategy4626] This variant adds a wstETH vault layer, so stETH is wrapped to wstETH and then deposited into an external ERC4626 vault.
[Feynman: Strategy4626.constructor] It accepts only vaults whose asset is wstETH, then approves stETH to wstETH and wstETH to the selected vault.
[Feynman: Strategy4626._stake] It performs the normal WETH-to-stETH staking, then wraps every direct stETH balance and deposits every direct wstETH balance into the vault.
[Feynman: Strategy4626._swapLSTToAsset] It first frees enough stETH from the wrapped/vault layer, then sells up to the direct stETH now available.
[Feynman: Strategy4626._initiateLSTWithdrawal] It first frees enough stETH, requires the requested stETH to be available, then queues the normal Lido withdrawal.
[Feynman: Strategy4626.availableDepositLimit] It combines the base deposit capacity with the downstream vault's own maximum deposit capacity.
[Feynman: Strategy4626.valueOfWstETH] It values loose wstETH plus vault shares as stETH.
[Feynman: Strategy4626.valueOfLST] It counts direct stETH plus the wrapped/vault position.
[Feynman: Strategy4626._freeStETH] It makes direct stETH available by redeeming vault shares if needed and unwrapping all loose wstETH.
[Feynman: Strategy4626.manualRedeem] Emergency authorized callers can redeem vault shares into loose wstETH.
[Feynman: Strategy4626.manualUnwrap] Emergency authorized callers can unwrap loose wstETH into direct stETH.
[Inversion: Strategy4626._stake] Call it with zero WETH and loose stETH staged by an emergency role; call it after management set capacity to zero; call it between manualUnwrap and manualSwapToAsset.

[Feynman: Strategy4626Factory] This factory stores default role addresses and deploys at most one Strategy4626 per selected vault.
[Feynman: Strategy4626Factory.newStrategy4626] Anyone can ask the factory to deploy a strategy for a vault that has not already been recorded.
[Feynman: Strategy4626Factory.setAddresses] Current factory management changes the role defaults used for future deployments.
[Feynman: Strategy4626Factory.isDeployedStrategy] This checks whether a strategy's vault points back to that strategy in the factory mapping.
[Feynman: StrategyAprOracle] This periphery oracle always returns a fixed 4 percent APR estimate.

## Pair inventory

- deposit/mint vs withdraw/redeem: TokenizedStrategy deposit calls BaseLSTAccumulator._deployFunds; withdraw calls BaseLSTAccumulator._freeFunds, but availableWithdrawLimit is idle-WETH-only. This is an intentional illiquidity split.
- stake vs unstake: Strategy._stake chooses Curve or Lido with a 1:1 minimum; Strategy._swapLSTToAsset uses caller minOut. Management controls the reverse slippage, so no unauthenticated path.
- request vs fulfill: BaseLSTAccumulator.initiateLSTWithdrawal increments pendingRedemptions and Strategy._initiateLSTWithdrawal returns encoded uint256[]; BaseLSTAccumulator.claimLSTWithdrawal decrements pendingRedemptions and Strategy._claimLSTWithdrawal decodes a uint256. Finding below.
- claim vs manualClaim: normal claim decrements pendingRedemptions by received ETH; emergency manualClaimWithdrawals either leaves pending unchanged or zeros it. This is a privileged recovery asymmetry; not a finding by itself.
- report vs claim/clear: report requires pendingRedemptions == 0; claim and clear are the only first-party lowerers besides emergency batch zeroing.
- Strategy vs Strategy4626 stake: Strategy._stake(_amount == 0) returns without moving tokens; Strategy4626._stake(_amount == 0) can still wrap/deposit all loose stETH/wstETH. Lead below.
- Strategy4626 swap vs initiate: _swapLSTToAsset can proceed with less direct stETH after _freeStETH by using Math.min(_amount, balanceOfLST()); _initiateLSTWithdrawal requires full availability. This can make manual swaps partial while queue requests revert; no untrusted caller path found.
- automated emergencyWithdraw vs manual recovery: TokenizedStrategy.emergencyWithdraw reaches BaseLSTAccumulator._emergencyWithdraw, which only looks at direct stETH; Strategy4626 manualRedeem/manualUnwrap know about the vault layer. Lead below.
- deposit-limit/open-deposit setters vs report/tend staking: tests explicitly assert harvest/tend can stake idle WETH after stakeAsset is false, so this was treated as intended behavior and not reported.
- factory deploy vs update: newStrategy4626 stamps role defaults at deployment; setAddresses affects only future deployments. No exploit path found because vault identity reads are view/static and roles are factory defaults, not caller-controlled.
- setReportBuffer vs estimatedTotalAssets: the setter lacks a MAX_BPS bound while the reader subtracts reportBuffer from MAX_BPS. This is management-only parameter risk and was not reported as an asymmetry finding.

## Findings

FINDING | contract: Strategy | function: initiateLSTWithdrawal/claimLSTWithdrawal | bug_class: encode-decode-asymmetry | group_key: Strategy | initiateLSTWithdrawal/claimLSTWithdrawal | encode-decode-asymmetry
path: management -> BaseLSTAccumulator.initiateLSTWithdrawal -> pendingRedemptions += amount -> Strategy._initiateLSTWithdrawal returns abi.encode(uint256[] requestIds) -> keeper/management -> BaseLSTAccumulator.claimLSTWithdrawal(returnData) -> Strategy._claimLSTWithdrawal decodes the first word as uint256 -> claimWithdrawal(32) instead of the actual request id -> pendingRedemptions remains nonzero and report() stays blocked
pair_or_branch: request/fulfill claim-data handoff
asymmetry: request side encodes a dynamic uint256[] while fulfill side decodes a scalar uint256; the normal claim path and the emergency batch claim path also expect different request-id shapes
proof: Strategy._initiateLSTWithdrawal builds uint256[] requestIds from IQueue.requestWithdrawals and returns abi.encode(requestIds) at src/Strategy.sol:97-99; Strategy._claimLSTWithdrawal reads abi.decode(_claimData, (uint256)) and passes that to IQueue.claimWithdrawal at src/Strategy.sol:104-108; a one-element uint256[] ABI blob begins with offset 0x20, so claimLSTWithdrawal(raw returnData) decodes requestId = 32 before touching the real element; the repo test has to decode returnData as uint256[] and re-encode requestIds[0] before claim at src/test/WithdrawalQueue.t.sol:72-80; pendingRedemptions blocks reports at src/BaseLSTAccumulator.sol:147 and is only reduced after a successful claim at src/BaseLSTAccumulator.sol:269-271
description: The public queue request return value is not directly consumable by the matching public claim function, so documented/naive claim-data handoff can claim the wrong request id or revert and leave reports blocked.
fix: Make both sides use one shape, either return abi.encode(requestIds[0]) for the one-request path or decode uint256[] in _claimLSTWithdrawal and claim the expected id(s).

## Leads

LEAD | contract: Strategy4626 | function: _stake | bug_class: zero-amount-restake-asymmetry | group_key: Strategy4626 | _stake | zero-amount-restake-asymmetry
pair_or_branch: Strategy._stake(0) vs Strategy4626._stake(0), and manualRedeem/manualUnwrap vs keeper report/tend
asymmetry: the base Strategy returns immediately on _stake(0), but Strategy4626._stake calls super._stake(0) and then still wraps every loose stETH and deposits every loose wstETH into the vault
code_smells: Strategy4626._stake wraps balanceOfLST() and deposits balanceOfWstETH() after super._stake(_amount), without requiring _amount > 0, at src/Strategy4626.sol:29-41; BaseLSTAccumulator._harvestAndReport always calls _stake(Math.min(balanceOfAsset(), availableDepositLimit(address(this)))) at src/BaseLSTAccumulator.sol:146-155, so a report with zero idle/capacity still invokes Strategy4626._stake(0); manualRedeem/manualUnwrap intentionally create loose wstETH/stETH at src/Strategy4626.sol:103-116
description: A keeper report/tend can rewrap and redeposit stETH/wstETH that emergency roles manually freed, even when no new WETH is being staked and even when capacity controls return zero; this looks like an automated path undoing a manual unwind, but exploitability depends on keeper timing and intended ops sequencing.

LEAD | contract: Strategy4626 | function: emergencyWithdraw | bug_class: emergency-unwind-missing-vault-layer | group_key: Strategy4626 | emergencyWithdraw | emergency-unwind-missing-vault-layer
pair_or_branch: automated shutdownWithdraw/emergencyWithdraw vs manualRedeem/manualUnwrap/manualSwapToAsset
asymmetry: automated emergency withdrawal only considers direct stETH, while the Strategy4626 value path and manual recovery functions include wstETH and vault shares
code_smells: TokenizedStrategy.emergencyWithdraw calls shutdownWithdraw at lib/tokenized-strategy/src/TokenizedStrategy.sol:1356-1363, BaseStrategy.shutdownWithdraw dispatches _emergencyWithdraw at lib/tokenized-strategy/src/BaseStrategy.sol:438-439, and BaseLSTAccumulator._emergencyWithdraw returns immediately when balanceOfLST() is zero at src/BaseLSTAccumulator.sol:158-162; Strategy4626 values vault exposure in valueOfLST at src/Strategy4626.sol:74 and provides manualRedeem/manualUnwrap at src/Strategy4626.sol:103-116, but does not override _emergencyWithdraw
description: For a Strategy4626 instance whose assets are in the intended wstETH vault position, shutdown emergencyWithdraw can free no WETH while the manual path can, leaving the inherited emergency path incomplete rather than directly exploitable.
