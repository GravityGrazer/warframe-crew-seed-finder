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
Enter your account ID and enter desired crew member stats.

# Using the database
- You can access your SpaceNinjaServer database using something like MongoDB Compass
- Add a new connection and copy your URL which you can find when you start your server "[info] MongoDB server running at [URL]"
- After connecting, go to openWF>inventories>YOUR-INVENTORY-HERE>CrewMembers
- I recommend just buying a cheap crewmate to edit in the database rather than importing it yourself, but there is a example at the bottom if you wish.
- You will have to keep track of what crewmate is who based on syndicate / elite stats of the crew member, the name is generated with the seed so you can't see that in the database.
- Replace the seed with your new generated seed, save it (update) then re-sync in game by using /sync or reloading your game / area

## Notes
- This script does not find bonuses but you can set the stats as you wish but you might need to look around a bit more for something like +25% speed for Vidar.
- Made for 7/19/26 build of SpaceNinjaServer.
- Seed only controls the stats, bonus and name, a Red Veil crew member will always be one unless changed.
- Pro-tip, you can use /sync in Warframe to sync the database after you update it without having to reload your game / data.

## Extra
- https://wiki.warframe.com/w/Railjack/Crew
<details>
<summary>View Crew Member DB Example</summary>

json { "0": { "ItemType": "/Lotus/Types/Game/CrewShip/CrewMember/RedVeilCrewMemberGeneratorMediumVersionTwo", "NemesisFingerprint": { "$numberLong": "0" }, "Seed": { "$numberLong": "1466783333535691" }, "SkillEfficiency": { "PILOTING": { "Assigned": 0 }, "GUNNERY": { "Assigned": 2 }, "ENGINEERING": { "Assigned": 0 }, "COMBAT": { "Assigned": 0 }, "SURVIVABILITY": { "Assigned": 1 } }, "WeaponId": { "$oid": "6a39d69b1fe964707ed0bed5" }, "XP": 0, "PowersuitType": "/Lotus/Powersuits/NpcPowersuits/CrewMemberMaleSuit", "SecondInCommand": true, "_id": { "$oid": "6a4fed8fcc5c85a3e3e00d6b" }, "Configs": [], "AssignedRole": 2, "WeaponConfigIdx": 0 } }
</details> ```
