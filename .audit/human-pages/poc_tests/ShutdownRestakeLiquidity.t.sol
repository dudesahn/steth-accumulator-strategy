// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.18;

import {Setup, ERC20} from "../../../src/test/utils/Setup.sol";

contract ShutdownRestakeLiquidityPoC is Setup {
    function test_keeperCanRestakeEmergencyLiquidityAfterShutdown() public {
        uint256 amount = 10 ether;

        mintAndDepositIntoStrategy(strategy, user, amount);

        vm.prank(emergencyAdmin);
        strategy.shutdownStrategy();

        vm.prank(emergencyAdmin);
        strategy.emergencyWithdraw(type(uint256).max);

        uint256 liquidBefore = asset.balanceOf(address(strategy));
        uint256 maxRedeemBefore = strategy.maxRedeem(user);
        assertGt(liquidBefore, 0, "no emergency liquidity");
        assertGt(maxRedeemBefore, 0, "no liquid redemption");

        vm.prank(keeper);
        strategy.tend();

        assertLt(asset.balanceOf(address(strategy)), liquidBefore, "WETH was not restaked");
        assertLt(strategy.maxRedeem(user), maxRedeemBefore, "liquid redemption was not reduced");
        assertGt(ERC20(tokenAddrs["STETH"]).balanceOf(address(strategy)), 0, "no stETH after retend");
    }
}
