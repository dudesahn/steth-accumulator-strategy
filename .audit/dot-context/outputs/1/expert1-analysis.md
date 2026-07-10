# Expert 1 Analysis

## Scope and Methods

Persona: Primary Smart Contract Auditor.

Target scope reviewed:
- `src/BaseLSTAccumulator.sol`
- `src/Strategy.sol`
- `src/Strategy4626.sol`
- `src/Strategy4626Factory.sol`
- `src/periphery/StrategyAprOracle.sol`
- `src/interfaces/*.sol`

Explicitly out of target scope: `src/test/**`, `.audit`, `.context`, `x-ray`, `broadcast`, `cache`, generated artifacts, prior findings, and scratchpads.

Supporting context read but not treated as target code:
- `README.md`, `foundry.toml`, `Makefile`, deployment scripts, selected tests.
- Yearn `TokenizedStrategy`, `BaseStrategy`, and `BaseHealthCheck` dependency code to understand callback and role behavior.

Dot-context workflow files read before audit:
- `/Users/dudesahn/Documents/GitHub/codex/skill-research/dot-context/skills/smart-contract-audit/SKILL.md`
- `/Users/dudesahn/Documents/GitHub/codex/skill-research/dot-context/skills/smart-contract-audit/multi-expert.md`
- `/Users/dudesahn/Documents/GitHub/codex/skill-research/dot-context/skills/smart-contract-audit/solidity-checks.md`
- `/Users/dudesahn/Documents/GitHub/codex/skill-research/dot-context/skills/smart-contract-audit/finding-format.md`
- `/Users/dudesahn/Documents/GitHub/codex/skill-research/dot-context/skills/smart-contract-audit/reference/solidity/protocols/yield.md`

Methods used:
- Enumerated in-scope Solidity files with `rg --files -g 'src/**/*.sol' -g '!src/test/**'`.
- Line-numbered the in-scope contracts with `nl -ba`.
- Mapped fund flows across WETH -> ETH -> stETH -> wstETH -> ERC4626 vault, Lido withdrawal queue, Curve swaps, Yearn deposit/withdraw/report callbacks, and role-gated manual operations.
- Searched for external calls, Curve/Lido interactions, report/deposit/withdraw paths, pending redemption accounting, role gates, slippage parameters, ERC4626 conversions, and emergency paths.
- Did not run tests or builds because this lane was instructed to write only the assigned output file, and Foundry runs can update cache/build artifacts.

## Candidate Findings

### M-01 Existing users' accrued yield can be diluted by just-in-time deposits because factory deployments disable profit locking

Severity: Medium
Confidence: Medium

Locations:
- `src/Strategy4626Factory.sol:62-64`
- `src/BaseLSTAccumulator.sol:146-155`
- `src/BaseLSTAccumulator.sol:177-179`
- `src/Strategy4626.sol:69-75`
- Supporting dependency context: `lib/tokenized-strategy/src/TokenizedStrategy.sol:487-510`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:837-851`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:1164-1181`, `lib/tokenized-strategy/src/TokenizedStrategy.sol:1245-1247`

Description:
`Strategy4626Factory.newStrategy4626()` explicitly calls `setProfitMaxUnlockTime(0)` on every factory-created strategy. The underlying TokenizedStrategy default is a 10-day profit unlock period, but with this factory setting reported profit is not locked into strategy-owned shares. The report path then updates `S.totalAssets` immediately after `_harvestAndReport()` returns the real asset value.

Deposits mint shares against the last reported `totalAssets`, not against the current unreported value of the stETH, wstETH, and ERC4626 vault positions. This creates a just-in-time deposit window: if stETH rebases, the wrapped vault accrues yield, or value otherwise accumulates between reports, a depositor can enter immediately before the keeper report and receive shares priced as if that accrued yield did not exist. When the report runs, the profit is immediately reflected in PPS instead of being time-unlocked to existing holders.

Attack path:
1. Existing users have deposited into a factory-created `Strategy4626`, and deposits are open.
2. The strategy accrues unreported profit in stETH, wstETH, or the ERC4626 vault since the last report.
3. An attacker observes or predicts an upcoming keeper report and deposits a large amount before it.
4. The attacker receives shares using stale `TokenizedStrategy.totalAssets`.
5. The keeper calls `report()`, `_harvestAndReport()` includes the accrued LST/vault value, and profit is immediately unlocked because `profitMaxUnlockTime == 0`.
6. The attacker now owns a pro-rata share of profit that economically belonged to pre-existing depositors.
7. The attacker exits once WETH liquidity is made idle through normal management operations, or immediately if sufficient idle WETH exists.

Economic meaning:
This is not an instant principal drain. It is economically meaningful as yield theft/dilution. Approximate attacker gain is:

`attacker_deposit / (existing_assets + attacker_deposit) * unreported_profit - costs`

The loss is borne by existing holders as reduced share of accrued yield. Exploitability depends on open deposits, report cadence, amount of unreported profit, attacker capital, and ability to exit after liquidity is made available. It is less severe than direct fund theft because the strategy is intentionally illiquid by default and `availableWithdrawLimit()` restricts normal exits to idle WETH. It becomes more meaningful with large TVL, predictable keeper reports, long intervals between reports, or pending Lido withdrawals that block reports while deposits remain open.

What verification would prove or disprove it:
- Prove: On a fork or deterministic mock, deploy through `Strategy4626Factory`, accept management, open deposits, let user A deposit, create unreported profit by donating/accruing stETH or increasing the ERC4626 vault's assets, let attacker B deposit before report, run `report()`, then compare B's post-report `convertToAssets(balanceOf(B))` against a baseline where B deposited after report.
- Prove economic extraction: Make WETH idle using `manualSwapToAsset()` and show B can redeem more value than their fair share of post-deposit yield, with user A receiving less than in the no-B case.
- Disprove or downgrade: Show production intends deposits to remain closed around reports, management reports immediately before opening deposits, or `profitMaxUnlockTime` is reset to a non-zero period before any user deposits.

Suggested remediation:
- Do not set `profitMaxUnlockTime` to zero by default in the factory. Preserve the TokenizedStrategy default or set a non-zero unlock period appropriate for the expected report cadence.
- If instant unlock is intentional, enforce an operational guard: close deposits before reports with material unreported profit and reopen only after reporting.
- Add a regression test that demonstrates a pre-report depositor cannot capture prior accrued profit.

### L-02 Standard emergencyWithdraw does not unwind Strategy4626 vault positions when all exposure is wrapped

Severity: Low
Confidence: High

Locations:
- `src/Strategy4626.sol:29-42`
- `src/Strategy4626.sol:69-75`
- `src/Strategy4626.sol:103-115`
- `src/BaseLSTAccumulator.sol:158-163`
- `src/BaseLSTAccumulator.sol:185-187`
- Supporting dependency context: `lib/tokenized-strategy/src/TokenizedStrategy.sol:1356-1363`

Description:
Normal `Strategy4626` deposits call `super._stake()`, wrap resulting stETH into wstETH, and deposit all wstETH into the configured ERC4626 vault. The inherited `_emergencyWithdraw()` path, however, only checks loose `balanceOfLST()` and returns immediately if the strategy holds no raw stETH. It does not use `valueOfLST()`, redeem ERC4626 vault shares, or unwrap wstETH.

As a result, after a normal Strategy4626 deposit where the position is held primarily as ERC4626 vault shares, the standard Yearn `emergencyWithdraw()` callback can no-op even though the strategy still has substantial LST exposure.

Attack/failure path:
1. Users deposit WETH into `Strategy4626`.
2. The strategy stakes into stETH, wraps into wstETH, and deposits into the ERC4626 vault.
3. During an incident, emergency admin shuts down the strategy and calls TokenizedStrategy `emergencyWithdraw(amount)`.
4. The call reaches `BaseLSTAccumulator._emergencyWithdraw()`.
5. Because loose `balanceOfLST()` is zero, the function returns without freeing vault shares or WETH.

Economic meaning:
This is not an external attacker profit path, and it does not permanently lock funds because `manualRedeem()` and `manualUnwrap()` exist for emergency-authorized callers. It is still operationally meaningful: the standard emergency path does not do what Yearn operators would normally expect for the ERC4626 variant, potentially delaying recovery during a vault, Lido, or Curve incident. The severity is Low because a privileged multi-call sequence can recover funds if operators know to use it.

What verification would prove or disprove it:
- Prove: Deposit into `Strategy4626`, assert vault shares are non-zero and raw stETH is zero, shut down, call `emergencyWithdraw(type(uint256).max)`, and assert vault shares and WETH balance are unchanged.
- Prove mitigation path: Then call `manualRedeem()`, `manualUnwrap()`, and `emergencyWithdraw()` to show the privileged fallback sequence frees WETH.
- Disprove or downgrade: Show operational runbooks never rely on TokenizedStrategy `emergencyWithdraw()` for Strategy4626, or override `_emergencyWithdraw()` before deployment.

Suggested remediation:
- Override `_emergencyWithdraw()` in `Strategy4626` to call `_freeStETH(_amount)` before swapping to WETH.
- Use `valueOfLST()` rather than only `balanceOfLST()` when deciding whether an ERC4626-backed position exists.
- Keep the manual functions, but make the standard emergency callback capable of a best-effort unwind.

## Dismissed and False-Positive Notes

- Reentrancy: Deposits, withdrawals, reports, tends, and emergency withdrawals are guarded by TokenizedStrategy `nonReentrant`; strategy callbacks are `onlySelf`. I did not identify an externally reachable reentrancy path through WETH, Lido, Curve, or the ERC4626 vault integrations.
- First-depositor share inflation: TokenizedStrategy tracks `totalAssets` internally and mints shares from reported assets, so direct token donations do not immediately manipulate deposit conversions. Donations become reportable profit rather than direct pre-deposit PPS manipulation.
- Curve swap slippage: `_stake()` only uses Curve for ETH -> stETH when `get_dy` is greater than the input and sets min out to 1:1. stETH -> ETH swaps are management controlled and accept caller-supplied `_minOut`; emergency swap uses zero min out but is privileged. I did not classify this as a permissionless sandwich/fund-loss issue.
- Lido withdrawal queue accounting: `pendingRedemptions` blocks reports while queue requests are outstanding. Because only management can initiate withdrawals and management/emergency roles can clear or batch-claim, I did not classify this alone as an external exploit. It can, however, increase the stale-accounting window relevant to M-01 if deposits remain open.
- ERC4626 rounding in `_freeStETH()`: The code uses `previewWithdraw()` and adds two wei before unwrapping. I did not find a user-profitable rounding direction issue; likely impact is dust or partial liquidity handling.
- Access control: Management, keeper, and emergency functions route through TokenizedStrategy role checks. The factory is permissionless for deployment, but the deployer does not become strategy management.
- Factory zero-address and wrong-asset configuration: Constructors and `setAddresses()` are light on validation, but the direct impact is deployment misconfiguration or failed future deployments, not an external exploit against an initialized strategy.
- `setReportBuffer()` bounds: `reportBuffer > MAX_BPS` can underflow `estimatedTotalAssets()` and break deposits/reports, but this is management-only misconfiguration. I did not classify it as a security finding without an untrusted setter path.
- Raw ETH receiver: Anyone can send ETH to the strategy, but later swap/claim paths wrap the full ETH balance into WETH for the strategy. This is value-accretive rather than extractive.

--- END OF EXPERT 1 ANALYSIS ---
