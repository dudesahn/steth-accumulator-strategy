# Nemesis Feedback Pass 3 - Targeted Feynman Review

## Inputs From State Pass
- `reportBuffer` lacks a local bound despite being used as a BPS subtraction input.
- Withdrawal claim data has a hidden array-to-scalar transformation requirement.
- APR oracle is constant and disconnected from target strategy state.

## Targeted Checks

### Report Buffer Root Cause
- The setter is management-gated, but management-gated values still feed public views, deposit/mint max checks, and keeper reports.
- A value above `MAX_BPS` is not a meaningful economic buffer; it only creates an arithmetic panic.
- No downstream lazy reconciliation or health check catches the issue before the underflow.
- Conclusion: verified Low, recommended setter cap.

### Withdrawal Claim API Root Cause
- The base interface exposes both initiation and claim as untyped bytes, so an integrator can reasonably assume initiation return data is accepted by claim.
- The implementation and tests rely on off-chain decoding and re-encoding of only the first request id.
- The contract does not store outstanding request ids, so it cannot validate that scalar claim data corresponds to the pending amount.
- Conclusion: verified Low, recommended typed API or aligned bytes encoding.

### APR Oracle Root Cause
- The oracle contract is a periphery runtime contract but behaves like a placeholder.
- The test suite only checks that the answer is nonzero and below 100%, so it cannot catch stale or capacity-insensitive allocation answers.
- Conclusion: verified Low if deployable periphery is in scope; recommended implementation or explicit non-production exclusion.

## New Findings
- No new findings beyond NEM-001 through NEM-003.
