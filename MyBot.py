import logging
import time

from hlt import Game

game = Game("rv-x")
# Then we print our start message to the logs
logging.info("Starting my Settler bot!")


SHIPS_CONTROL_TIMOUT = 10
DELTA_TIME = 1.6


try:
    me = None
    turn = -1
    while True:
        last_time = time.time()
        # Update the map for the new turn and get the latest version
        game_map = game.update_map()
        turn += 1

        command_queue = {}

        ships = game_map.undocked_ship
        nb_ships = SHIPS_CONTROL_TIMOUT

        players = game_map.all_players()


        logging.info('Number of undocked ship %s'% len(ships))
        for ship in ships:
            nb_ships -= 1
            cmd = None

            if turn < 10 and len(players) == 2:
                game_map.assign_ship_short(ship, game_map)
                cmd = game_map.ship_assignment[ship.id]['action'](ship, game_map)
            else:
                game_map.assign_ship(ship, game_map)
                cmd = game_map.ship_assignment[ship.id]['action'](ship, game_map)

            if cmd is not None:
                command_queue[ship.id] = cmd

            if nb_ships <= 0:
                current_time = time.time()
                if current_time - last_time > DELTA_TIME:
                    break
                last_time = current_time
                nb_ships = SHIPS_CONTROL_TIMOUT

        for planet in game_map.all_planets():
            undock = game_map.defend_planet(planet, game_map)
            for k, v in undock.items():
                command_queue[k] = v

        for ship in game_map.undocking_ship:
            command_queue[ship.id] = ship.undock()

        # Send our set of commands to the Halite engine for this turn
        game.send_command_queue(list(command_queue.values()))
    # TURN END
except:
    logging.exception('GAME CRASHED')
# GAME END