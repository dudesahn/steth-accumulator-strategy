// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.18;

import {ERC20} from "../../../src/Strategy.sol";
import {Setup4626} from "../../../src/test/utils/Setup4626.sol";

contract Strategy4626EmergencyWithdrawNoopPoC is Setup4626 {
    function test_emergencyWithdrawDoesNotFreeVaultedPosition() public {
        uint256 amount = 10 ether;

        mintAndDepositIntoStrategy(strategy, user, amount);

        uint256 vaultSharesBefore = vault4626.balanceOf(address(strategy4626));
        assertGt(vaultSharesBefore, 0, "no vault position");
        uint256 looseStethBefore = ERC20(tokenAddrs["STETH"]).balanceOf(address(strategy4626));
        assertEq(asset.balanceOf(address(strategy4626)), 0, "unexpected loose WETH");

        vm.prank(emergencyAdmin);
        strategy.shutdownStrategy();

        vm.prank(emergencyAdmin);
        strategy.emergencyWithdraw(type(uint256).max);

        assertEq(vault4626.balanceOf(address(strategy4626)), vaultSharesBefore, "vault position changed");
        assertLe(asset.balanceOf(address(strategy4626)), looseStethBefore + 2, "freed more than pre-existing dust");
        assertLe(strategy.maxRedeem(user), looseStethBefore + 2, "material liquidity was freed");
    }
}
