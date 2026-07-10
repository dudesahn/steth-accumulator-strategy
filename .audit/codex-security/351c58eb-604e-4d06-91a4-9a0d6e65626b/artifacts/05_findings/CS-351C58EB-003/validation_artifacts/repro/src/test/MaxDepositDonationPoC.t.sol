// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.23;

import {Test} from "forge-std/Test.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {ERC4626} from "@openzeppelin/contracts/token/ERC20/extensions/ERC4626.sol";
import {Strategy4626} from "../Strategy4626.sol";
import {IStrategy4626Interface} from "../interfaces/IStrategy4626Interface.sol";

contract BoundedWstETHVault is ERC4626 {
    uint256 public cap;

    constructor(IERC20 asset_, uint256 cap_) ERC20("Bounded wstETH Vault", "bwstETH") ERC4626(asset_) {
        cap = cap_;
    }

    function maxDeposit(address) public view override returns (uint256) {
        return cap;
    }
}

contract MaxDepositDonationPoC is Test {
    address internal constant WETH = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;
    address internal constant WSTETH = 0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0;

    function testDonatedLooseWstethCanRevertTendWhenVaultCapacityIsLower() public {
        BoundedWstETHVault vault = new BoundedWstETHVault(IERC20(WSTETH), 1 ether);
        IStrategy4626Interface strategy =
            IStrategy4626Interface(address(new Strategy4626(WETH, "validation strategy", address(vault))));

        deal(WSTETH, address(strategy), 2 ether);

        vm.expectRevert(bytes("ERC4626: deposit more than max"));
        strategy.tend();
    }
}
