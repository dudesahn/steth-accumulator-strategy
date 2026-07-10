# Repository Coverage Ledger

Scan id: `351c58eb-604e-4d06-91a4-9a0d6e65626b`

Scope: production code only. In-scope worklist is 16 first-party files under `src/**` and `script/**`, excluding `src/test/**`, mocks, `lib/**` except directly relied-on API semantics, build/cache/broadcast output, `.audit/**`, `x-ray/**`, scanner reports, and cached analysis.

## Worklist Closure

| row id | file(s) | area | disposition | candidate ids | evidence |
| --- | --- | --- | --- | --- | --- |
| WL-001 | `src/BaseLSTAccumulator.sol` | base strategy | reportable | `CS-351C58EB-002` | Full-file receipt in `shard_01_base.md`; nine high-impact rows closed. |
| WL-002 | `src/Strategy.sol` | stETH strategy | reportable | `CS-351C58EB-001` | Full-file receipt in `shard_02_strategy.md`; Lido claim-data mismatch found. |
| WL-003 | `src/Strategy4626.sol` | ERC4626 strategy | reportable | `CS-351C58EB-003` | Full-file receipt in `shard_03_4626_factory.md`; maxDeposit donation griefing candidate found. |
| WL-004 | `src/Strategy4626Factory.sol` | factory | suppressed | none | Full-file receipt in `shard_03_4626_factory.md`; duplicate, role propagation, setAddresses, and provenance rows closed. |
| WL-005 | `src/periphery/StrategyAprOracle.sol` | periphery oracle | deferred | `CS-351C58EB-005` | Full-file receipt in `shard_05_interfaces_oracle.md`; static APR row needs production registration evidence. |
| WL-006 | strategy interfaces | interfaces | reportable | `CS-351C58EB-001` | `IBaseLSTAccumulator`, `IStrategyInterface`, and `IStrategy4626Interface` read in full; interface handoff row opened, emergency/manual rows suppressed. |
| WL-007 | protocol interfaces | interfaces | reportable | `CS-351C58EB-001` | `ICurve`, `IQueue`, `ISTETH`, `IWETH`, and `IWstETH` read in full; IQueue ABI shape row opened, other unit/signature rows suppressed or not applicable. |
| WL-008 | `script/Deploy.s.sol` | deployment | suppressed | none | Full-file receipt in `shard_06_deploy.md`; direct Strategy setup applies logged role values. |
| WL-009 | `script/Deploy4626.s.sol` | deployment | reportable | `CS-351C58EB-004` | Full-file receipt in `shard_06_deploy.md`; direct Strategy4626 setup mismatch found. |
| WL-010 | `script/Deploy4626Factory.s.sol` | deployment | suppressed | none | Full-file receipt in `shard_06_deploy.md`; factory role defaults are constructor inputs. |

## High-Impact Family Closure

| row id | family / boundary | files checked | disposition | candidate ids | evidence summary |
| --- | --- | --- | --- | --- | --- |
| HIF-001 | Privileged access control on management, keeper, and emergency operations | `src/BaseLSTAccumulator.sol`, `src/Strategy.sol`, `src/Strategy4626.sol`, interfaces, factory | suppressed | none | Sensitive setters and manual fund movement resolve to `onlyManagement`, `onlyKeepers`, or `onlyEmergencyAuthorized`; no untrusted public caller reaches them. |
| HIF-002 | Lido withdrawal queue request/claim accounting | `src/Strategy.sol`, `src/interfaces/IQueue.sol`, `src/BaseLSTAccumulator.sol`, interfaces | reportable | `CS-351C58EB-001` | `requestWithdrawals` returns `uint256[]`; initiation returns `abi.encode(requestIds)`; claim decodes scalar `uint256`; pending redemptions can remain nonzero. |
| HIF-003 | `stakeAsset` staking disable control | `src/BaseLSTAccumulator.sol`, `src/Strategy.sol`, `src/Strategy4626.sol` | reportable | `CS-351C58EB-002` | `_deployFunds` checks `stakeAsset`; `_harvestAndReport` and `_tend` call `_stake` without the same guard. |
| HIF-004 | ERC4626 `maxDeposit` and loose-balance deposit amount | `src/Strategy4626.sol`, `src/BaseLSTAccumulator.sol`, IERC4626 API | reportable | `CS-351C58EB-003` | `availableDepositLimit` caps new WETH amount but `_stake` deposits all loose wstETH, including donations, into a potentially bounded vault. |
| HIF-005 | ERC4626/wstETH unit conversion and freeStETH rounding | `src/Strategy4626.sol`, protocol interfaces | suppressed | none | Constructor checks vault asset is wstETH; value functions convert wstETH to stETH; `_freeStETH` adds rounding buffer and clamps to maxRedeem. |
| HIF-006 | Curve/Lido staking and stETH-to-WETH slippage | `src/Strategy.sol`, `src/interfaces/ICurve.sol`, `src/interfaces/ISTETH.sol` | suppressed | none | Curve staking uses min 1:1 when selected; manual unstake route uses caller-provided minOut; emergency zero-minOut is privileged shutdown behavior. |
| HIF-007 | Liquid withdrawal availability and no automatic unstaking | `src/BaseLSTAccumulator.sol`, TokenizedStrategy API | suppressed | none | Withdraw availability is liquid WETH only; inherited max-loss checks apply; no untrusted forced-unstake or drain path found. |
| HIF-008 | Report accounting, donation, and reportBuffer effects | `src/BaseLSTAccumulator.sol`, BaseHealthCheck API | suppressed | none | Reports are keeper-gated, block on pending redemptions, and use discounted LST valuation; reportBuffer misconfiguration is management-only. |
| HIF-009 | Deployment role/default configuration | `script/*.s.sol`, `src/Strategy4626Factory.sol`, TokenizedStrategy API | reportable | `CS-351C58EB-004` | `Deploy4626.s.sol` logs intended management but never calls setters; direct Strategy and factory paths have setup controls. |
| HIF-010 | APR oracle semantics and allocator signal | `src/periphery/StrategyAprOracle.sol`, AprOracle API | deferred | `CS-351C58EB-005` | Oracle returns static 4e16 and ignores `_strategy`/`_delta`; no in-repo registration or deployment evidence found. |
| HIF-011 | Factory deployment uniqueness, role propagation, and provenance | `src/Strategy4626Factory.sol` | suppressed | none | One strategy per vault mapping, role defaults applied after construction, and `setAddresses` is management-gated. |
| HIF-012 | RCE/injection/deserialization/SSRF/path/file/web families | all production Solidity/deploy files | not_applicable | none | Solidity strategy/deploy scripts expose no process, query, parser, filesystem, HTTP, redirect, template, upload, or deserialization sinks in production code. |

No advisory, CVE, GHSA, release, or package-version seeds were provided, so no `seed_research.md` was required for discovery.
