# scouting

import numpy as np
from sc2.units import Units
from sc2.position import Point2

from ares.behaviors.combat import CombatManeuver
from ares.behaviors.combat.individual import KeepUnitSafe, PathUnitToTarget
from ares.consts import UnitRole, UnitTreeQueryType


def control_scout(bot, scout_units: Units, main_army: Units) -> None:
    """
    Controls your scouting units: decides whether to follow the main army
    or visit expansion locations when safe.
    """

    # Create a new CombatManeuver to hold the orders for scouts
    scout_actions = CombatManeuver()

    # The air grid for flying scouts, or ground if you have ground scouts
    # (Depending on your scout type; adjust if needed)
    air_grid = bot.mediator.get_air_grid

    # Quick check if we actually have scouts
    if not scout_units:
        return

    # Decide where scouts should go
    # Example: If attacking or under attack, keep the scout near the main army.
    if bot._commenced_attack or bot._under_attack:
        for scout in scout_units:
            # Keep the scout safe if it’s taking damage
            if scout.shield_percentage < 1:
                scout_actions.add(
                    KeepUnitSafe(
                        unit=scout,
                        grid=air_grid
                    )
                )
            else:
                # Follow army at some offset
                direction_vector = (main_army.center - scout.position).normalized
                # e.g., 15 distance in front, or behind, or to the side
                # depending on how you want them to 'shadow' the army
                follow_target = main_army.center.towards(bot.attack_target, 15) - direction_vector * scout.radius
                scout_actions.add(
                    PathUnitToTarget(
                        unit=scout,
                        target=follow_target,
                        grid=air_grid,
                        danger_distance=10
                    )
                )

    else:
        # Peaceful scouting: move scout around expansions or enemy start
        # Create a list of potential scout targets
        # This is your old `targets = self.expansion_locations_list[:5] + [self.enemy_start_locations[0]]`
        # Adjust or parametrize as desired
        targets = bot.expansion_locations_list[:5] + [bot.enemy_start_locations[0]]

        # If we haven't assigned a current scout target, do so
        if not hasattr(bot, 'current_scout_target') or bot.current_scout_target is None:
            if targets:
                bot.current_scout_target = targets[0]

        for scout in scout_units:
            # If damaged, run away
            if scout.shield_percentage < 1:
                scout_actions.add(
                    KeepUnitSafe(
                        unit=scout,
                        grid=air_grid
                    )
                )
            else:
                # If close to the current target, pick the next
                if bot.current_scout_target and scout.distance_to(bot.current_scout_target) < 1:
                    # Move to the next index
                    current_index = targets.index(bot.current_scout_target)
                    if current_index + 1 < len(targets):
                        bot.current_scout_target = targets[current_index + 1]
                    else:
                        # If we've used all targets, reset or set None
                        bot.current_scout_target = None

                # Move to the current target if it exists
                if bot.current_scout_target is not None:
                    scout_actions.add(
                        PathUnitToTarget(
                            unit=scout,
                            target=bot.current_scout_target,
                            grid=air_grid,
                            danger_distance=10
                        )
                    )

    # Register the entire scout action plan
    bot.register_behavior(scout_actions)