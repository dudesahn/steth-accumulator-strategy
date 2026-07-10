# Nemesis Feedback Pass 4 - Targeted State Review

## Inputs From Feedback Pass 3
- NEM-001 root cause: missing numeric domain check for a BPS parameter.
- NEM-002 root cause: hidden ABI transformation for queue request identity.
- NEM-003 root cause: placeholder oracle uncoupled from allocation state.

## Propagation Checks

### NEM-001 Propagation
- Readers affected: `estimatedTotalAssets()`, `_depositLimit()`, `availableDepositLimit()`, `_harvestAndReport()`.
- TokenizedStrategy withdrawals that use only `availableWithdrawLimit()` are not directly affected, but reports and new deposits are.
- Management can reset `reportBuffer`, so this is not permanent lock.
- No additional severity promotion.

### NEM-002 Propagation
- `pendingRedemptions` blocks `_harvestAndReport()` while nonzero.
- Emergency paths can recover via `manualClaimWithdrawals()` or `clearPendingRedemptions()`, but normal typed tracking is absent.
- Existing tests pass because they avoid the direct-return-data path.
- No additional severity promotion.

### NEM-003 Propagation
- The oracle has no internal callers in this repo.
- Impact depends on external allocator wiring.
- No additional severity promotion without deployment evidence.

## Convergence
- No new coupled state pairs or root causes were discovered in this pass.
- Nemesis loop converged after four passes.
