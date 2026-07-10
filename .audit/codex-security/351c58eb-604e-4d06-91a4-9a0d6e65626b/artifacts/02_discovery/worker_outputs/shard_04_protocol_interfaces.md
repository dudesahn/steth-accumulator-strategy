# shard_04_protocol_interfaces discovery output

scan_id: `351c58eb-604e-4d06-91a4-9a0d6e65626b`

scope: production code only; assigned files `src/interfaces/ICurve.sol`, `src/interfaces/IQueue.sol`, `src/interfaces/ISTETH.sol`, `src/interfaces/IWETH.sol`, `src/interfaces/IWstETH.sol`.

threat model receipt: read `/private/var/folders/s_/3h_wvzqx385frkp70gr8cpdc0000gn/T/codex-security-scans-HMBJE7/steth-accumulator-strategy/521fff28ad978a37115be8995a1d631611fa1d3d_20260708T164548Z_sqevo7au/artifacts/01_context/threat_model.md` lines 1-74. Relevant rows: protocol interface assumptions and external Lido/Curve/WETH/wstETH/ERC4626 dependencies at lines 28, 35-38; queue/accounting and unit-sensitive wstETH/vault paths at lines 42-48; existing controls at lines 52-62.

## Full-file receipts

| assigned file | line range read | concise evidence |
| --- | ---: | --- |
| `src/interfaces/ICurve.sol` | 1-13 | Minimal Curve interface declares payable `exchange(int128,int128,uint256,uint256) returns (uint256)` at lines 5-8, `price_oracle()` at line 9, `balances(uint256)` at line 10, and `get_dy(int128,int128,uint256)` at line 12. First-party callers use only `get_dy`/`exchange` in `src/Strategy.sol:58-65` and `src/Strategy.sol:78-81`; `price_oracle`/`balances` are unused in production. |
| `src/interfaces/IQueue.sol` | 1-10 | Withdrawal queue interface returns `uint256[] memory requestIds` from `requestWithdrawals` at lines 5-7 and exposes scalar `claimWithdrawal(uint256)` at line 8 plus batch `claimWithdrawals(uint256[],uint256[])` at line 10. First-party encoder/decoder mismatch found at `src/Strategy.sol:97-105`. |
| `src/interfaces/ISTETH.sol` | 1-9 | Interface extends `IERC20`, declares payable `submit(address) returns (uint256)` at line 7 and `isStakingPaused() returns (bool)` at line 8. First-party call sites are deposit gating at `src/Strategy.sol:38-42` and direct staking at `src/Strategy.sol:68`; return value is not security-critical because balances are observed separately. |
| `src/interfaces/IWETH.sol` | 1-12 | Interface extends `IERC20`, declares `deposit()` at line 7, `decimals() returns (uint256)` at line 9, and `withdraw(uint256)` at line 11. First-party call sites are WETH unwrap/wrap at `src/Strategy.sol:55`, `src/Strategy.sol:81`, `src/Strategy.sol:112`, and `src/Strategy.sol:125`; `decimals()` is unused in production. |
| `src/interfaces/IWstETH.sol` | 1-14 | Interface extends `IERC20`, declares `wrap`, `unwrap`, and stETH/wstETH conversion views at lines 7-13. First-party call sites are `src/Strategy4626.sol:34`, `src/Strategy4626.sol:82`, `src/Strategy4626.sol:95`, `src/Strategy4626.sol:100`, and `src/Strategy4626.sol:114`; units are consistently wstETH for vault assets and stETH for strategy value. |

## Coverage rows

| family | disposition | evidence |
| --- | --- | --- |
| Lido withdrawal queue return-data shape and claim accounting | reportable | `IQueue.requestWithdrawals` returns `uint256[]` at `src/interfaces/IQueue.sol:5-7`; `Strategy._initiateLSTWithdrawal` returns `abi.encode(requestIds)` at `src/Strategy.sol:97-99`; `Strategy._claimLSTWithdrawal` decodes the bytes as a scalar `uint256` and passes it to `claimWithdrawal` at `src/Strategy.sol:104-108`; `BaseLSTAccumulator` increments/decrements `pendingRedemptions` and blocks reports while nonzero at `src/BaseLSTAccumulator.sol:146-148` and `src/BaseLSTAccumulator.sol:259-271`. Candidate `CS-351C58EB-IFACE-001`. |
| Curve ETH/stETH index, payable value, return handling, and min-out units | suppressed | Curve interface uses `int128` indexes and uint256 amounts at `src/interfaces/ICurve.sol:5-12`; strategy constants map ETH to `0` and stETH to `1` at `src/Strategy.sol:21-25`; WETH is unwrapped before ETH->stETH quote/swap at `src/Strategy.sol:55-65`; stETH->ETH swap uses `_minOut` then wraps received ETH at `src/Strategy.sol:75-81`. Return values are ignored, but the pool min-out controls and post-call token balances are the accounting source. No concrete exploit path from the minimal interface. |
| stETH submit return value and staking-pause semantics | suppressed | `ISTETH.submit` returns minted stETH at `src/interfaces/ISTETH.sol:7`; caller ignores the return at `src/Strategy.sol:68`, but strategy accounting reads stETH balances through `balanceOfLST` at `src/BaseLSTAccumulator.sol:185-191` and `Strategy4626` wraps the observed stETH balance at `src/Strategy4626.sol:32-41`. `isStakingPaused()` gates deposits at `src/Strategy.sol:38-42`. No concrete first-party loss path from return-value handling. |
| WETH deposit/withdraw return handling, decimals, and ETH balance wrapping | suppressed | `IWETH.deposit`/`withdraw` have no return values at `src/interfaces/IWETH.sol:7-11`; WETH unwrap/wrap sites are `src/Strategy.sol:55`, `src/Strategy.sol:81`, `src/Strategy.sol:112`, and `src/Strategy.sol:125`. `decimals()` is declared at `src/interfaces/IWETH.sol:9` but unused. Claim path measures ETH received with a pre/post balance delta at `src/Strategy.sol:107-112`; any preexisting ETH is wrapped into strategy WETH, not sent out. No concrete exploit path from the minimal interface. |
| wstETH conversion units, wrap/unwrap return handling, and ERC4626 asset-domain crossing | suppressed | Constructor requires `vault.asset() == address(wstETH)` at `src/Strategy4626.sol:20-23`; stETH is wrapped and wstETH deposited at `src/Strategy4626.sol:32-41`; vault `maxDeposit` is converted from wstETH to stETH value at `src/Strategy4626.sol:55-63`; `valueOfWstETH` converts direct and vault-held wstETH to stETH at `src/Strategy4626.sol:69-74`; `_freeStETH` uses `getWstETHByStETH`, adds 2 wei for double rounding, clamps to `maxRedeem`, and requires enough stETH before Lido queue initiation at `src/Strategy4626.sol:77-95` and `src/Strategy4626.sol:49-52`. Manual redeem/unwrap are emergency-only at `src/Strategy4626.sol:103-114`. No concrete first-party exploit path from ignored wrap/unwrap returns or unit conversion. |
| Unused minimal-interface members | not_applicable | `ICurve.price_oracle`, `ICurve.balances`, and `IWETH.decimals` are declared at `src/interfaces/ICurve.sol:9-10` and `src/interfaces/IWETH.sol:9`, but production search found no first-party call sites. |

## Raw candidate objects

```yaml
- candidate_id: "CS-351C58EB-IFACE-001"
  title: "Lido withdrawal queue return data is encoded as uint256[] but claimed as a scalar uint256"
  affected_locations:
    - label: "interface_source"
      file: "src/interfaces/IQueue.sol"
      lines: "5-7"
      detail: "requestWithdrawals returns uint256[] memory requestIds."
    - label: "root_control/encoder"
      file: "src/Strategy.sol"
      lines: "91-99"
      detail: "_initiateLSTWithdrawal requests one withdrawal, receives uint256[] requestIds, and returns abi.encode(requestIds)."
    - label: "sink/decoder"
      file: "src/Strategy.sol"
      lines: "104-108"
      detail: "_claimLSTWithdrawal decodes _claimData as (uint256) and passes the decoded scalar to claimWithdrawal."
    - label: "accounting_gate"
      file: "src/BaseLSTAccumulator.sol"
      lines: "146-148"
      detail: "_harvestAndReport reverts while pendingRedemptions is nonzero."
    - label: "accounting_update"
      file: "src/BaseLSTAccumulator.sol"
      lines: "259-271"
      detail: "initiateLSTWithdrawal increments pendingRedemptions before returning claim data; claimLSTWithdrawal only decrements after a successful claim."
  instance_key: "queue-claim-data-shape:src/Strategy.sol:99"
  attacker_or_privileged_source: "Privileged management initiates the Lido withdrawal and receives first-party returnData; privileged keepers later provide _claimData to claimLSTWithdrawal. This is an operational privileged-source issue, not an untrusted external theft path."
  broken_control_or_sink: "The first-party encoder returns ABI bytes for a dynamic uint256[] while the first-party decoder expects a scalar uint256. ABI-decoding the returned dynamic-array bytes as uint256 reads the array head/offset word rather than requestIds[0], so the claim sink is called with the wrong request id."
  impact: "Normal use of the returned claim data can fail to claim the actual Lido withdrawal request, leaving stETH/ETH redemption value stuck in the withdrawal queue and pendingRedemptions nonzero. Because reports require pendingRedemptions == 0, the strategy can remain unable to report until an emergency/manual recovery path is used or the correct scalar request id is reconstructed off-chain."
  closest_control_and_why_incomplete: "claimLSTWithdrawal is onlyKeepers and manualClaimWithdrawals is onlyEmergencyAuthorized, but these controls do not make the canonical returnData self-consistent. The emergency batch helper at src/Strategy.sol:116-125 can recover with explicit requestIds/hints and optionally zero pendingRedemptions, but it is a separate privileged recovery path and can realize accounting loss if used incorrectly."
  candidate_local_validation:
    evidence:
      - "src/interfaces/IQueue.sol:5-7 establishes the queue return value is uint256[] requestIds."
      - "src/Strategy.sol:97-99 encodes the whole dynamic array as bytes."
      - "src/Strategy.sol:104-108 decodes claim data as a single uint256 and calls scalar claimWithdrawal."
      - "src/BaseLSTAccumulator.sol:146-148 and 259-271 show failed claims preserve pendingRedemptions and block reports."
    counterevidence:
      - "A keeper that ignores the returned bytes and instead passes abi.encode(actualRequestId) can use the scalar claim path successfully."
      - "Emergency-authorized callers can use manualClaimWithdrawals with explicit arrays at src/Strategy.sol:116-125."
      - "The issue does not give an untrusted caller direct asset withdrawal authority; management/keeper/emergency roles are trusted in the threat model."
    proof_gaps:
      - "Runtime validation should confirm the keeper/operations workflow consumes initiateLSTWithdrawal returnData directly."
      - "Runtime validation should confirm canonical Lido claimWithdrawal(32) behavior for a strategy that does not own request id 32; expected result is revert or wrong-request failure."
  attack_path_facts:
    - "Management calls BaseLSTAccumulator.initiateLSTWithdrawal; pendingRedemptions increases before the Lido queue request."
    - "Strategy._initiateLSTWithdrawal calls requestWithdrawals with a one-element amounts array and returns abi.encode(requestIds), where requestIds is a dynamic uint256[]."
    - "Keeper later calls BaseLSTAccumulator.claimLSTWithdrawal with that returned bytes."
    - "Strategy._claimLSTWithdrawal decodes the bytes as uint256 and calls IQueue.claimWithdrawal with that scalar, not requestIds[0]."
    - "If the scalar is not the actual request id, the claim does not settle the queued withdrawal and pendingRedemptions remains nonzero, blocking harvest/report."
  cwe:
    - "CWE-704"
  validation_recommended: true
```

## Summary

Found 1 technically plausible candidate: `CS-351C58EB-IFACE-001`, a Lido withdrawal queue ABI shape mismatch between `requestWithdrawals` return data and the scalar claim decoder. All other assigned interface rows were closed as suppressed or not applicable with first-party line evidence above.
