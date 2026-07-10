#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

SCAN_ID = "351c58eb-604e-4d06-91a4-9a0d6e65626b"
SCAN_DIR = Path(__file__).resolve().parents[1]
ARTIFACTS = SCAN_DIR / "artifacts"
FINDINGS_DIR = ARTIFACTS / "05_findings"

INCLUDE_PATHS = [
    "src/BaseLSTAccumulator.sol",
    "src/Strategy.sol",
    "src/Strategy4626.sol",
    "src/Strategy4626Factory.sol",
    "src/periphery/StrategyAprOracle.sol",
    "src/interfaces/IBaseLSTAccumulator.sol",
    "src/interfaces/IStrategyInterface.sol",
    "src/interfaces/IStrategy4626Interface.sol",
    "src/interfaces/ICurve.sol",
    "src/interfaces/IQueue.sol",
    "src/interfaces/ISTETH.sol",
    "src/interfaces/IWETH.sol",
    "src/interfaces/IWstETH.sol",
    "script/Deploy.s.sol",
    "script/Deploy4626.s.sol",
    "script/Deploy4626Factory.s.sol",
]

EXCLUDE_PATHS = [
    "src/test/**",
    "test/**",
    "mocks/**",
    "lib/**",
    "out/**",
    "cache/**",
    "broadcast/**",
    ".audit/**",
    "x-ray/**",
    "scanner reports",
    "cached analysis",
]


def rel(path: Path) -> str:
    return path.relative_to(SCAN_DIR).as_posix()


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_ledger(candidate_id: str, row: dict[str, object]) -> None:
    ledger = FINDINGS_DIR / candidate_id / "candidate_ledger.jsonl"
    existing = ledger.read_text(encoding="utf-8") if ledger.exists() else ""
    for line in existing.splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("phase") == row["phase"] and payload.get("candidate_id") == candidate_id:
            return
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


ATTACK_REPORTS = {
    "CS-351C58EB-001": {
        "title": "Lido withdrawal return data encodes a request-id array but the normal claim path decodes a scalar id",
        "decision": "ignore",
        "severity": "ignore",
        "impact": "medium",
        "likelihood": "low",
        "report": """# Attack Path Analysis: CS-351C58EB-001

## Title

Lido withdrawal return data encodes a request-id array but the normal claim path decodes a scalar id

## Attack Path

1. Management calls `initiateLSTWithdrawal`, which increments `pendingRedemptions` and returns bytes from `Strategy._initiateLSTWithdrawal`.
2. `Strategy._initiateLSTWithdrawal` calls Lido `requestWithdrawals`, receives a `uint256[] requestIds`, and returns `abi.encode(requestIds)`.
3. A keeper later calls `claimLSTWithdrawal` with claim data. The internal claim path decodes the bytes as a scalar `uint256` instead of `uint256[]`.
4. If the operator hands the raw initiation bytes to the claim path, the scalar decode reads the dynamic-array offset word, not the actual request id, so the claim targets the wrong request and `pendingRedemptions` can remain nonzero.

## Facts

- Service mapping: Yearn V3 stETH accumulator Lido withdrawal queue workflow.
- Entry points: `initiateLSTWithdrawal` is management-only; `claimLSTWithdrawal` is keeper-only.
- Trust boundary: management and keepers are privileged operational roles in the threat model.
- Reachability: no lower-privileged depositor or outside caller can initiate or claim the Lido queue request through this path.
- Existing controls: reports block while `pendingRedemptions` is nonzero, and emergency/manual claim/reset paths exist for authorized operators.

## Counterevidence

The strongest counterevidence is that this is an operator-workflow data-shape mismatch rather than an untrusted attacker path. Existing fork tests succeed by decoding the returned array and re-encoding the scalar request id before claim. The bug remains real for raw-return-data operational handoff, but the scan policy suppresses privileged-only workflow hazards unless they establish a meaningful lower-privileged attack path or privilege delta.

## Severity Calibration

- Impact: medium. A malformed claim can block reports through nonzero `pendingRedemptions` and require emergency/manual recovery.
- Likelihood: low. Exploitation depends on management/keeper workflow behavior and no untrusted caller can supply the normal initiation/claim sequence.
- Matrix result: ignore.

## Final Policy Decision

`ignore`. Keep the validation artifact as an operational fix candidate, but do not emit a final security finding.
""",
        "ledger": {
            "phase": "attack_path",
            "status": "ignore",
            "candidate_id": "CS-351C58EB-001",
            "artifact": "artifacts/05_findings/CS-351C58EB-001/attack_path_analysis_report.md",
            "decision": "ignore",
            "impact": "medium",
            "likelihood": "low",
            "facts": "The ABI mismatch is real, but only management and keeper workflows can reach the normal initiation/claim path; no lower-privileged attacker path was established.",
            "counterevidence": "Existing tests decode the returned array and re-encode the scalar id; emergency/manual recovery exists.",
        },
    },
    "CS-351C58EB-002": {
        "title": "stakeAsset disable switch is bypassed by keeper report and tend paths",
        "decision": "report",
        "severity": "low",
        "impact": "medium",
        "likelihood": "medium",
        "report": """# Attack Path Analysis: CS-351C58EB-002

## Title

stakeAsset disable switch is bypassed by keeper report and tend paths

## Attack Path

1. Management calls `setStakeAsset(false)` to disable automatic staking of idle WETH.
2. `_deployFunds` honors `stakeAsset` and does not stake new deposits while the flag is disabled.
3. A keeper can still trigger `report` or `tend`; both paths call `_stake` without checking `stakeAsset`.
4. Idle WETH is converted to stETH or routed onward by the concrete strategy despite the management risk switch.

## Facts

- Service mapping: Yearn V3 strategy reporting and tending.
- Entry points: inherited keeper report/tend callbacks reach `_harvestAndReport` and `_tend`.
- Trust boundary: keepers are privileged, but lower-trust than management for risk-parameter changes.
- Reachability: a keeper can trigger the path after management disables staking; the behavior was confirmed by the focused fork test `test_harvestStakesBypassesStakeAssetFlag`.
- Existing controls: report staking is bounded by `availableDepositLimit`; tend staking uses the idle amount passed by the inherited strategy.

## Counterevidence

The path is keeper-gated and cannot be triggered by arbitrary depositors. There is also some design ambiguity: the comment on `stakeAsset` mentions deposits, while the setter comment mentions harvest. Those facts limit severity, but they do not defeat reportability because the flag is presented as the strategy's staking switch and management is the role authorized to set it.

## Severity Calibration

- Impact: medium. Keeper-triggered staking can reintroduce Lido or downstream vault exposure and reduce liquidity after management attempted to disable that risk.
- Likelihood: medium. The caller must be a keeper, but keeper report/tend is a normal production workflow.
- Matrix result: low.

## Final Policy Decision

`report`. Emit as a low-severity privilege-boundary/control-bypass finding.
""",
        "ledger": {
            "phase": "attack_path",
            "status": "reportable",
            "candidate_id": "CS-351C58EB-002",
            "artifact": "artifacts/05_findings/CS-351C58EB-002/attack_path_analysis_report.md",
            "decision": "report",
            "severity": "low",
            "impact": "medium",
            "likelihood": "medium",
            "facts": "Keeper report/tend reaches `_stake` after management disables `stakeAsset`; this crosses the management risk-control boundary but remains keeper-gated.",
            "counterevidence": "Not reachable by arbitrary depositors; some setter/comment ambiguity lowers severity.",
        },
    },
    "CS-351C58EB-003": {
        "title": "Donated loose stETH/wstETH can exceed downstream ERC4626 maxDeposit and revert maintenance flows",
        "decision": "report",
        "severity": "medium",
        "impact": "medium",
        "likelihood": "high",
        "report": """# Attack Path Analysis: CS-351C58EB-003

## Title

Donated loose stETH/wstETH can exceed downstream ERC4626 maxDeposit and revert maintenance flows

## Attack Path

1. Any external account transfers stETH or wstETH directly to the `Strategy4626` address.
2. The strategy's `availableDepositLimit` limits new WETH acceptance using the downstream vault's `maxDeposit(address(this))`.
3. During report, tend, deposit deployment, or manual stake, `Strategy4626._stake` wraps all loose stETH and then deposits the entire loose wstETH balance into the downstream vault.
4. If the donated loose wstETH balance exceeds the downstream vault's current `maxDeposit`, `vault.deposit` reverts and blocks the maintenance flow.

## Facts

- Service mapping: `Strategy4626` maintenance flow crossing WETH, stETH, wstETH, and a downstream ERC4626 vault.
- Entry points: direct ERC20 donations are permissionless; the reverting deposit is triggered by normal keeper/management/deposit maintenance calls.
- Trust boundary: the attacker cannot call `_stake` directly, but can alter the strategy's token balance before an authorized maintenance call.
- Reachability: the disposable Foundry PoC copied the target code, donated loose wstETH, bounded the mock vault's max deposit, and observed the expected ERC4626 max-deposit revert.
- Existing controls: `availableDepositLimit` checks `vault.maxDeposit`, but only for the new WETH deposit limit, not for the actual loose wstETH amount passed to `vault.deposit`.

## Counterevidence

The attacker must donate value and needs an authorized maintenance call to trigger the revert. Existing emergency methods can redeem or unwrap balances in some states. These factors constrain impact to availability/griefing rather than theft, but they do not remove the unauthenticated donation boundary or the direct PoC.

## Severity Calibration

- Impact: medium. The bug can block deposits, reports, tends, or manual staking for affected vault configurations and force operator intervention.
- Likelihood: high. Direct token transfers are permissionless and a very small donation can be enough when `maxDeposit` is zero or nearly exhausted.
- Matrix result: medium.

## Final Policy Decision

`report`. Emit as a medium-severity donation-griefing and ERC4626 limit-bypass finding.
""",
        "ledger": {
            "phase": "attack_path",
            "status": "reportable",
            "candidate_id": "CS-351C58EB-003",
            "artifact": "artifacts/05_findings/CS-351C58EB-003/attack_path_analysis_report.md",
            "decision": "report",
            "severity": "medium",
            "impact": "medium",
            "likelihood": "high",
            "facts": "An unauthenticated donor can alter loose stETH/wstETH balance before a keeper/management/deposit-triggered `_stake`, and `_stake` deposits the whole loose wstETH amount without rechecking `maxDeposit`.",
            "counterevidence": "The attack is griefing, not theft; it requires donated value and an authorized maintenance trigger.",
        },
    },
    "CS-351C58EB-004": {
        "title": "Standalone Strategy4626 deployment logs intended management but leaves deployer-controlled defaults",
        "decision": "ignore",
        "severity": "ignore",
        "impact": "medium",
        "likelihood": "ignore",
        "report": """# Attack Path Analysis: CS-351C58EB-004

## Title

Standalone Strategy4626 deployment logs intended management but leaves deployer-controlled defaults

## Attack Path

1. An operator runs `script/Deploy4626.s.sol`.
2. The script constructs a `Strategy4626` and stops broadcasting without applying role, fee, keeper, emergency admin, or pending-management setters.
3. The logs print an intended management address and tell management to call `acceptManagement`, but the script never sets that address as pending management.

## Facts

- Service mapping: deployment script for a direct `Strategy4626` instance.
- Entry points: developer/operator broadcast of a deployment script.
- Trust boundary: the script and broadcast account are developer/operator controlled.
- Reachability: no runtime caller can exploit this after a correct deployment; the issue exists only if a trusted deployer uses this script without review or repair.
- Existing controls: the factory deployment path does set roles after construction, and the direct `Deploy.s.sol` path applies setup controls for the non-4626 strategy.

## Counterevidence

This is a real deployment footgun, but it is a protected-write-path/developer-only precondition. No broadcast artifact was inspected showing it was used in production, and the deployer can repair configuration before deposits. Under the policy matrix, developer-only deployment mistakes are suppressed unless they create an attacker-reachable privilege delta.

## Severity Calibration

- Impact: medium. A mistakenly broadcast direct strategy can leave the deployer with unintended authority and unset operational roles.
- Likelihood: ignore. The precondition is trusted operator misuse of a deploy script, not a reachable runtime attack path.
- Matrix result: ignore.

## Final Policy Decision

`ignore`. Keep as a deployment hardening note in reviewed surfaces, not a final security finding.
""",
        "ledger": {
            "phase": "attack_path",
            "status": "ignore",
            "candidate_id": "CS-351C58EB-004",
            "artifact": "artifacts/05_findings/CS-351C58EB-004/attack_path_analysis_report.md",
            "decision": "ignore",
            "impact": "medium",
            "likelihood": "ignore",
            "facts": "The direct deployment script omits setup, but only a trusted deployer running the script can create the bad state.",
            "counterevidence": "Factory and direct non-4626 scripts set roles; no production broadcast proved use of this direct script.",
        },
    },
    "CS-351C58EB-005": {
        "title": "StrategyAprOracle returns a constant 4% APR for any strategy and debt delta",
        "decision": "ignore",
        "severity": "ignore",
        "impact": "unknown",
        "likelihood": "ignore",
        "report": """# Attack Path Analysis: CS-351C58EB-005

## Title

StrategyAprOracle returns a constant 4% APR for any strategy and debt delta

## Attack Path

1. `StrategyAprOracle.aprAfterDebtChange` ignores `_strategy` and `_delta` and returns `4e16`.
2. If this oracle were registered as a production debt-allocation oracle, it could mislead allocators about expected APR.
3. The scan found no in-repo deployment, registration, or production wiring path for this oracle.

## Facts

- Service mapping: periphery APR oracle source file.
- Entry points: external view oracle function.
- Trust boundary: no attacker-controlled runtime path to allocator decisions was established from repository evidence.
- Reachability: production registration is unproven; constructor labels the oracle `Strategy Apr Oracle Example`.
- Existing controls: none in the oracle logic itself, but absence of production wiring is decisive for final reportability in this scan.

## Counterevidence

The behavior is static and poor for a real allocator oracle, but the strongest repository counterevidence is that the only source label calls it an example and production deploy/registration searches found no consumer path. Missing external deployment evidence lowers confidence, and the repository does not establish an in-scope attacker path.

## Severity Calibration

- Impact: unknown. Misallocation impact depends entirely on external registration and consumers.
- Likelihood: ignore. No production workflow or attacker path was established in the scanned repo.
- Matrix result: ignore.

## Final Policy Decision

`ignore`. Record as a rejected/deferred surface; rerun a targeted review if external registration evidence is later supplied.
""",
        "ledger": {
            "phase": "attack_path",
            "status": "ignore",
            "candidate_id": "CS-351C58EB-005",
            "artifact": "artifacts/05_findings/CS-351C58EB-005/attack_path_analysis_report.md",
            "decision": "ignore",
            "impact": "unknown",
            "likelihood": "ignore",
            "facts": "Constant APR behavior is confirmed, but no production registration or attacker-reachable allocator path was established.",
            "counterevidence": "Constructor name includes Example and repository searches found no deploy or registration path.",
        },
    },
}


def attack_path_artifacts() -> None:
    scan_level = ["# Attack Path Analysis Report", "", f"Scan id: `{SCAN_ID}`", ""]
    scan_level.append("| Candidate | Decision | Severity | Impact | Likelihood | Artifact |")
    scan_level.append("| --- | --- | --- | --- | --- | --- |")
    for candidate_id, entry in ATTACK_REPORTS.items():
        finding_dir = FINDINGS_DIR / candidate_id
        report_path = finding_dir / "attack_path_analysis_report.md"
        write_text(report_path, entry["report"])
        append_ledger(candidate_id, entry["ledger"])
        scan_level.append(
            f"| `{candidate_id}` | {entry['decision']} | {entry['severity']} | "
            f"{entry['impact']} | {entry['likelihood']} | `{rel(report_path)}` |"
        )
    write_text(FINDINGS_DIR / "attack_path_analysis_report.md", "\n".join(scan_level))


def final_findings() -> dict[str, object]:
    return {
        "documentType": "codex-security.findings",
        "schemaVersion": "1.0",
        "scanId": SCAN_ID,
        "findings": [
            {
                "ruleId": "web3.erc4626.donation-maxdeposit-dos",
                "identity": {
                    "anchor": "strategy4626-loose-wsteth-maxdeposit",
                    "instance": "src/strategy4626.sol/line-41",
                },
                "title": "Loose wstETH donations can exceed the downstream vault maxDeposit and block maintenance",
                "summary": "`Strategy4626._stake` wraps any loose stETH and deposits the strategy's entire loose wstETH balance into the downstream ERC4626 vault. `availableDepositLimit` consults `vault.maxDeposit(address(this))`, but that cap is applied only to new WETH intake, not to the actual loose wstETH amount sent to `vault.deposit`. An unauthenticated token donor can therefore make the next report, tend, deposit deployment, or manual stake revert when the downstream vault has little or no remaining deposit capacity.",
                "severity": {
                    "level": "medium",
                    "score": 5.2,
                    "scoringSystem": "Codex Security Impact x Likelihood",
                    "vector": "impact=medium,likelihood=high",
                    "rationale": "The issue is externally reachable because anyone can transfer stETH or wstETH directly to the strategy, and the PoC confirmed the revert when loose wstETH exceeds a bounded ERC4626 `maxDeposit`. The consequence is availability and operator-intervention risk rather than direct theft, so medium impact with high likelihood yields medium severity.",
                    "changeConditions": "Severity would rise if a production downstream vault commonly reaches zero headroom with meaningful strategy debt and no practical emergency recovery, and would fall if `_stake` capped the actual deposit amount or if the integrated vault always returns unlimited `maxDeposit`.",
                },
                "confidence": {
                    "level": "high",
                    "rationale": "Direct source tracing plus a disposable Foundry PoC against copied target code confirmed the maxDeposit revert; remaining uncertainty is deployment-specific vault headroom.",
                },
                "taxonomy": {
                    "category": "Donation griefing / ERC4626 limit bypass",
                    "cwe": ["CWE-400: Uncontrolled Resource Consumption"],
                },
                "locations": [
                    {
                        "path": "src/Strategy4626.sol",
                        "startLine": 41,
                        "endLine": 41,
                        "role": "root_control",
                    },
                    {
                        "path": "src/Strategy4626.sol",
                        "startLine": 55,
                        "endLine": 63,
                        "role": "incomplete_limit_check",
                    },
                    {
                        "path": "src/BaseLSTAccumulator.sol",
                        "startLine": 146,
                        "endLine": 153,
                        "role": "keeper_report_entrypoint",
                    },
                ],
                "codeEvidence": [
                    {
                        "id": "stake-deposits-entire-loose-wsteth",
                        "label": "Stake deposits the entire loose wstETH balance",
                        "path": "src/Strategy4626.sol",
                        "startLine": 29,
                        "endLine": 42,
                        "language": "solidity",
                        "code": "function _stake(uint256 _amount) internal virtual override {\n    super._stake(_amount);\n\n    uint256 stethBalance = balanceOfLST();\n    if (stethBalance > 0) {\n        wstETH.wrap(stethBalance);\n    }\n\n    uint256 wstETHBalance = balanceOfWstETH();\n    // Can round to 0 if stethBalance is too small\n    if (wstETHBalance == 0) return;\n\n    vault.deposit(wstETHBalance, address(this));\n}",
                        "explanation": "`_stake` deposits `balanceOfWstETH()` after wrapping all loose stETH, so direct donations are included in the amount sent to the downstream vault.",
                    },
                    {
                        "id": "available-limit-caps-new-weth-only",
                        "label": "maxDeposit only reduces the advertised new deposit limit",
                        "path": "src/Strategy4626.sol",
                        "startLine": 55,
                        "endLine": 63,
                        "language": "solidity",
                        "code": "function availableDepositLimit(address _owner) public view virtual override returns (uint256) {\n    uint256 superLimit = super.availableDepositLimit(_owner);\n    if (superLimit == 0) return 0;\n\n    uint256 maxDeposit = vault.maxDeposit(address(this));\n    if (maxDeposit == type(uint256).max) return superLimit;\n\n    return Math.min(superLimit, _stETHValue(maxDeposit));\n}",
                        "explanation": "The vault cap is used to limit new WETH deposits, but it is not re-applied to the actual loose wstETH balance deposited by `_stake`.",
                    },
                    {
                        "id": "report-enters-stake",
                        "label": "Keeper report calls the staking path",
                        "path": "src/BaseLSTAccumulator.sol",
                        "startLine": 146,
                        "endLine": 153,
                        "language": "solidity",
                        "code": "function _harvestAndReport() internal virtual override returns (uint256 _totalAssets) {\n    require(pendingRedemptions == 0, \"Pending redemptions\");\n\n    _claimAndSellRewards();\n\n    // Stake any loose asset\n    _stake(Math.min(balanceOfAsset(), availableDepositLimit(address(this))));",
                        "explanation": "A normal keeper report can reach `_stake`, where donated loose wstETH is deposited without its own maxDeposit cap.",
                    },
                ],
                "rootCause": {
                    "summary": "The violated invariant is that every downstream ERC4626 `deposit` amount must be bounded by the vault's current `maxDeposit`. The implementation checks `maxDeposit` only while calculating how much new WETH can enter, but the later sink deposits the strategy's full loose wstETH balance, including balances created by direct token transfers.",
                    "evidenceRefs": [
                        "available-limit-caps-new-weth-only",
                        "stake-deposits-entire-loose-wsteth",
                    ],
                },
                "validation": {
                    "method": "static source trace plus disposable Foundry PoC",
                    "summary": "Validation copied the target code into a disposable scan artifact, donated loose wstETH to the strategy, bounded a mock ERC4626 vault's deposit capacity, and observed the expected `ERC4626: deposit more than max` revert.",
                    "evidenceRefs": [
                        "stake-deposits-entire-loose-wsteth",
                        "available-limit-caps-new-weth-only",
                    ],
                    "evidence": [
                        "`env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-path src/test/MaxDepositDonationPoC.t.sol -vv --fork-url https://ethereum.publicnode.com` passed 1/1 in the disposable validation copy.",
                        "The original production build also succeeded with `forge build`.",
                    ],
                    "counterEvidence": [
                        "The attacker sacrifices donated token value and still needs a keeper, management, deposit, or manual-stake trigger to hit the revert.",
                        "Emergency roles may be able to unwind some stuck balances, so the direct impact is availability and intervention cost.",
                    ],
                },
                "attackPath": {
                    "summary": "An unauthenticated donor transfers stETH or wstETH to the strategy, waits for a normal maintenance trigger, and causes `_stake` to call `vault.deposit` with more wstETH than the downstream vault currently accepts.",
                    "dataflow": {
                        "summary": "direct token transfer to strategy -> `balanceOfLST` or `balanceOfWstETH` -> `_stake` wraps/reads loose balance -> `vault.deposit(wstETHBalance, address(this))` -> ERC4626 maxDeposit revert",
                        "source": "permissionless direct stETH or wstETH transfer to the strategy address",
                        "sink": "`vault.deposit(wstETHBalance, address(this))`",
                        "outcome": "maintenance call reverts while the loose balance exceeds downstream vault deposit headroom",
                    },
                    "reachability": {
                        "summary": "The attacker cannot call `_stake` directly, but direct token transfers are permissionless and normal keeper, management, or deposit workflows provide the trigger.",
                        "attacker": "external token donor",
                        "entrypoint": "direct stETH or wstETH transfer followed by report, tend, deposit deployment, or manual stake",
                        "outcome": "availability griefing and operator intervention for affected vault configurations",
                        "preconditions": [
                            "The downstream ERC4626 vault has finite or temporarily exhausted `maxDeposit` for the strategy.",
                            "A subsequent authorized maintenance flow reaches `_stake`.",
                        ],
                    },
                    "evidenceRefs": [
                        "stake-deposits-entire-loose-wsteth",
                        "report-enters-stake",
                    ],
                    "impact": {
                        "level": "medium",
                        "why": "The effect is a stuck maintenance path rather than an asset drain.",
                    },
                    "likelihood": {
                        "level": "high",
                        "why": "Token donation is permissionless and very small donations can matter when vault headroom is zero or near zero.",
                    },
                    "limitations": [
                        "Severity depends on the chosen downstream vault and its live deposit headroom.",
                    ],
                },
                "remediation": "Before calling `vault.deposit`, cap the actual wstETH amount by `vault.maxDeposit(address(this))` and leave surplus wstETH idle or route it through an explicit recovery path. Apply the cap after wrapping loose stETH and before the ERC4626 call, and avoid reverting the whole report/tend path when only donated surplus exceeds vault headroom.",
                "remediationTests": [
                    "Add a bounded ERC4626 mock test where donated loose wstETH exceeds `maxDeposit` and assert report/tend does not revert.",
                    "Add a zero-headroom test that leaves donated wstETH idle while still reporting correctly.",
                ],
                "preventiveControls": [
                    "Treat direct token transfers as attacker-controlled balances in all token-flow reviews.",
                    "For every ERC4626 integration, assert the actual `deposit` amount is no greater than live `maxDeposit` at the sink.",
                ],
                "provenance": {
                    "source": "Codex Security scan 351c58eb discovery, validation, and attack-path artifacts",
                },
                "extensions": {
                    "candidateId": "CS-351C58EB-003",
                    "candidateLedger": "artifacts/05_findings/CS-351C58EB-003/candidate_ledger.jsonl",
                    "validationReport": "artifacts/05_findings/CS-351C58EB-003/validation_report.md",
                    "attackPathReport": "artifacts/05_findings/CS-351C58EB-003/attack_path_analysis_report.md",
                    "confidenceScore": 0.88,
                },
            },
            {
                "ruleId": "web3.strategy.keeper-risk-control-bypass",
                "identity": {
                    "anchor": "baselstaccumulator-stakeasset-keeper-bypass",
                    "instance": "src/baselstaccumulator.sol/line-152",
                },
                "title": "Keeper report and tend paths bypass the management stakeAsset disable switch",
                "summary": "`setStakeAsset(false)` is the management-controlled switch that disables automatic staking in `_deployFunds`, but keeper-triggered report and tend callbacks still call `_stake` without the same guard. A keeper can therefore move idle WETH into stETH or the downstream vault after management disables staking, crossing the intended management risk-control boundary.",
                "severity": {
                    "level": "low",
                    "score": 3.6,
                    "scoringSystem": "Codex Security Impact x Likelihood",
                    "vector": "impact=medium,likelihood=medium",
                    "rationale": "The effect can reintroduce LST/vault exposure and reduce liquidity after management disables staking, but exploitation requires the keeper role and does not let arbitrary users steal funds. The management-vs-keeper privilege delta keeps it reportable while the trusted role precondition lowers severity.",
                    "changeConditions": "Severity would rise if keeper access is permissionless or broadly delegated and management uses `stakeAsset=false` as an emergency stop, and would fall if the project documents separate deposit-only semantics for the flag.",
                },
                "confidence": {
                    "level": "high",
                    "rationale": "Static tracing and an existing focused fork test confirmed report staking after `stakeAsset=false`; remaining uncertainty is intended semantics.",
                },
                "taxonomy": {
                    "category": "Privilege boundary bypass / operational control bypass",
                    "cwe": ["CWE-284: Improper Access Control"],
                },
                "locations": [
                    {
                        "path": "src/BaseLSTAccumulator.sol",
                        "startLine": 152,
                        "endLine": 152,
                        "role": "root_control",
                    },
                    {
                        "path": "src/BaseLSTAccumulator.sol",
                        "startLine": 165,
                        "endLine": 166,
                        "role": "second_entrypoint",
                    },
                    {
                        "path": "src/BaseLSTAccumulator.sol",
                        "startLine": 203,
                        "endLine": 206,
                        "role": "management_control",
                    },
                ],
                "codeEvidence": [
                    {
                        "id": "deploy-funds-honors-stakeasset",
                        "label": "_deployFunds honors the stakeAsset flag",
                        "path": "src/BaseLSTAccumulator.sol",
                        "startLine": 109,
                        "endLine": 112,
                        "language": "solidity",
                        "code": "function _deployFunds(uint256 _amount) internal virtual override {\n    if (stakeAsset && _amount > ASSET_DUST) {\n        _stake(_amount);\n    }\n}",
                        "explanation": "The deposit deployment path treats `stakeAsset` as a guard before staking WETH.",
                    },
                    {
                        "id": "report-stakes-without-flag",
                        "label": "Report stakes idle WETH without checking stakeAsset",
                        "path": "src/BaseLSTAccumulator.sol",
                        "startLine": 146,
                        "endLine": 153,
                        "language": "solidity",
                        "code": "function _harvestAndReport() internal virtual override returns (uint256 _totalAssets) {\n    require(pendingRedemptions == 0, \"Pending redemptions\");\n\n    _claimAndSellRewards();\n\n    // Stake any loose asset\n    _stake(Math.min(balanceOfAsset(), availableDepositLimit(address(this))));",
                        "explanation": "`_harvestAndReport` can be reached by keeper reporting and calls `_stake` even when management has set `stakeAsset` to false.",
                    },
                    {
                        "id": "tend-stakes-without-flag",
                        "label": "Tend stakes idle WETH without checking stakeAsset",
                        "path": "src/BaseLSTAccumulator.sol",
                        "startLine": 165,
                        "endLine": 166,
                        "language": "solidity",
                        "code": "function _tend(uint256 _totalIdle) internal virtual override {\n    _stake(_totalIdle);\n}",
                        "explanation": "`_tend` delegates the idle amount directly to `_stake` without applying the same guard.",
                    },
                    {
                        "id": "management-sets-stakeasset",
                        "label": "Only management can set stakeAsset",
                        "path": "src/BaseLSTAccumulator.sol",
                        "startLine": 203,
                        "endLine": 206,
                        "language": "solidity",
                        "code": "/// @notice Set whether the strategy will stake asset to LST during harvest\nfunction setStakeAsset(bool _stakeAsset) external virtual onlyManagement {\n    stakeAsset = _stakeAsset;\n    emit StakeAssetUpdated(_stakeAsset);\n}",
                        "explanation": "The switch is management-controlled and its notice describes harvest staking, so keeper-triggered report/tend bypasses the management risk control.",
                    },
                ],
                "rootCause": {
                    "summary": "The violated invariant is that the management staking switch should gate all automatic staking paths, not only deposit deployment. The implementation applies the guard in `_deployFunds` but omits it from report and tend callbacks.",
                    "evidenceRefs": [
                        "deploy-funds-honors-stakeasset",
                        "report-stakes-without-flag",
                        "tend-stakes-without-flag",
                        "management-sets-stakeasset",
                    ],
                },
                "validation": {
                    "method": "static source trace and focused fork test",
                    "summary": "Validation traced the flag from `setStakeAsset` to all staking callbacks and used the existing focused fork test to confirm report can stake idle WETH after `stakeAsset` is disabled.",
                    "evidenceRefs": [
                        "report-stakes-without-flag",
                        "tend-stakes-without-flag",
                    ],
                    "evidence": [
                        "`env ETH_RPC_URL=https://ethereum.publicnode.com forge test --match-test test_harvestStakesBypassesStakeAssetFlag -vv --fork-url https://ethereum.publicnode.com` passed 1/1.",
                        "`forge build` succeeded for the production contracts.",
                    ],
                    "counterEvidence": [
                        "The path is keeper-gated and not reachable by arbitrary depositors.",
                        "The state variable comment mentions deposits, which leaves some intent ambiguity, but the setter notice explicitly mentions harvest staking.",
                    ],
                },
                "attackPath": {
                    "summary": "A keeper calls report or tend after management disables `stakeAsset`; the callback reaches `_stake` and converts idle WETH despite the management flag.",
                    "dataflow": {
                        "summary": "`setStakeAsset(false)` -> keeper report/tend -> `_harvestAndReport` or `_tend` -> `_stake` -> Lido/Curve/4626 staking side effect",
                        "source": "keeper-triggered report or tend",
                        "sink": "`_stake` conversion of WETH into LST or downstream vault exposure",
                        "outcome": "management-disabled staking still occurs",
                    },
                    "reachability": {
                        "summary": "The attacker position is a keeper or compromised keeper. That is privileged, but it is lower-trust than management for changing staking risk controls.",
                        "attacker": "keeper role",
                        "entrypoint": "inherited report or tend callback",
                        "outcome": "idle WETH becomes staked after management disabled staking",
                        "preconditions": [
                            "Management has set `stakeAsset` to false.",
                            "The strategy holds idle WETH or receives idle amount from the inherited callback.",
                        ],
                    },
                    "evidenceRefs": [
                        "report-stakes-without-flag",
                        "tend-stakes-without-flag",
                        "management-sets-stakeasset",
                    ],
                    "impact": {
                        "level": "medium",
                        "why": "The keeper can reintroduce illiquidity or LST/vault exposure after management tried to disable it.",
                    },
                    "likelihood": {
                        "level": "medium",
                        "why": "Keeper report/tend is a normal production workflow, but the caller must already have keeper privileges.",
                    },
                    "limitations": [
                        "This does not let arbitrary users move assets and does not by itself drain funds.",
                    ],
                },
                "remediation": "Apply the `stakeAsset` guard consistently in `_harvestAndReport` and `_tend`, or split the configuration into explicitly documented deposit-staking and keeper-maintenance-staking controls. If staking is disabled, report should skip `_stake` and tend should return without moving idle WETH.",
                "remediationTests": [
                    "Add tests that set `stakeAsset=false` and assert `report` does not call the Lido/Curve staking path.",
                    "Add tests that set `stakeAsset=false` and assert `tend` leaves idle WETH unchanged.",
                ],
                "preventiveControls": [
                    "Require every management risk switch to have callback coverage tests across deposit, report, tend, and manual paths.",
                    "Document whether keepers are allowed to override each management-controlled staking mode.",
                ],
                "provenance": {
                    "source": "Codex Security scan 351c58eb discovery, validation, and attack-path artifacts",
                },
                "extensions": {
                    "candidateId": "CS-351C58EB-002",
                    "candidateLedger": "artifacts/05_findings/CS-351C58EB-002/candidate_ledger.jsonl",
                    "validationReport": "artifacts/05_findings/CS-351C58EB-002/validation_report.md",
                    "attackPathReport": "artifacts/05_findings/CS-351C58EB-002/attack_path_analysis_report.md",
                    "confidenceScore": 0.82,
                },
            },
        ],
    }


def final_coverage() -> dict[str, object]:
    surfaces = [
        {
            "id": "surface-strategy4626-erc4626",
            "label": "Strategy4626 ERC4626 integration",
            "disposition": "reported",
            "riskArea": "Token-flow and downstream vault capacity",
            "notes": "Loose stETH/wstETH donation can make `_stake` exceed live downstream `maxDeposit`; final finding CS-351C58EB-003.",
            "receiptRefs": [
                "artifacts/03_coverage/repository_coverage_ledger.md",
                "artifacts/05_findings/CS-351C58EB-003/candidate_ledger.jsonl",
                "artifacts/05_findings/CS-351C58EB-003/validation_report.md",
                "artifacts/05_findings/CS-351C58EB-003/attack_path_analysis_report.md",
            ],
        },
        {
            "id": "surface-baselstaccumulator-stakeasset",
            "label": "BaseLSTAccumulator staking control",
            "disposition": "reported",
            "riskArea": "Keeper versus management trust boundary",
            "notes": "Keeper report and tend paths bypass the management `stakeAsset` switch; final finding CS-351C58EB-002.",
            "receiptRefs": [
                "artifacts/03_coverage/repository_coverage_ledger.md",
                "artifacts/05_findings/CS-351C58EB-002/candidate_ledger.jsonl",
                "artifacts/05_findings/CS-351C58EB-002/validation_report.md",
                "artifacts/05_findings/CS-351C58EB-002/attack_path_analysis_report.md",
            ],
        },
        {
            "id": "surface-lido-queue-claim-data",
            "label": "Lido withdrawal queue initiation and claim data",
            "disposition": "rejected",
            "riskArea": "Asynchronous redemption accounting",
            "notes": "ABI mismatch is validated, but final policy suppressed it because the path is management/keeper workflow-only and existing tests use the safe scalar re-encoding.",
            "receiptRefs": [
                "artifacts/03_coverage/repository_coverage_ledger.md",
                "artifacts/05_findings/CS-351C58EB-001/candidate_ledger.jsonl",
                "artifacts/05_findings/CS-351C58EB-001/validation_report.md",
                "artifacts/05_findings/CS-351C58EB-001/attack_path_analysis_report.md",
            ],
        },
        {
            "id": "surface-deployment-scripts",
            "label": "Deployment scripts and factory role setup",
            "disposition": "rejected",
            "riskArea": "Deployment role configuration",
            "notes": "`Deploy4626.s.sol` omits direct post-deploy role setup, but the precondition is trusted deployer misuse; factory and non-4626 deploy paths apply setup.",
            "receiptRefs": [
                "artifacts/03_coverage/repository_coverage_ledger.md",
                "artifacts/05_findings/CS-351C58EB-004/candidate_ledger.jsonl",
                "artifacts/05_findings/CS-351C58EB-004/validation_report.md",
                "artifacts/05_findings/CS-351C58EB-004/attack_path_analysis_report.md",
                "artifacts/02_discovery/worker_outputs/shard_06_deploy.md",
            ],
        },
        {
            "id": "surface-apr-oracle",
            "label": "StrategyAprOracle APR output",
            "disposition": "rejected",
            "riskArea": "Allocator signal integrity",
            "notes": "Constant 4 percent APR behavior is confirmed, but no production deploy or registration path was found and the constructor labels it an example oracle.",
            "receiptRefs": [
                "artifacts/03_coverage/repository_coverage_ledger.md",
                "artifacts/05_findings/CS-351C58EB-005/candidate_ledger.jsonl",
                "artifacts/05_findings/CS-351C58EB-005/validation_report.md",
                "artifacts/05_findings/CS-351C58EB-005/attack_path_analysis_report.md",
            ],
        },
        {
            "id": "surface-factory",
            "label": "Strategy4626Factory deployment uniqueness and role propagation",
            "disposition": "no_issue_found",
            "riskArea": "Factory deployment provenance",
            "notes": "One strategy per vault mapping, role propagation, and management-gated address updates were reviewed with no surviving issue.",
            "receiptRefs": [
                "artifacts/03_coverage/repository_coverage_ledger.md",
                "artifacts/02_discovery/worker_outputs/shard_03_4626_factory.md",
            ],
        },
        {
            "id": "surface-curve-lido-swap",
            "label": "Curve, Lido staking, and stETH-to-WETH swap routes",
            "disposition": "no_issue_found",
            "riskArea": "External protocol routing and slippage",
            "notes": "Curve staking path uses a 1:1 minimum when selected, manual unwind slippage is caller-controlled, and no untrusted forced unwind path survived.",
            "receiptRefs": [
                "artifacts/03_coverage/repository_coverage_ledger.md",
                "artifacts/02_discovery/worker_outputs/shard_02_strategy.md",
            ],
        },
        {
            "id": "surface-nonapplicable-web-families",
            "label": "RCE, injection, deserialization, SSRF, file, and web sink families",
            "disposition": "not_applicable",
            "riskArea": "Generic application security sink classes",
            "notes": "The production Solidity/deploy surface exposes no process, query, parser, filesystem, HTTP, redirect, template, upload, or deserialization sinks.",
            "receiptRefs": [
                "artifacts/03_coverage/repository_coverage_ledger.md",
            ],
        },
    ]

    return {
        "documentType": "codex-security.coverage",
        "schemaVersion": "1.0",
        "scanId": SCAN_ID,
        "mode": "repository",
        "completeness": "complete",
        "inventoryStrategy": "custom",
        "includePaths": INCLUDE_PATHS,
        "excludePaths": EXCLUDE_PATHS,
        "surfaces": surfaces,
        "explicitExclusions": [
            {
                "pattern": "src/test/**, test/**, mocks/**",
                "reason": "Tests and mocks were excluded as scan input; targeted tests were used only for validation.",
            },
            {
                "pattern": "lib/**",
                "reason": "Vendored dependencies were excluded except when directly relied on for API semantics.",
            },
            {
                "pattern": "out/**, cache/**, broadcast/**",
                "reason": "Build artifacts and cached Foundry output were excluded.",
            },
            {
                "pattern": ".audit/**, x-ray/**, scanner reports, cached analysis",
                "reason": "Prior audit artifacts and scanner output were excluded from scan input.",
            },
        ],
        "deferred": [],
        "openQuestions": [
            {
                "question": "If `StrategyAprOracle` is intended for production registration outside this repository, it needs a targeted oracle-consumer review.",
                "followUpPrompt": "Review the external deployment or registry transaction for `src/periphery/StrategyAprOracle.sol` and determine whether constant `aprAfterDebtChange` can influence debt allocation.",
            }
        ],
    }


def final_manifest(completed_at: str) -> dict[str, object]:
    return {
        "documentType": "codex-security.scan-manifest",
        "schemaVersion": "1.0",
        "scan": {
            "id": SCAN_ID,
            "producer": {
                "name": "Codex Security",
                "version": "0.1.10",
            },
            "status": "completed",
            "startedAt": "2026-07-08T16:45:48Z",
            "completedAt": completed_at,
            "target": {
                "kind": "git_revision",
                "targetId": "521fff28ad978a37115be8995a1d631611fa1d3d",
                "displayName": "steth-accumulator-strategy",
                "remote": "https://github.com/dudesahn/steth-accumulator-strategy.git",
                "revision": "521fff28ad978a37115be8995a1d631611fa1d3d",
            },
            "scope": {
                "includePaths": INCLUDE_PATHS,
                "excludePaths": EXCLUDE_PATHS,
                "summary": "Production-code-only repository scan of first-party Solidity contracts and deploy scripts. Tests, mocks, vendored dependencies, build output, prior audit artifacts, scanner reports, and cached analysis were excluded from scan input.",
                "artifactsReviewed": [
                    "artifacts/01_context/threat_model.md",
                    "artifacts/02_discovery/deep_review_input.jsonl",
                    "artifacts/02_discovery/finding_discovery_report.md",
                    "artifacts/03_coverage/repository_coverage_ledger.md",
                    "artifacts/04_reconciliation/deduped_candidates.jsonl",
                    "artifacts/05_findings/validation_summary.md",
                    "artifacts/05_findings/attack_path_analysis_report.md",
                ],
                "runtimeStatus": "Production contracts compiled with `forge build`; targeted fork tests and one disposable PoC passed. No missing test dependency such as `vyper` was required.",
                "validationMode": "Independent discovery shards, targeted validation, counterevidence review, and attack-path policy calibration.",
                "context": "The scan was anchored to git revision 521fff28ad978a37115be8995a1d631611fa1d3d. Existing untracked `.audit/` material was excluded from scan input and used only as a final mirror destination.",
                "limitations": [
                    "Vendored Yearn, OpenZeppelin, Lido, Curve, WETH, wstETH, and ERC4626 implementations were treated as out of scope except for first-party integration semantics.",
                    "No live production deployment or registry state was used to prove external `StrategyAprOracle` registration.",
                    "Severity for ERC4626 headroom issues depends on the downstream vault selected at deployment time.",
                ],
            },
            "threatModel": {
                "summary": "The repository implements Yearn V3 TokenizedStrategy contracts that accept WETH, stake or swap into stETH, optionally wrap into wstETH and deposit into a downstream ERC4626 vault, and rely on management, keeper, and emergency roles for risk controls and maintenance. The main security objectives are preserving asset/share accounting, preventing unauthorized fund movement, preventing untrusted griefing of reports/tends/deposits, and keeping deployment role configuration consistent.",
                "assets": [
                    "Deposited WETH, stETH, wstETH, ERC4626 vault shares, pending Lido withdrawal claims, Yearn strategy shares, and privileged role authority.",
                    "Allocator APR signals when periphery oracle code is deployed and registered.",
                ],
                "trustBoundaries": [
                    "Depositors and vault allocators are outside the operator boundary and interact through inherited ERC4626 strategy entrypoints.",
                    "Management controls risk parameters, deposit gates, role defaults, manual routes, and deployment setup.",
                    "Keepers can report, tend, and claim withdrawals but should not bypass management-only risk decisions.",
                    "Emergency authorized accounts can perform sensitive recovery actions.",
                    "External protocols such as Lido, Curve, WETH, wstETH, and downstream ERC4626 vaults are external dependencies whose live limits and rates affect safety.",
                ],
                "attackerCapabilities": [
                    "Call public or inherited strategy entrypoints when deposits are open or the caller is allowed.",
                    "Transfer stETH, wstETH, WETH, or ETH directly to strategy addresses.",
                    "Influence public timing around Curve pricing, Lido queue state, and keeper/report execution.",
                    "Compromise or act as a lower-trust keeper for keeper-scoped attack paths.",
                ],
                "securityObjectives": [
                    "Only authorized roles may move funds or change risk parameters.",
                    "Management risk switches must gate the operational callbacks they are documented to control.",
                    "Direct token donations must not make maintenance flows revert or over-report value.",
                    "ERC4626 vault interactions must respect live capacity and unit conversions at the actual sink.",
                    "Deployment scripts must not silently leave strategies under unintended roles.",
                ],
                "assumptions": [
                    "Yearn TokenizedStrategy and periphery base contracts enforce their documented role checks and share-accounting semantics.",
                    "Canonical WETH, stETH, wstETH, Lido withdrawal queue, and Curve contracts behave according to their public APIs.",
                    "Management and emergency roles are trusted; harmful behavior requiring only those roles is generally not a final security finding unless it creates a clear privilege delta.",
                    "Downstream ERC4626 vaults used by `Strategy4626` have wstETH as `asset()` but may have finite live deposit capacity.",
                ],
            },
            "coverageRef": "coverage.json",
            "findingsRef": "findings.json",
        },
    }


def reviewed_surfaces_markdown(coverage: dict[str, object]) -> str:
    lines = [
        "# Reviewed Surfaces",
        "",
        f"Scan id: `{SCAN_ID}`",
        "",
        "| Surface | Risk Area | Outcome | Notes |",
        "| --- | --- | --- | --- |",
    ]
    labels = {
        "reported": "Reported",
        "no_issue_found": "No issue found",
        "rejected": "Rejected",
        "not_applicable": "Not applicable",
        "needs_follow_up": "Needs follow-up",
    }
    for surface in coverage["surfaces"]:  # type: ignore[index]
        lines.append(
            f"| {surface['label']} | {surface.get('riskArea', 'not recorded')} | "
            f"{labels.get(surface['disposition'], surface['disposition'])} | {surface.get('notes', '')} |"
        )
    return "\n".join(lines)


def main() -> None:
    attack_path_artifacts()
    coverage = final_coverage()
    write_text(ARTIFACTS / "03_coverage" / "reviewed_surfaces.md", reviewed_surfaces_markdown(coverage))
    write_json(SCAN_DIR / "findings.json", final_findings())
    write_json(SCAN_DIR / "coverage.json", coverage)
    completed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    write_json(SCAN_DIR / "scan-manifest.json", final_manifest(completed_at))


if __name__ == "__main__":
    main()
