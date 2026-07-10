# Attack Path Analysis: CS-351C58EB-002

## Title

stakeAsset disable switch is bypassed by keeper report and tend paths

## Attack Path

1. Management calls `setStakeAsset(false)` to disable automatic staking of idle WETH.
2. `_deployFunds` honors `stakeAsset` and does not stake new deposits while the flag is disabled.
3. A keeper can still trigger `report` or `tend`; both paths call `_stake` without checking `stakeAsset`.
4. Idle WETH is converted to stETH or routed onward by the concrete strategy despite the management risk switch.

## Facts

- Service mapping: Yearn V3 strategy reporting and tending.
- Entry points: inherited keeper report/tend callbacks reach `_harvestAndReport` and `_tend`.
- Trust boundary: keepers are privileged, but lower-trust than management for risk-parameter changes.
- Reachability: a keeper can trigger the path after management disables staking; the behavior was confirmed by the focused fork test `test_harvestStakesBypassesStakeAssetFlag`.
- Existing controls: report staking is bounded by `availableDepositLimit`; tend staking uses the idle amount passed by the inherited strategy.

## Counterevidence

The path is keeper-gated and cannot be triggered by arbitrary depositors. There is also some design ambiguity: the comment on `stakeAsset` mentions deposits, while the setter comment mentions harvest. Those facts limit severity, but they do not defeat reportability because the flag is presented as the strategy's staking switch and management is the role authorized to set it.

## Severity Calibration

- Impact: medium. Keeper-triggered staking can reintroduce Lido or downstream vault exposure and reduce liquidity after management attempted to disable that risk.
- Likelihood: medium. The caller must be a keeper, but keeper report/tend is a normal production workflow.
- Matrix result: low.

## Final Policy Decision

`report`. Emit as a low-severity privilege-boundary/control-bypass finding.
