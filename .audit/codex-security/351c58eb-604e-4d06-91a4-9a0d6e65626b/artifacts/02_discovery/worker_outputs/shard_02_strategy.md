# Finding Discovery Worker Output: shard_02_strategy

Scan ID: 351c58eb-604e-4d06-91a4-9a0d6e65626b
Target: /Users/dudesahn/Documents/GitHub/codex/review/steth-accumulator-strategy
Assigned files: src/Strategy.sol only

## Full-file Receipts

- src/Strategy.sol:1-131 read in full. Evidence: constructor sets canonical stETH, Curve, and WETH approval at lines 18-34; unrestricted ETH receive at line 36; staking-paused deposit-limit override at lines 38-43; WETH->ETH route selection through Curve or Lido at lines 51-69; stETH->ETH Curve swap and WETH wrapping at lines 74-82; Lido withdrawal request/claim handling at lines 91-113; emergency batch manual claim at lines 116-126; referral setter at lines 128-130.

Minimal supporting code read for concrete evidence:

- src/BaseLSTAccumulator.sol:79-88 defines child withdrawal request/claim data contracts; src/BaseLSTAccumulator.sol:146-155 blocks reports while `pendingRedemptions != 0`; src/BaseLSTAccumulator.sol:158-163 uses `_swapLSTToAsset(..., 0)` only during emergency withdraw; src/BaseLSTAccumulator.sol:241-245, 250-253, 259-263, 269-271, and 279-280 show management/keeper/manual redemption flows and pending-redemption accounting.
- src/interfaces/IQueue.sol:4-10 shows `requestWithdrawals` returns `uint256[]` while single/batch claim functions consume request ids.
- src/interfaces/ICurve.sol:4-12 shows the Curve `exchange` and `get_dy` API used by the strategy.
- src/interfaces/ISTETH.sol:6-8 shows Lido `submit` and `isStakingPaused`.
- lib/tokenized-strategy/src/BaseStrategy.sol:51-74 confirms `onlyManagement`, `onlyKeepers`, and `onlyEmergencyAuthorized` role checks.

## Coverage Rows

| Family / focus area | Disposition | Evidence and rationale |
| --- | --- | --- |
| Curve/Lido route selection in `_stake` | suppressed | src/Strategy.sol:51-69 unwraps WETH, uses `get_dy`, and only uses Curve when quoted output is greater than `_amount`; the Curve call sets `_min_to_amount = _amount` at src/Strategy.sol:60-65, so spot movement causes revert rather than sub-1:1 execution. Direct Lido fallback at src/Strategy.sol:67-68 has no attacker-selected recipient except the management-set referral. |
| stETH withdrawal queue request/claim data handling | reportable | src/Strategy.sol:97-99 returns `abi.encode(requestIds)` where `requestIds` is a dynamic `uint256[]`, but src/Strategy.sol:104-109 decodes claim data as a scalar `uint256` and claims that id. Base flow exposes the returned bytes from management initiation at src/BaseLSTAccumulator.sol:259-263 and later takes keeper-supplied claim data at src/BaseLSTAccumulator.sol:269-271. Candidate CS-FD-351C-S02-001. |
| `pendingRedemptions` around normal claim | reportable as part of CS-FD-351C-S02-001 | Base reports revert while pending redemptions remain at src/BaseLSTAccumulator.sol:146-147. The normal claim path only decrements after `_claimLSTWithdrawal` returns a redeemed amount at src/BaseLSTAccumulator.sol:269-271, so a mismatched claim payload can leave the strategy unable to report until manual recovery. |
| `manualClaimWithdrawals` batch claim and pending reset | suppressed | src/Strategy.sol:116-126 is `onlyEmergencyAuthorized` and can optionally set `pendingRedemptions = 0`. This is powerful and can realize losses if misused, but it is explicitly emergency-authorized supporting recovery; the threat model treats emergency authorized accounts as trusted for manual Lido claims. |
| ETH/WETH balance assumptions | suppressed | src/Strategy.sol:36 accepts ETH, but ETH is swept into WETH after LST->asset swaps and claims at src/Strategy.sol:80-82, 107-112, and 120-125. Direct ETH donations can be temporarily unreported until a sweep path runs, but the observed effect is a donation/profit or liveness cleanup dependency, not an untrusted drain path. |
| Referral setting | suppressed | src/Strategy.sol:27 stores `referral`, src/Strategy.sol:68 passes it to Lido `submit`, and src/Strategy.sol:128-130 restricts updates to `onlyManagement`. No funds are transferred to the referral in first-party code. |
| Staking-paused handling | suppressed | src/Strategy.sol:38-43 returns a zero deposit limit when Lido staking is paused, blocking normal deposits through `availableDepositLimit`. Existing idle WETH may still be manually staked/tended through `_stake`; if the Curve premium route is not available, direct Lido submit reverts. This is privileged/liveness behavior rather than an untrusted loss path. |
| Slippage/min-out controls | suppressed | src/Strategy.sol:58-65 enforces at least 1:1 for WETH->stETH Curve staking; src/Strategy.sol:74-81 passes caller-provided `_minOut` for stETH->ETH manual swaps. Base emergency withdraw uses `_minOut = 0` at src/BaseLSTAccumulator.sol:158-163, but that path is emergency-authorized and shutdown-related. |
| Public `receive()` behavior | suppressed | src/Strategy.sol:36 has no sender restriction. Public ETH receipt enables donation/forced-balance scenarios, but subsequent swap/claim/manual-claim paths wrap the full ETH balance into WETH at src/Strategy.sol:80-82, 107-112, and 120-125; no candidate attacker profit path was identified from raw ETH alone. |
| External function authorization in assigned file | suppressed | `manualClaimWithdrawals` is `onlyEmergencyAuthorized` at src/Strategy.sol:116-119 and `setReferral` is `onlyManagement` at src/Strategy.sol:128-130. Other assigned functions are internal except unrestricted receive, covered above. |

## Raw Candidate Objects

```json
[
  {
    "candidate_id": "CS-FD-351C-S02-001",
    "title": "Withdrawal initiation returns array-encoded claim data that the normal claim path decodes as a single request id",
    "instance_key": "withdrawal-claim-data:src/Strategy.sol:97",
    "disposition": "reportable",
    "affected_locations": [
      {
        "file": "src/Strategy.sol",
        "line": 97,
        "label": "source",
        "evidence": "Lido `requestWithdrawals` returns `uint256[] memory requestIds`."
      },
      {
        "file": "src/Strategy.sol",
        "line": 99,
        "label": "root_control",
        "evidence": "The strategy returns `abi.encode(requestIds)`, i.e. ABI encoding for a dynamic uint256 array."
      },
      {
        "file": "src/Strategy.sol",
        "line": 105,
        "label": "sink",
        "evidence": "`_claimLSTWithdrawal` decodes the supplied claim bytes as `(uint256)` rather than `(uint256[])` or a canonical request-id wrapper."
      },
      {
        "file": "src/Strategy.sol",
        "line": 108,
        "label": "sink",
        "evidence": "The decoded scalar is passed to `claimWithdrawal(_requestId)`."
      },
      {
        "file": "src/BaseLSTAccumulator.sol",
        "line": 263,
        "label": "entrypoint/wrapper",
        "evidence": "The external management function returns the child `_initiateLSTWithdrawal` bytes directly."
      },
      {
        "file": "src/BaseLSTAccumulator.sol",
        "line": 269,
        "label": "entrypoint/wrapper",
        "evidence": "The external keeper function accepts arbitrary `_claimData` bytes for the child claim implementation."
      },
      {
        "file": "src/BaseLSTAccumulator.sol",
        "line": 147,
        "label": "impact_control",
        "evidence": "`_harvestAndReport` reverts while `pendingRedemptions` is nonzero."
      }
    ],
    "attacker_controlled_or_privileged_source": "Privileged/operational source: management initiates Lido withdrawal and receives return bytes; keeper or management later supplies `_claimData` to `claimLSTWithdrawal`. If automation treats the returned initiation bytes as the documented claim data, the bytes are not in the format the claim sink expects.",
    "broken_control_or_sink": "The request path emits dynamic-array ABI data but the claim path consumes scalar ABI data without a typed wrapper, selector, length check, or helper that transforms the returned data into the expected scalar request id.",
    "impact": "Normal Lido withdrawal claims can target the wrong request id or revert, leaving `pendingRedemptions` uncleared. Because reports require `pendingRedemptions == 0`, this can block reports and normal accounting until emergency/manual intervention. In an unlikely collision with a strategy-owned finalized request id equal to the decoded offset, the claim path could also clear the wrong request and decrement pending accounting against an unintended redemption.",
    "closest_control_and_why_incomplete": "Access control limits initiation to management and normal claims to keepers via src/BaseLSTAccumulator.sol:259 and src/BaseLSTAccumulator.sol:269, and emergency recovery exists through `manualClaimWithdrawals` at src/Strategy.sol:116-126 plus `clearPendingRedemptions` at src/BaseLSTAccumulator.sol:279-280. These controls do not make the normal returned request bytes self-consistent with the normal claim decoder, so operator automation can still enter the broken path and require emergency recovery.",
    "candidate_local_validation": {
      "evidence": [
        "src/interfaces/IQueue.sol:5-7 defines `requestWithdrawals` as returning `uint256[] memory requestIds`.",
        "src/Strategy.sol:97-99 encodes that dynamic array directly as the initiation return data.",
        "src/Strategy.sol:104-108 decodes claim data as a scalar `uint256` and sends it to `claimWithdrawal`.",
        "For ABI encoding, `abi.encode(uint256[]([id]))` begins with the dynamic array offset word `0x20`; decoding the same bytes as `(uint256)` yields `32`, not `id`.",
        "src/BaseLSTAccumulator.sol:146-147 blocks reports while pending redemptions remain, and src/BaseLSTAccumulator.sol:269-271 only decrements after a successful child claim."
      ],
      "counterevidence": [
        "A correctly written keeper can decode the returned array off-chain and call `claimLSTWithdrawal(abi.encode(requestIds[0]))`, which avoids the mismatch.",
        "`manualClaimWithdrawals` can claim batches with explicit ids/hints, and management can clear pending redemptions, so the issue is recoverable by trusted roles.",
        "The affected operations are not callable by arbitrary depositors or public users."
      ],
      "proof_gaps": [
        "Need validation against intended keeper scripts/runbooks to confirm whether raw `returnData` is expected to be passed into `claimLSTWithdrawal`.",
        "Need live or fork confirmation of Lido `claimWithdrawal(32)` behavior for the common case where the strategy does not own request id 32; expected result is revert/no claim."
      ]
    },
    "attack_path_facts": [
      "Management calls `initiateLSTWithdrawal(_amount)`, which increments `pendingRedemptions` before returning the child bytes.",
      "The child request implementation returns `abi.encode(requestIds)` for a dynamic array with one request id.",
      "Keeper automation or an operator passes those returned bytes directly to `claimLSTWithdrawal` as the interface-level claim data.",
      "The child claim implementation decodes the first word as a scalar request id, producing the ABI offset word rather than the actual Lido request id.",
      "The Lido queue claim attempts the wrong request id; if it reverts, `pendingRedemptions` remains nonzero and `_harvestAndReport` continues to revert."
    ],
    "validation_recommended": true,
    "cwe": [
      "CWE-704"
    ]
  }
]
```
