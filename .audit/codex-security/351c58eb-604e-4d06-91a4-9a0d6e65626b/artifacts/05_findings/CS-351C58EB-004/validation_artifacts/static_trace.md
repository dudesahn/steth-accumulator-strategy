# Static Trace

Validated source/control/sink:

- `script/Deploy4626.s.sol:18`: direct `new Strategy4626(WETH, name, vault)`.
- `script/Deploy4626.s.sol:20`: broadcast stops with no setters.
- `script/Deploy4626.s.sol:26-28`: logs intended management and acceptance note.
- `lib/tokenized-strategy/src/BaseStrategy.sol:138-150`: initialization uses `msg.sender` for management, performance fee recipient, and keeper.
- `lib/tokenized-strategy/src/TokenizedStrategy.sol:453-470`: default fee/unlock/role state is initialized.
- `script/Deploy.s.sol:25-28` and `src/Strategy4626Factory.sol:54-64`: nearby safe setup patterns.
