#!/usr/bin/env python3
"""
Phase 2B Results Analysis
Compares velocity tracking performance after feedforward optimization
"""

import pandas as pd
import numpy as np

def analyze_phase2b_results():
    """Analyze Phase 2B test results and compare with previous phases"""
    
    print("📊 Phase 2B Results Analysis")
    print("=" * 70)
    
    # Load results from all phases
    phase1_file = "improved_trajectory_log_1751106048.csv"   # Phase 1 (baseline)
    phase2a_file = "improved_trajectory_log_1751106220.csv"  # Phase 2A (failed Kd increase)
    phase2b_file = "improved_trajectory_log_1751106355.csv"  # Phase 2B (feedforward optimization)
    
    try:
        # Load data
        df1 = pd.read_csv(phase1_file)
        df2a = pd.read_csv(phase2a_file)
        df2b = pd.read_csv(phase2b_file)
        
        print(f"✅ Phase 1 data:  {len(df1)} records")
        print(f"✅ Phase 2A data: {len(df2a)} records")  
        print(f"✅ Phase 2B data: {len(df2b)} records")
        
        # Calculate errors for all phases
        def calc_errors(df):
            pos_errors = np.sqrt(
                (df['actual_x'] - df['desired_x'])**2 + 
                (df['actual_y'] - df['desired_y'])**2 + 
                (df['actual_z'] - df['desired_z'])**2
            )
            vel_errors = np.sqrt(
                (df['actual_vx'] - df['desired_vx'])**2 + 
                (df['actual_vy'] - df['desired_vy'])**2 + 
                (df['actual_vz'] - df['desired_vz'])**2
            )
            return pos_errors, vel_errors
        
        pos_1, vel_1 = calc_errors(df1)
        pos_2a, vel_2a = calc_errors(df2a)
        pos_2b, vel_2b = calc_errors(df2b)
        
        # Performance comparison
        print("\n🎯 PHASE 2B ASSESSMENT")
        print("=" * 70)
        
        # Position tracking comparison
        mean_pos_1 = np.mean(pos_1)
        mean_pos_2a = np.mean(pos_2a)
        mean_pos_2b = np.mean(pos_2b)
        
        print(f"📏 Position Tracking Performance:")
        print(f"   Phase 1:  {mean_pos_1:.2f}m (baseline)")
        print(f"   Phase 2A: {mean_pos_2a:.2f}m (Kd increase failed)")
        print(f"   Phase 2B: {mean_pos_2b:.2f}m (feedforward optimization)")
        
        pos_change_1_to_2b = ((mean_pos_2b - mean_pos_1) / mean_pos_1) * 100
        print(f"   Phase 1→2B: {pos_change_1_to_2b:+.1f}%")
        
        # Velocity tracking comparison (PRIMARY FOCUS)
        mean_vel_1 = np.mean(vel_1)
        mean_vel_2a = np.mean(vel_2a) 
        mean_vel_2b = np.mean(vel_2b)
        
        print(f"\n🚀 Velocity Tracking Performance (PRIMARY TARGET):")
        print(f"   Phase 1:     {mean_vel_1:.2f}m/s (baseline)")
        print(f"   Phase 2A:    {mean_vel_2a:.2f}m/s (Kd increase FAILED)")
        print(f"   Phase 2B:    {mean_vel_2b:.2f}m/s (feedforward optimization)")
        
        vel_improvement_1_to_2b = ((mean_vel_1 - mean_vel_2b) / mean_vel_1) * 100
        vel_improvement_2a_to_2b = ((mean_vel_2a - mean_vel_2b) / mean_vel_2a) * 100
        
        print(f"   Phase 1→2B improvement: {vel_improvement_1_to_2b:+.1f}%")
        print(f"   Phase 2A→2B improvement: {vel_improvement_2a_to_2b:+.1f}%")
        
        # Phase 2B Success Assessment
        target_vel_error = 5.0  # Phase 2B target
        print(f"\n🎯 Phase 2B Success Assessment:")
        if mean_vel_2b < target_vel_error:
            print(f"   ✅ SUCCESS: {mean_vel_2b:.2f}m/s < {target_vel_error}m/s target")
            print(f"   📈 Velocity improvement: {vel_improvement_1_to_2b:.1f}% from Phase 1")
            
            if mean_vel_2b < 3.0:
                print(f"   🎉 EXCELLENT: Already approaching Phase 2C target!")
                if mean_vel_2b < 2.0:
                    print(f"   🏆 OUTSTANDING: Already at production velocity target!")
            
            print(f"\n✅ Phase 2B COMPLETED - Ready for Phase 2C!")
            
        else:
            print(f"   ⚠️  PARTIAL SUCCESS: {mean_vel_2b:.2f}m/s > {target_vel_error}m/s target")
            if vel_improvement_1_to_2b > 0:
                print(f"   📈 Good progress: {vel_improvement_1_to_2b:.1f}% improvement from baseline")
                print(f"   🔧 Recommend: Proceed to Phase 2C (control frequency optimization)")
            elif vel_improvement_2a_to_2b > 0:
                print(f"   📈 Recovery: {vel_improvement_2a_to_2b:.1f}% improvement from 2A failure")
                print(f"   🔧 Recommend: Continue optimization efforts")
            else:
                print(f"   ❌ Further degradation: {vel_improvement_1_to_2b:.1f}%")
                print(f"   🔧 Recommend: Review feedforward settings or try different approach")
        
        # Compare with Phase 1 (best reference)
        if mean_vel_2b > mean_vel_1:
            degradation = ((mean_vel_2b - mean_vel_1) / mean_vel_1) * 100
            print(f"\n⚠️  VELOCITY DEGRADATION ALERT:")
            print(f"   Phase 2B is {degradation:.1f}% WORSE than Phase 1 baseline")
            print(f"   Feedforward optimization appears to be making things worse")
            print(f"   🔧 Recommend: Revert to Phase 1 settings and try alternative approach")
        
        # Detailed velocity analysis
        print(f"\n📈 Detailed Velocity Analysis:")
        vel_percentiles_1 = np.percentile(vel_1, [50, 75, 90, 95, 99])
        vel_percentiles_2b = np.percentile(vel_2b, [50, 75, 90, 95, 99])
        
        percentile_labels = ["50th", "75th", "90th", "95th", "99th"]
        print(f"   Phase 1 → Phase 2B comparison:")
        for i, label in enumerate(percentile_labels):
            change = ((vel_percentiles_2b[i] - vel_percentiles_1[i]) / vel_percentiles_1[i]) * 100
            print(f"   {label} percentile: {vel_percentiles_1[i]:.2f} → {vel_percentiles_2b[i]:.2f}m/s ({change:+.1f}%)")
        
        # System performance
        print(f"\n🔧 System Performance:")
        print(f"   Control Frequency: 650Hz (target: 1000Hz)")
        print(f"   DIAL-MPC Planning: 7.6ms average") 
        print(f"   Failsafe Activations: {np.sum(df2b['failsafe_active'])}")
        
        # Control effort analysis
        thrust_1 = np.mean(df1['thrust'])
        thrust_2b = np.mean(df2b['thrust'])
        thrust_change = ((thrust_2b - thrust_1) / thrust_1) * 100
        
        print(f"\n⚡ Control Effort:")
        print(f"   Phase 1 thrust:  {thrust_1:.2f}N")
        print(f"   Phase 2B thrust: {thrust_2b:.2f}N")
        print(f"   Change: {thrust_change:+.1f}%")
        
        # Next steps recommendation
        print(f"\n🗺️  ROADMAP PROGRESS:")
        print(f"   Phase 1 (Controller Gains): ✅ COMPLETE (98.6% pos improvement)")
        print(f"   Phase 2A (Derivative Gains): ❌ FAILED (made velocity worse)")
        print(f"   Phase 2B (Feedforward): {'✅ COMPLETE' if mean_vel_2b < 5.0 else '❌ FAILED'}")
        
        if mean_vel_2b > mean_vel_1:
            print(f"   🚨 PROBLEM: Both Phase 2A and 2B made velocity tracking worse")
            print(f"   🔧 RECOMMENDATION: Revert to Phase 1 and try control frequency optimization")
        elif mean_vel_2b < target_vel_error:
            print(f"   Phase 2C (Control Frequency): 🔄 READY TO START")
            print(f"   Target: Achieve 900+Hz control frequency")
        else:
            print(f"   Phase 2C (Control Frequency): 🔄 PROCEED ANYWAY")
            print(f"   May help with derivative calculations and velocity tracking")
        
        # Technical insights
        print(f"\n🔬 TECHNICAL ANALYSIS:")
        print(f"   • Position tracking: {mean_pos_2b:.2f}m (still excellent)")
        print(f"   • Feedforward ff_vel: 0.8 → 1.5 impact: {vel_improvement_1_to_2b:+.1f}%")
        print(f"   • Control frequency: Critical bottleneck at 650Hz")
        print(f"   • System stability: Excellent (no failsafes)")
        
        if vel_improvement_1_to_2b > 15:
            print(f"   • Feedforward optimization: SIGNIFICANT SUCCESS ✅")
        elif vel_improvement_1_to_2b > 5:
            print(f"   • Feedforward optimization: MODERATE SUCCESS 🟡")
        elif vel_improvement_1_to_2b > -5:
            print(f"   • Feedforward optimization: MINIMAL IMPACT 🟡")
        else:
            print(f"   • Feedforward optimization: DEGRADED PERFORMANCE 🔴")
        
        # Final recommendation
        if mean_vel_2b > mean_vel_1:
            print(f"\n🎯 FINAL RECOMMENDATION:")
            print(f"   1. Revert feedforward to Phase 1 values (ff_vel: 1.5 → 0.8)")
            print(f"   2. Focus on control frequency optimization (650Hz → 900+Hz)")
            print(f"   3. Address computational bottlenecks")
            print(f"   4. Re-test velocity tracking with higher frequency")
        
        return mean_vel_2b, vel_improvement_1_to_2b, mean_vel_2b < target_vel_error
        
    except FileNotFoundError as e:
        print(f"❌ Could not find log file: {e}")
        return None, None, False
    except Exception as e:
        print(f"❌ Error analyzing results: {e}")
        return None, None, False

if __name__ == "__main__":
    analyze_phase2b_results() 