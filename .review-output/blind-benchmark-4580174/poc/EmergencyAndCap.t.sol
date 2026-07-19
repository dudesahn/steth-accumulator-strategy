// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.23;

import {Setup, ERC20} from "../../../src/test/utils/Setup.sol";
import {MockWithdrawalQueue} from "../../../src/test/mocks/MockWithdrawalQueue.sol";
import {ICurve} from "../../../src/interfaces/ICurve.sol";

contract EmergencyAndCapPoC is Setup {
    address internal constant WITHDRAWAL_QUEUE = 0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1;
    address internal constant CURVE_POOL = 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022;

    function setUp() public override {
        super.setUp();

        MockWithdrawalQueue mockQueue = new MockWithdrawalQueue();
        vm.etch(WITHDRAWAL_QUEUE, address(mockQueue).code);
        vm.store(WITHDRAWAL_QUEUE, bytes32(uint256(1)), bytes32(uint256(1)));
        vm.deal(WITHDRAWAL_QUEUE, 1000 ether);
    }

    function _shutdownAndFree() internal returns (uint256 recovered) {
        mintAndDepositIntoStrategy(strategy, user, 10 ether);

        vm.prank(emergencyAdmin);
        strategy.shutdownStrategy();

        // The committed shutdown tests also require management to configure
        // a nonzero buffer before the emergency admin can unwind below peg.
        vm.prank(management);
        strategy.setReportBuffer(50);

        vm.prank(emergencyAdmin);
        strategy.emergencyWithdraw(type(uint256).max);

        recovered = asset.balanceOf(address(strategy));
        assertGt(recovered, 0, "no WETH recovered");
    }

    function test_keeperCanTendRecoveredFundsAfterShutdownDespiteConfigStops() public {
        uint256 recovered = _shutdownAndFree();

        vm.startPrank(management);
        strategy.setStakeAsset(false);
        strategy.setDepositLimit(0);
        vm.stopPrank();

        vm.prank(keeper);
        strategy.tend();

        assertEq(asset.balanceOf(address(strategy)), 0, "shutdown WETH stayed idle");
        assertGt(ERC20(tokenAddrs["STETH"]).balanceOf(address(strategy)), 0, "WETH was not redeployed");
        assertGt(recovered, 0, "invalid setup");
    }

    function test_reportRedeploysRecoveredFundsAfterShutdownWhenStakeFlagIsFalse() public {
        _shutdownAndFree();

        vm.startPrank(management);
        strategy.setStakeAsset(false);
        strategy.setDoHealthCheck(false);
        vm.stopPrank();

        vm.prank(keeper);
        strategy.report();

        assertEq(asset.balanceOf(address(strategy)), 0, "shutdown WETH stayed idle");
        assertGt(ERC20(tokenAddrs["STETH"]).balanceOf(address(strategy)), 0, "report did not redeploy");
    }

    function test_defaultEmergencyBufferRevertsAtPinnedBelowPegCurveState() public {
        mintAndDepositIntoStrategy(strategy, user, 10 ether);
        uint256 stethBalance = ERC20(tokenAddrs["STETH"]).balanceOf(address(strategy));
        uint256 curveQuote = ICurve(CURVE_POOL).get_dy(1, 0, stethBalance);
        assertLt(curveQuote, stethBalance, "pinned Curve quote is not below 1:1");
        assertEq(strategy.reportBuffer(), 0, "buffer is not default zero");

        vm.prank(emergencyAdmin);
        strategy.shutdownStrategy();

        vm.prank(emergencyAdmin);
        vm.expectRevert();
        strategy.emergencyWithdraw(type(uint256).max);
    }

    function test_pendingQueuePrincipalReopensAndBypassesDepositCap() public {
        uint256 initialDeposit = 100 ether;
        mintAndDepositIntoStrategy(strategy, user, initialDeposit);

        uint256 cap = strategy.estimatedTotalAssets();
        vm.prank(management);
        strategy.setDepositLimit(cap);
        assertEq(strategy.availableDepositLimit(user), 0, "cap not initially exhausted");

        uint256 stethBalance = ERC20(tokenAddrs["STETH"]).balanceOf(address(strategy));
        vm.prank(management);
        strategy.initiateLSTWithdrawal(stethBalance);

        uint256 reopened = strategy.availableDepositLimit(user);
        assertGt(reopened, cap - 1 ether, "queued principal did not reopen cap");

        address secondUser = address(0xBEEF);
        mintAndDepositIntoStrategy(strategy, secondUser, reopened);

        uint256 economicExposure = strategy.pendingRedemptions() + strategy.estimatedTotalAssets();
        assertGt(economicExposure, cap, "pending plus active exposure did not exceed cap");
    }
}
