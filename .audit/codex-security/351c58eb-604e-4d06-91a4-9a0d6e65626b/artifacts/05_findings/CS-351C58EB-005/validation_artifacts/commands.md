# Validation Commands

```sh
env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-path src/test/Oracle.t.sol -vv --fork-url https://ethereum.publicnode.com
```

Result: 1 test passed, but the test only checks `0 < apr < 100%`.

```sh
rg -n "StrategyAprOracle|Deploy4626|Deploy4626Factory|setOracle|AprOracle|oracle" . -g '!lib/**' -g '!src/test/**' -g '!.audit/**' -g '!x-ray/**' -g '!broadcast/**' -g '!cache/**' -g '!out/**'
```

Result: no production deploy or registration path for `StrategyAprOracle`; only its own source file and unrelated names were found.
