# Pashov Solidity Auditor Lane 6 - Periphery

commit: 521fff28ad978a37115be8995a1d631611fa1d3d
scope: BaseLSTAccumulator, Strategy, Strategy4626, Strategy4626Factory, StrategyAprOracle
specialty: StrategyAprOracle, factory deployment behavior, Yearn TokenizedStrategy/periphery interfaces, APR assumptions, ERC4626 adapter boundaries
result: 0 FINDING blocks, 4 LEAD blocks

## Mental Tool Markers

[Feynman: StrategyAprOracle]
This contract is a small answer box for allocators and interfaces. They ask, "if this strategy's debt changes by this much, what yearly return should I expect?" The answer is always 4%, no matter which strategy asks and no matter whether debt is added, removed, or unchanged. The fuzzy spot is that the comments describe a live estimate, but the implementation is a fixed illustrative number.

[Inversion: StrategyAprOracle.aprAfterDebtChange]
1. Call it with the real stETH accumulator at current debt and with `_delta = 0`; it returns `4e16`.
2. Call it with the same strategy and `_delta = int256(1_000_000 ether)`; it still returns `4e16`.
3. Call it with an unrelated address or a saturated downstream vault; it still returns `4e16` instead of rejecting or reflecting capacity.

[Feynman: Strategy4626Factory]
This contract is a public deployment desk. Anyone can hand it a vault address, and it builds one accumulator strategy for that vault. The new strategy starts with the factory in charge, the configured management address waiting to accept control, and configured keeper/emergency/fee settings copied from the factory at that moment.

[Inversion: Strategy4626Factory.newStrategy4626]
1. A random caller deploys for the intended Yearn wstETH vault before governance does; the caller gets no roles, but the one allowed deployment slot and event are consumed.
2. A random caller deploys for an exotic ERC4626 vault whose `asset()` is wstETH but whose conversion and redeem behavior are non-standard.
3. A random caller passes a vault whose `symbol()` reverts or burns gas; the call reverts before the strategy is created, affecting only that deployment attempt.

[Feynman: Strategy4626Factory.isDeployedStrategy]
This helper tries to answer whether a strategy came from this factory. It asks the candidate strategy which vault it uses, then checks whether that vault maps back to the candidate. The fuzzy spot is that the helper assumes the candidate is willing and able to answer `vault()`.

[Inversion: Strategy4626Factory.isDeployedStrategy]
1. Pass an EOA as `_strategy`; the helper's `vault()` call reverts instead of returning false.
2. Pass a contract whose `vault()` deliberately reverts; every caller of the helper reverts with it.
3. Pass a contract whose `vault()` returns a valid vault but is not the mapped strategy; the helper correctly returns false.

[Feynman: Strategy4626]
This contract puts the stETH accumulator behind a wstETH vault layer. When it receives WETH, it gets stETH, wraps it to wstETH, and deposits that wstETH into another ERC4626 vault. When it needs stETH back, it redeems vault shares, unwraps wstETH, and then uses the core stETH paths. The fuzzy spot is that it only checks the vault's asset, then trusts the vault's capacity, accounting, preview, and redemption answers.

[Inversion: Strategy4626 ERC4626 boundary]
1. Use a vault whose `asset()` is wstETH but whose `convertToAssets()` overstates redeemable wstETH; reported LST value becomes inflated.
2. Use a vault whose `maxDeposit()` says capacity exists but `deposit()` later reverts or mints unusable shares; deposits and harvest staking can fail.
3. Use a vault whose `previewWithdraw()` and `redeem()` disagree at the edge; `_freeStETH()` may unwrap less or more loose wstETH than the requested stETH amount.

## Findings

No FINDING blocks emitted. I did not identify a concrete, unguarded exploit path in the periphery lane that met the required proof bar.

## Leads

LEAD | contract: StrategyAprOracle | function: aprAfterDebtChange | bug_class: constant-apr-ignores-debt-and-strategy | group_key: StrategyAprOracle | aprAfterDebtChange | constant-apr-ignores-debt-and-strategy
code_smells: `src/periphery/StrategyAprOracle.sol:28-32` returns `4e16` for every `_strategy` and `_delta`; `lib/tokenized-strategy-periphery/src/AprOracle/AprOracle.sol:61-84` forwards strategy-specific `_debtChange` to configured custom oracles; `lib/tokenized-strategy-periphery/README.md:87-89` says custom APR oracles are meant to return expected APY given `debtChange`; `src/test/Oracle.t.sol:26-35` leaves the negative/positive debt-change sensitivity checks commented out.
description: If this example oracle is configured as a live strategy oracle, allocators or off-chain routers can receive the same 4% APR for zero, large positive, large negative, saturated, or unrelated strategy inputs; this remains a LEAD because setting the oracle is authorized upstream and I did not trace a permissionless allocator action that forces users onto the stale value.

LEAD | contract: Strategy4626Factory | function: newStrategy4626 | bug_class: permissionless-one-shot-deployment-slot | group_key: Strategy4626Factory | newStrategy4626 | permissionless-one-shot-deployment-slot
code_smells: `src/Strategy4626Factory.sol:43-69` lets any caller consume `deployments[_vault]` and emit `NewStrategy4626` for a vault with no reset path; the only vault identity check is the `Strategy4626` constructor's `asset() == wstETH` requirement; `src/test/Strategy4626Factory.t.sol:31-46` confirms the caller does not receive roles because the factory stays management until the configured pending management accepts.
description: A third party can front-run or squat the single factory slot/event for any wstETH ERC4626 vault, which may confuse factory-based discovery or deployment operations; this remains a LEAD because the caller cannot steal strategy roles and the configured management can still accept the deployed strategy if it is legitimate.

LEAD | contract: Strategy4626 | function: constructor/availableDepositLimit/valueOfWstETH/_freeStETH | bug_class: erc4626-adapter-trust-boundary | group_key: Strategy4626 | ERC4626 vault boundary | erc4626-adapter-trust-boundary
code_smells: `src/Strategy4626.sol:20-23` only validates that the external vault asset is wstETH, while later logic trusts `vault.maxDeposit`, `vault.convertToAssets`, `vault.previewWithdraw`, `vault.maxRedeem`, `vault.deposit`, and `vault.redeem` for deposit capacity, accounting, and unwind behavior; the factory allows arbitrary `_vault` values that satisfy this asset check.
description: A non-standard or malicious wstETH ERC4626 vault could inflate reported LST value, overstate capacity, or make unwinds fail after integration; this remains a LEAD because user entry still depends on management accepting/opening/configuring the strategy and I did not prove a forced-user path into an attacker-selected vault.

LEAD | contract: Strategy4626Factory | function: isDeployedStrategy | bug_class: view-helper-reverts-on-arbitrary-input | group_key: Strategy4626Factory | isDeployedStrategy | view-helper-reverts-on-arbitrary-input
code_smells: `src/Strategy4626Factory.sol:85-88` casts any `_strategy` to `IStrategy4626Interface` and calls `vault()` before checking the mapping, so EOAs, unrelated contracts, or contracts with reverting `vault()` implementations make the helper revert instead of returning false.
description: On-chain or off-chain consumers that call this helper over untrusted candidate addresses can be griefed by non-conforming inputs; this remains a LEAD because no in-scope contract consumes `isDeployedStrategy` in a state-changing path.

## Disqualified Trails

- Factory role theft via permissionless deployment: disproven by the factory setter sequence and tests. The deployed strategy's management is the factory, pending management is the configured `management`, and the external deployer receives no keeper, management, emergency, or fee role.
- Zero-address factory defaults: `setAddresses` can make future deployments revert or remove factory control, but this is a management-only self-configuration hazard, not an untrusted attack path under the shared rules.
- Confirmed APR exploit: not proven. The fixed APR is materially unsafe as production oracle logic, but the upstream `AprOracle.setOracle` path is authorized by governance or strategy management.
