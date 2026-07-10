# Invariant Map

> stETH Accumulator Strategy | 8 guards | 7 inferred | 1 not enforced on-chain

---

## 1. Enforced Guards (Reference)

Per-call preconditions. Heading IDs below (`G-N`) are anchor targets from x-ray.md attack surfaces.

#### G-1
`if (deployments[_vault] != address(0)) revert AlreadyDeployed(deployments[_vault])` · `src/Strategy4626Factory.sol:44` · one Strategy4626 deployment is allowed per ERC4626 vault.

#### G-2
`require(msg.sender == management, "!management")` · `src/Strategy4626Factory.sol:78` · only the current factory management address can rotate deployment roles.

#### G-3
`require(pendingRedemptions == 0, "Pending redemptions")` · `src/BaseLSTAccumulator.sol:147` · reports cannot record NAV while Lido queue redemptions are outstanding.

#### G-4
`require(_amount > 0, "!amount")` · `src/BaseLSTAccumulator.sol:243` · manual LST-to-asset swaps must operate on nonzero available LST value.

#### G-5
`require(_amount > 0, "!amount")` · `src/BaseLSTAccumulator.sol:252` · manual staking must operate on nonzero idle asset.

#### G-6
`require(_amount > 0, "!amount")` · `src/BaseLSTAccumulator.sol:261` · Lido withdrawal requests must be backed by nonzero LST value.

#### G-7
`require(IERC4626(_vault).asset() == address(wstETH), "wrong vault")` · `src/Strategy4626.sol:21` · Strategy4626 only integrates vaults whose accounting asset is wstETH.

#### G-8
`require(balanceOfLST() >= _amount, "!available")` · `src/Strategy4626.sol:51` · Lido queue requests only proceed after enough stETH has been freed from the wrapped/vault position.

---

## 2. Inferred Invariants (Single-Contract)

#### I-1

`Bound` · On-chain: **Yes**

> Deposits are limited to `_depositLimit()` only when deposits are open or the receiver is whitelisted.

**Derivation** - guard-lift: `if (openDeposits || allowed[_owner]) return _depositLimit(); return 0` at `src/BaseLSTAccumulator.sol:126-130`; write sites are `setOpenDeposits` and `setAllowed` at `src/BaseLSTAccumulator.sol:216-224`.

**If violated** - non-whitelisted addresses could enter when management intended a closed strategy.

#### I-2

`Bound` · On-chain: **Yes**

> Normal ERC4626 withdrawals are bounded by idle WETH, not by total WETH-equivalent LST value.

**Derivation** - guard-lift: `availableWithdrawLimit()` returns `balanceOfAsset()` at `src/BaseLSTAccumulator.sol:133-144`; TokenizedStrategy consumes this limit in `_maxWithdraw` / `_maxRedeem`.

**If violated** - users could request liquid exits against funds that are still in stETH, wstETH, or the external ERC4626 vault.

#### I-3

`StateMachine` · On-chain: **Yes**

> `pendingRedemptions > 0` blocks reports until keeper claim or management emergency clearing lowers the pending amount.

**Derivation** - edge: `pendingRedemptions += _amount` at `src/BaseLSTAccumulator.sol:262`; claim/clear edges at `src/BaseLSTAccumulator.sol:271` and `src/BaseLSTAccumulator.sol:280`; report guard at `src/BaseLSTAccumulator.sol:147`.

**If violated** - reports could mix queued-but-unclaimed Lido value into realized strategy accounting.

#### I-4

`Bound` · On-chain: **No**

> `reportBuffer` is intended to be a basis-point haircut, but no setter guard enforces `reportBuffer <= MAX_BPS`.

**Derivation** - guard-lift gap: `estimatedTotalAssets()` uses `(MAX_BPS - reportBuffer)` at `src/BaseLSTAccumulator.sol:178`; `setReportBuffer()` writes the value at `src/BaseLSTAccumulator.sol:198-200` with no equivalent bound.

**If violated** - ETA-dependent views/reports can revert under Solidity 0.8 checked subtraction.

#### I-5

`Ratio` · On-chain: **Yes**

> Reported LST value is haircut by `reportBuffer` before being added to idle asset.

**Derivation** - ratio: `balanceOfAsset() + ((valueOfLST() * (MAX_BPS - reportBuffer)) / MAX_BPS)` at `src/BaseLSTAccumulator.sol:177-179`.

**If violated** - total-assets reporting would no longer match the strategy's explicit haircut model.

#### I-6

`Ratio` · On-chain: **Yes**

> Strategy4626 values the wrapped vault position as `stETH balance + wstETH(stETH value of loose wstETH + vault assets)`.

**Derivation** - ratio: `valueOfWstETH()` at `src/Strategy4626.sol:69-71` and `valueOfLST()` at `src/Strategy4626.sol:73-75`.

**If violated** - reports, deposit limits, and manual unwind sizing would read a different asset base than the vault position actually represents.

#### I-7

`StateMachine` · On-chain: **Yes**

> Factory deployments are one-shot per `_vault`: unset deployment moves to a concrete strategy address and has no reset path.

**Derivation** - edge: `deployments[_vault] == address(0)` at `src/Strategy4626Factory.sol:44` -> `deployments[_vault] = address(newStrategy)` at `src/Strategy4626Factory.sol:68`.

**If violated** - duplicate strategies could be created for the same vault with ambiguous discovery via `isDeployedStrategy`.

---

## 3. Inferred Invariants (Cross-Contract)

#### X-1

On-chain: **Yes**

> TokenizedStrategy deposit/mint limits trust `availableDepositLimit(receiver)`, which in Strategy4626 further trusts the downstream ERC4626 vault's `maxDeposit(address(this))`.

**Caller side** - `src/Strategy4626.sol:55-63` - converts the vault max-deposit amount from wstETH into stETH value before returning the strategy deposit cap.

**Callee side** - external ERC4626 vault - outside scope; only the asset identity is checked at `src/Strategy4626.sol:21`.

**If violated** - the strategy's deposit capacity can diverge from the vault's live capacity.

#### X-2

On-chain: **Yes**

> TokenizedStrategy report accounting trusts the strategy callback to return an accurate WETH-equivalent total.

**Caller side** - `lib/tokenized-strategy/src/TokenizedStrategy.sol:1081-1094` - `report()` calls `harvestAndReport()` and records the returned total assets.

**Callee side** - `src/BaseLSTAccumulator.sol:146-155` and `src/Strategy4626.sol:69-75` - rewards are claimed/sold, idle WETH is staked, and ETA is returned.

**If violated** - profit/loss locking records the wrong asset base.

#### X-3

On-chain: **Yes**

> TokenizedStrategy withdrawals trust the strategy's custom withdraw limit and do not invoke automatic unstaking in this implementation.

**Caller side** - `lib/tokenized-strategy/src/TokenizedStrategy.sol:900-928` - `_maxWithdraw` / `_maxRedeem` cap exits by `availableWithdrawLimit(owner)`.

**Callee side** - `src/BaseLSTAccumulator.sol:115-144` - `_freeFunds` is intentionally empty and the withdraw limit returns idle asset balance.

**If violated** - ERC4626 exits could require liquidity the strategy does not automatically free.

---

## 4. Economic Invariants

#### E-1

On-chain: **Yes**

> The reportable NAV is idle WETH plus haircut LST/wstETH value, and only when `pendingRedemptions == 0`.

**Follows from** - `I-3` + `I-5` + `I-6` + `X-2`

**If violated** - report-cycle profit/loss and locked-profit math would be calibrated to a different asset base.

#### E-2

On-chain: **Yes**

> User exit liquidity is intentionally separated from total strategy value: users can exit only through idle WETH unless roles unwind LST or vault positions.

**Follows from** - `I-2` + `X-3`

**If violated** - the strategy would promise liquid redemptions against illiquid or externally queued positions.
