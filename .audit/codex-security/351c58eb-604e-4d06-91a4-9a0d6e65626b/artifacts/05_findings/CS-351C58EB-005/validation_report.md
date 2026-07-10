# Validation Report: CS-351C58EB-005

Title: `StrategyAprOracle` returns a constant 4% APR for any strategy and debt delta.

Disposition: `deferred`

Confidence: `0.65`

## Rubric

- [x] Static placeholder behavior is confirmed.
- [x] Expected API semantics are checked against imported `AprOracleBase`.
- [x] Existing test limitations are identified.
- [x] Production registration/deployment search was bounded.
- [ ] Reportable allocator impact is not proven.

## Evidence

`src/periphery/StrategyAprOracle.sol:28-32` ignores `_strategy` and `_delta` and always returns `4e16`. The imported periphery API expects APR after a signed debt change. Existing `Oracle.t.sol` passed but only asserts APR is greater than zero and less than 100%; comments leave debt-change behavior as TODO.

Production search excluding tests, vendored deps, prior audits, x-ray, broadcast/cache/out found no deployment, registration, or allocator consumer path for `StrategyAprOracle`.

## Counterevidence and Gaps

The constructor names it `"Strategy Apr Oracle Example"`. No in-repo production registration path was found. Absence of a local registration path does not prove it is never used, because registration can happen outside this repo.

## Closure

The row remains deferred. It should become reportable only if deployment or allocator registration evidence shows this oracle is production-used; it can be suppressed if maintainers confirm the file is example-only and never registered.
