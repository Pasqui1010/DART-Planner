#!/usr/bin/env python3
"""
DART-Planner Web Demo
Showcases edge-first autonomous navigation with real-time visualization
"""
import os
import sys
import json
import time
import threading
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import numpy as np

# Add src to path for imports
sys.path.insert(0, '/app/src')

# Import DART-Planner components
from planning.se3_mpc_planner import SE3MPCPlanner
from perception.explicit_geometric_mapper import ExplicitGeometricMapper
from edge.onboard_autonomous_controller import OnboardAutonomousController
from utils.drone_simulator import DroneSimulator

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dart-planner-demo'
socketio = SocketIO(app, cors_allowed_origins="*")

class DARTPlannerDemo:
    """Real-time demonstration of DART-Planner capabilities"""
    
    def __init__(self):
        self.running = False
        self.demo_thread = None
        
        # Initialize components
        self.simulator = DroneSimulator()
        self.se3_planner = SE3MPCPlanner()
        self.mapper = ExplicitGeometricMapper()
        self.controller = OnboardAutonomousController()
        
        # Demo state
        self.current_position = np.array([0.0, 0.0, 1.0])
        self.target_position = np.array([5.0, 5.0, 2.0])
        self.obstacles = self._generate_demo_obstacles()
        self.trajectory_history = []
        self.performance_metrics = {
            'planning_time_ms': [],
            'mapping_queries_per_sec': 0,
            'autonomous_operation_time': 0
        }
        
    def _generate_demo_obstacles(self):
        """Generate obstacles for demonstration"""
        obstacles = []
        # Create a challenging obstacle course
        obstacle_positions = [
            [2.0, 1.0, 1.5, 0.5],  # [x, y, z, radius]
            [3.5, 3.0, 1.8, 0.7],
            [1.5, 4.0, 1.2, 0.4],
            [4.0, 2.5, 2.2, 0.6]
        ]
        
        for pos in obstacle_positions:
            obstacles.append({
                'position': pos[:3],
                'radius': pos[3],
                'type': 'sphere'
            })
            
        return obstacles
    
    def start_demo(self):
        """Start the autonomous navigation demonstration"""
        if not self.running:
            self.running = True
            self.demo_thread = threading.Thread(target=self._demo_loop)
            self.demo_thread.daemon = True
            self.demo_thread.start()
            
    def stop_demo(self):
        """Stop the demonstration"""
        self.running = False
        if self.demo_thread:
            self.demo_thread.join()
            
    def _demo_loop(self):
        """Main demonstration loop showcasing autonomous operation"""
        start_time = time.time()
        
        while self.running:
            # Simulate edge-first autonomous operation
            loop_start = time.time()
            
            # 1. Update mapper with sensor data (explicit geometric mapping)
            self._update_mapper()
            
            # 2. Plan trajectory using SE(3) MPC
            trajectory, planning_time = self._plan_trajectory()
            
            # 3. Execute autonomous control
            self._execute_control_step(trajectory)
            
            # 4. Update performance metrics
            self._update_metrics(planning_time, start_time)
            
            # 5. Emit real-time data to web interface
            self._emit_telemetry()
            
            # Control loop timing (100 Hz simulation)
            loop_time = time.time() - loop_start
            sleep_time = max(0, 0.01 - loop_time)  # 100 Hz
            time.sleep(sleep_time)
            
    def _update_mapper(self):
        """Update explicit geometric mapper with obstacle data"""
        # Simulate sensor input and deterministic mapping
        for obstacle in self.obstacles:
            self.mapper.update_occupancy(
                position=obstacle['position'],
                radius=obstacle['radius'],
                occupancy_probability=0.95  # High confidence, deterministic
            )
            
    def _plan_trajectory(self):
        """Plan trajectory using SE(3) MPC planner"""
        start_time = time.time()
        
        # SE(3) MPC planning (designed for quadrotors)
        trajectory = self.se3_planner.plan_trajectory(
            current_state=self.current_position,
            target_state=self.target_position,
            obstacle_map=self.mapper.get_occupancy_grid(),
            horizon_length=20,
            dt=0.1
        )
        
        planning_time = (time.time() - start_time) * 1000  # Convert to ms
        return trajectory, planning_time
        
    def _execute_control_step(self, trajectory):
        """Execute one step of autonomous control"""
        if len(trajectory) > 0:
            # Move towards first waypoint
            direction = trajectory[0] - self.current_position
            distance = np.linalg.norm(direction)
            
            if distance > 0.1:
                # Normalize and apply velocity
                velocity = direction / distance * 0.05  # Smooth movement
                self.current_position += velocity
                
                # Add to history
                self.trajectory_history.append(self.current_position.copy())
                
                # Keep history manageable
                if len(self.trajectory_history) > 500:
                    self.trajectory_history = self.trajectory_history[-400:]
            else:
                # Near target, set new random target
                self.target_position = np.array([
                    np.random.uniform(0, 6),
                    np.random.uniform(0, 6),
                    np.random.uniform(1, 3)
                ])
                
    def _update_metrics(self, planning_time, start_time):
        """Update performance metrics"""
        self.performance_metrics['planning_time_ms'].append(planning_time)
        if len(self.performance_metrics['planning_time_ms']) > 100:
            self.performance_metrics['planning_time_ms'] = \
                self.performance_metrics['planning_time_ms'][-50:]
                
        self.performance_metrics['autonomous_operation_time'] = \
            time.time() - start_time
            
        # Simulate mapping query rate (explicit mapping is fast)
        self.performance_metrics['mapping_queries_per_sec'] = 1000  # 1kHz capability
        
    def _emit_telemetry(self):
        """Emit real-time telemetry data to web interface"""
        telemetry = {
            'drone_position': self.current_position.tolist(),
            'target_position': self.target_position.tolist(),
            'obstacles': self.obstacles,
            'trajectory_history': [pos.tolist() for pos in self.trajectory_history[-50:]],
            'performance': {
                'avg_planning_time_ms': np.mean(self.performance_metrics['planning_time_ms']) if self.performance_metrics['planning_time_ms'] else 0,
                'mapping_query_rate': self.performance_metrics['mapping_queries_per_sec'],
                'autonomous_time_sec': self.performance_metrics['autonomous_operation_time'],
                'edge_first_status': 'AUTONOMOUS',  # Always autonomous!
                'neural_dependency': 'NONE'  # No neural magic oracles
            }
        }
        
        socketio.emit('telemetry_update', telemetry)

# Global demo instance
demo = DARTPlannerDemo()

@app.route('/')
def index():
    """Main demo page"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'component': 'dart-planner-demo'})

@app.route('/api/start_demo', methods=['POST'])
def start_demo():
    """Start the autonomous navigation demo"""
    demo.start_demo()
    return jsonify({'status': 'started'})

@app.route('/api/stop_demo', methods=['POST'])
def stop_demo():
    """Stop the demonstration"""
    demo.stop_demo()
    return jsonify({'status': 'stopped'})

@app.route('/api/status')
def get_status():
    """Get current demo status"""
    return jsonify({
        'running': demo.running,
        'components': {
            'se3_mpc': 'operational',
            'explicit_mapper': 'operational',
            'edge_controller': 'operational'
        }
    })

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'data': 'Connected to DART-Planner Demo'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

if __name__ == '__main__':
    print("🚁 DART-Planner Demo Server Starting...")
    print("🌐 Open http://localhost:8080 to see edge-first autonomous navigation!")
    print("✅ Features: SE(3) MPC + Explicit Mapping + Edge-First Architecture")
    socketio.run(app, host='0.0.0.0', port=8080, debug=False) 