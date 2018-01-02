"""
Welcome to your first Halite-II bot!

This bot's name is Settler. It's purpose is simple (don't expect it to win complex games :) ):
1. Initialize game
2. If a ship is not docked and there are unowned planets
2.a. Try to Dock in the planet if close enough
2.b If not, go towards the planet

Note: Please do not place print statements here as they are used to communicate with the Halite engine. If you need
to log anything use the logging module.
"""
# Let's start by importing the Halite Starter Kit so we can interface with the Halite engine
import hlt
# Then let's import the logging module so we can print out information
import logging

from hlt import constants
from hlt.entity import Ship, Planet


# GAME START
# Here we define the bot's name as Settler and initialize the game, including communication with the Halite engine.

game = hlt.Game("Settler")
# Then we print our start message to the logs
logging.info("Starting my Settler bot!")

target_planets = {}
number_players = None

def can_dock(distance, planet):
    return distance < planet.radius + constants.DOCK_RADIUS + constants.SHIP_RADIUS


def full_fight(ship, planets, all_planets, foe_ships, game_map, me):
    foe_ships_by_distance = {}
    for foe_ship in foe_ships:
        foe_ships_by_distance.setdefault(ship.calculate_distance_between(foe_ship), []).append(foe_ship)

    first_distance = None
    for distance in sorted(foe_ships_by_distance):
        if first_distance is None:
            first_distance = distance

        near_foe_ships = foe_ships_by_distance[distance]
        for foe_ship in near_foe_ships:
            if foe_ship.docking_status != Ship.DockingStatus.UNDOCKED or distance < 10:
                if foe_ship.planet is not None:
                    target_planets[ship.id] = foe_ship.planet.id
                return ship.navigate(ship.closest_point_to(foe_ship), game_map, speed=hlt.constants.MAX_SPEED)

    return ship.navigate(ship.closest_point_to(foe_ships_by_distance[first_distance][0]), game_map,
                         speed=hlt.constants.MAX_SPEED)


def undocked_ship(ship, planets, all_planets, foe_ships, game_map, me):
    planets_by_distance = {}

    global target_planets


    for planet in list(all_planets.values()):
        distance = ship.calculate_distance_between(planet)
        planets_by_distance.setdefault(distance, []).append(planet)

    for distance in sorted(planets_by_distance):
        near_planets = planets_by_distance[distance]

        for planet in near_planets:

            if (planet.is_owned() is False or (planet.is_owned() is True \
                                               and planet.owner.id == me.id \
                                               and planet.is_full() is False)) \
                    and can_dock(distance, planet):
                return ship.dock(planet)

            if planet.id in planets and distance > 4:
                planets.remove(planet.id)
                return ship.navigate(ship.closest_point_to(planet), game_map,
                                                   speed=hlt.constants.MAX_SPEED)

    # planet_targeted = target_planets.get(ship.id, None)
    # if planet_targeted is not None:
    #     new_planet = all_planets.get(planet_targeted, None)
    #     if new_planet.is_owned() is False and ship.can_dock(new_planet):
    #         return ship.dock(new_planet)

    foe_ships_by_distance = {}
    for foe_ship in foe_ships:
        foe_ships_by_distance.setdefault(ship.calculate_distance_between(foe_ship), []).append(foe_ship)

    first_distance = None
    for distance in sorted(foe_ships_by_distance):
        if first_distance is None:
            first_distance = distance

        near_foe_ships = foe_ships_by_distance[distance]
        for foe_ship in near_foe_ships:
            if foe_ship.docking_status != Ship.DockingStatus.UNDOCKED or distance < 10:
                if foe_ship.planet is not None:
                    target_planets[ship.id] = foe_ship.planet.id
                return ship.navigate(ship.closest_point_to(foe_ship), game_map, speed=hlt.constants.MAX_SPEED)

    return ship.navigate(ship.closest_point_to(foe_ships_by_distance[first_distance][0]), game_map,
                                 speed=hlt.constants.MAX_SPEED)


SHIPS_CONTROL_TIMOUT = 10
DELTA_TIME = 1.7


try:
    import time
    me = None
    while True:
        last_time = time.time()
        # TURN START
        # Update the map for the new turn and get the latest version
        game_map = game.update_map()

        if me is None:
            me = game_map.get_me()


        # Here we define the set of commands to be sent to the Halite engine at the end of the turn
        command_queue = []

        ships = game_map.get_me().all_ships()

        planets = set(p.id for p in game_map.all_planets())
        all_planets = {p.id: p for p in game_map.all_planets()}

        players = game_map.all_players()

        if number_players is None:
            number_players = len(players)


        foe_ships = []
        for player in players:
            if player.id == me.id:
                continue
            foe_ships.extend(player.all_ships())


        nb_ships = SHIPS_CONTROL_TIMOUT

        for ship in ships:
            nb_ships -= 1
            cmd = None

            if (number_players == 2 and ship.id % 3 != 0) or ship.id % 3 == 0:
                if ship.docking_status == Ship.DockingStatus.UNDOCKED:
                    cmd = full_fight(ship, planets, all_planets, foe_ships, game_map, me)
            else:
                if ship.docking_status == Ship.DockingStatus.UNDOCKED:
                    cmd = undocked_ship(ship, planets, all_planets, foe_ships, game_map, me)

            if cmd is not None:
                command_queue.append(cmd)

            if nb_ships <= 0:
                current_time = time.time()
                if current_time - last_time > DELTA_TIME:
                    break
                last_time = current_time
                nb_ships = SHIPS_CONTROL_TIMOUT

        # Send our set of commands to the Halite engine for this turn
        game.send_command_queue(command_queue)
    # TURN END
except:
    logging.exception('GAME CRASHED')
# GAME END