#!/usr/bin/env python3
"""
DART-Planner Web Demo (FastAPI Version)
Showcases edge-first autonomous navigation with real-time visualization.
Now running on a modern ASGI stack with a universal security gateway.
"""
import json
from dart_planner.common.di_container import get_container
import os
import sys
import threading
import time

import numpy as np
from fastapi import FastAPI, Request, HTTPException, Depends, APIRouter, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import socketio
from pydantic import BaseModel
import asyncio
from sqlalchemy.orm import Session

# Add src to path
# This is a common pattern for demos, but for robust applications,
# consider installing the package in editable mode (`pip install -e .`)

from demos.web_demo.dummy_drone_controller import DummyDroneController
from security.auth import AuthManager, Role, require_role, UserSession, UserCreate, UserUpdate
from security.db.database import get_db
from security.db.service import UserService
from gateway.middleware import CSRFMiddleware, SecureMiddleware
from common.types import DroneState
from dart_planner.edge.onboard_autonomous_controller import OnboardAutonomousController
from dart_planner.perception.explicit_geometric_mapper import ExplicitGeometricMapper
from dart_planner.planning.se3_mpc_planner import SE3MPCPlanner
from dart_planner.utils.drone_simulator import DroneSimulator
from demos.web_demo.input_validator import InputValidator
from dart_planner.communication.telemetry_compression import TelemetryCompressor, WebSocketTelemetryManager, CompressionType

# --- FastAPI App Initialization ---
app = FastAPI(
    title="DART-Planner Secure Demo",
    description="Demonstrates secure, autonomous drone operations via a FastAPI gateway.",
    version="2.0.0"
)

# Add the security middleware to the application
app.add_middleware(CSRFMiddleware)
app.add_middleware(SecureMiddleware)

# --- Static Files and Templates ---
# It's important to use absolute paths for templates and static files in this context
current_dir = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(current_dir, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(current_dir, "templates"))


# --- Socket.IO Setup ---
# We use the pure ASGI Socket.IO server
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)
app.mount("/socket.io", socket_app)


# --- Security and Authentication ---
auth_manager = AuthManager(user_service=UserService())
user_service = UserService()

# --- API Routers ---
api_router = APIRouter(prefix="/api")
admin_router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_role(Role.ADMIN))])

# --- Pydantic Models ---
class LoginRequest(BaseModel):
    username: str
    password: str

# --- Authentication Endpoints ---
@api_router.post("/login")
async def login_for_access_token(response: Response, form_data: LoginRequest, db: Session = Depends(get_db)):
    access_token, refresh_token = await auth_manager.login_and_get_tokens(
        form_data.username, form_data.password, db
    )
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Set tokens in secure, HttpOnly cookies
    response.set_cookie(
        key="access_token", value=f"Bearer {access_token}", httponly=True, samesite='strict'
    )
    response.set_cookie(
        key="refresh_token", value=f"Bearer {refresh_token}", httponly=True, samesite='strict'
    )
    return {"message": "Login successful"}

@api_router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logout successful"}


@api_router.get("/me", response_model=UserSession)
async def read_users_me(current_user: UserSession = Depends(auth_manager.get_current_user)):
    return current_user

# --- Admin Endpoints ---
@admin_router.get("/users")
async def get_all_users(db: Session = Depends(get_db)):
    return await user_service.get_all_users(db)

@admin_router.post("/users")
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    return await user_service.create_user(db, user.username, user.password, user.role)

@admin_router.put("/users/{user_id}")
async def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    return await user_service.update_user_role(db, user_id, user_update.role)

@admin_router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    return await user_service.delete_user(db, user_id)

@admin_router.get("/roles")
async def get_roles():
    return [role.value for role in Role]

# --- Demo Control Endpoints ---
@api_router.post("/start_demo")
async def start_demo(_: UserSession = Depends(require_role(Role.PILOT))):
    demo_runner.start_demo()
    return {"message": "Demo started"}

@api_router.post("/stop_demo")
async def stop_demo(_: UserSession = Depends(require_role(Role.PILOT))):
    demo_runner.stop_demo()
    return {"message": "Demo stopped"}

@api_router.post("/set_target")
async def set_target(request: Request, _: UserSession = Depends(require_role(Role.OPERATOR))):
    data = await request.json()
    try:
        validated_coord = InputValidator().validate_coordinate(data, "position")
        demo_runner.target_position = np.array(list(validated_coord.values()))
        return {"message": "Target updated", "new_target": demo_runner.target_position.tolist()}
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")

@api_router.post("/mission")
async def upload_mission(request: Request, _: UserSession = Depends(require_role(Role.OPERATOR))):
    data = await request.json()
    if "waypoints" not in data or not isinstance(data["waypoints"], list):
        raise HTTPException(status_code=400, detail="Payload must contain a 'waypoints' list.")
    try:
        validated = InputValidator().validate_trajectory(data)
        demo_runner.set_mission(validated)
        return {"message": "Mission uploaded", "waypoints": validated}
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Validation Error: {e}")

@api_router.get("/status")
async def get_status(_: UserSession = Depends(require_role(Role.OPERATOR))):
    return JSONResponse(content=demo_runner.get_status_data())

@api_router.get("/telemetry/compressed")
async def get_compressed_telemetry(
    compression: str = "gzip",
    _: UserSession = Depends(require_role(Role.OPERATOR))
):
    """Get compressed telemetry data for efficient transmission"""
    try:
        compression_type = CompressionType(compression)
        raw_telemetry = demo_runner.get_status_data()
        
        if compression_type == CompressionType.GZIP:
            compressed_data = demo_runner.telemetry_compressor._compress_gzip(raw_telemetry)
            return Response(
                content=compressed_data,
                media_type="application/octet-stream",
                headers={"Content-Encoding": "gzip", "Content-Type": "application/json"}
            )
        elif compression_type == CompressionType.BINARY:
            binary_data = demo_runner.telemetry_compressor._serialize_binary(raw_telemetry)
            return Response(
                content=binary_data,
                media_type="application/octet-stream",
                headers={"Content-Type": "application/octet-stream"}
            )
        else:
            return JSONResponse(content=raw_telemetry)
            
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported compression type: {compression}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compression error: {str(e)}")

# --- Main Application Logic ---
# (Drone controller, simulation, etc.)

# Global instance of the drone controller
# In a real application, this would be managed more carefully.
drone_controller: OnboardAutonomousController = None

class DARTPlannerDemo:
    """Real-time demonstration of DART-Planner capabilities (Singleton)"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DARTPlannerDemo, cls).__new__(cls)
            cls._instance.init_demo()
        return cls._instance

    def init_demo(self):
        self.running = False
        self.demo_thread = None
        self.simulator = DroneSimulator()
        self.se3_planner = get_container().create_planner_container().get_se3_planner())
        self.mapper = ExplicitGeometricMapper()
        self.controller = OnboardAutonomousController()
        self.current_position = np.array([0.0, 0.0, 1.0])
        self.target_position = np.array([5.0, 5.0, 2.0])
        self.obstacles = self._generate_demo_obstacles()
        self.trajectory_history = []
        self.performance_metrics = {
            "planning_time_ms": [],
            "mapping_queries_per_sec": 0,
            "autonomous_operation_time": 0,
        }
        
        # Initialize telemetry compression system
        self.telemetry_compressor = TelemetryCompressor(compression_level=6, enable_binary=True)
        self.websocket_manager = WebSocketTelemetryManager(self.telemetry_compressor)
        self.client_compression_prefs = {}  # Track client compression preferences
        }
        self.waypoint_queue = [] # Added for mission support

    def _generate_demo_obstacles(self):
        obstacle_positions = [
            [2.0, 1.0, 1.5, 0.5], [3.5, 3.0, 1.8, 0.7],
            [1.5, 4.0, 1.2, 0.4], [4.0, 2.5, 2.2, 0.6],
        ]
        return [{"position": pos[:3], "radius": pos[3], "type": "sphere"} for pos in obstacle_positions]

    def start_demo(self):
        if not self.running:
            self.running = True
            self.demo_thread = threading.Thread(target=self._demo_loop)
            self.demo_thread.daemon = True
            self.demo_thread.start()

    def stop_demo(self):
        self.running = False
        if self.demo_thread:
            self.demo_thread.join()

    def _demo_loop(self):
        start_time = time.time()
        while self.running:
            loop_start = time.time()
            self._update_mapper()
            trajectory, planning_time = self._plan_trajectory()
            self._execute_control_step(trajectory)
            self._update_metrics(planning_time, start_time)
            self._emit_telemetry()
            time.sleep(max(0, 0.01 - (time.time() - loop_start)))

    def _update_mapper(self):
        for obstacle in self.obstacles:
            self.mapper.add_obstacle(
                center=np.array(obstacle["position"]), radius=obstacle["radius"]
            )

    def _plan_trajectory(self):
        start_time = time.time()
        dummy_state = DroneState(
            timestamp=time.time(), position=self.current_position.copy(),
            velocity=np.zeros(3), attitude=np.zeros(3), angular_velocity=np.zeros(3),
        )
        traj_obj = self.se3_planner.plan_trajectory(
            current_state=dummy_state, goal_position=self.target_position
        )
        planned_positions = getattr(traj_obj, "positions", np.array([]))
        planning_time = (time.time() - start_time) * 1000
        return planned_positions, planning_time

    def set_mission(self, waypoints):
        """Replace current target queue with a new mission (list of waypoints)."""
        if not waypoints:
            return
        # For demo: set target to first waypoint and queue others
        self.waypoint_queue = [np.array([wp['x'], wp['y'], wp['z']]) for wp in waypoints]
        self.target_position = self.waypoint_queue.pop(0)

    def _execute_control_step(self, trajectory):
        if trajectory is not None and len(trajectory) > 0:
            self.current_position = self.simulator.move_towards(
                self.current_position, trajectory[0]
            )
            self.trajectory_history.append(self.current_position.tolist())
            if len(self.trajectory_history) > 200:
                self.trajectory_history.pop(0)

    def _update_metrics(self, planning_time, start_time):
        self.performance_metrics["planning_time_ms"].append(planning_time)
        if len(self.performance_metrics["planning_time_ms"]) > 100:
            self.performance_metrics["planning_time_ms"].pop(0)
        self.performance_metrics["autonomous_operation_time"] = time.time() - start_time

        # Move to next waypoint when close
        if self.waypoint_queue and np.linalg.norm(self.current_position - self.target_position) < 0.3:
            self.target_position = self.waypoint_queue.pop(0)

    def _emit_telemetry(self):
        if sio.async_mode == "asgi":
            # Get raw telemetry data
            raw_telemetry = self.get_status_data()
            
            # Use compression for all connected clients
            for client_id in self.client_compression_prefs:
                compression_type = self.client_compression_prefs[client_id]
                compressed_telemetry = self.websocket_manager.prepare_websocket_telemetry(
                    raw_telemetry, 
                    client_id=client_id,
                    force_binary=(compression_type == CompressionType.BINARY)
                )
                sio.emit("telemetry", compressed_telemetry, room=client_id)
            
            # Fallback for clients without compression preference
            sio.emit("telemetry", raw_telemetry)

    def get_status_data(self):
        avg_planning_time = np.mean(self.performance_metrics["planning_time_ms"]) if self.performance_metrics["planning_time_ms"] else 0
        return {
            "running": self.running,
            "position": self.current_position.tolist(),
            "target": self.target_position.tolist(),
            "obstacles": self.obstacles,
            "trajectory": self.trajectory_history,
            "performance": {
                "avg_planning_time_ms": round(avg_planning_time, 2),
                "autonomous_operation_time_s": round(self.performance_metrics["autonomous_operation_time"], 1),
            },
        }

# --- API Endpoints ---
demo_runner = DARTPlannerDemo()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
def health():
    return {"status": "ok"}

# --- WebSocket Event Handlers ---

@sio.on('connect')
async def connect(sid, environ):
    request = Request(environ)
    try:
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Socket.IO auth failed: Missing token cookie.")

        # The token includes "Bearer ", so we need to strip it.
        token = token.replace("Bearer ", "")
        
        # We need a db session to check token revocation
        db = next(get_db())
        session = await auth_manager.validate_token(token, db)
        if not session:
             raise HTTPException(status_code=401, detail="Socket.IO auth failed: Invalid token.")

        await sio.save_session(sid, {'user_session': session.dict()})
        print(f"Socket.IO client connected: {sid}, user: {session.username}")
        
        # Set default compression preference for new client
        demo_runner.client_compression_prefs[sid] = CompressionType.GZIP
        demo_runner.websocket_manager.set_client_preference(sid, CompressionType.GZIP)
        
        # Send initial telemetry with compression
        initial_telemetry = demo_runner.websocket_manager.prepare_websocket_telemetry(
            demo_runner.get_status_data(), 
            client_id=sid
        )
        await sio.emit("telemetry", initial_telemetry, room=sid)

    except Exception as e:
        print(f"Socket.IO connection failed: {e}")
        await sio.disconnect(sid)
    finally:
        db.close()

@sio.on('compression_preference')
async def handle_compression_preference(sid, data):
    """Handle client compression preference updates"""
    try:
        compression_type = CompressionType(data.get('type', 'gzip'))
        demo_runner.client_compression_prefs[sid] = compression_type
        demo_runner.websocket_manager.set_client_preference(sid, compression_type)
        print(f"Client {sid} set compression preference: {compression_type.value}")
        await sio.emit("compression_ack", {"status": "ok", "type": compression_type.value}, room=sid)
    except Exception as e:
        print(f"Error setting compression preference: {e}")
        await sio.emit("compression_ack", {"status": "error", "message": str(e)}, room=sid)

@sio.on('disconnect')
def disconnect(sid):
    print(f"Socket.IO client disconnected: {sid}")
    # Clean up compression preferences for disconnected client
    if sid in demo_runner.client_compression_prefs:
        del demo_runner.client_compression_prefs[sid]

# --- App Cleanup ---
@app.on_event("shutdown")
def shutdown_event():
    stop_simulation()
    print("DART-Planner demo shut down.")

# Include the API routers
app.include_router(api_router)
app.include_router(admin_router)

if __name__ == '__main__':
    # This setup allows running the app directly for development.
    # For production, use a proper ASGI server like `uvicorn app:app --reload`
    import uvicorn
    
    # Run the initial setup in an async context
    asyncio.run(setup_simulation())
    
    # Start the web server
    uvicorn.run(app, host="0.0.0.0", port=8000)
