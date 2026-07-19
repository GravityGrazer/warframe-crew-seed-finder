#!/usr/bin/env python3
"""
Warframe Crew Member Seed Finder
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


def meets_requirements(stats: dict, minima: dict) -> bool:
    return all(stats.get(skill, 0) >= min_val for skill, min_val in minima.items())


def main():
    print("=" * 55)
    print("   Warframe Crew Member Seed Finder (Elite / Strong)")
    print("=" * 55)
    print()

    # --- Account ID ---
    print("Enter your account owner ID (MongoDB ObjectId, 24 hex chars):")
    print("  (This is the _id from your account, NOT the crew member _id)")
    account_id = input("> ").strip()

    if len(account_id) < 8:
        print("ERROR: Account ID too short.")
        sys.exit(1)

    account_rand_seed = get_account_rand_seed(account_id)
    print(f"\n  Account rand seed: {account_rand_seed} (0x{account_rand_seed:06X})")
    print()

    # --- Tier ---
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

    # --- Minimum stats ---
    print("Enter minimum stat for each skill (0 = no requirement, max 5):")
    minima = {}
    for skill in SKILL_NAMES:
        while True:
            val = input(f"  Min {skill:14s}: ").strip()
            try:
                v = int(val) if val else 0
                if 0 <= v <= 5:
                    minima[skill] = v
                    break
                print("    Must be 0-5.")
            except ValueError:
                print("    Enter a number 0-5.")

    print()
    total_min = sum(minima.values())
    if total_min > skill_points:
        print(f"WARNING: Your minimums sum to {total_min} but only {skill_points} points")
        print("         are distributed. This may take a very long time or be impossible.")
        print()

    # --- Search mode ---
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
            # Sequential
            for lower_32 in range(0x100000000):
                attempt += 1
                seed = build_seed(lower_32, account_rand_seed)
                stats = get_crew_member_skills(seed, skill_points)

                if meets_requirements(stats, minima):
                    found_count += 1
                    elapsed = time.time() - start_time
                    print(f"\n{'='*55}")
                    print(f"  FOUND #{found_count} after {attempt:,} attempts ({elapsed:.1f}s)")
                    print(f"{'='*55}")
                    print_seed_results(seed, lower_32, stats, account_rand_seed)

                    cont = input("\n  Keep searching? (y/n): ").strip().lower()
                    if cont != "y":
                        break

                if attempt % report_interval == 0:
                    elapsed = time.time() - start_time
                    rate = attempt / elapsed if elapsed > 0 else 0
                    print(f"  ...{attempt:>12,} seeds checked | {rate:,.0f}/s | "
                          f"lower_32=0x{lower_32:08X}", end="\r")
        else:
            # Random
            while True:
                attempt += 1
                lower_32 = random.randint(0, 0xFFFFFFFF)
                seed = build_seed(lower_32, account_rand_seed)
                stats = get_crew_member_skills(seed, skill_points)

                if meets_requirements(stats, minima):
                    found_count += 1
                    elapsed = time.time() - start_time
                    print(f"\n{'='*55}")
                    print(f"  FOUND #{found_count} after {attempt:,} attempts ({elapsed:.1f}s)")
                    print(f"{'='*55}")
                    print_seed_results(seed, lower_32, stats, account_rand_seed)

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


def print_seed_results(seed: int, lower_32: int, stats: dict, account_rand_seed: int):
    """Pretty-print a found seed and its stats."""
    print(f"  Seed (decimal) : {seed}")
    print(f"  Seed (hex)     : 0x{seed & MASK64:016X}")
    print(f"  Lower 32 bits  : 0x{lower_32:08X} ({lower_32})")
    print(f"  Account seed   : 0x{account_rand_seed:06X} ({account_rand_seed})")
    print()
    print("  Stats:")
    bar_chart = {0: "□□□□□", 1: "■□□□□", 2: "■■□□□", 3: "■■■□□", 4: "■■■■□", 5: "■■■■■"}
    for skill in SKILL_NAMES:
        val = stats[skill]
        print(f"    {skill:14s}: {val} {bar_chart.get(val, '?')}")
    total = sum(stats.values())
    print(f"    {'TOTAL':14s}: {total}")


if __name__ == "__main__":
    main()
