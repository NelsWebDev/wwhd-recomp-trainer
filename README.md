# Wind Waker HD Trainer for Cemu (macOS)

A small, native-feeling Python/Tkinter trainer for the macOS version of Cemu. It
uses only Python's standard library and macOS Mach APIs; no Windows .NET or
third-party packages are needed.

## Requirements

- macOS
- Python 3 with Tkinter
- Cemu with **The Legend of Zelda: The Wind Waker HD (US v0 / BCZE01)** loaded

The memory offsets are based on the original trainer's published support for
Cemu 2.6 and the US v0 game. Other game regions, revisions, or emulator builds
may use different memory layouts.

## Run

```sh
python3 trainer.py
```

Start Cemu and load the game before connecting. The trainer looks for a running
process named `Cemu` and reads the `base:` address from Cemu's log in
`~/Library/Application Support/Cemu/log.txt`. If auto-detection does not find
the base, enter the hexadecimal address from the log in the connection panel.

## Permissions (Mach error 5)

macOS only lets administrators inspect another process's memory, so run the
trainer with `sudo` from Terminal (Cemu can stay running as your normal user):

```sh
sudo python3 trainer.py
```

If it is still denied as root, your Cemu build uses the hardened runtime. Re-sign
your own copy with the `get-task-allow` entitlement:

```sh
cat > /tmp/ent.plist <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>com.apple.security.get-task-allow</key><true/></dict></plist>
EOF
codesign --force --deep --sign - --entitlements /tmp/ent.plist /Applications/Cemu.app
```

then restart Cemu. SIP stays enabled.

## Features

- Health, stamina capacity and current stamina, rupees and wallet capacity
- Beedle points, underwater breath, player coordinates and teleportation
- Bracelets, charms, pearls, Triforce fragments, sea-chart discoveries, treasure
  charts, and decoded Triforce charts
- Sword, shield, bomb/arrow capacities and counts, equipment unlocks, inventory
  slots, and songs

Changes are written directly to the running Cemu process and are not saved to
the game automatically. Use at your own risk and make a save-state or game save
before changing values.

## Reference

Feature and game-memory-offset compatibility reference:
[ZeldaWindWakerTrainer-for-CEMU](https://github.com/jamesst20/ZeldaWindWakerTrainer-for-CEMU).
