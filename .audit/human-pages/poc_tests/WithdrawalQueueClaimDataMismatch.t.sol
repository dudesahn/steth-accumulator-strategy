// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.18;

import {Setup, ERC20} from "../../../src/test/utils/Setup.sol";
import {MockWithdrawalQueue} from "../../../src/test/mocks/MockWithdrawalQueue.sol";

contract WithdrawalQueueClaimDataMismatchPoC is Setup {
    address internal constant WITHDRAWAL_QUEUE = 0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1;

    function setUp() public override {
        super.setUp();

        MockWithdrawalQueue mockQueue = new MockWithdrawalQueue();
        vm.etch(WITHDRAWAL_QUEUE, address(mockQueue).code);
        vm.store(WITHDRAWAL_QUEUE, bytes32(uint256(1)), bytes32(uint256(1)));
        vm.deal(WITHDRAWAL_QUEUE, 1_000 ether);
    }

    function test_initiateReturnDataCannotBePassedDirectlyToClaim() public {
        uint256 amount = 10 ether;
        mintAndDepositIntoStrategy(strategy, user, amount);

        uint256 stethBalance = ERC20(tokenAddrs["STETH"]).balanceOf(address(strategy));

        vm.prank(management);
        bytes memory returnData = strategy.initiateLSTWithdrawal(stethBalance);

        uint256[] memory requestIds = abi.decode(returnData, (uint256[]));
        assertEq(requestIds.length, 1, "request count");
        assertEq(requestIds[0], 1, "request id");

        uint256 wronglyDecodedRequestId = abi.decode(returnData, (uint256));
        assertEq(wronglyDecodedRequestId, 32, "array head offset");

        vm.prank(keeper);
        vm.expectRevert("Invalid request");
        strategy.claimLSTWithdrawal(returnData);

        assertEq(strategy.pendingRedemptions(), stethBalance, "pending should remain after failed direct claim");

        vm.prank(keeper);
        strategy.claimLSTWithdrawal(abi.encode(requestIds[0]));

        assertEq(strategy.pendingRedemptions(), 0, "scalar request id clears pending");
    }
}
