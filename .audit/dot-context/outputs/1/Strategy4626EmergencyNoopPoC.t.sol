// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.18;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Setup4626} from "../../../src/test/utils/Setup4626.sol";

contract Strategy4626EmergencyNoopPoC is Setup4626 {
    function test_PoC_strategy4626EmergencyWithdrawDoesNotFreeVaultPosition() public {
        uint256 amount = 10 ether;

        mintAndDepositIntoStrategy(strategy, user, amount);

        uint256 vaultSharesBefore = vault4626.balanceOf(address(strategy4626));
        assertGt(vaultSharesBefore, 0, "normal position was not deposited into vault");
        assertLe(ERC20(tokenAddrs["STETH"]).balanceOf(address(strategy4626)), 2, "unexpected material loose stETH");
        assertEq(asset.balanceOf(address(strategy4626)), 0, "unexpected loose WETH");
        assertLe(strategy4626.maxRedeem(user), 2, "position should be illiquid before emergency unwind");

        vm.prank(emergencyAdmin);
        strategy4626.shutdownStrategy();

        vm.prank(emergencyAdmin);
        strategy4626.emergencyWithdraw(type(uint256).max);

        assertEq(vault4626.balanceOf(address(strategy4626)), vaultSharesBefore, "vault shares should be unchanged");
        assertLe(asset.balanceOf(address(strategy4626)), 2, "emergency withdraw unexpectedly freed material WETH");
        assertLe(strategy4626.maxRedeem(user), 2, "user can materially redeem despite no ERC4626 unwind");
    }
}

/*
 * ## Proof Explanation
 *
 * test_PoC_strategy4626EmergencyWithdrawDoesNotFreeVaultPosition proves that
 * Strategy4626's inherited emergency path does not unwind its normal position:
 *
 * 1. A user deposits WETH into Strategy4626.
 * 2. The strategy stakes to stETH, wraps to wstETH, and deposits wstETH into
 *    the configured ERC4626 vault.
 * 3. The emergency admin shuts the strategy down and calls emergencyWithdraw.
 * 4. BaseLSTAccumulator._emergencyWithdraw checks only loose stETH, sees zero,
 *    and returns.
 * 5. Vault shares remain unchanged, no WETH is freed, and maxRedeem remains
 *    zero for the user.
 *
 * If Strategy4626 overrides _emergencyWithdraw to redeem vault shares and unwrap
 * wstETH, the vault-share and maxRedeem assertions no longer hold.
 */
