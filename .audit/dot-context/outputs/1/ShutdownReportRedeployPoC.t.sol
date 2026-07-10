// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.18;

import {Setup, ERC20} from "../../../src/test/utils/Setup.sol";

contract ShutdownReportRedeployPoC is Setup {
    function test_PoC_shutdownReportRedeploysFreedFunds() public {
        uint256 amount = 10 ether;

        mintAndDepositIntoStrategy(strategy, user, amount);

        vm.prank(emergencyAdmin);
        strategy.shutdownStrategy();

        vm.prank(emergencyAdmin);
        strategy.emergencyWithdraw(type(uint256).max);

        uint256 liquidBeforeReport = asset.balanceOf(address(strategy));
        assertGt(liquidBeforeReport, 0, "shutdown did not free liquid WETH");
        assertGt(strategy.maxRedeem(user), 0, "user cannot redeem after emergency withdraw");

        vm.prank(keeper);
        strategy.report();

        assertEq(asset.balanceOf(address(strategy)), 0, "report should have redeployed idle WETH");
        assertEq(strategy.maxRedeem(user), 0, "user withdrawals are blocked again after report");
        assertGt(ERC20(tokenAddrs["STETH"]).balanceOf(address(strategy)), 0, "funds were not restaked into stETH");
    }
}

/*
 * ## Proof Explanation
 *
 * test_PoC_shutdownReportRedeploysFreedFunds proves that the strategy can
 * redeploy liquid funds after shutdown:
 *
 * 1. A user deposits WETH and the strategy stakes it into stETH.
 * 2. The emergency admin shuts the strategy down and calls emergencyWithdraw,
 *    converting stETH back to liquid WETH so users can redeem.
 * 3. A keeper calls report after shutdown.
 * 4. BaseLSTAccumulator._harvestAndReport stakes the idle WETH again because it
 *    does not check TokenizedStrategy.isShutdown().
 * 5. maxRedeem(user) falls back to zero, showing users are blocked again until
 *    another emergency unwind occurs.
 *
 * The assertion on maxRedeem is the key security condition: if the shutdown
 * report path is fixed to avoid redeploying funds, maxRedeem remains non-zero.
 */
