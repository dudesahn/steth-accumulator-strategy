// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.23;

import {Test} from "forge-std/Test.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC4626} from "@openzeppelin/contracts/token/ERC20/extensions/ERC4626.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {Strategy4626} from "../../../src/Strategy4626.sol";
import {ISTETH} from "../../../src/interfaces/ISTETH.sol";
import {IStrategy4626Interface} from "../../../src/interfaces/IStrategy4626Interface.sol";

contract BlockingVault is ERC4626 {
    bool public blocked;

    constructor(IERC20 asset_) ERC20("Blocking wstETH Vault", "bwstETH") ERC4626(asset_) {}

    function setBlocked(bool _blocked) external {
        blocked = _blocked;
    }

    function maxRedeem(address owner) public view override returns (uint256) {
        return blocked ? 0 : super.maxRedeem(owner);
    }
}

contract CommentAwareEdgesPoC is Test {
    address internal constant WETH = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address internal constant STETH = 0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84;
    address internal constant WSTETH = 0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0;

    IStrategy4626Interface internal strategy;
    BlockingVault internal vault;

    function setUp() public {
        vault = new BlockingVault(IERC20(WSTETH));
        strategy = IStrategy4626Interface(address(new Strategy4626(WETH, "Comment-aware PoC", address(vault))));
        strategy.setOpen(true);
    }

    function _depositWithStakingDisabled(uint256 amount) internal {
        strategy.setStakeAsset(false);
        deal(WETH, address(this), amount);
        IERC20(WETH).approve(address(strategy), amount);
        strategy.deposit(amount, address(this));
    }

    function _depositAndInvest(uint256 amount) internal {
        deal(WETH, address(this), amount);
        IERC20(WETH).approve(address(strategy), amount);
        strategy.deposit(amount, address(this));
    }

    function test_directTendIgnoresShutdownStakeFlagAndDepositLimit() public {
        _depositWithStakingDisabled(10 ether);
        assertEq(IERC20(WETH).balanceOf(address(strategy)), 10 ether, "deposit was not idle");

        strategy.setDepositLimit(0);
        strategy.shutdownStrategy();

        // The issue response says the deposit limit catches this case, while the
        // fix only applies the limit in tendTrigger(). The callable path does not.
        strategy.tend();

        assertEq(IERC20(WETH).balanceOf(address(strategy)), 0, "tend respected shutdown controls");
        assertGt(vault.balanceOf(address(strategy)), 0, "tend did not redeploy principal");
    }

    function test_zeroUnwrapBlocksOtherwisePossiblePartialManualRecovery() public {
        _depositAndInvest(10 ether);
        assertGt(vault.balanceOf(address(strategy)), 0, "vault position missing");

        // Add liquid stETH after the strategy has established a vault position.
        vm.deal(address(this), 1 ether);
        uint256 minted = ISTETH(STETH).submit{value: 1 ether}(address(0));
        IERC20(STETH).transfer(address(strategy), minted);
        assertGt(IERC20(STETH).balanceOf(address(strategy)), 0, "loose stETH missing");

        // A temporarily illiquid ERC-4626 destination advertises maxRedeem == 0.
        // _freeStETH then calls wstETH.unwrap(0) before the caller can swap the
        // already-liquid stETH amount via its partial-recovery Math.min branch.
        vault.setBlocked(true);
        vm.expectRevert(bytes("wstETH: zero amount unwrap not allowed"));
        strategy.manualSwapToAsset(2 ether, 0);
    }
}
