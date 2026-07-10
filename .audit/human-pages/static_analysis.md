# Static Analysis

## Commands and Results

Command:

```bash
which slither 2>/dev/null || true
```

Result:

```text
/opt/homebrew/bin/slither
```

Command:

```bash
which semgrep 2>/dev/null || true
```

Result:

```text
semgrep not found
```

Command:

```bash
sed -n '1,80p' lib/openzeppelin-contracts/package.json
```

Result summary:

```text
OpenZeppelin package version: 4.9.5
```

Command:

```bash
forge build --force --skip 'src/test/*PoC*.t.sol'
```

Result summary:

```text
Compiling 65 files with Solc 0.8.23
Solc 0.8.23 finished in 1.67s
Compiler run successful with warnings.
```

Warnings were unused parameters/local variables in the APR oracle/tests/mock queue, Foundry lint/style notes, and unchecked ERC20 transfer lint warnings in tests/mocks. The command also emitted a sandbox warning that Foundry could not write `/Users/dudesahn/.foundry/cache/signatures`; compilation still succeeded.

Command:

```bash
slither src/ --filter-paths "lib/|node_modules/|src/test/FactoryProfitUnlockDilutionPoC.t.sol"
```

Result summary:

```text
Slither analyzed src/ and found 57 result(s); process exited 255 because findings were present.
```

Isolation note: the first Slither pass was intentionally broad per Human Pages defaults, but Slither surfaced a stale/generated `*PoC*` test path from build metadata. No PoC-file contents were manually read or used. Follow-up build/test work uses `--skip 'src/test/*PoC*.t.sol'` where applicable, and candidate selection below ignores PoC-file-derived output.

## Slither Production-Relevant Signals to Triage

- `Strategy4626Factory.newStrategy4626` reentrancy/no-eth/events warning: external calls to the newly deployed strategy and its setters occur before `deployments[_vault] = address(newStrategy)` at `src/Strategy4626Factory.sol:52-68`.
- `Strategy.manualClaimWithdrawals` benign reentrancy warning: external queue claim before optional `pendingRedemptions = 0` at `src/Strategy.sol:116-126`.
- Missing zero-checks in `Strategy4626Factory` constructor and `setAddresses` for management/role/asset addresses at `src/Strategy4626Factory.sol:24-35` and `src/Strategy4626Factory.sol:72-83`.
- Missing zero-check in `Strategy.setReferral` at `src/Strategy.sol:128-130`.
- Strict equality warnings around zero checks and `pendingRedemptions == 0`; these need manual context and are not findings by themselves.
- Solidity version warning for `^0.8.18` pragmas in interfaces/periphery/tests is likely mitigated by `foundry.toml` pinning `solc = "0.8.23"`.

## Mostly Test/Mock or Informational Slither Output

- Arbitrary transfer/unchecked transfer warnings in `src/test/*` and `src/test/mocks/MockWithdrawalQueue.sol`.
- Reentrancy/calls-in-loop/costly-loop warnings in the mock withdrawal queue.
- Dead-code/unused-state style notes such as `BaseLSTAccumulator.WAD`.
- Naming/style lint notes from Forge.

