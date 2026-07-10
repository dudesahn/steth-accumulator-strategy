# Validation Commands

Disposable copy:

```text
artifacts/05_findings/CS-351C58EB-003/validation_artifacts/repro
```

Command:

```sh
env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-path src/test/MaxDepositDonationPoC.t.sol -vv --fork-url https://ethereum.publicnode.com
```

Result: compiled copied target code and passed 1/1.
