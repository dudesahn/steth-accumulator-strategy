// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.23;

import {Setup, ERC20} from "../../../src/test/utils/Setup.sol";
import {MockWithdrawalQueue} from "../../../src/test/mocks/MockWithdrawalQueue.sol";

contract ClaimDataMismatchPoC is Setup {
    address internal constant WITHDRAWAL_QUEUE = 0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1;

    function setUp() public override {
        super.setUp();

        MockWithdrawalQueue mockQueue = new MockWithdrawalQueue();
        vm.etch(WITHDRAWAL_QUEUE, address(mockQueue).code);
        vm.store(WITHDRAWAL_QUEUE, bytes32(uint256(1)), bytes32(uint256(1)));
        vm.deal(WITHDRAWAL_QUEUE, 1000 ether);
    }

    function test_directForwardOfReturnedClaimDataUsesWrongRequestId() public {
        uint256 amount = 10 ether;
        mintAndDepositIntoStrategy(strategy, user, amount);

        uint256 stethBalance = ERC20(tokenAddrs["STETH"]).balanceOf(address(strategy));

        vm.prank(management);
        bytes memory returnData = strategy.initiateLSTWithdrawal(stethBalance);

        uint256 pendingBefore = strategy.pendingRedemptions();

        // initiateLSTWithdrawal returns abi.encode(uint256[]), while the claim
        // path decodes its bytes argument as a scalar uint256. Forwarding the
        // advertised return data therefore decodes the ABI offset (32), not ID 1.
        vm.prank(keeper);
        vm.expectRevert("Invalid request");
        strategy.claimLSTWithdrawal(returnData);

        assertEq(strategy.pendingRedemptions(), pendingBefore, "pending changed after failed claim");

        // The hidden adapter step used by the committed tests succeeds.
        uint256[] memory requestIds = abi.decode(returnData, (uint256[]));
        vm.prank(keeper);
        uint256 claimed = strategy.claimLSTWithdrawal(abi.encode(requestIds[0]));

        assertApproxEqAbs(claimed, stethBalance, 2, "correctly encoded ID did not claim");
        assertEq(strategy.pendingRedemptions(), 0, "pending not cleared after correct claim");
    }
}
