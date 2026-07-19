"""
Warframe Crew Member Seed Finder (Elite / Strong)
Replicates the SRng + getCrewMemberSkills logic from SpaceNinjaServer
to find seeds that produce crew members with desired minimum stats.
"""

import random
import sys
import time

MASK64 = 0xFFFFFFFFFFFFFFFF
MULTIPLIER = 0x5851F42D4C957F2D
INCREMENT = 0x14057B7EF767814F

SKILL_NAMES = ["PILOTING", "GUNNERY", "ENGINEERING", "COMBAT", "SURVIVABILITY"]

# Strong = 12 points, Medium = 10, Base = 8
TIER_POINTS = {
    "strong": 12,
    "medium": 10,
    "base": 8,
}

class SRng:
    """Replicates the SRng class from rngService.ts — Knuth LCG matching the game client."""

    def __init__(self, seed: int):
        self.state = seed & MASK64

    def random_int(self, min_val: int, max_val: int) -> int:
        diff = max_val - min_val
        if diff != 0:
            self.state = (MULTIPLIER * self.state + INCREMENT) & MASK64
            min_val += (int(self.state >> 32) & 0x3FFFFFFF) % (diff + 1)
        return min_val

    def random_float(self) -> float:
        self.state = (MULTIPLIER * self.state + INCREMENT) & MASK64
        return (int(self.state >> 38) & 0xFFFFFF) * 0.000000059604645

def get_account_rand_seed(account_owner_id: str) -> int:
    """Replicates getAccountRandSeed: parseInt(accountOwnerId.substring(2, 8), 16)"""
    return int(account_owner_id[2:8], 16)

def build_seed(lower_32: int, account_rand_seed: int) -> int:
    """
    Replicates: seed |= BigInt(getAccountRandSeed(inventory)) << 32n
    The lower 32 bits come from the random purchase seed;
    bits 32-55 are OR'd with the account-derived seed.
    """
    return (lower_32 & 0xFFFFFFFF) | ((account_rand_seed & 0xFFFFFF) << 32)

def get_crew_member_skills(seed: int, skill_points_to_assign: int = 12) -> dict:
    """
    Replicates the commented-out getCrewMemberSkills function.
    Shuffles skill order using SRng, then distributes skill points round-robin
    with random amounts per skill (max 5 per skill).
    """
    rng = SRng(seed)

    skills = list(SKILL_NAMES)

    # Fisher-Yates-ish shuffle (matches TS: for i = 1..4, swap with randomInt(0, i))
    for i in range(1, 5):
        swap_index = rng.random_int(0, i)
        if swap_index != i:
            skills[i], skills[swap_index] = skills[swap_index], skills[i]

    rng.random_float()  # unused call, but advances state

    # Distribute skill points round-robin
    skill_assignments = [0, 0, 0, 0, 0]
    skill = 0
    remaining = skill_points_to_assign
    while remaining > 0:
        max_increase = min(5 - skill_assignments[skill], remaining)
        increase = rng.random_int(0, max_increase)
        skill_assignments[skill] += increase
        remaining -= increase
        skill = (skill + 1) % 5

    # Sort descending — highest stats get assigned to the first skills in the shuffled order
    skill_assignments.sort(reverse=True)

    combined = {}
    for i in range(5):
        combined[skills[i]] = skill_assignments[i]
    return combined

def validate_requirements(requirements: dict, skill_points: int, req_mode: str):
    """Validate if the requirements are possible given the skill points available."""
    total_req = sum(requirements.values())
    issues = []
    
    for skill, val in requirements.items():
        if val < 0 or val > 5:
            issues.append(f"{skill}: value {val} is out of range (must be 0-5)")
    
    if req_mode == "minimum":
        if total_req > skill_points:
            issues.append(f"Total minimums ({total_req}) exceed available skill points ({skill_points})")
    
    if req_mode == "exact":
        if total_req != skill_points:
            if total_req > skill_points:
                issues.append(f"Total stats ({total_req}) exceed available skill points ({skill_points}) - IMPOSSIBLE")
            else:
                issues.append(f"Total stats ({total_req}) less than available skill points ({skill_points}) - IMPOSSIBLE")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "total_requested": total_req,
        "available": skill_points
    }

def meets_requirements(stats: dict, requirements: dict, req_mode: str) -> bool:
    if req_mode == "exact":
        return all(stats.get(skill, 0) == req_val for skill, req_val in requirements.items())
    else:
        return all(stats.get(skill, 0) >= req_val for skill, req_val in requirements.items())

def main():
    print("=" * 55)
    print("   Warframe Crew Member Seed Finder (Elite / Strong)")
    print("=" * 55)
    print()

    print("Enter your account owner ID (MongoDB ObjectId, 24 hex chars):")
    print("  (This is the _id from your account, NOT the crew member _id)")
    account_id = input("> ").strip()

    if len(account_id) < 8:
        print("ERROR: Account ID too short.")
        sys.exit(1)

    account_rand_seed = get_account_rand_seed(account_id)
    print(f"\n  Account rand seed: {account_rand_seed} (0x{account_rand_seed:06X})")
    print()

    print("Crew member tier:")
    print("  1) Strong  (12 skill points) [elite]")
    print("  2) Medium  (10 skill points)")
    print("  3) Base    (8 skill points)")
    tier_choice = input("Select [1-3], default 1: ").strip() or "1"
    tier_map = {"1": "strong", "2": "medium", "3": "base"}
    tier = tier_map.get(tier_choice, "strong")
    skill_points = TIER_POINTS[tier]
    print(f"\n  Using '{tier}' tier with {skill_points} skill points.")
    print()

    print("Requirement mode:")
    print("  1) Minimum (stats >= entered values)")
    print("  2) Exact   (stats must match entered values exactly)")
    mode_choice = input("Select [1-2], default 1: ").strip() or "1"
    req_mode = "minimum" if mode_choice == "1" else "exact"
    print(f"\n  Mode: {req_mode.upper()}")
    print()

    print(f"Enter stat value for each skill (0-5):")
    print()
    
    requirements = {}
    current_total = 0
    
    for idx, skill in enumerate(SKILL_NAMES):
        skills_remaining = len(SKILL_NAMES) - idx
        points_remaining = skill_points - current_total
        
        if current_total >= skill_points:
            requirements[skill] = 0
            print(f"  {skill:14s}: 0 (ran out of points)")
            continue
        
        if req_mode == "exact":
            max_possible_with_remaining = skills_remaining * 5
            
            if points_remaining > max_possible_with_remaining:
                print(f"\n{'='*55}")
                print(f"  IMPOSSIBLE CONFIGURATION")
                print(f"{'='*55}")
                print(f"  Need {points_remaining} more points but only {skills_remaining} skills left")
                print(f"  Maximum possible with {skills_remaining} skills: {max_possible_with_remaining}")
                print(f"\n  Try reducing earlier skill values.")
                sys.exit(1)
            
            if skills_remaining == 1:
                forced_value = points_remaining
                if forced_value < 0 or forced_value > 5:
                    print(f"\n{'='*55}")
                    print(f"  IMPOSSIBLE CONFIGURATION")
                    print(f"{'='*55}")
                    print(f"  Last skill requires {forced_value} points but max allowed is 5")
                    print(f"\n  Your first 4 skills sum to {current_total}, need {skill_points}")
                    print(f"  Try adjusting your earlier entries.")
                    sys.exit(1)
                requirements[skill] = forced_value
                continue
        
        while True:
            val = input(f"  {skill:14s}: ").strip()
            try:
                v = int(val) if val else 0
                if 0 <= v <= 5:
                    if (current_total + v) > skill_points:
                        print(f"    Exceeds {skill_points} points, try again")
                        continue
                    
                    requirements[skill] = v
                    current_total += v
                    
                    if req_mode == "exact":
                        points_after = skill_points - current_total
                        skills_left = len(SKILL_NAMES) - idx - 1
                        max_possible = skills_left * 5
                        
                        if skills_left > 0 and points_after > max_possible:
                            print(f"    Cannot reach {skill_points} with remaining skills")
                            print(f"    Need {points_after} more from {skills_left} skills (max {max_possible})")
                    
                    break
                print("    Must be 0-5.")
            except ValueError:
                print("    Enter a number 0-5.")

    print()
    validation = validate_requirements(requirements, skill_points, req_mode)
    
    if not validation["valid"]:
        print("=" * 55)
        print("  INVALID REQUIREMENTS DETECTED")
        print("=" * 55)
        print(f"\n  Available skill points: {validation['available']}")
        print(f"  Total requested: {validation['total_requested']}")
        print()
        print("  Issues found:")
        for issue in validation["issues"]:
            print(f"    ✗ {issue}")
        print()
        print("  Please restart and adjust your requirements.")
        sys.exit(1)

    print("Search mode:")
    print("  1) Random  (fast, finds any valid seed)")
    print("  2) Sequential (iterate 0..2^32, exhaustive)")
    mode = input("Select [1-2], default 1: ").strip() or "1"

    print()
    print("-" * 55)
    print("Searching... (Ctrl+C to stop)")
    print()

    found_count = 0
    attempt = 0
    start_time = time.time()
    report_interval = 100_000

    try:
        if mode == "2":
            for lower_32 in range(0x100000000):
                attempt += 1
                seed = build_seed(lower_32, account_rand_seed)
                stats = get_crew_member_skills(seed, skill_points)

                if meets_requirements(stats, requirements, req_mode):
                    found_count += 1
                    elapsed = time.time() - start_time
                    print(f"\n{'='*55}")
                    print(f"  FOUND #{found_count} after {attempt:,} attempts ({elapsed:.1f}s)")
                    print(f"{'='*55}")
                    print_seed_results(seed, stats, requirements, req_mode)

                    cont = input("\n  Keep searching? (y/n): ").strip().lower()
                    if cont != "y":
                        break

                if attempt % report_interval == 0:
                    elapsed = time.time() - start_time
                    rate = attempt / elapsed if elapsed > 0 else 0
                    print(f"  ...{attempt:>12,} seeds checked | {rate:,.0f}/s | "
                          f"lower_32=0x{lower_32:08X}", end="\r")
        else:
            while True:
                attempt += 1
                lower_32 = random.randint(0, 0xFFFFFFFF)
                seed = build_seed(lower_32, account_rand_seed)
                stats = get_crew_member_skills(seed, skill_points)

                if meets_requirements(stats, requirements, req_mode):
                    found_count += 1
                    elapsed = time.time() - start_time
                    print(f"\n{'='*55}")
                    print(f"  FOUND #{found_count} after {attempt:,} attempts ({elapsed:.1f}s)")
                    print(f"{'='*55}")
                    print_seed_results(seed, stats, requirements, req_mode)

                    cont = input("\n  Keep searching? (y/n): ").strip().lower()
                    if cont != "y":
                        break

                if attempt % report_interval == 0:
                    elapsed = time.time() - start_time
                    rate = attempt / elapsed if elapsed > 0 else 0
                    print(f"  ...{attempt:>12,} seeds checked | {rate:,.0f}/s", end="\r")

    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n\nStopped after {attempt:,} attempts ({elapsed:.1f}s)")

    print("\nDone.")

def print_seed_results(seed: int, stats: dict, requirements: dict, req_mode: str):
    """Pretty-print a found seed with stats and requirements comparison."""
    print(f"  Seed: {seed}")
    print()
    
    mode_label = "STATS" if req_mode == "exact" else "CURRENT / MIN"
    print(f"  Skill          | {mode_label:13s}")
    print(f"  ---------------|---------------")
    for skill in SKILL_NAMES:
        current = stats[skill]
        target = requirements[skill]
        if req_mode == "minimum":
            line = f"    {skill:14s}: {current} / {target}"
        else:
            status = "✓" if current == target else "✗"
            line = f"    {skill:14s}: {current} (target: {target}) {status}"
        print(line)
    
    total = sum(stats.values())
    print(f"  {'TOTAL':14s}: {total}")

if __name__ == "__main__":
    main()
