import abc
import logging
import math
import random
from enum import Enum

from .navigation import Circle, navigate, calculate_distance_between, calculate_direction, calculate_angle_between, closest_point_to
from . import constants


INTERMEDIATE_RATIO = 0.5

class Entity:
    """
    Then entity abstract base-class represents all game entities possible. As a base all entities possess
    a position, radius, health, an owner and an id. Note that ease of interoperability, Position inherits from
    Entity.

    :ivar id: The entity ID
    :ivar x: The entity x-coordinate.
    :ivar y: The entity y-coordinate.
    :ivar radius: The radius of the entity (may be 0)
    :ivar health: The entity's health.
    :ivar owner: The player ID of the owner, if any. If None, Entity is not owned.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, x, y, radius, health, player, entity_id):
        self.pos = Circle(x, y, radius)
        self.health = health
        self.owner = player
        self.id = entity_id

    def calculate_distance_between(self, target):
        """
        Calculates the distance between this object and the target.

        :param Entity target: The target to get distance to.
        :return: distance
        :rtype: float
        """

        return calculate_distance_between(self.pos, target.pos)

    def calculate_angle_between(self, target):
        """
        Calculates the angle between this object and the target in degrees.

        :param Entity target: The target to get the angle between.
        :return: Angle between entities in degrees
        :rtype: float
        """
        return calculate_angle_between(self.pos, target.pos)


    def closest_point_to(self, target, min_distance=3):
        """
        Find the closest point to the given ship near the given target, outside its given radius,
        with an added fudge of min_distance.

        :param Entity target: The target to compare against
        :param int min_distance: Minimum distance specified from the object's outer radius
        :return: The closest point's coordinates
        :rtype: Position
        """
        circle = closest_point_to(self.pos, target.pos, min_distance)
        return Position(circle.x, circle.y)

    @abc.abstractmethod
    def _link(self, players, planets):
        pass

    def __str__(self):
        return "Entity {} (id: {}) at position: (x = {}, y = {}), with radius = {}" \
            .format(self.__class__.__name__, self.id, int(self.pos.x), int(self.pos.y), int(self.pos.radius))

    def __repr__(self):
        return self.__str__()


class Planet(Entity):
    """
    A planet on the game map.

    :ivar id: The planet ID.
    :ivar x: The planet x-coordinate.
    :ivar y: The planet y-coordinate.
    :ivar radius: The planet radius.
    :ivar num_docking_spots: The max number of ships that can be docked.
    :ivar current_production: How much production the planet has generated at the moment.
                              Once it reaches the threshold, a ship will spawn and this will be reset.
    :ivar remaining_resources: The remaining production capacity of the planet.
    :ivar health: The planet's health.
    :ivar owner: The player ID of the owner, if any. If None, Entity is not owned.

    """

    def __init__(self, planet_id, x, y, hp, radius, docking_spots, current, remaining, owned, owner, docked_ships):
        self.id = planet_id
        self.pos = Circle(x, y, radius)
        self.num_docking_spots = docking_spots
        self.current_production = current
        self.remaining_resources = remaining

        self.health = hp
        self.owner = owner if bool(int(owned)) else None
        self._docked_ship_ids = docked_ships
        self._docked_ships = {}
        self.anticipating_remaining_resources = self.num_docking_spots - len(docked_ships)

    def get_docked_ship(self, ship_id):
        """
        Return the docked ship designated by its id.

        :param int ship_id: The id of the ship to be returned.
        :return: The Ship object representing that id or None if not docked.
        :rtype: Ship
        """
        return self._docked_ships.get(ship_id)

    def all_docked_ships(self):
        """
        The list of all ships docked into the planet

        :return: The list of all ships docked
        :rtype: list[Ship]
        """
        return list(self._docked_ships.values())

    def is_owned(self):
        """
        Determines if the planet has an owner.
        :return: True if owned, False otherwise
        :rtype: bool
        """
        return self.owner is not None

    def nb_available_docking_spots(self):
        """
        Return the number of available spots to dock
        :return:
        """
        return self.num_docking_spots - len(self._docked_ship_ids)

    def is_full(self):
        """
        Determines if the planet has been fully occupied (all possible ships are docked)

        :return: True if full, False otherwise.
        :rtype: bool
        """
        return self.nb_available_docking_spots() <= 0

    def is_free(self, player):
        """
        Check is the planet is free for this player
        :param player:
        :return:
        """
        # If the planet is empty, it's free
        if not self.is_owned():
            return True

        # Check if the planet belong to some else
        if self.owner != player:
            return False

        # Check if the planet is full
        if self.is_full():
            return False

        # The planet is free!
        return True

    def _link(self, players, planets):
        """
        This function serves to take the id values set in the parse function and use it to populate the planet
        owner and docked_ships params with the actual objects representing each, rather than IDs

        :param dict[int, gane_map.Player] players: A dictionary of player objects keyed by id
        :return: nothing
        """
        if self.owner is not None:
            self.owner = players.get(self.owner)
            for ship in self._docked_ship_ids:
                self._docked_ships[ship] = self.owner.get_ship(ship)

    @staticmethod
    def _parse_single(tokens):
        """
        Parse a single planet given tokenized input from the game environment.

        :return: The planet ID, planet object, and unused tokens.
        :rtype: (int, Planet, list[str])
        """
        (plid, x, y, hp, r, docking, current, remaining,
         owned, owner, num_docked_ships, *remainder) = tokens

        plid = int(plid)
        docked_ships = []

        for _ in range(int(num_docked_ships)):
            ship_id, *remainder = remainder
            docked_ships.append(int(ship_id))

        planet = Planet(int(plid),
                        float(x), float(y),
                        int(hp), float(r), int(docking),
                        int(current), int(remaining),
                        bool(int(owned)), int(owner),
                        docked_ships)

        return plid, planet, remainder

    @staticmethod
    def _parse(tokens):
        """
        Parse planet data given a tokenized input.

        :param list[str] tokens: The tokenized input
        :return: the populated planet dict and the unused tokens.
        :rtype: (dict, list[str])
        """
        num_planets, *remainder = tokens
        num_planets = int(num_planets)
        planets = {}

        for _ in range(num_planets):
            plid, planet, remainder = Planet._parse_single(remainder)
            planets[plid] = planet

        return planets, remainder


class Ship(Entity):
    """
    A ship in the game.

    :ivar id: The ship ID.
    :ivar pos: The ship position (Circle)
    :ivar health: The ship's remaining health.
    :ivar DockingStatus docking_status: The docking status (UNDOCKED, DOCKED, DOCKING, UNDOCKING)
    :ivar planet: The ID of the planet the ship is docked to, if applicable.
    :ivar owner: The player ID of the owner, if any. If None, Entity is not owned.
    :ivar velocity Circl: contains vel_x & vel_y
    """

    class DockingStatus(Enum):
        UNDOCKED = 0
        DOCKING = 1
        DOCKED = 2
        UNDOCKING = 3

    def __init__(self, player_id, ship_id, x, y, hp, vel_x, vel_y, docking_status, planet, progress, cooldown):
        self.id = ship_id
        self.pos = Circle(x, y, constants.SHIP_RADIUS)
        self.owner = player_id
        self.health = hp
        self.docking_status = docking_status
        self.planet = planet if (docking_status is not Ship.DockingStatus.UNDOCKED) else None
        self._docking_progress = progress
        self._weapon_cooldown = cooldown
        self.velocity = Circle(vel_x, vel_y, 0)

    def thrust(self, magnitude, angle):
        """
        Generate a command to accelerate this ship.

        :param int magnitude: The speed through which to move the ship
        :param int angle: The angle to move the ship in
        :return: The command string to be passed to the Halite engine.
        :rtype: str
        """
        # restrict magnitude between 0 and MAX_SPEED
        if magnitude > constants.MAX_SPEED:
            logging.ERROR("RECEIVED an invalid thrust ! %s" % magnitude)

        magnitude = min(magnitude, constants.MAX_SPEED)
        magnitude = max(magnitude, 0)
        # we want to round angle to nearest integer, but we want to round
        # magnitude down to prevent overshooting and unintended collisions
        return "t {} {} {}".format(self.id, int(magnitude), round(angle))

    def dock(self, planet):
        """
        Generate a command to dock to a planet.

        :param Planet planet: The planet object to dock to
        :return: The command string to be passed to the Halite engine.
        :rtype: str
        """
        return "d {} {}".format(self.id, planet.id)

    def undock(self):
        """
        Generate a command to undock from the current planet.

        :return: The command trying to be passed to the Halite engine.
        :rtype: str
        """
        return "u {}".format(self.id)

    def navigate(self, target, game_map, speed, max_corrections=90, angular_step=1, ignore_ships=False,
                 ignore_planets=False, ignore_ghosts=False, assassin=False, closest=False,
                 kamikaze=False):
        """
        # Will calculate a valid path between the ship and the target

        :param target: The target to move to
        :param game_map: The game_map used to get the list of obstacles
        :param speed: The maximum speed for this move
        :param max_corrections: The number of retries in trajectory change
        :param angular_step: The step in angle between each trajectory
        :param ignore_ships: Should we ignore ships in obstacles list
        :param ignore_planets:  Should we ignore planets in obstacles list
        :param ignore_ghosts:  Should we ignore ghosts in obstacles list
        :param assassin:  Is the ship an assassin
        :param closest:  Shold we navigate to the target's position? or the closest position within the radius
        :return:
        """

        # Should we navigate to the point directly? or the closest points inside our radius?
        if closest:
            closest_target = self.closest_point_to(target)
        else:
            closest_target = target

        final_speed, angle, ghost = navigate(self.pos, closest_target.pos, game_map, speed, max_corrections=max_corrections, angular_step=angular_step, ignore_ships=ignore_ships,
                                             ignore_planets=ignore_planets, ignore_ghosts=ignore_ghosts, assassin=assassin)

        # If there is a ghost it means we found a way to navigate
        if ghost is not None:
            # Add the ghost to the map
            game_map.add_ghost((self.pos, ghost))
            # Move
            return self.thrust(final_speed, angle)

        # Retry with an intermediate position
        logging.debug("Can't find a path to %s, so Looking for an intermediate position" % target.id)
        # Calculate the intermediate position
        # Take the direction
        new_target = calculate_direction(self.pos, target.pos)
        # Calculate length of the direction
        distance = calculate_distance_between(self.pos, target.pos)

        # Create a new speed, much slower
        new_speed = min(speed, distance)
        new_speed *= INTERMEDIATE_RATIO
        # Apply a ratio to find an intermediate point at "speed" distance
        logging.debug("Going at a new point located at 'speed:%s' distance of the ship" % new_speed)
        if distance != 0:
            new_target.x *= new_speed / distance
            new_target.y *= new_speed / distance

        # Add the direction to the ship position
        new_target.x += self.pos.x
        new_target.y += self.pos.y
        final_speed, angle, ghost = navigate(self.pos, new_target, game_map, new_speed,
                                             max_corrections=max_corrections + 30, angular_step=angular_step,
                                             ignore_ships=ignore_ships, ignore_planets=ignore_planets,
                                             ignore_ghosts=ignore_ghosts, assassin=assassin)


        if ghost is not None:
            game_map.add_ghost((self.pos, ghost))
        else:
            logging.debug("Couldn't find a path for the intermediate position either")

        if kamikaze is True and target == closest_target:
            final_speed = constants.MAX_SPEED
            angle = calculate_angle_between(self.pos, target.pos)

        return self.thrust(final_speed, angle)

    def can_dock(self, planet):
        """
        Determine whether a ship can dock to a planet

        :param Planet planet: The planet wherein you wish to dock
        :return: True if can dock, False otherwise
        :rtype: bool
        """
        return calculate_distance_between(self.pos, planet.pos) <= planet.pos.radius + constants.DOCK_RADIUS + constants.SHIP_RADIUS

    def _link(self, players, planets):
        """
        This function serves to take the id values set in the parse function and use it to populate the ship
        owner and docked_ships params with the actual objects representing each, rather than IDs

        :param dict[int, game_map.Player] players: A dictionary of player objects keyed by id
        :param dict[int, Planet] players: A dictionary of planet objects keyed by id
        :return: nothing
        """
        self.owner = players.get(self.owner)  # All ships should have an owner. If not, this will just reset to None
        self.planet = planets.get(self.planet)  # If not will just reset to none



    DEFENSE_RADIUS = 35

    @staticmethod
    def fight(self, map):

        # alea = random.uniform(0, 100)
        # if alea > 85:
        #     del map.ship_assignment[self.id]
        #     return


        if self.docking_status in [Ship.DockingStatus.DOCKED, Ship.DockingStatus.DOCKING]:
            return self.undock()

        foe = None
        if 'foe' in map.ship_assignment[self.id]:
            try:
                foe_owner = map.get_player(map.ship_assignment[self.id][1])
                foe = foe_owner.get_ship(map.ship_assignment[self.id][0])
                if foe is not None:
                    map.ship_assignment[self.id]['foe'] = (foe.id, foe.owner.id)
            except:
                pass

        if foe is not None and map.ship_exist(foe):
            return self.navigate(self.closest_point_to(foe), map, speed=constants.MAX_SPEED)

        foe_ships_by_distance = {}
        for foe_ship in map.get_foe_ships():
            foe_ships_by_distance.setdefault(self.calculate_distance_between(foe_ship), []).append(foe_ship)

        for distance in sorted(foe_ships_by_distance):

            near_foe_ships = foe_ships_by_distance[distance]
            for foe_ship in near_foe_ships:
                map.ship_assignment[self.id]['foe'] = (foe_ship.id, foe_ship.owner.id)
                return self.navigate(self.closest_point_to(foe_ship), map, speed=constants.MAX_SPEED)



        del map.ship_assignment[self.id]
        return None

    @staticmethod
    def bomb(self, map):

        alea = random.uniform(0, 100)
        if alea > 90:
            map.ship_assignment[self.id]['action'] = Ship.fight

        foe_ship = None

        if 'foe' in map.ship_assignment[self.id]:
            foe_id, foe_owner_id = map.ship_assignment[self.id]['foe']
            foe_ship = map.get_player(foe_owner_id).get_ship(foe_id)

        if foe_ship is not None:
            return self.navigate(self.closest_point_to(foe_ship), map, speed=constants.MAX_SPEED, assassin=True)

        foe_ships_by_distance = {}
        for foe_ship in map.get_foe_ships():
            foe_ships_by_distance.setdefault(self.calculate_distance_between(foe_ship), []).append(foe_ship)

        closest_foe = None
        for distance in sorted(foe_ships_by_distance.keys()):
            if closest_foe is None:
                closest_foe = distance

            near_foe_ships = foe_ships_by_distance[distance]
            for foe_ship in near_foe_ships:
                if foe_ship.docking_status != Ship.DockingStatus.UNDOCKED or distance < 10:
                    map.ship_assignment[self.id]['foe'] = (foe_ship.id, foe_ship.owner.id)
                    return self.navigate(self.closest_point_to(foe_ship), map, speed=constants.MAX_SPEED, assassin=True)
        foe_ship = foe_ships_by_distance[closest_foe][0]
        map.ship_assignment[self.id]['foe'] = (foe_ship.id, foe_ship.owner.id)


        return self.navigate(self.closest_point_to(foe_ship), map, speed=constants.MAX_SPEED, assassin=True)

    @staticmethod
    def defend(self, map):


        if 'position' in  map.ship_assignment[self.id]:
            position = map.ship_assignment[self.id]['position']
        else:
            map.ship_assignment[self.id]['position'] = Position(x=self.pos.x, y=self.pos.y, radius=self.pos.radius)
            position = map.ship_assignment[self.id]['position']

        if self.docking_status in [Ship.DockingStatus.DOCKED, Ship.DockingStatus.DOCKING]:
            return self.undock()

        if self.calculate_distance_between(position) > self.DEFENSE_RADIUS:
            return self.navigate(self.closest_point_to(position), map, speed=constants.MAX_SPEED)

        foe_ships_by_distance = {}
        for foe_ship in map.get_foe_ships():
            foe_ships_by_distance.setdefault(self.calculate_distance_between(foe_ship), []).append(foe_ship)

        for distance in sorted(foe_ships_by_distance.keys()):

            if distance > self.DEFENSE_RADIUS:
                break

            return self.navigate(self.closest_point_to(foe_ships_by_distance[distance][0]), map,
                                 speed=constants.MAX_SPEED)

        map.ship_assignment[self.id]['action'] = Ship.fight
        return Ship.fight(self, map)

    @staticmethod
    def pure_settle(self, map):

        planet = map.get_planet(map.ship_assignment[self.id]['planet'])

        if planet is None:
            map.ship_assignment[self.id]['action'] = Ship.fight
            return Ship.fight(self, map)

        if (planet.is_owned() is False or (planet.is_owned() is True \
                                           and planet.owner.id == map.get_me().id \
                                           and planet.is_full() is False)):
            if self.can_dock(planet):
                del map.ship_assignment[self.id]
                return self.dock(planet)
            else:
                return self.navigate(self.closest_point_to(planet), map,
                                     speed=constants.MAX_SPEED)

        if planet.is_owned() is True and planet.owner.id != map.get_me().id:
            map.ship_assignment[self.id] = {'action': self.bomb,}
            return Ship.bomb(self, map)

        map.ship_assignment[self.id]['action'] = Ship.fight
        return Ship.fight(self, map)



    @staticmethod
    def settle(self, map):

        # if len(map.all_players()) > 2:
        #     alea = random.uniform(0, 100)
        #     if alea > 85:
        #         map.ship_assignment[self.id]['action'] = Ship.pure_settle
        #         return Ship.pure_settle(self, map)

        foe_ships_by_distance = {}
        for foe_ship in map.get_foe_ships():
            foe_ships_by_distance.setdefault(self.calculate_distance_between(foe_ship), []).append(foe_ship)

        for distance in sorted(foe_ships_by_distance.keys()):
            if distance > self.DEFENSE_RADIUS:
                break
            return self.navigate(self.closest_point_to(foe_ships_by_distance[distance][0]), map,
                                 speed=constants.MAX_SPEED)

        planet = map.get_planet(map.ship_assignment[self.id]['planet'])

        if planet is None:
            del map.ship_assignment[self.id]
            return Ship.fight(self, map)

        if (planet.is_owned() is False or (planet.is_owned() is True \
                                           and planet.owner.id == map.get_me().id \
                                           and planet.is_full() is False)) \
                and self.can_dock(planet):
            del map.ship_assignment[self.id]
            return self.dock(planet)

        if distance > 3:
            return self.navigate(self.closest_point_to(planet), map,
                                 speed=constants.MAX_SPEED)

        map.ship_assignment[self.id]['action'] = Ship.fight
        return Ship.fight(self, map)

    @staticmethod
    def nothing(self, map):
        del map.ship_assignment[self.id]
        return None

    @staticmethod
    def kamikaze(self, map):

        if 'planet' in map.ship_assignment[self.id]:
            target = map.get_planet(map.ship_assignment[self.id]['planet'])
            if target is not None:
                final_speed = constants.MAX_SPEED
                angle = calculate_angle_between(self.pos, target.pos)
                cmd = self.thrust(final_speed, angle)
                logging.info('Kamikaze: %s'%cmd)
                return  cmd

        planets_by_distance = {}
        for planet in list(map.all_planets()):
            distance = self.calculate_distance_between(planet)
            planets_by_distance.setdefault(distance, []).append(planet)

        for distance in sorted(planets_by_distance.keys()):
            near_planets = planets_by_distance[distance]

            for planet in near_planets:
                if planet.is_owned() and planet.owner.id != map.get_me().id:
                    map.ship_assignment[self.id]['planet'] = planet.id
                    return self.navigate(self.closest_point_to(planet), map,
                                         speed=constants.MAX_SPEED,
                                         kamikaze=True)

        return None

    def can_dock_by_distance(self, distance, planet):
        return distance < planet.pos.radius + constants.DOCK_RADIUS + constants.SHIP_RADIUS

    @staticmethod
    def _parse_single(player_id, tokens):
        """
        Parse a single ship given tokenized input from the game environment.

        :param int player_id: The id of the player who controls the ships
        :param list[tokens]: The remaining tokens
        :return: The ship ID, ship object, and unused tokens.
        :rtype: int, Ship, list[str]
        """
        (sid, x, y, hp, vel_x, vel_y,
         docked, docked_planet, progress, cooldown, *remainder) = tokens

        sid = int(sid)
        docked = Ship.DockingStatus(int(docked))

        ship = Ship(player_id,
                    sid,
                    float(x), float(y),
                    int(hp),
                    float(vel_x), float(vel_y),
                    docked, int(docked_planet),
                    int(progress), int(cooldown))

        return sid, ship, remainder

    @staticmethod
    def _parse(player_id, tokens):
        """
        Parse ship data given a tokenized input.

        :param int player_id: The id of the player who owns the ships
        :param list[str] tokens: The tokenized input
        :return: The dict of Players and unused tokens.
        :rtype: (dict, list[str])
        """
        ships = {}
        num_ships, *remainder = tokens
        for _ in range(int(num_ships)):
            ship_id, ships[ship_id], remainder = Ship._parse_single(player_id, remainder)
        return ships, remainder


class Position(Entity):
    """
    A simple wrapper for a coordinate. Intended to be passed to some functions in place of a ship or planet.

    :ivar id: Unused
    :ivar pos: The position in Circle
    :ivar health: Unused.
    :ivar owner: Unused.
    """

    def __init__(self, x, y, radius = 0):
        self.pos = Circle(x, y, radius)
        self.health = None
        self.owner = None
        self.id = None

    def _link(self, players, planets):
        raise NotImplementedError("Position should not have link attributes.")