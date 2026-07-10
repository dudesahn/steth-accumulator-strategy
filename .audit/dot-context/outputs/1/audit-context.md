# Dot-Context Audit Context

## Scope

In scope as target code:
- `src/BaseLSTAccumulator.sol`
- `src/Strategy.sol`
- `src/Strategy4626.sol`
- `src/Strategy4626Factory.sol`
- `src/periphery/StrategyAprOracle.sol`
- `src/interfaces/*.sol`

Supporting context only:
- `src/test/**/*.sol`
- `script/**/*.sol`
- `foundry.toml`
- `Makefile`
- `README.md`
- external dependencies in `lib/`

Out of scope as target code:
- prior audit outputs, scratchpads, generated reports, PoCs, notes, `.audit`, `.context`, cache directories, broadcast outputs, and previous findings.

## Protocol Classification

The repo is an EVM Solidity Foundry project implementing a Yearn V3 TokenizedStrategy for WETH-to-stETH accumulation. The core strategy can stake WETH into Lido stETH, optionally route ETH through the Curve ETH/stETH pool when Curve quotes better than 1:1, manually swap stETH back to WETH, initiate and claim Lido withdrawal queue redemptions, and wrap strategy exposure into an ERC4626 wstETH vault variant.

The primary dot-context checklist is Solidity yield/strategy-vault security, with additional attention to staking/LST integrations, Curve slippage, ERC4626 rounding/accounting, withdrawal queue accounting, role restrictions, and emergency/manual controls.

## Initial Threat Model

Primary assets at risk:
- WETH strategy asset deposits
- stETH and wstETH balances held by the strategy
- ERC4626 vault shares held by `Strategy4626`
- pending Lido withdrawal queue claims

Primary actors:
- permissionless depositors and withdrawers through Yearn TokenizedStrategy flows
- management, keeper, emergency roles
- MEV actors around Curve swaps and Lido queue timing
- external protocol dependencies: Lido stETH, wstETH, withdrawal queue, Curve ETH/stETH, ERC4626 vaults

Key invariants to check:
- estimated total assets should include all liquid and queued value without double counting
- pending redemptions should track only queued/unclaimed LST value and not be stale after claims
- deposit gating must not accidentally bypass allowlists or asset limits
- slippage-sensitive swaps must be bounded by caller-provided or protocol-enforced minimums
- external protocols cannot cause permanent lockup or unbounded loss under normal role assumptions

## Run Notes

This run maps dot-context's default `.context/outputs/N` convention to `.audit/dot-context/outputs/1` per user instruction. No `.context` compatibility shim has been created.

## Final Finding Summary

Validated Medium findings:
- M-01: Factory-created Strategy4626 deployments disable profit locking, allowing pre-report deposits to capture prior yield.
- M-02: Manual LST-to-WETH swaps expose discounted liquidity before accounting records the loss.
- M-03: Post-shutdown reports can re-stake emergency-withdrawn WETH and block withdrawals again.
- M-04: Strategy4626 emergencyWithdraw does not materially free the normal ERC4626-held position.

Validated Low findings:
- L-01: Lido withdrawal initiation returns an encoded array but keeper claim decodes a scalar request id.
- L-02: StrategyAprOracle returns a fixed APR for every strategy and debt delta.

Durable PoCs:
- `FactoryProfitUnlockDilutionPoC.t.sol`
- `ManualSwapStaleAccountingPoC.t.sol`
- `ShutdownReportRedeployPoC.t.sol`
- `Strategy4626EmergencyNoopPoC.t.sol`

Final baseline after temporary PoC mirrors were removed:
- `env ETH_RPC_URL=https://ethereum.publicnode.com forge test -vv --fork-url https://ethereum.publicnode.com`
- 46 tests passed, 0 failed, 0 skipped.
