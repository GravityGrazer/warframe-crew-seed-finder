# Warframe Crew Seed Finder
Warframe SpaceNinjaServer crew member RNG seed finder. Generates crew members with desired skill stats.

This tool reproduces the logic from SpaceNinjaServer, allowing you to bruteforce RNG seeds that generate Warframe crew members meeting your minimum stat requirements for:

- **Piloting**
- **Gunnery**
- **Engineering**
- **Combat**
- **Survivability**

## Requirements

- Python
- No external dependencies (uses standard library only)
- Know how to access and edit SpaceNinjaServer database (make backups)

## Usage (Linux / Windows)
```console
$ python warframe_crew_seed_finder.py
```

## Notes
- This script does not find bonuses but you can set the stats as you wish but you might need to look around a bit more for something like +25% speed for Vidar
- Made for 7/19/26 build of SpaceNinjaServer

## Extra
- https://wiki.warframe.com/w/Railjack/Crew
