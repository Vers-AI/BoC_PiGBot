# bot/hub/macro.py

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2
from sc2.units import Units

from ares.behaviors.macro import (
    ProductionController,
    SpawnController,
    MacroPlan,
    AutoSupply,
    BuildWorkers,
    ExpansionController,
    GasBuildingController,
)
from ares.consts import UnitRole

from bot.hub.reactions import one_base_reaction
from bot.hub.scouting import control_scout

# Army composition constants (instead of @property on a class)
STANDARD_ARMY = {
    UnitTypeId.IMMORTAL: {"proportion": 0.2, "priority": 2},
    UnitTypeId.COLOSSUS: {"proportion": 0.1, "priority": 3},
    UnitTypeId.HIGHTEMPLAR: {"proportion": 0.45, "priority": 1},
    UnitTypeId.ZEALOT: {"proportion": 0.25, "priority": 0},
}

CHEESE_DEFENSE_ARMY = {
    UnitTypeId.ZEALOT: {"proportion": 0.5, "priority": 0},
    UnitTypeId.STALKER: {"proportion": 0.4, "priority": 1},
    UnitTypeId.ADEPT: {"proportion": 0.1, "priority": 2},
}


async def handle_macro(
    bot,
    iteration: int,
    main_army: Units,
    warp_prism: Units,
    scout_units: Units,
    freeflow: bool,
) -> None:
    """
    Main macro logic: builds units, keeps supply up, reacts to cheese, 
    or transitions to late game. Call this in your bot's on_step.
    """
    # If our build is done and we haven't detected cheese, do standard macro
    if bot.build_order_runner.build_completed and not bot._used_cheese_response:
        macro_plan = MacroPlan()
        macro_plan.add(AutoSupply(base_location=bot.start_location))
        macro_plan.add(ProductionController(STANDARD_ARMY, base_location=bot.start_location))
        bot.register_behavior(
                GasBuildingController(to_count=len(bot.townhalls)*2, max_pending=2)
            )
        
        if not bot._under_attack:
            # TODO need make an optimum way of knowing when is the best time to expand
            bot.register_behavior(
                ExpansionController(to_count=3, max_pending=1)
            )
           
        # Spawn units near Warp Prism if available, else at base
        if warp_prism:
            prism_position = warp_prism[0].position
            macro_plan.add(
                SpawnController(STANDARD_ARMY, spawn_target=prism_position, freeflow_mode=freeflow)
            )
        else:
            macro_plan.add(SpawnController(STANDARD_ARMY, freeflow_mode=freeflow))

        bot.register_behavior(macro_plan)

    # If we detected cheese
    elif bot._cheese_reaction_completed:
        if not bot._under_attack:
            bot.register_behavior(
                ExpansionController(to_count=3, max_pending=1)
            )
            bot.register_behavior(
                GasBuildingController(to_count=len(bot.townhalls)*2, max_pending=2)
            )

            # Build a cheese defense plan
            cheese_defense_plan = MacroPlan()
            cheese_defense_plan.add(AutoSupply(base_location=bot.start_location))
            cheese_defense_plan.add(
                SpawnController(CHEESE_DEFENSE_ARMY, spawn_target=bot.start_location, freeflow_mode=freeflow)
            )
            cheese_defense_plan.add(
                ProductionController(CHEESE_DEFENSE_ARMY, base_location=bot.start_location)
            )

            bot.register_behavior(cheese_defense_plan)

        # Build extra probes
        if bot.townhalls.ready.amount <= 2 and bot.workers.amount < 44:
            bot.register_behavior(
                BuildWorkers(to_count=44)
            )
            _chrono_townhalls(bot)
        elif bot.townhalls.ready.amount == 3 and bot.workers.amount < 66:
            bot.register_behavior(
                BuildWorkers(to_count=66)
            )
            _chrono_townhalls(bot)


    # Scout control or build observer if no scout
    if scout_units and main_army:
        control_scout(bot, scout_units, main_army)
    else:
        if bot.time > 4 * 60:
            if bot.structures(UnitTypeId.ROBOTICSFACILITY).ready:
                if (bot.units(UnitTypeId.OBSERVER).amount < 1 
                    and bot.already_pending(UnitTypeId.OBSERVER) == 0
                    and bot.can_afford(UnitTypeId.OBSERVER)):
                    bot.train(UnitTypeId.OBSERVER)

    

    # Merge Archons if we have at least 2 High Templars
    if bot.units(UnitTypeId.HIGHTEMPLAR).amount >= 2:
        for templar in bot.units(UnitTypeId.HIGHTEMPLAR).ready:
            templar(AbilityId.MORPH_ARCHON)



def _chrono_townhalls(bot) -> None:
    """
    Helper function to chrono your townhalls if possible.
    """
    for th in bot.townhalls:
        if not th.is_idle and th.energy >= 50:
            th(AbilityId.EFFECT_CHRONOBOOST, th)
