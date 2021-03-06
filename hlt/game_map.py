from .navigation import calculate_distance_between
from hlt.entity import Ship
from . import collision, entity
from .collision import intersect_segment_circle

import logging


class Map:
    """
    Map which houses the current game information/metadata.
    
    :ivar my_id: Current player id associated with the map
    :ivar width: Map width
    :ivar height: Map height
    """

    MAX_SHIPS = 40

    def __init__(self, my_id, width, height):
        """
        :param my_id: User's id (tag)
        :param width: Map width
        :param height: Map height
        """
        self.my_id = my_id
        self.width = width
        self.height = height
        self._players = {}
        self._planets = {}
        self._ghosts = []

        self.foe_ships = None
        self._foe_ships_exit_table = None
        self.planets_assigned = None
        self.ship_assignment = {}

    def get_me(self):
        """
        :return: The user's player
        :rtype: Player
        """
        return self._players.get(self.my_id)

    def get_player(self, player_id):
        """
        :param int player_id: The id of the desired player
        :return: The player associated with player_id
        :rtype: Player
        """
        return self._players.get(player_id)

    def all_players(self):
        """
        :return: List of all players
        :rtype: list[Player]
        """
        return list(self._players.values())

    def get_planet(self, planet_id):
        """
        :param int planet_id:
        :return: The planet associated with planet_id
        :rtype: entity.Planet
        """
        return self._planets.get(planet_id, None)

    def all_planets(self):
        """
        :return: List of all planets
        :rtype: list[entity.Planet]
        """
        return list(self._planets.values())

    def all_ships(self):
        """
        Helper function to extract all ships from all players
        :return: List of ships
        :rtype: List[Ship]
        """
        all_ships = []
        for player in self.all_players():
            all_ships.extend(player.all_ships())
        return all_ships

    def nearby_entities_by_distance(self, entity):
        """
        :param entity: The source entity to find distances from
        :return: Dict containing all entities with their designated distances
        :rtype: dict
        """
        result = {}
        for foreign_entity in self._all_ships() + self.all_planets():
            if entity == foreign_entity:
                continue
            result.setdefault(entity.calculate_distance_between(foreign_entity), []).append(foreign_entity)
        return result

    def _link(self):
        """
        Updates all the entities with the correct ship and planet objects

        :return:
        """
        for celestial_object in self.all_planets() + self._all_ships():
            celestial_object._link(self._players, self._planets)

    def _parse(self, map_string):
        """
        Parse the map description from the game.

        :param map_string: The string which the Halite engine outputs
        :return: nothing
        """
        tokens = map_string.split()

        self._players, tokens = Player._parse(tokens)
        self._planets, tokens = entity.Planet._parse(tokens)

        self._ghosts = []

        assert(len(tokens) == 0)  # There should be no remaining tokens at this point
        self._link()

        self.foe_ships = None
        self.planets_assigned = set(p.id for p in self.all_planets())

        self.ships = 0
        self.fighters = 0
        self.bombers = 0
        self.settlers = 0
        self.defenders = 0
        self.realocate_defender = 0
        self.runners = 0


        self.undocked_ship = []
        self.undocking_ship = []

        self.living_ship = {}

        for s in self.get_me().all_ships():
            self.living_ship[s.id] = True
            if s.docking_status == Ship.DockingStatus.UNDOCKED:
                self.ships += 1
                self.undocked_ship.append(s)
            if s.docking_status == Ship.DockingStatus.UNDOCKING:
                self.undocking_ship.append(s)

        self.foe_ships_assignment = {}
        to_delete = []
        for k, v in self.ship_assignment.items():
            try:
                self.living_ship[k]
            except:
                to_delete.append(k)
                continue

            if v['action'].__name__ == 'fight':
                self.fighters += 1
                try:
                    foe_owner = map.get_player(map.ship_assignment[self.id]['foe'][1])
                    foe = foe_owner.get_ship(map.ship_assignment[self.id]['foe'][0])
                    if foe is None:
                        try:
                            del self.ship_assignment[self.id]['foe']
                        except:
                            pass

                    else:
                        self.foe_ships_assignment[foe.id] = k
                except:
                    pass
                continue
            if v['action'].__name__ == 'bomb':
                self.bombers += 1
                continue
            elif v['action'].__name__ == 'settle':
                self.settlers += 1
                if 'planet' in v:
                    self._planets[v['planet']].anticipating_remaining_resources -= 1
                continue
            elif v['action'].__name__ == 'defend':
                self.defenders += 1
                continue
            elif v['action'].__name__ == 'runner':
                self.runners += 1
                continue
            elif v['action'].__name__ == 'rabbit':
                self.runners += 1
                continue

        for k in to_delete:
            del self.ship_assignment[k]

        self.kamikazes = self.ships - self.MAX_SHIPS

        players = self.all_players()
        planets_by_player = {}

        for planet in list(self.all_planets()):
            if planet.is_owned() is True:
                try:
                    planets_by_player[planet.owner.id].append(planet.id)
                except:
                    planets_by_player[planet.owner.id] = [planet.id, ]

        self.planets_by_player = planets_by_player
        logging.info(self.planets_by_player)

    def all_ghost(self):
        """
        Helper function to extract all ghosts
        :return: List of ghost
        :rtype: List[Circle]
        """
        return self._ghosts

    def _all_ships(self):
        """
        Helper function to extract all ships from all players

        :return: List of ships
        :rtype: List[Ship]
        """
        all_ships = []
        for player in self.all_players():
            all_ships.extend(player.all_ships())
        return all_ships

    def _intersects_entity(self, target):
        """
        Check if the specified entity (x, y, r) intersects any planets. Entity is assumed to not be a planet.

        :param entity.Entity target: The entity to check intersections with.
        :return: The colliding entity if so, else None.
        :rtype: entity.Entity
        """
        for celestial_object in self._all_ships() + self.all_planets():
            if celestial_object is target:
                continue
            d = celestial_object.calculate_distance_between(target)
            if d <= celestial_object.radius + target.radius + 0.1:
                return celestial_object
        return None

    def obstacles_between(self, ship, target, ignore=()):
        """
        Check whether there is a straight-line path to the given point, without planetary obstacles in between.

        :param entity.Ship ship: Source entity
        :param entity.Entity target: Target entity
        :param entity.Entity ignore: Which entity type to ignore
        :return: The list of obstacles between the ship and target
        :rtype: list[entity.Entity]
        """
        obstacles = []
        if ignore_ships is False:
            for enemy_ship in self.all_ships():
                if enemy_ship == ship or enemy_ship == target:
                    continue
                if intersect_segment_circle(ship, target, enemy_ship, fudge=ship.pos.radius + 0.1):
                    obstacles.append(enemy_ship)
        if ignore_planets is False:
            for planet in self.all_planets():
                if planet == ship or planet == target:
                    continue
                if intersect_segment_circle(ship, target, planet, fudge=ship.pos.radius + 0.1):
                    obstacles.append(planet)
        return obstacles

    def add_ghost(self, ghost):
        self._ghosts.append(ghost)

    def get_foe_ships(self):

        if self.foe_ships is not None:
            return  self.foe_ships

        self.foe_ships = []
        self._foe_ships_exit_table = {}
        for player in self.all_players():
            self._foe_ships_exit_table[player.id] = {}
            if player.id == self.my_id:
                continue
            self.foe_ships.extend(player.all_ships())
            for s in player.all_ships():
                self._foe_ships_exit_table[player.id][s.id] = s
        return self.foe_ships

    def ship_exist(self, ship):

        if ship is None:
            return  False

        if self.foe_ships is None:
            self.get_foe_ships()

        return ship.id in self._foe_ships_exit_table[ship.owner.id]

    def assign_ship_short(self, ship, map):

        if ship.id in self.ship_assignment and self.ship_assignment[ship.id]['action'].__name__ != 'nothing':
            logging.info('Already Assigned ship: %s %s' % (ship.id, self.ship_assignment[ship.id]['action'].__name__))

        if ship.id in self.ship_assignment and self.ship_assignment[ship.id]['action'].__name__ == 'rabbit' and map.fighters < 2:
            logging.info('Already Assigned ship: %s %s' % (ship.id, self.ship_assignment[ship.id]['action'].__name__))
            return

        foe_ships_by_distance = {}
        for foe_ship in map.get_foe_ships():
            foe_ships_by_distance.setdefault(ship.calculate_distance_between(foe_ship), []).append(foe_ship)

        for distance in sorted(foe_ships_by_distance):
            if distance < 90:
                map.ship_assignment[ship.id] = {'action': Ship.fight}
                return
            elif map.runners < 1:
                map.ship_assignment[ship.id] = {'action': ship.rabbit}
                map.runners += 1
                return


        return self.assign_ship(ship, map)



    def assign_ship(self, ship, map):



        # if self.defenders >= 6 \
        #     and self.realocate_defender < 4 \
        #     and ship.id in self.ship_assignment and self.ship_assignment[ship.id]['action'].__name__ != 'defend':
        #     self.realocate_defender += 1
        #     self.defenders -= 1
        #     self.ship_assignment[ship.id]['action'] = Ship.fight

        if ship.id in self.ship_assignment and self.ship_assignment[ship.id]['action'].__name__ != 'nothing':
            logging.info('Already Assigned ship: %s %s' % (ship.id, self.ship_assignment[ship.id]['action'].__name__))
            return

        logging.info('Assign ship: %s' % ship.id)

        planets_by_distance = {}
        for planet in list(self.all_planets()):
            distance = ship.calculate_distance_between(planet) / (planet.num_docking_spots)
            planets_by_distance.setdefault(distance, []).append(planet)

        for distance in sorted(planets_by_distance.keys()):
            near_planets = planets_by_distance[distance]
            for p in near_planets:
                logging.info('%s %s %s' % (p.id, ship.id, p.anticipating_remaining_resources))
                if (p.is_owned() is False or p.owner.id == self.get_me().id) and p.anticipating_remaining_resources > 0 :
                    self.settlers += 1
                    p.anticipating_remaining_resources -= 1
                    self.ship_assignment[ship.id] = {'action': ship.settle, 'planet': p.id}
                    return

        if self.runners < 1 and len(map.all_players())>2:
            self.ship_assignment[ship.id] = {'action': ship.runner}
            self.runners += 1
            return

        if self.runners < 2 and len(map.all_players())>2:
            self.ship_assignment[ship.id] = {'action': ship.rabbit}
            self.runners += 1
            return

        for distance in sorted(planets_by_distance.keys()):
            near_planets = planets_by_distance[distance]
            for p in near_planets:
                if p.is_owned() is True and p.owner.id != map.get_me().id:
                    self.bombers += 1
                    self.ship_assignment[ship.id] = {'action': ship.bomb, 'planet': p.id}
                    return

        if self.runners < 4 and len(self.all_players()) > 2:
            self.ship_assignment[ship.id] = {'action': ship.rabbit}
            self.runners += 1
            return


        self.ship_assignment[ship.id] = {'action': ship.fight}

    def defend_planet(self, planet, map):

        if planet.is_owned() is False or planet.owner.id != map.get_me().id:
            return {}

        planet_defenders = self.defenders + self.fighters + self.settlers + self.runners

        if planet_defenders > 1:
            return {}

        foe_ships_by_distance = {}

        for foe_ship in map.get_foe_ships():
            foe_ships_by_distance.setdefault(planet.calculate_distance_between(foe_ship), []).append(foe_ship)

        cmd = {}
        docked_ship = iter(planet.all_docked_ships())
        for distance in sorted(foe_ships_by_distance.keys()):
            if distance > planet.DEFENSE_RADIUS + planet.pos.radius:
                break

            for foe_ship in foe_ships_by_distance[distance]:

                if foe_ship.docking_status != Ship.DockingStatus.UNDOCKED:
                    continue

                if planet_defenders > 0:
                    planet_defenders -= 1
                    continue

                logging.info('Try to awake a ship')
                try:
                    ship = next(docked_ship)
                    logging.info('Awake a ship: %s' % ship.id)
                    self.ship_assignment[ship.id] = {'action': ship.defend, 'previous_planet':planet.id}
                    cmd[ship.id] = ship.undock()
                except:
                    logging.exception('Awake a ship failed')
                    return cmd

        return cmd


class Player:
    """
    :ivar id: The player's unique id
    """
    def __init__(self, player_id, ships={}):
        """
        :param player_id: User's id
        :param ships: Ships user controls (optional)
        """
        self.id = player_id
        self._ships = ships

    def all_ships(self):
        """
        :return: A list of all ships which belong to the user
        :rtype: list[entity.Ship]
        """
        return list(self._ships.values())

    def get_ship(self, ship_id):
        """
        :param int ship_id: The ship id of the desired ship.
        :return: The ship designated by ship_id belonging to this user.
        :rtype: entity.Ship
        """
        return self._ships.get(ship_id, None)

    @staticmethod
    def _parse_single(tokens):
        """
        Parse one user given an input string from the Halite engine.

        :param list[str] tokens: The input string as a list of str from the Halite engine.
        :return: The parsed player id, player object, and remaining tokens
        :rtype: (int, Player, list[str])
        """
        player_id, *remainder = tokens
        player_id = int(player_id)
        ships, remainder = entity.Ship._parse(player_id, remainder)
        player = Player(player_id, ships)
        return player_id, player, remainder

    @staticmethod
    def _parse(tokens):
        """
        Parse an entire user input string from the Halite engine for all users.

        :param list[str] tokens: The input string as a list of str from the Halite engine.
        :return: The parsed players in the form of player dict, and remaining tokens
        :rtype: (dict, list[str])
        """
        num_players, *remainder = tokens
        num_players = int(num_players)
        players = {}

        for _ in range(num_players):
            player, players[player], remainder = Player._parse_single(remainder)

        return players, remainder

    def __str__(self):
        return "Player {} with ships {}".format(self.id, self.all_ships())

    def __repr__(self):
        return self.__str__()
