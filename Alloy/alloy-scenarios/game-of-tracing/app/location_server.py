"""Location server implementation."""
import os, sqlite3, requests, random, time, threading
from threading import Thread, Lock
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from game_config import LOCATIONS, COSTS, RESOURCE_GENERATION, DATABASE_FILE
from telemetry import GameTelemetry
from opentelemetry.propagate import extract, inject
from opentelemetry import trace
from opentelemetry.trace import SpanKind
from enum import Enum
from typing import Optional, List, Tuple, Dict

class PathType(Enum):
    RESOURCE = 'resource'
    ATTACK = 'attack'

class LocationServer:
    def __init__(self, location_id):
        self.location_id = location_id
        self.location_info = LOCATIONS[location_id]
        self.app = Flask(__name__)
        self.last_resource_collection = {}
        self.resource_cooldown = {}
        self.lock = Lock()
        
        # Initialize telemetry with consistent service name
        # Always use hyphenated lowercase for service names
        service_name = location_id.replace('_', '-')
        self.telemetry = GameTelemetry(service_name=service_name)
        self.logger = self.telemetry.get_logger()
        self.tracer = self.telemetry.get_tracer()
        
        # Give telemetry access to location state
        self.telemetry._get_location_state = self._get_location_state
        
        self.setup_routes()
        self.db_path = os.environ.get('DATABASE_FILE', DATABASE_FILE)
        self._initialize_database()
        
        if self.location_info["type"] == "village":
            self._start_passive_generation()

    def _get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_database(self):
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id TEXT PRIMARY KEY,
            resources INTEGER NOT NULL,
            army INTEGER NOT NULL,
            faction TEXT NOT NULL
        )
        ''')
        
        cursor.execute("SELECT COUNT(*) FROM locations")
        if cursor.fetchone()[0] == 0:
            for loc_id, loc_info in LOCATIONS.items():
                cursor.execute(
                    "INSERT INTO locations VALUES (?, ?, ?, ?)",
                    (loc_id, loc_info["initial_resources"], loc_info["initial_army"], loc_info["faction"])
                )
            conn.commit()
        conn.close()

    def _get_location_state(self, location_id):
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM locations WHERE id = ?", (location_id,))
        row = cursor.fetchone()
        
        state = None
        if row:
            state = {
                "resources": row['resources'],
                "army": row['army'],
                "faction": row['faction']
            }
        conn.close()
        return state

    def _update_location_state(self, location_id, resources=None, army=None, faction=None):
        set_clauses = []
        params = []
        
        if resources is not None:
            set_clauses.append("resources = ?")
            params.append(resources)
        if army is not None:
            set_clauses.append("army = ?")
            params.append(army)
        if faction is not None:
            set_clauses.append("faction = ?")
            params.append(faction)
        
        if not set_clauses:
            return False
        
        params.append(location_id)
        
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE locations SET {', '.join(set_clauses)} WHERE id = ?",
            params
        )
        conn.commit()
        conn.close()

        # Force metric collection on important state changes
        if faction is not None or resources is not None or army is not None:
            self.telemetry.collect_metrics()
            
        return True

    def _find_path(self, target: str, path_type: PathType) -> Optional[List[str]]:
        """Unified pathfinding for both resources and armies."""
        location_state = self._get_location_state(self.location_id)
        faction = location_state["faction"]
        
        if path_type == PathType.RESOURCE and faction not in ['southern', 'northern']:
            return None
            
        distances = {loc: float('infinity') for loc in LOCATIONS.keys()}
        distances[self.location_id] = 0
        previous = {loc: None for loc in LOCATIONS.keys()}
        unvisited = set(LOCATIONS.keys())
        
        def get_weight(loc_id: str) -> float:
            state = self._get_location_state(loc_id)
            loc_faction = state["faction"]
            
            if path_type == PathType.RESOURCE:
                if loc_faction == faction:
                    return 1
                elif loc_faction == "neutral":
                    return 2
                return float('infinity')
            else:  # PathType.ATTACK
                if loc_faction == faction:
                    return 1
                elif loc_faction == "neutral":
                    return 2
                return 3
        
        while unvisited:
            current = min(unvisited, key=lambda loc: distances[loc])
            if current == target:
                break
                
            unvisited.remove(current)
            for neighbor in LOCATIONS[current]["connections"]:
                if neighbor in unvisited:
                    weight = get_weight(neighbor)
                    distance = distances[current] + weight
                    
                    if distance < distances[neighbor]:
                        distances[neighbor] = distance
                        previous[neighbor] = current
        
        if previous[target] is None:
            return None
            
        path = []
        current = target
        while current is not None:
            path.append(current)
            current = previous[current]
        
        return list(reversed(path))

    def _handle_battle(self, attacking_army: int, attacking_faction: str, 
                      defending_army: int, defending_faction: str) -> tuple[str, int, str]:
        """Handle battle between armies and return result."""
        # Same faction = reinforcement
        if attacking_faction == defending_faction:
            self.logger.info(f"Reinforcement battle between {attacking_faction} armies")
            self.telemetry.record_battle(attacking_faction, defending_faction, "reinforcement")
            return "reinforcement", attacking_army + defending_army, attacking_faction
        
        # Actual combat
        if attacking_army > defending_army:
            self.logger.info(f"Attacker victory: {attacking_army} vs {defending_army}")
            remaining = attacking_army - defending_army
            self.telemetry.record_battle(attacking_faction, defending_faction, "attacker_victory")
            return "attacker_victory", remaining, attacking_faction
        elif defending_army > attacking_army:
            remaining = defending_army - attacking_army
            self.logger.info(f"Defender victory: {defending_army} vs {attacking_army}")
            self.telemetry.record_battle(attacking_faction, defending_faction, "defender_victory")
            return "defender_victory", remaining, defending_faction
        else:
            self.logger.info(f"Stalemate: {attacking_army} vs {defending_army}")
            self.telemetry.record_battle(attacking_faction, defending_faction, "stalemate")
            return "stalemate", 0, defending_faction

    def _continue_army_movement(self, army_size: int, faction: str, current_loc: str, 
                              next_loc: str, remaining_path: List[str], is_attack_move: bool = False) -> Dict:
        """Continue army movement to next location."""
        # Get the current span before starting the thread
        current_span = trace.get_current_span()

        def move():
            try:
                time.sleep(5)  # Wait 5 seconds before moving
                
                # Use the parent span's context in the new thread
                with trace.use_span(current_span):
                    with self.tracer.start_as_current_span(
                        "army_movement",
                        kind=SpanKind.SERVER,
                        attributes={
                            "source_location": current_loc,
                            "target_location": next_loc,
                            "army_size": army_size,
                            "is_attack_move": is_attack_move
                        }
                    ) as movement_span:
                        target_url = f"{self.get_location_url(next_loc)}/receive_army"
                        self.logger.info(f"Moving army from {current_loc} to {next_loc}")
                        
                        result = self._make_request_with_trace(
                            'post',
                            target_url,
                            {
                                "army_size": army_size,
                                "faction": faction,
                                "source_location": current_loc,
                                "remaining_path": remaining_path,
                                "is_attack_move": is_attack_move
                            }
                        )
                        
                        if not result.get("success", False):
                            movement_span.set_status(trace.StatusCode.ERROR, "Army movement failed")
                            movement_span.set_attribute("error", result.get("message", "Unknown error"))
                            self.logger.error(f"Army movement failed: {result.get('message', 'Unknown error')}")
                        else:
                            # Force metric collection after successful army movement
                            self.telemetry.collect_metrics()
                
            except Exception as e:
                self.logger.error(f"Failed to move army to {next_loc}: {str(e)}")
                raise
        
        # Start movement in background thread
        Thread(target=move).start()
        
        # Force metric collection at the start of movement
        self.telemetry.collect_metrics()
        
        # Return immediate response indicating movement has started
        return {
            "success": True,
            "message": f"Army movement started from {current_loc} to {next_loc}",
            "is_attack_move": is_attack_move
        }

    def _transfer_resources_along_path(self, resources: int, path: List[str]) -> bool:
        """Transfer resources along a path with delays."""
        if not path or len(path) < 2:
            return False
            
        # Get the current span before starting the thread
        current_span = trace.get_current_span()
            
        def transfer():
            current_loc = path[0]
            next_loc = path[1]
            
            time.sleep(5)  # Wait before starting transfer
            
            try:
                # Use the parent span's context in the new thread
                with trace.use_span(current_span):
                    with self.tracer.start_as_current_span(
                        "resource_movement",
                        kind=SpanKind.SERVER,
                        attributes={
                            "source_location": current_loc,
                            "target_location": next_loc,
                            "resources_amount": resources
                        }
                    ) as movement_span:
                        target_url = f"{self.get_location_url(next_loc)}/receive_resources"
                        result = self._make_request_with_trace(
                            'post',
                            target_url,
                            {
                                "resources": resources,
                                "source_location": current_loc,
                                "remaining_path": path[1:],
                                "faction": self._get_location_state(self.location_id)["faction"]
                            }
                        )
                        
                        if result.get("success", False):
                            current_loc_resources = self._get_location_state(current_loc)['resources']
                            self._update_location_state(current_loc, resources=current_loc_resources - resources)
                            # Force metric collection after successful resource transfer
                            self.telemetry.collect_metrics()
                        else:
                            movement_span.set_status(trace.StatusCode.ERROR, "Resource transfer failed")
                
            except Exception as e:
                self.logger.error(f"Failed to send resources to {next_loc} from {current_loc}: {str(e)}")
        
        Thread(target=transfer).start()
        return True

    def _make_request_with_trace(self, method: str, url: str, json_data: Optional[Dict] = None) -> Dict:
        """Make HTTP request with trace context propagated in headers."""
        headers = {"Content-Type": "application/json"}
        
        with self.tracer.start_as_current_span(
            "http_request",
            kind=SpanKind.CLIENT
        ) as request_span:
            inject(headers)  # This will now inject the current request_span's context
            
            try:
                if method.lower() == 'get':
                    response = requests.get(url, headers=headers)
                elif method.lower() == 'post':
                    response = requests.post(url, json=json_data, headers=headers)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                request_span.set_attribute("http.status_code", response.status_code)
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                request_span.set_status(trace.StatusCode.ERROR, str(e))
                self.logger.error(f"Request failed: {str(e)}")
                raise

    def _can_collect_resources(self) -> tuple[bool, Optional[str], Optional[int]]:
        """Check if location can collect resources.
        Returns:
            tuple: (can_collect, message, cooldown_seconds)
        """
        with self.lock:
            if self.location_info["type"] != "capital":
                return False, "Only capitals can manually collect resources", None
            
            now = datetime.now()
            
            # Check resource sending cooldown
            if self.location_id in self.resource_cooldown:
                cooldown_end = self.resource_cooldown[self.location_id]
                if now < cooldown_end:
                    remaining = (cooldown_end - now).seconds
                    return False, f"Resource generation on cooldown for {remaining} seconds", remaining
            
            # Check collection cooldown
            last_time = self.last_resource_collection.get(self.location_id, datetime.min)
            wait_time = timedelta(seconds=5)
            
            if now - last_time < wait_time:
                remaining = wait_time - (now - last_time)
                return False, f"Must wait {remaining.seconds} seconds to collect resources", remaining.seconds
            
            return True, None, None

    def _start_resource_cooldown(self):
        with self.lock:
            self.resource_cooldown[self.location_id] = datetime.now() + timedelta(seconds=5)

    def get_location_url(self, location_id):
        port = LOCATIONS[location_id]["port"]
        if os.environ.get('LOCATION_ID'):
            docker_service_name = location_id.replace('_', '-')
            return f"http://{docker_service_name}:{port}"
        return f"http://localhost:{port}"

    def _start_passive_generation(self):
        def generate_resources():
            while True:
                time.sleep(15)
                location_state = self._get_location_state(self.location_id)
                current_resources = location_state["resources"]
                new_resources = current_resources + RESOURCE_GENERATION["village"]
                self._update_location_state(self.location_id, resources=new_resources)
                # Force metric collection after passive resource generation
                self.telemetry.collect_metrics()
        
        Thread(target=generate_resources, daemon=True).start()

    def reset_database(self):
        """Reset the database to initial state."""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM locations")
        
        for loc_id, loc_info in LOCATIONS.items():
            cursor.execute(
                "INSERT INTO locations VALUES (?, ?, ?, ?)",
                (
                    loc_id,
                    loc_info["initial_resources"],
                    loc_info["initial_army"],
                    loc_info["faction"]
                )
            )
        
        conn.commit()
        conn.close()
        self.logger.info("Database reset to initial state")

    def setup_routes(self):
        @self.app.route('/', methods=['GET'])
        def info():
            location_state = self._get_location_state(self.location_id)
            
            cooldown_info = None
            with self.lock:
                now = datetime.now()
                last_time = self.last_resource_collection.get(self.location_id, datetime.min)
                wait_time = timedelta(seconds=15 if self.location_info["type"] == "village" else 5)
                
                if now - last_time < wait_time:
                    remaining = wait_time - (now - last_time)
                    cooldown_info = remaining.seconds
            
            return jsonify({
                "location_id": self.location_id,
                "name": self.location_info["name"],
                "faction": location_state["faction"],
                "connections": self.location_info["connections"],
                "resources": location_state["resources"],
                "army": location_state["army"],
                "resource_cooldown": cooldown_info
            })
        
        @self.app.route('/collect_resources', methods=['POST'])
        def collect_resources():
            """Collect resources from a location"""
            can_collect, message, cooldown_seconds = self._can_collect_resources()
            if not can_collect:
                return jsonify({
                    "success": False,
                    "message": message,
                    "cooldown": True,
                    "cooldown_seconds": cooldown_seconds
                }), 200  # Return 200 for cooldown, as it's an expected state
            
            location_type = self.location_info["type"]
            resources_gained = RESOURCE_GENERATION[location_type]
            
            location_state = self._get_location_state(self.location_id)
            new_resources = location_state["resources"] + resources_gained
            self._update_location_state(self.location_id, resources=new_resources)
            
            with self.lock:
                self.last_resource_collection[self.location_id] = datetime.now()
            
            # Force metric collection after resource update
            self.telemetry.collect_metrics()
            
            return jsonify({
                "success": True,
                "message": f"Collected {resources_gained} resources",
                "current_resources": new_resources,
                "cooldown": False
            })
        
        @self.app.route('/create_army', methods=['POST'])
        def create_army():
            if self.location_info["type"] != "capital":
                return jsonify({
                    "success": False,
                    "message": "Only capitals can create armies"
                }), 403
            
            location_state = self._get_location_state(self.location_id)
            current_resources = location_state["resources"]
            current_army = location_state["army"]
            cost = COSTS["create_army"]
            
            if current_resources < cost:
                return jsonify({
                    "success": False,
                    "message": f"Not enough resources. Need {cost}, have {current_resources}"
                }), 400
            
            new_resources = current_resources - cost
            new_army = current_army + 1
            
            self._update_location_state(
                self.location_id,
                resources=new_resources,
                army=new_army
            )
            
            # Force metric collection after army creation
            self.telemetry.collect_metrics()
            
            return jsonify({
                "success": True,
                "message": "Army created",
                "current_army": new_army,
                "current_resources": new_resources
            })
        
        @self.app.route('/move_army', methods=['POST'])
        def move_army():
            # Extract trace context from request headers
            context = extract(request.headers)
            
            with self.tracer.start_as_current_span(
                "move_army_request",
                context=context,
                kind=SpanKind.SERVER,
                attributes={
                    "location_name": self.location_info["name"],
                    "location_type": self.location_info["type"]
                }
            ) as move_span:
                data = request.get_json()
                if not data or 'target_location' not in data:
                    move_span.set_status(trace.StatusCode.ERROR, "Target location not specified")
                    return jsonify({"success": False, "message": "Target location not specified"}), 400
                
                target_location = data['target_location']
                remaining_path = data.get('remaining_path', [])
                is_attack_move = data.get('is_attack_move', False)
                
                move_span.set_attribute("target_location", target_location)
                move_span.set_attribute("is_attack_move", is_attack_move)
                
                if target_location not in self.location_info["connections"]:
                    move_span.set_status(trace.StatusCode.ERROR, f"Cannot move to {target_location}")
                    return jsonify({
                        "success": False,
                        "message": f"Cannot move to {target_location}. Not connected to {self.location_id}"
                    }), 400
                
                location_state = self._get_location_state(self.location_id)
                if location_state["army"] <= 0:
                    move_span.set_status(trace.StatusCode.ERROR, "No army to move")
                    return jsonify({
                        "success": False,
                        "message": "No army to move"
                    }), 400
                
                try:
                    army_size = location_state["army"]
                    current_faction = location_state["faction"]
                    
                    move_span.set_attribute("army_size", army_size)
                    move_span.set_attribute("faction", current_faction)
                    
                    # Update the source location's army to 0
                    self._update_location_state(self.location_id, army=0)
                    
                    # Force metric collection after army leaves the location
                    self.telemetry.collect_metrics()
                    
                    result = self._continue_army_movement(
                        army_size,
                        current_faction,
                        self.location_id,
                        target_location,
                        remaining_path,
                        is_attack_move
                    )
                    
                    if not result.get("success", True):
                        move_span.set_status(trace.StatusCode.ERROR, result.get("message", "Unknown error"))
                    
                    return jsonify(result)
                except Exception as e:
                    move_span.record_exception(e)
                    move_span.set_status(trace.StatusCode.ERROR, str(e))
                    return jsonify({
                        "success": False,
                        "message": f"Failed to move army: {str(e)}"
                    }), 500
        
        @self.app.route('/all_out_attack', methods=['POST'])
        def all_out_attack():
            """Launch an all-out attack from a capital to the enemy capital"""
            context = extract(request.headers)
            
            with self.tracer.start_as_current_span(
                "all_out_attack",
                context=context,
                kind=SpanKind.SERVER,
                attributes={
                    "location_name": self.location_info["name"],
                    "location_type": self.location_info["type"]
                }
            ) as attack_span:
                try:
                    if self.location_info["type"] != "capital":
                        attack_span.set_status(trace.StatusCode.ERROR, "Only capitals can launch all-out attacks")
                        return jsonify({
                            "success": False,
                            "message": "Only capitals can launch all-out attacks"
                        }), 403
                    
                    location_state = self._get_location_state(self.location_id)
                    army_size = location_state["army"]
                    faction = location_state["faction"]
                    
                    if army_size <= 0:
                        attack_span.set_status(trace.StatusCode.ERROR, "No army available for attack")
                        return jsonify({
                            "success": False,
                            "message": "No army available for attack"
                        }), 400
                    
                    # Determine enemy capital based on faction
                    target_capital = "northern_capital" if faction == "southern" else "southern_capital"
                    attack_span.set_attribute("target_capital", target_capital)
                    
                    attack_path = self._find_path(target_capital, PathType.ATTACK)
                    
                    if not attack_path:
                        attack_span.set_status(trace.StatusCode.ERROR, "No valid path to enemy capital")
                        return jsonify({
                            "success": False,
                            "message": "No valid path to enemy capital"
                        }), 400
                    
                    attack_span.set_attribute("attack_path", str(attack_path))
                    attack_span.set_attribute("initial_army_size", army_size)
                    
                    # Set army to 0 before starting the attack
                    self._update_location_state(self.location_id, army=0)
                    
                    if len(attack_path) > 1:
                        next_loc = attack_path[1]
                        result = self._continue_army_movement(
                            army_size,
                            faction,
                            self.location_id,
                            next_loc,
                            attack_path[1:],
                            is_attack_move=True
                        )
                        
                        if not result.get("success", False):
                            # If movement fails, restore the army
                            self._update_location_state(self.location_id, army=army_size)
                            attack_span.set_status(trace.StatusCode.ERROR, "Failed to start attack")
                            return jsonify({
                                "success": False,
                                "message": f"Failed to start attack: {result.get('message', 'Unknown error')}"
                            }), 400
                        
                        return jsonify({
                            "success": True,
                            "message": f"All-out attack started with {army_size} troops",
                            "path": attack_path,
                            "army_size": army_size
                        })
                    
                    return jsonify({
                        "success": False,
                        "message": "Invalid attack path"
                    }), 400
                    
                except Exception as e:
                    attack_span.record_exception(e)
                    attack_span.set_status(trace.StatusCode.ERROR, str(e))
                    raise
        
        @self.app.route('/receive_army', methods=['POST'])
        def receive_army():
            try:
                data = request.get_json()
                self.logger.info(f"Received army at {self.location_id}: {data}")
                
                if not data or 'army_size' not in data or 'faction' not in data:
                    return jsonify({"success": False, "message": "Invalid army data"}), 400
                
                context = extract(request.headers)
                
                with self.tracer.start_as_current_span(
                    "receive_army",
                    context=context,
                    kind=SpanKind.SERVER,
                    attributes={
                        "location_name": self.location_info["name"],
                        "location_type": self.location_info["type"]
                    }
                ) as battle_span:
                    attacking_army = data['army_size']
                    attacking_faction = data['faction']
                    source_location = data.get('source_location', 'unknown')
                    remaining_path = data.get('remaining_path', [])
                    is_attack_move = data.get('is_attack_move', False)
                    
                    location_state = self._get_location_state(self.location_id)
                    defending_army = location_state["army"]
                    defending_faction = location_state["faction"]
                    
                    battle_span.set_attribute("source_location", source_location)
                    battle_span.set_attribute("attacking_army", attacking_army)
                    battle_span.set_attribute("defending_army", defending_army)
                    battle_span.set_attribute("remaining_path", str(remaining_path))
                    battle_span.set_attribute("is_attack_move", is_attack_move)

                    self.logger.info(f"Received army at {self.location_id}: {data}")
                    self.logger.info(f"Remaining path: {remaining_path}, is_attack_move: {is_attack_move}")
                    
                    if attacking_faction == defending_faction:
                        # For all-out attacks, combine armies with friendly villages
                        if is_attack_move and self.location_info["type"] == "village":
                            # Add village's army to the attacking force
                            attacking_army += defending_army
                            # Set village's army to 0
                            self._update_location_state(self.location_id, army=0)
                            battle_span.set_attribute("combined_army_size", attacking_army)
                            self.logger.info(f"Combined armies at {self.location_id}: {attacking_army} (village army was {defending_army})")
                        
                        # Continue movement if there's a path remaining
                        if is_attack_move and remaining_path:
                            next_location = remaining_path[0]
                            new_remaining_path = remaining_path[1:] if len(remaining_path) > 1 else []
                            self.logger.info(f"Continuing attack from {self.location_id} to {next_location}, new path: {new_remaining_path}")
                            
                            result = self._continue_army_movement(
                                attacking_army,  # Use the potentially increased army size
                                attacking_faction,
                                self.location_id,
                                next_location,
                                new_remaining_path,
                                is_attack_move
                            )
                            battle_span.set_attribute("result", "friendly_passage")
                            self.logger.info(f"Friendly passage result: {result}")
                            # Force metric collection after friendly passage
                            self.telemetry.collect_metrics()
                            return jsonify(result)
                        elif not is_attack_move:
                            # Normal army movement - combine armies
                            new_army = defending_army + attacking_army
                            self._update_location_state(self.location_id, army=new_army)
                            battle_span.set_attribute("result", "armies_combined")
                            self.logger.info(f"Armies combined at {self.location_info['name']}: {new_army}")
                            # Force metric collection after combining armies
                            self.telemetry.collect_metrics()
                            return jsonify({
                                "success": True,
                                "message": f"Armies combined at {self.location_info['name']}",
                                "current_army": new_army,
                                "faction": defending_faction
                            })
                        else:
                            # All-out attack reached friendly location with no remaining path
                            # This shouldn't normally happen, but handle it gracefully
                            if self.location_info["type"] == "capital":
                                # If it's our own capital, stop here
                                self._update_location_state(self.location_id, army=attacking_army)
                                battle_span.set_attribute("result", "returned_to_capital")
                                self.logger.warning(f"All-out attack returned to own capital with {attacking_army} troops")
                            else:
                                # For villages, the army should already be zeroed out above
                                battle_span.set_attribute("result", "attack_ended_at_village")
                                self.logger.warning(f"All-out attack ended at friendly village {self.location_id}")
                            
                            self.telemetry.collect_metrics()
                            return jsonify({
                                "success": True,
                                "message": f"Army movement ended at {self.location_info['name']}",
                                "current_army": self._get_location_state(self.location_id)["army"],
                                "faction": defending_faction
                            })
                    
                    battle_result, remaining_army, new_faction = self._handle_battle(
                        attacking_army,
                        attacking_faction,
                        defending_army,
                        defending_faction
                    )
                    
                    self._update_location_state(
                        self.location_id,
                        army=remaining_army,
                        faction=new_faction
                    )
                    
                    battle_span.set_attribute("result", battle_result)
                    battle_span.set_attribute("remaining_army", remaining_army)
                    
                    if battle_result == "attacker_victory" and is_attack_move and remaining_path:
                        self.logger.info(f"Continuing army movement at {self.location_id}: {remaining_army}")
                        self.logger.info(f"Battle victory - continuing to {remaining_path[0]}, path: {remaining_path[1:]}")
                        result = self._continue_army_movement(
                            remaining_army,
                            attacking_faction,
                            self.location_id,
                            remaining_path[0],
                            remaining_path[1:] if len(remaining_path) > 1 else [],
                            is_attack_move
                        )
                        return jsonify(result)
                    
                    if battle_result != "attacker_victory":
                        self.logger.warning(f"Battle result: {battle_result}")
                        battle_span.set_status(trace.StatusCode.ERROR, f"Attack {battle_result}")
                    
                    # Force metric collection after battle resolution
                    self.telemetry.collect_metrics()
                    
                    return jsonify({
                        "success": battle_result == "attacker_victory",
                        "message": f"Battle at {self.location_info['name']}: {battle_result}",
                        "current_army": remaining_army,
                        "faction": new_faction
                    })
                    
            except Exception as e:
                self.logger.error(f"Error in receive_army: {str(e)}")
                return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500
        
        @self.app.route('/reset', methods=['POST'])
        def reset():
            self.reset_database()
            return jsonify({"success": True, "message": "Game state reset to initial values"})
        
        @self.app.route('/send_resources_to_capital', methods=['POST'])
        def send_resources_to_capital():
            # Extract trace context from request headers
            context = extract(request.headers)
            
            with self.tracer.start_as_current_span(
                "send_resources_to_capital",
                context=context,  # Use the extracted context
                kind=SpanKind.SERVER,
                attributes={
                    "location_name": self.location_info["name"],
                    "location_type": self.location_info["type"]
                }
            ) as span:
                try:
                    location_state = self._get_location_state(self.location_id)
                    current_resources = location_state["resources"]
                    faction = location_state["faction"]
                    
                    span.set_attribute("resources_amount", current_resources)
                    span.set_attribute("faction", faction)
                    
                    if self.location_info["type"] != "village":
                        span.set_status(trace.StatusCode.ERROR, "Only villages can send resources")
                        self.logger.error(f"Only villages can send resources to capital")
                        return jsonify({
                            "success": False,
                            "message": "Only villages can send resources to capital"
                        }), 403
                    
                    if faction not in ['southern', 'northern']:
                        span.set_status(trace.StatusCode.ERROR, "Village must belong to a faction")
                        self.logger.error(f"Village must belong to a faction to send resources")
                        return jsonify({
                            "success": False,
                            "message": "Village must belong to a faction to send resources"
                        }), 403
                    
                    # Determine target capital based on faction
                    target_capital = "southern_capital" if faction == "southern" else "northern_capital"
                    path = self._find_path(target_capital, PathType.RESOURCE)
                    if not path:
                        span.set_status(trace.StatusCode.ERROR, "No valid path to capital")
                        self.logger.error(f"No valid path to capital found")
                        return jsonify({
                            "success": False,
                            "message": "No valid path to capital found"
                        }), 400
                    
                    span.set_attribute("path_to_capital", str(path))
                    
                    if self._transfer_resources_along_path(current_resources, path):
                        self._start_resource_cooldown()
                        self.logger.info(f"Resources sent to capital via {path}")
                        # Force metric collection after initiating resource transfer
                        self.telemetry.collect_metrics()
                        return jsonify({
                            "success": True,
                            "message": f"Sending {current_resources} resources to capital via {' -> '.join(path)}",
                            "path": path,
                            "amount": current_resources
                        })
                    else:
                        span.set_status(trace.StatusCode.ERROR, "Failed to start resource transfer")
                        self.logger.error(f"Failed to start resource transfer")
                        return jsonify({
                            "success": False,
                            "message": "Failed to start resource transfer"
                        }), 500
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.StatusCode.ERROR, str(e))
                    self.logger.error(f"Error in send_resources_to_capital: {str(e)}")
                    return jsonify({
                        "success": False,
                        "message": f"Error: {str(e)}"
                    }), 500
        
        @self.app.route('/receive_resources', methods=['POST'])
        def receive_resources():
            data = request.get_json()
            if not data or 'resources' not in data or 'faction' not in data:
                return jsonify({"success": False, "message": "Invalid resource data"}), 400
            
            context = extract(request.headers)
            
            with self.tracer.start_as_current_span(
                "receive_resources",
                context=context,
                attributes={
                    "location": self.location_id,
                    "location_type": self.location_info["type"],
                    "sending_faction": data['faction'],
                    "receiving_faction": self._get_location_state(self.location_id)["faction"],
                    "resources_amount": data['resources']
                }
            ) as transfer_span:
                incoming_resources = data['resources']
                source_location = data.get('source_location', 'unknown')
                remaining_path = data.get('remaining_path', [])
                faction = data['faction']
                
                transfer_span.set_attribute("source_location", source_location)
                
                location_state = self._get_location_state(self.location_id)
                current_resources = location_state["resources"]
                current_faction = location_state["faction"]
                
                if current_faction != faction:
                    transfer_span.set_status(trace.Status(trace.StatusCode.ERROR, f"Resources captured by {current_faction}"))
                    self._update_location_state(self.location_id, resources=current_resources + incoming_resources)
                    # Force metric collection after resource capture
                    self.telemetry.collect_metrics()
                    self.logger.error(f"Resources captured by {current_faction}")
                    return jsonify({
                        "success": False,
                        "message": f"Resources captured by {current_faction}!",
                        "current_resources": current_resources + incoming_resources
                    })
                
                new_resources = current_resources + incoming_resources
                self._update_location_state(self.location_id, resources=new_resources)
                # Force metric collection after receiving resources
                self.telemetry.collect_metrics()
                self.logger.info(f"Resources updated to {new_resources}")
                
                if len(remaining_path) > 1:
                    next_loc = remaining_path[1]
                    
                    def continue_transfer():
                        with self._start_movement_trace(
                            "resource_movement",
                            self.location_id,
                            next_loc,
                            resources=incoming_resources
                        ) as movement_span:
                            try:
                                time.sleep(5)
                                target_url = f"{self.get_location_url(next_loc)}/receive_resources"
                                self.logger.info(f"Sending resources to {next_loc} with target URL: {target_url}")
                                result = self._make_request_with_trace('post', target_url, {
                                    "resources": incoming_resources,
                                    "source_location": self.location_id,
                                    "remaining_path": remaining_path[1:],
                                    "faction": faction
                                })
                                
                                if not result.get("success", False):
                                    movement_span.set_status(trace.Status(trace.StatusCode.ERROR, "Resource transfer failed"))
                                
                                current_state = self._get_location_state(self.location_id)
                                self._update_location_state(self.location_id, 
                                    resources=current_state["resources"] - incoming_resources)
                                # Force metric collection after forwarding resources
                                self.telemetry.collect_metrics()
                                self.logger.info(f"Resources updated to {current_state['resources'] - incoming_resources}")
                            except Exception as e:
                                movement_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                                self.logger.error(f"Failed to forward resources to {next_loc}: {str(e)}")
                    
                    Thread(target=continue_transfer).start()
                
                transfer_span.set_attribute("final_resources", new_resources)
                if self.location_info["type"] == "capital":
                    transfer_span.set_attribute("resources_reached_capital", True)
                
                self.logger.info(f"Resources received at {self.location_info['name']}")
                return jsonify({
                    "success": True,
                    "message": f"Resources received at {self.location_info['name']}",
                    "current_resources": new_resources
                })
    
    def run(self):
        port = self.location_info["port"]
        self.app.run(host='0.0.0.0', port=port) 
        self.logger.info(f"Location server running on port {port}")