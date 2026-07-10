# steth-accumulator-strategy Threat Model

## Overview

This repository implements Yearn V3 TokenizedStrategy contracts for accumulating stETH from WETH. The primary runtime code is Solidity under `src/`, with deploy scripts under `script/`. The deployed strategy accepts WETH as its accounting asset, stakes or swaps into stETH, optionally wraps and deposits stETH into a downstream ERC4626 vault, and exposes management and keeper operations for redemptions, manual swaps, emergency actions, and reporting.

The primary production surfaces are:

- `src/BaseLSTAccumulator.sol`: shared accounting, deposit gating, report accounting, keeper/management operations, pending redemption tracking, manual stake/swap/withdraw flows, and emergency withdrawal hooks.
- `src/Strategy.sol`: stETH-specific route selection through Lido staking or the Curve stETH/ETH pool, Lido withdrawal queue initiation/claiming, referral configuration, and emergency batch claims.
- `src/Strategy4626.sol`: ERC4626 integration around wstETH, including wrapping/unwrapping, vault deposit/redeem flows, and max-deposit bounded availability.
- `src/Strategy4626Factory.sol`: repeatable deployment of `Strategy4626` instances and initial role/fee/unlock configuration.
- `src/periphery/StrategyAprOracle.sol`: a simple APR oracle used by periphery consumers to estimate expected strategy APR.
- `script/*.s.sol`: operational deployment scripts that encode role addresses, asset/vault constants, and post-deploy setter calls.

Tests under `src/test/**`, mocks, build/cache output, vendored dependencies under `lib/**`, prior audit artifacts under `.audit/**` and `x-ray/**`, and scanner/cached analysis are not production scan input. Vendored dependencies and tests may still be consulted later only to understand inherited APIs or to execute verification.

## Threat Model, Trust Boundaries, and Assumptions

The main assets are deposited WETH, stETH/wstETH balances, ERC4626 vault shares, pending Lido withdrawal claims, Yearn strategy shares, and privileged role authority. Correctness depends on preserving asset/share accounting, not over-reporting `estimatedTotalAssets`, avoiding unbounded loss realization during reports, and ensuring that only authorized operators can change risk parameters or move assets through manual routes.

The important trust boundaries are:

- Depositors and vault allocators are outside the strategy's operator boundary. They can call standard TokenizedStrategy ERC4626 entrypoints through the inherited Yearn implementation, subject to `availableDepositLimit`, `availableWithdrawLimit`, and TokenizedStrategy controls.
- Management is trusted to set deposit limits, open deposits, allowlists, report buffer, staking/tending thresholds, referral address, factory role defaults, and manual unwind parameters. Management mistakes can cause loss, stuck accounting, or adverse execution but are privileged actions.
- Keepers are trusted to call report/tend and `claimLSTWithdrawal` when redemptions mature. They should not be able to bypass management-only fund movement, but malicious or unavailable keepers can affect timing and accounting freshness.
- Emergency authorized accounts are trusted for emergency withdrawal, manual Lido claim hints, ERC4626 redeem, and unwrap operations. These actions are sensitive because they can change liquid balances and pending redemption state.
- External protocols are not controlled by this repository. Lido stETH, the Lido withdrawal queue, Curve stETH/ETH pool, WETH, wstETH, and downstream ERC4626 vaults supply balances, rates, redemptions, swaps, and callback-free token behavior assumed by the strategy.
- Deployment scripts are operator-controlled. Hardcoded role and asset/vault constants are not attacker-controlled at runtime but can be deployment footguns if copied or broadcast without review.

Attacker-controlled inputs include deposit/withdraw amounts through inherited ERC4626 strategy entrypoints when deposits are open or an address is allowed, public timing around Curve pricing and Lido queue state, gas/basefee conditions that affect tend triggering, donation or direct token transfers to the strategy, and any externally observable opportunity to manipulate Curve spot output before `_stake` or `_swapLSTToAsset`. Operator-controlled inputs include management/keeper/emergency calls, `_minOut` values, report buffers, deposit gates, redemption amounts, claim data, and factory role settings. Developer-controlled inputs include deployment constants, chosen downstream ERC4626 vault addresses, dependency versions, and test/fork configuration.

Core assumptions for severity evaluation:

- Yearn TokenizedStrategy and periphery base contracts are relied on for role checks, share accounting, report mechanics, and health-check behavior. The scan should inspect first-party integration points but treat vendored dependency internals as out of scope unless a first-party call relies on a specific inherited behavior.
- WETH, stETH, wstETH, and the canonical Lido/Curve contracts are assumed to be honest but market-dependent. Their rates, liquidity, and queue delays may be adverse without being contract exploits.
- Management, keeper, and emergency roles are trusted but not omnipotent for severity calibration: missing access control on sensitive operations is critical/high, while a harmful action that already requires management is generally lower unless it creates an unexpected loss path or violates Yearn operational assumptions.
- ERC4626 vaults used with `Strategy4626` must actually have wstETH as `asset()`. Other vault properties such as max deposit, preview/redeem rounding, share liquidity, or withdrawal constraints still matter to safety.

## Attack Surface, Mitigations, and Attacker Stories

The highest-value attack surfaces are the token-flow and accounting seams:

- `_deployFunds`, `_harvestAndReport`, `_tend`, `manualStake`, and `_stake` convert WETH to stETH through Lido or Curve. Relevant bug classes include route-manipulation losses, wrong min-out assumptions, unexpected ETH balances, stale or manipulated Curve quotes, and staking-paused handling.
- `_freeFunds`, `availableWithdrawLimit`, `manualSwapToAsset`, `_swapLSTToAsset`, `_emergencyWithdraw`, and ERC4626 redeem/unwrap paths determine whether withdrawals and emergency actions can recover liquid WETH without over-reporting value or ignoring slippage.
- `initiateLSTWithdrawal`, `claimLSTWithdrawal`, `manualClaimWithdrawals`, and `clearPendingRedemptions` track asynchronous Lido redemptions. Relevant bug classes include malformed claim data, mismatched request accounting, incorrect pending-redemption decrementing, stuck reports, and privileged reset paths that crystallize losses unexpectedly.
- `Strategy4626._freeStETH` crosses stETH, wstETH, and downstream ERC4626 vault unit domains. Rounding, `previewWithdraw`, `maxRedeem`, and redeem return values are security-relevant because they determine whether enough stETH is available before swaps or Lido withdrawal requests.
- `Strategy4626Factory.newStrategy4626` deploys strategies for arbitrary vault addresses subject to the constructor `asset()` check and stores a one-strategy-per-vault mapping. Relevant bugs include duplicate-deployment bypass, incorrect role propagation, unaccepted management, unsafe role updates, and false positives from `isDeployedStrategy`.
- `StrategyAprOracle.aprAfterDebtChange` is a periphery input to debt allocation. Incorrect APR reporting is unlikely to directly steal funds from this contract, but it can mislead allocators if treated as production-grade instead of a static placeholder.
- Deployment scripts encode privileged addresses and setup sequences. Misconfigured roles, missing management acceptance, missing keeper/emergency assignment, or deploying direct `Strategy4626` without applying intended setters can produce operational risk.

Existing controls that affect severity include:

- `BaseLSTAccumulator` gates deposits through `openDeposits`, an allowlist, and `depositLimit`.
- Manual stake, manual swap, redemption initiation, parameter setters, and factory address updates are management-gated.
- Lido claim and manual claim helpers are keeper or emergency authorized rather than public.
- `availableWithdrawLimit` only advertises liquid asset balance, avoiding automatic unstaking in normal withdrawals.
- `_harvestAndReport` refuses to report while `pendingRedemptions` is nonzero, reducing the chance of silently reporting through unsettled asynchronous withdrawals.
- `Strategy._depositLimit` disables new deposits when Lido staking is paused.
- Curve swaps use a caller-provided or 1:1 minimum output depending on route, making slippage assumptions explicit.
- `Strategy4626` checks the downstream ERC4626 vault asset is canonical wstETH.
- `Strategy4626Factory` tracks `deployments[_vault]` and reverts duplicate vault deployments.

Realistic attacker stories include manipulating Curve spot state around staking or unwind routes, donating tokens or ETH to alter balances and reports, using public deposit/withdraw timing to exploit rounding or stale limits, exploiting an incorrectly trusted ERC4626 vault integration, causing keeper/report liveness failures around pending redemptions, and abusing any missing role check on manual fund movement. Out-of-scope or lower-priority stories include compromising management keys, malicious changes to vendored Yearn/OpenZeppelin code outside first-party usage, or generic fork/test-only failures without a production call path.

## Severity Calibration (Critical, High, Medium, Low)

Critical severity is appropriate for first-party bugs that let an untrusted caller drain strategy assets, mint/redeem shares against materially false accounting, bypass role controls on privileged fund movement, or force permanent loss of a large fraction of managed funds in a realistic production configuration. Examples include public access to a swap/withdrawal path that sends assets out, an accounting bug that lets deposits mint shares too cheaply and withdraw valuable assets, or a unit conversion bug that causes large over-reporting exploitable by depositors.

High severity is appropriate for realistic loss, insolvency, or severe stuck-funds paths that require plausible market conditions, a keeper/report flow, or a bounded operator action that violates expected safety guarantees. Examples include manipulable Curve route selection causing repeated loss during permissionless reports/tends, incorrect `pendingRedemptions` handling that blocks reporting or hides unresolved redemptions, or ERC4626 rounding/redeem logic that prevents required stETH availability while still reporting it as assets.

Medium severity is appropriate for constrained value loss, significant operational footguns, misleading allocator signals, or griefing that affects availability/accounting but does not directly enable untrusted theft. Examples include unsafe default deployment parameters, APR oracle values that misallocate debt if used in production, overly permissive deposit opening assumptions, or keeper-triggerable timing that delays claims/reports without extracting funds.

Low severity is appropriate for defense-in-depth issues, minor configurability risks, event/accounting clarity gaps, and privileged-only behavior that is clearly within the trusted role model. Examples include missing zero-address validation for role defaults, confusing deployment log output, stale comments, or manual emergency paths whose loss risk is documented and management-gated.
