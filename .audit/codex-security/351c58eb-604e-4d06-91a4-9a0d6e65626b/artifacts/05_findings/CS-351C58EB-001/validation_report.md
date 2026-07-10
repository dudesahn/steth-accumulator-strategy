# Validation Report: CS-351C58EB-001

Title: Lido withdrawal return data encodes a request-id array but the normal claim path decodes a scalar id.

Disposition: `reportable`

Confidence: `0.74`

## Rubric

- [x] Exact source/control/sink tuple is present.
- [x] Production reachability exists through management `initiateLSTWithdrawal` and keeper/management `claimLSTWithdrawal`.
- [x] ABI mismatch is confirmed independently from source and `cast`.
- [x] Existing tests show the successful path requires decoding `uint256[]` and re-encoding `requestIds[0]`.
- [x] Role gates and emergency/manual recovery are recorded as counterevidence.

## Evidence

`src/interfaces/IQueue.sol:5-7` returns `uint256[] memory requestIds`; `src/Strategy.sol:97-99` returns `abi.encode(requestIds)`; `src/Strategy.sol:104-108` decodes `_claimData` as scalar `uint256` and calls `claimWithdrawal(_requestId)`. `src/BaseLSTAccumulator.sol:259-271` increments pending redemptions before request and only decrements after a successful claim; `src/BaseLSTAccumulator.sol:146-147` blocks reports while pending redemptions are nonzero.

The ABI probe encoded `[123]` as a dynamic array and decoding the same bytes as scalar `uint256` returned `32`, the ABI offset word, not `123`.

Existing `WithdrawalQueue.t.sol` tests passed 7/7 on a mainnet fork, and they only succeed by decoding `returnData` as `uint256[]` and calling `claimLSTWithdrawal(abi.encode(requestIds[0]))`.

## Counterevidence and Gaps

The path is not public: initiation is management-gated and claiming is keeper/management-gated. Correct operator code can reshape the returned bytes before claiming. Emergency/manual recovery can claim explicit ids and zero or clear pending redemptions, but those are privileged recovery paths and can realize losses if used incorrectly. No production keeper bot was available to prove raw `returnData` is actually passed directly.

## Closure

The code bug and liveness/accounting impact survive validation. Severity should reflect privileged preconditions and recovery, not direct public theft.
