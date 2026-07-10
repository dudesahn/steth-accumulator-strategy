# Validation Commands

```sh
env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-path src/test/WithdrawalQueue.t.sol -vv --fork-url https://ethereum.publicnode.com
```

Result: 7 tests passed.

```sh
cast abi-encode "f(uint256[])" "[123]"
```

Result:

```text
0x0000000000000000000000000000000000000000000000000000000000000020...
```

```sh
cast decode-abi "f()(uint256)" 0x00000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000007b
```

Result: `32`.
