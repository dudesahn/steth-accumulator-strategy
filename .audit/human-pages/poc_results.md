# PoC Results

## Build Availability

```bash
forge build --force --skip 'src/test/*PoC*.t.sol'
```

Result:

```text
Compiler run successful with warnings.
```

## Baseline Tests

```bash
env ETH_RPC_URL=https://ethereum.publicnode.com forge test -vv --no-match-path 'src/test/*PoC*.t.sol' --fork-url https://ethereum.publicnode.com
```

Result:

```text
46 tests passed, 0 failed, 0 skipped across 8 suites.
```

## Focused PoCs

### Shutdown Liquidity Re-Staking

PoC file: `.audit/human-pages/poc_tests/ShutdownRestakeLiquidity.t.sol`

```bash
env ETH_RPC_URL=https://ethereum.publicnode.com forge test --contracts .audit/human-pages/poc_tests --match-path .audit/human-pages/poc_tests/ShutdownRestakeLiquidity.t.sol -vvv --fork-url https://ethereum.publicnode.com
```

Result:

```text
1 test passed. The PoC shows shutdown plus emergencyWithdraw creates WETH liquidity, then keeper tend restakes it, reducing WETH and user maxRedeem while increasing stETH exposure.
```

### Lido Claim-Data Mismatch

PoC file: `.audit/human-pages/poc_tests/WithdrawalQueueClaimDataMismatch.t.sol`

```bash
env ETH_RPC_URL=https://ethereum.publicnode.com forge test --contracts .audit/human-pages/poc_tests --match-path .audit/human-pages/poc_tests/WithdrawalQueueClaimDataMismatch.t.sol -vvv --fork-url https://ethereum.publicnode.com
```

Result:

```text
1 test passed. The PoC shows initiate return data decodes as scalar 32, direct claim reverts and leaves pendingRedemptions nonzero, while abi.encode(requestIds[0]) succeeds and clears pendingRedemptions.
```

### Strategy4626 Emergency Withdraw Scope

PoC file: `.audit/human-pages/poc_tests/Strategy4626EmergencyWithdrawNoop.t.sol`

Initial command without `--contracts`:

```bash
env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-path .audit/human-pages/poc_tests/Strategy4626EmergencyWithdrawNoop.t.sol -vvv --fork-url https://ethereum.publicnode.com
```

Result:

```text
No tests matched because project sources are configured under src.
```

Initial exact-zero assertion run:

```bash
env ETH_RPC_URL=https://ethereum.publicnode.com forge test --contracts .audit/human-pages/poc_tests --match-path .audit/human-pages/poc_tests/Strategy4626EmergencyWithdrawNoop.t.sol -vvv --fork-url https://ethereum.publicnode.com
```

Result:

```text
1 test failed because fork state had 1 wei loose stETH dust. This failure informed the final dust-tolerant assertion.
```

Final command:

```bash
env ETH_RPC_URL=https://ethereum.publicnode.com forge test --contracts .audit/human-pages/poc_tests --match-path .audit/human-pages/poc_tests/Strategy4626EmergencyWithdrawNoop.t.sol -vvv --fork-url https://ethereum.publicnode.com
```

Result:

```text
1 test passed. The PoC shows emergencyWithdraw leaves Strategy4626 vault shares unchanged and frees only pre-existing loose stETH dust. Verifier downgraded this to a low operational note because manualRedeem/manualUnwrap escape hatches exist.
```

## Machine-Readable Findings Validation

```bash
node -e "const fs=require('fs'); const lines=fs.readFileSync('.audit/human-pages/findings.jsonl','utf8').trim().split(/\\n/).filter(Boolean); for (const [i,l] of lines.entries()) { const o=JSON.parse(l); for (const k of ['schema_version','finding_id','source','title','affected','impact','preconditions','evidence','synthesized_severity','confidence','status','dedupe_key','notes']) if (!(k in o)) throw new Error('line '+(i+1)+' missing '+k); } console.log('valid jsonl lines:', lines.length);"
```

Result:

```text
valid jsonl lines: 5
```
