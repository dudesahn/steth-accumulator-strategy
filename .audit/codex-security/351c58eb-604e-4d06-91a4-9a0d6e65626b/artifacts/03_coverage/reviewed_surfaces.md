# Reviewed Surfaces

Scan id: `351c58eb-604e-4d06-91a4-9a0d6e65626b`

| Surface | Risk Area | Outcome | Notes |
| --- | --- | --- | --- |
| Strategy4626 ERC4626 integration | Token-flow and downstream vault capacity | Reported | Loose stETH/wstETH donation can make `_stake` exceed live downstream `maxDeposit`; final finding CS-351C58EB-003. |
| BaseLSTAccumulator staking control | Keeper versus management trust boundary | Reported | Keeper report and tend paths bypass the management `stakeAsset` switch; final finding CS-351C58EB-002. |
| Lido withdrawal queue initiation and claim data | Asynchronous redemption accounting | Rejected | ABI mismatch is validated, but final policy suppressed it because the path is management/keeper workflow-only and existing tests use the safe scalar re-encoding. |
| Deployment scripts and factory role setup | Deployment role configuration | Rejected | `Deploy4626.s.sol` omits direct post-deploy role setup, but the precondition is trusted deployer misuse; factory and non-4626 deploy paths apply setup. |
| StrategyAprOracle APR output | Allocator signal integrity | Rejected | Constant 4 percent APR behavior is confirmed, but no production deploy or registration path was found and the constructor labels it an example oracle. |
| Strategy4626Factory deployment uniqueness and role propagation | Factory deployment provenance | No issue found | One strategy per vault mapping, role propagation, and management-gated address updates were reviewed with no surviving issue. |
| Curve, Lido staking, and stETH-to-WETH swap routes | External protocol routing and slippage | No issue found | Curve staking path uses a 1:1 minimum when selected, manual unwind slippage is caller-controlled, and no untrusted forced unwind path survived. |
| RCE, injection, deserialization, SSRF, file, and web sink families | Generic application security sink classes | Not applicable | The production Solidity/deploy surface exposes no process, query, parser, filesystem, HTTP, redirect, template, upload, or deserialization sinks. |
