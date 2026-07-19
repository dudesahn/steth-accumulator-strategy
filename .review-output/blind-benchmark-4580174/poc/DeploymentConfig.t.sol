// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.23;

import {Test} from "forge-std/Test.sol";
import {Strategy4626} from "../../../src/Strategy4626.sol";
import {IStrategy4626Interface} from "../../../src/interfaces/IStrategy4626Interface.sol";

contract DeploymentConfigPoC is Test {
    address internal constant WETH = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address internal constant VAULT = 0xE73b2561309Bed1035D2145275BCA1aEcf85A8F7;
    address internal constant SCRIPT_MANAGEMENT = 0x1b5f15DCb82d25f91c65b53CEe151E8b9fBdD271;

    function test_directDeploymentDoesNotConfigureAdvertisedManagementOrRoles() public {
        IStrategy4626Interface strategy = IStrategy4626Interface(
            address(new Strategy4626(WETH, "wstETH/yvUSD Morpho Lender Borrower Convertor", VAULT))
        );

        // BaseStrategy assigns these roles to the deployer. The standalone
        // Deploy4626 script performs the same constructor call and no setters.
        assertEq(strategy.management(), address(this), "deployer is not management");
        assertEq(strategy.pendingManagement(), address(0), "unexpected pending management");
        assertEq(strategy.keeper(), address(this), "deployer is not keeper");
        assertEq(strategy.performanceFeeRecipient(), address(this), "deployer is not fee recipient");
        assertEq(strategy.emergencyAdmin(), address(0), "unexpected emergency admin");

        vm.prank(SCRIPT_MANAGEMENT);
        vm.expectRevert("!pending");
        strategy.acceptManagement();
    }
}
