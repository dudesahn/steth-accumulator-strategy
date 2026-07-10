# Attack Path Analysis: CS-351C58EB-001

## Title

Lido withdrawal return data encodes a request-id array but the normal claim path decodes a scalar id

## Attack Path

1. Management calls `initiateLSTWithdrawal`, which increments `pendingRedemptions` and returns bytes from `Strategy._initiateLSTWithdrawal`.
2. `Strategy._initiateLSTWithdrawal` calls Lido `requestWithdrawals`, receives a `uint256[] requestIds`, and returns `abi.encode(requestIds)`.
3. A keeper later calls `claimLSTWithdrawal` with claim data. The internal claim path decodes the bytes as a scalar `uint256` instead of `uint256[]`.
4. If the operator hands the raw initiation bytes to the claim path, the scalar decode reads the dynamic-array offset word, not the actual request id, so the claim targets the wrong request and `pendingRedemptions` can remain nonzero.

## Facts

- Service mapping: Yearn V3 stETH accumulator Lido withdrawal queue workflow.
- Entry points: `initiateLSTWithdrawal` is management-only; `claimLSTWithdrawal` is keeper-only.
- Trust boundary: management and keepers are privileged operational roles in the threat model.
- Reachability: no lower-privileged depositor or outside caller can initiate or claim the Lido queue request through this path.
- Existing controls: reports block while `pendingRedemptions` is nonzero, and emergency/manual claim/reset paths exist for authorized operators.

## Counterevidence

The strongest counterevidence is that this is an operator-workflow data-shape mismatch rather than an untrusted attacker path. Existing fork tests succeed by decoding the returned array and re-encoding the scalar request id before claim. The bug remains real for raw-return-data operational handoff, but the scan policy suppresses privileged-only workflow hazards unless they establish a meaningful lower-privileged attack path or privilege delta.

## Severity Calibration

- Impact: medium. A malformed claim can block reports through nonzero `pendingRedemptions` and require emergency/manual recovery.
- Likelihood: low. Exploitation depends on management/keeper workflow behavior and no untrusted caller can supply the normal initiation/claim sequence.
- Matrix result: ignore.

## Final Policy Decision

`ignore`. Keep the validation artifact as an operational fix candidate, but do not emit a final security finding.
