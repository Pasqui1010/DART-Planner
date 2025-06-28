#!/usr/bin/env python3
"""
Phase 1 Controller Optimization Test
===================================
Implement and test the Phase 1 controller improvements to reduce position error from 67m to <30m.

This script temporarily modifies the geometric controller with optimized gains and runs a test.
"""

import sys
import os
import time
import numpy as np

# Add the src directory to the path so we can import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def backup_original_controller():
    """Backup the original controller before modification."""
    import shutil
    
    original_file = "src/control/geometric_controller.py"
    backup_file = "src/control/geometric_controller_backup.py"
    
    if not os.path.exists(backup_file):
        shutil.copy2(original_file, backup_file)
        print(f"✅ Backed up original controller to {backup_file}")
    else:
        print(f"ℹ️  Backup already exists at {backup_file}")

def apply_phase1_optimizations():
    """Apply Phase 1 optimizations to the geometric controller."""
    
    controller_file = "src/control/geometric_controller.py"
    
    # Read the current file
    with open(controller_file, 'r') as f:
        content = f.read()
    
    # Phase 1 optimizations (increase proportional gains)
    optimizations = {
        # Position gains: Increase Kp from [6,6,8] to [10,10,12] (67% increase)
        'kp_pos: np.ndarray = field(default_factory=lambda: np.array([6.0, 6.0, 8.0]))':
            'kp_pos: np.ndarray = field(default_factory=lambda: np.array([10.0, 10.0, 12.0]))',
        
        # Integral gains: Reduce Ki from [1,1,2] to [0.5,0.5,1] (50% reduction) 
        'ki_pos: np.ndarray = field(default_factory=lambda: np.array([1.0, 1.0, 2.0]))':
            'ki_pos: np.ndarray = field(default_factory=lambda: np.array([0.5, 0.5, 1.0]))',
        
        # Derivative gains: Increase Kd from [4,4,5] to [6,6,8] (50% increase)
        'kd_pos: np.ndarray = field(default_factory=lambda: np.array([4.0, 4.0, 5.0]))':
            'kd_pos: np.ndarray = field(default_factory=lambda: np.array([6.0, 6.0, 8.0]))',
        
        # Attitude gains: Increase Kp from [10,10,4] to [12,12,5] (20% increase) 
        'kp_att: np.ndarray = field(default_factory=lambda: np.array([10.0, 10.0, 4.0]))':
            'kp_att: np.ndarray = field(default_factory=lambda: np.array([12.0, 12.0, 5.0]))',
        
        # Feedforward: Increase ff_pos from 0.8 to 1.2 (50% increase)
        'ff_pos: float = 0.8':
            'ff_pos: float = 1.2',
        
        # Update the controller description
        'Optimized high-frequency geometric controller for quadrotor.':
            'PHASE 1 OPTIMIZED geometric controller for quadrotor.'
    }
    
    # Apply optimizations
    modified_content = content
    applied_optimizations = []
    
    for old_text, new_text in optimizations.items():
        if old_text in modified_content:
            modified_content = modified_content.replace(old_text, new_text)
            applied_optimizations.append(old_text.split(':')[0] if ':' in old_text else old_text[:50])
    
    # Write the modified file
    with open(controller_file, 'w') as f:
        f.write(modified_content)
    
    print(f"🔧 PHASE 1 OPTIMIZATIONS APPLIED:")
    print("=" * 40)
    for i, opt in enumerate(applied_optimizations, 1):
        print(f"   {i}. {opt}...")
    
    return len(applied_optimizations)

def restore_original_controller():
    """Restore the original controller from backup."""
    import shutil
    
    original_file = "src/control/geometric_controller.py"
    backup_file = "src/control/geometric_controller_backup.py"
    
    if os.path.exists(backup_file):
        shutil.copy2(backup_file, original_file)
        print(f"🔄 Restored original controller from {backup_file}")
    else:
        print(f"❌ No backup found at {backup_file}")

def run_phase1_test():
    """Run the system test with Phase 1 optimizations."""
    
    print(f"\n🚀 RUNNING PHASE 1 OPTIMIZATION TEST")
    print("=" * 45)
    print("Target: Reduce position error from 67m to <30m")
    print("Expected improvement: 40-60% error reduction")
    print()
    
    # Import and run the test
    try:
        import subprocess
        import sys
        
        # Run the comprehensive system test
        result = subprocess.run([
            sys.executable, "comprehensive_system_test.py"
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print("✅ Phase 1 test completed successfully")
            
            # Parse results for key metrics
            output = result.stdout
            
            # Extract position error from output
            lines = output.split('\n')
            for line in lines:
                if "Mean position error:" in line:
                    try:
                        error_str = line.split(':')[1].strip().replace('m', '')
                        mean_error = float(error_str)
                        baseline_error = 67.0
                        improvement = ((baseline_error - mean_error) / baseline_error) * 100
                        
                        print(f"\n📊 PHASE 1 RESULTS:")
                        print(f"   Baseline Error: {baseline_error:.1f}m")
                        print(f"   Phase 1 Error: {mean_error:.1f}m")  
                        print(f"   Improvement: {improvement:.1f}%")
                        
                        if mean_error < 30.0:
                            print(f"   🎯 TARGET ACHIEVED: <30m ✅")
                        else:
                            print(f"   ⚠️  Target not yet achieved (need <30m)")
                            
                        if improvement >= 40.0:
                            print(f"   📈 EXPECTED IMPROVEMENT MET: ≥40% ✅")
                        else:
                            print(f"   📈 More improvement needed (target ≥40%)")
                            
                        break
                    except:
                        pass
            
            return True
        else:
            print(f"❌ Test failed with return code {result.returncode}")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return False

def analyze_improvements_needed():
    """Analyze what additional improvements might be needed."""
    
    print(f"\n🔍 PHASE 1 ANALYSIS & NEXT STEPS:")
    print("=" * 40)
    
    print("If Phase 1 target achieved (<30m):")
    print("   ✅ Proceed to Phase 2: DIAL-MPC optimization")
    print("   🎯 Target: <15m position error")
    print("   📋 Focus: Cost function weights, sampling parameters")
    
    print("\nIf Phase 1 target NOT achieved:")
    print("   🔧 Additional controller tuning needed:")
    print("   1. Further increase Kp gains (test 15, 15, 18)")
    print("   2. Optimize integral limits and windup protection") 
    print("   3. Fine-tune derivative gains for better damping")
    print("   4. Adjust feedforward gains")
    
    print("\nGeneral recommendations:")
    print("   📝 Document each change and its impact")
    print("   ⚡ Test one parameter at a time")
    print("   📊 Measure improvement at each step")
    print("   🎯 Achieve 55%+ improvement before Phase 2")

def main():
    """Main function to run Phase 1 optimization test."""
    
    print("🎯 PHASE 1: CONTROLLER GAIN OPTIMIZATION")
    print("=" * 50)
    print("Objective: Reduce position error from 67m to <30m")
    print("Method: Increase proportional gains, optimize PID balance")
    print("Expected: 40-60% error reduction")
    print()
    
    try:
        # Step 1: Backup original controller
        backup_original_controller()
        
        # Step 2: Apply Phase 1 optimizations  
        num_optimizations = apply_phase1_optimizations()
        print(f"Applied {num_optimizations} optimizations")
        
        # Step 3: Run test with optimized controller
        time.sleep(1)  # Brief pause
        test_success = run_phase1_test()
        
        # Step 4: Analyze results and provide next steps
        analyze_improvements_needed()
        
        # Step 5: Ask user if they want to keep changes
        print(f"\n🤔 KEEP PHASE 1 OPTIMIZATIONS?")
        print("=" * 35)
        print("The optimized controller is currently active.")
        keep_changes = input("Keep optimizations? (y/n): ").lower().strip()
        
        if keep_changes == 'y':
            print("✅ Keeping Phase 1 optimizations")
            print("   The controller is now optimized for Phase 1")
            print("   Original backed up as geometric_controller_backup.py")
        else:
            restore_original_controller()
            print("🔄 Restored original controller")
        
        return test_success
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Test interrupted by user")
        restore_original_controller()
        return False
        
    except Exception as e:
        print(f"\n❌ Error during Phase 1 test: {e}")
        restore_original_controller()
        return False

if __name__ == "__main__":
    success = main()
    
    print(f"\n{'='*50}")
    if success:
        print("🎉 PHASE 1 OPTIMIZATION COMPLETE")
        print("   Ready for Phase 2: DIAL-MPC tuning") 
    else:
        print("⚠️  PHASE 1 OPTIMIZATION INCOMPLETE")
        print("   Review results and adjust approach")
    print("="*50) 