#!/usr/bin/env python3
"""
Motor Latency Calibration CLI

Usage:
    python scripts/calibrate_motor_latency.py [--adapter pixhawk|airsim] [--samples 50] [--output report.json]
"""

import argparse
import json
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dart_planner.hardware.motor_latency_calibration import calibrate_motor_latency, MotorLatencyCalibrator
from dart_planner.hardware.pixhawk_adapter import PixhawkAdapter
from dart_planner.hardware.airsim_adapter import AirSimAdapter

def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def create_adapter(adapter_type: str):
    """Create hardware adapter based on type."""
    if adapter_type.lower() == "pixhawk":
        return PixhawkAdapter()
    elif adapter_type.lower() == "airsim":
        return AirSimAdapter()
    else:
        raise ValueError(f"Unknown adapter type: {adapter_type}")

def main():
    """Main calibration function."""
    parser = argparse.ArgumentParser(description="Motor Latency Calibration")
    parser.add_argument("--adapter", choices=["pixhawk", "airsim"], default="pixhawk",
                       help="Hardware adapter type")
    parser.add_argument("--samples", type=int, default=50,
                       help="Number of calibration samples")
    parser.add_argument("--output", type=str, default="motor_latency_report.json",
                       help="Output file for calibration report")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--config", type=str,
                       help="Path to calibration configuration file")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Starting motor latency calibration with {args.adapter} adapter")
        
        # Create hardware adapter
        adapter = create_adapter(args.adapter)
        
        # Connect to hardware
        logger.info("Connecting to hardware...")
        adapter.connect()
        
        if not adapter.is_connected():
            logger.error("Failed to connect to hardware")
            return 1
        
        logger.info("Hardware connected successfully")
        
        # Load configuration if provided
        config = None
        if args.config:
            with open(args.config, 'r') as f:
                config = json.load(f)
        
        # Create calibrator
        calibrator = MotorLatencyCalibrator(adapter, config)
        
        # Run calibration
        logger.info(f"Running calibration with {args.samples} samples...")
        result = calibrator.calibrate_latency(args.samples)
        
        # Generate report
        report = calibrator.get_calibration_report()
        
        # Save report
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "="*60)
        print("MOTOR LATENCY CALIBRATION RESULTS")
        print("="*60)
        print(f"Adapter: {args.adapter}")
        print(f"Samples: {result.sample_count}")
        print(f"Mean Latency: {result.mean_latency_ms:.2f}ms")
        print(f"Std Dev: {result.std_latency_ms:.2f}ms")
        print(f"95th Percentile: {result.p95_latency_ms:.2f}ms")
        print(f"99th Percentile: {result.p99_latency_ms:.2f}ms")
        print(f"Recommended max_control_latency_ms: {result.recommended_max_latency_ms:.2f}ms")
        print(f"Calibration Quality: {result.calibration_quality}")
        print(f"Confidence Interval: {result.confidence_interval_ms[0]:.2f}ms - {result.confidence_interval_ms[1]:.2f}ms")
        print("="*60)
        
        # Update configuration if calibration was successful
        if result.calibration_quality in ["excellent", "good"]:
            logger.info("Calibration quality is good, updating configuration...")
            if calibrator.update_config_latency(result):
                logger.info("Configuration updated successfully")
            else:
                logger.warning("Failed to update configuration")
        else:
            logger.warning(f"Calibration quality is {result.calibration_quality}, not updating configuration")
        
        logger.info(f"Calibration report saved to {args.output}")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Calibration interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Calibration failed: {e}")
        return 1
    finally:
        # Disconnect from hardware
        try:
            if 'adapter' in locals():
                adapter.disconnect()
                logger.info("Hardware disconnected")
        except Exception as e:
            logger.warning(f"Error disconnecting from hardware: {e}")

if __name__ == "__main__":
    sys.exit(main()) 