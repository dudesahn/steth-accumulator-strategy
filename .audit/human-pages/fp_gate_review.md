# False-Positive Gate Review

Source: `.audit/human-pages/agent_outputs/verifier.md`.

## Summary

| Candidate | Verdict | Severity |
| --- | --- | --- |
| C1 shutdown report/tend re-stakes WETH | TRUE POSITIVE, PoC validated | Medium |
| C2 Strategy4626 emergencyWithdraw does not redeem vault | TRUE BEHAVIOR, downgraded | Low note |
| C3 Lido queue return-data mismatch | TRUE POSITIVE, PoC validated | Medium |
| C4 Strategy4626 no min-share check | PLAUSIBLE, deployment-conditional | Medium conditional |
| C5 Strategy4626 deposit limit ignores loose WETH | PLAUSIBLE/strong source trace | Medium conditional |
| C6 factory zero profit unlock report front-run | PLAUSIBLE, deployment-conditional | Medium conditional |
| C7 external ERC4626 NAV/liveness trust | PLAUSIBLE, broad dependency note | Low/info note |
| C8 manual swap stale-accounting race | DOWNGRADED | Low note |
| C9 factory zero-address/reportBuffer config | DOWNGRADED | Info/Low note |
| C10 duplicate factory deployment reentrancy and setReferral(0) | REJECTED | None |

## Gate Details

### C1: Shutdown report/tend can re-stake WETH liquidity

- Reachability: PASS. Keeper or management can call inherited `report()` and `tend()` after shutdown.
- Validation chain: PASS. Local `_harvestAndReport` and `_tend` stake loose WETH, and the PoC proves `tend()` re-stakes WETH after shutdown emergency withdrawal.
- Math bounds: PASS. Report stakes up to `min(balanceOfAsset(), availableDepositLimit(address(this)))`; `address(this)` is whitelisted and the local limit does not check shutdown.
- State preconditions: PASS. Idle WETH exists after emergency withdrawal, manual swap, Lido claim, or `stakeAsset=false`.
- Economic viability: PASS for liquidity grief. No theft, but exit liquidity is removed.
- Environment: PASS. Applies to Strategy and Strategy4626; keeper automation increases likelihood.
- Verdict: validated Medium finding.

### C2: Strategy4626 emergencyWithdraw does not redeem vaulted position

- Reachability: PASS. Emergency roles can call shutdown then inherited emergencyWithdraw.
- Validation chain: PASS. PoC shows Strategy4626 vault shares unchanged.
- Math bounds: PASS with dust-tolerant assertion.
- State preconditions: PASS only when value is vaulted.
- Economic viability: PARTIAL. It is an operational delay, not untrusted loss, and manual escape hatches exist.
- Environment: PARTIAL. Strategy4626 only; worse if the external vault blocks redemption.
- Verdict: downgraded to low report note.

### C3: Lido withdrawal initiation return data does not match claim decoder

- Reachability: PASS. Management initiates, keeper claims.
- Validation chain: PASS. Source returns `abi.encode(uint256[] requestIds)` and decodes scalar `uint256`; PoC proves direct return-data roundtrip fails.
- Math bounds: PASS. ABI dynamic-array encoding starts with offset word `0x20`.
- State preconditions: PASS. Pending Lido withdrawal exists and keeper uses returned bytes directly.
- Economic viability: PASS for report/accounting DoS until privileged/operator recovery.
- Environment: PASS. Applies to intended Lido queue flow.
- Verdict: validated Medium finding.

### C4/C7: Strategy4626 ERC4626 vault share/NAV/liveness trust

- Reachability: PASS for Strategy4626 vault paths.
- Validation chain: PASS for source dependency; no concrete endorsed unsafe vault proven.
- Math bounds: PASS conditionally for zero/dust shares or false NAV under manipulated/nonstandard vault.
- State preconditions: CONDITIONAL. Requires selected vault with unsafe ERC4626 behavior and open/allowlisted deposits.
- Economic viability: PASS conditionally; principal donation or false report possible.
- Environment: CONDITIONAL. Vetted vaults reduce likelihood.
- Verdict: plausible deployment-conditional finding/note.

### C5: Strategy4626 deposit limit ignores pre-existing loose WETH

- Reachability: PASS. Inherited `_deposit` deploys full loose WETH balance.
- Validation chain: PASS. Strategy4626 limit checks the new deposit capacity but `_stake` later deposits all resulting wstETH without a second cap check.
- Math bounds: PASS. New deposit can be within limit while new deposit plus idle WETH exceeds vault capacity.
- State preconditions: CONDITIONAL. Requires loose WETH and finite external vault cap.
- Economic viability: PASS for deposit DoS/liquidity redeployment.
- Environment: CONDITIONAL. Strategy4626 only.
- Verdict: plausible Medium conditional finding.

### C6: Factory-created Strategy4626 disables profit locking

- Reachability: PASS. Factory sets profit unlock time to zero.
- Validation chain: PASS. Deposits mint against last recorded assets; unreported gains enter on report; zero unlock skips profit-lock shares.
- Math bounds: PASS. Depositor can capture pro-rata share of unreported gain.
- State preconditions: CONDITIONAL. Requires public/allowlisted deposits, material unreported gains, and predictable reports.
- Economic viability: PASS conditionally as shareholder dilution.
- Environment: CONDITIONAL. Factory Strategy4626 only.
- Verdict: plausible Medium conditional finding.

### C8/C9: Operator/configuration issues

- Reachability: PASS through trusted management/deployer.
- Validation chain: PASS for source behavior.
- Math bounds: PASS for reportBuffer underflow and stale accounting window.
- State preconditions: trusted-role mistakes or sequencing.
- Economic viability: weak as untrusted attack.
- Environment: trusted operations.
- Verdict: downgraded to low/info notes.

### C10: Rejected signals

- Duplicate deployment reentrancy: FAIL. Reentry theory depends on stateful reentry during static/view calls; later calls target freshly deployed strategy setters.
- `setReferral(0)`: FAIL. Zero referral is valid/no-referral Lido data and setter is management-only.
- Verdict: rejected.
