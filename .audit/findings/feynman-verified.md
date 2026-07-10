# Nemesis Feynman Pass - Verified Output

## Promoted Findings

### FF-001 -> NEM-001: Unbounded report buffer can enter an underflowing accounting state
- Severity: Low.
- Verification: Static code trace.
- Evidence:
  - `src/BaseLSTAccumulator.sol:177-179` computes `balanceOfAsset() + ((valueOfLST() * (MAX_BPS - reportBuffer)) / MAX_BPS)`.
  - `src/BaseLSTAccumulator.sol:198-200` allows management to set any `uint256` as `reportBuffer`.
  - Existing tests cover valid buffers (`100`, `500`, `1000`) but do not cover `reportBuffer > MAX_BPS`.
- Impact: Management misconfiguration can make accounting views, deposit-limit checks, and reports revert until the value is reset.

### FF-002 -> NEM-002: Withdrawal initiation and claim bytes use different implicit encodings
- Severity: Low.
- Verification: Static ABI trace plus existing test behavior.
- Evidence:
  - `src/Strategy.sol:97-99` returns `abi.encode(requestIds)` where `requestIds` is `uint256[]`.
  - `src/Strategy.sol:104-108` decodes claim bytes as `uint256`.
  - `src/test/WithdrawalQueue.t.sol:72-80` succeeds by decoding the returned array and re-encoding `requestIds[0]`; the direct return bytes are not used.
  - `cast abi-encode "f(uint256[])" "[1]"` produced a first data word of `0x20`; interpreted as a scalar this is decimal `32`, not request id `1`.
- Impact: A keeper/operator passing the initiation return bytes directly can claim the wrong request id or revert, leaving `pendingRedemptions` uncleared and reports blocked.

### FF-003 -> NEM-003: APR oracle returns a constant 4% for any strategy and debt delta
- Severity: Low.
- Verification: Static code trace and test expectation review.
- Evidence:
  - `src/periphery/StrategyAprOracle.sol:28-32` ignores `_strategy` and `_delta` and returns `4e16`.
  - `src/test/Oracle.t.sol:26-36` leaves debt-sensitive assertions as TODOs.
- Impact: If this oracle is wired into allocation tooling, it can report positive APR for unsupported, full, shutdown, or no-yield states.

## Downgraded Or Eliminated
- `stakeAsset=false` not stopping report-time staking was downgraded because `src/test/StethSpecific.t.sol:332-354` explicitly tests and documents the current behavior.
- Factory-created strategies starting with factory management and pending user management was downgraded because `src/test/Strategy4626Factory.t.sol:31-46` asserts the intended two-step management acceptance flow.
- Pending redemption clearing/manual claim paths were treated as operationally dangerous but documented: comments on `clearPendingRedemptions()` warn that losses may be realized on the next report, and emergency claim can explicitly choose whether to zero pending redemptions.

## Test Commands
- `env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-path src/test/WithdrawalQueue.t.sol -vv --fork-url https://ethereum.publicnode.com`: 7 passed.
- `env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-path src/test/Strategy4626.t.sol -vv --fork-url https://ethereum.publicnode.com`: 5 passed.
- `env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-path src/test/Operation.t.sol -vv --fork-url https://ethereum.publicnode.com`: 8 passed.
- `env ETH_RPC_URL=https://ethereum.publicnode.com forge test -vv --fork-url https://ethereum.publicnode.com`: 46 passed.
