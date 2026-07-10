# Nemesis State Inconsistency Pass - Verified Output

## Promoted Findings

### SI-001 -> NEM-001: `reportBuffer` can exceed `MAX_BPS`
- Coupled state: `reportBuffer` and `MAX_BPS`.
- Verification: Static trace.
- Evidence: setter at `src/BaseLSTAccumulator.sol:198-200`; arithmetic reader at `src/BaseLSTAccumulator.sol:177-179`.
- Impact: management-only invalid state that reverts accounting readers and report/deposit limit paths.

### SI-002 -> NEM-002: Withdrawal claim data has no enforced shape
- Coupled state: queue request id(s) and `pendingRedemptions`.
- Verification: Static ABI trace and existing test behavior.
- Evidence: initiation returns an encoded array at `src/Strategy.sol:97-99`; claim decodes a scalar at `src/Strategy.sol:104-108`; tests transform the return bytes before claim at `src/test/WithdrawalQueue.t.sol:72-80`.
- Impact: direct use of the returned bytes can target the wrong id and keep reports blocked by pending redemptions.

### SI-003 -> NEM-003: APR oracle state is uncoupled from its inputs
- Coupled state: target strategy, debt delta, capacity/shutdown/yield state, and oracle APR.
- Verification: Static trace.
- Evidence: `src/periphery/StrategyAprOracle.sol:28-32` ignores all inputs; `src/test/Oracle.t.sol:26-36` leaves delta-sensitive assertions as TODOs.
- Impact: positive APR can be returned for states where no deployable yield exists, if the oracle is used in production allocation.

## Feedback Into Feynman
- Ask whether the `reportBuffer` setter should reject invalid input or intentionally allow "brick until reset" behavior. No evidence of intended invalid values was found.
- Ask whether the withdrawal API should expose typed request ids instead of untyped bytes. Existing tests demonstrate the hidden convention rather than enforcing it in the interface.
- Ask whether `StrategyAprOracle` is a deployable production periphery contract or a placeholder that should be excluded from runtime scope.
