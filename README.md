# Wind Waker HD Trainer for macOS (ZeldaWWHDRecomp)

A Python/Tkinter trainer for the native Wind Waker HD port
([ZeldaWWHDRecomp](https://github.com/ZeldaWWHDRecomp/ZeldaWWHDRecomp)). It is a rewrite of the
Cemu trainer; it edits the game's memory directly through Mach APIs.

## Run

1. Start Wind Waker HD and **load a Quest Log** (the save data only exists after that).
2. In Terminal: `sudo python3 trainer.py`
3. Click **Connect / refresh**. The base defaults to `0x200000000000`, where the port maps
   guest memory on macOS; change it only if your build differs.

Tabs: Player (health, magic, rupees, wallet 500/1000/5000, position, breath), Progress,
Equipment, Inventory.

## Permissions

`task_for_pid` needs root on macOS, hence `sudo`. If access is still denied (Mach error 5),
the game app likely uses the hardened runtime. Re-sign your own copy:

```sh
cat > /tmp/ent.plist <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>com.apple.security.get-task-allow</key><true/></dict></plist>
EOF
codesign --force --deep --sign - --entitlements /tmp/ent.plist "/path/to/Wind Waker HD.app"
```

## Notes

- Save data lives on the heap; the trainer follows the pointer at guest `0x101F84DC` (+0x20).
  Values are written live; save in game to keep them.
- Offsets are derived from the port's source and the original Cemu trainer; they have not been
  verified against a running game. Other game versions may differ.
- The port also has built-in cheats in its Gameplay menu.

## Test

`python3 -m unittest`
