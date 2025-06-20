#!/usr/bin/env python3
"""
Biomarker Analysis and Visualization System
==========================================

Main application entry point for processing biomarker data
and generating insights and visualizations.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.data_processor import BiomarkerDataProcessor
from src.models import DashboardData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Main application function"""
    logger.info("Starting Biomarker Analysis System")
    
    # Setup paths
    base_dir = Path(__file__).parent
    extract_dir = base_dir / "extract"
    public_dir = base_dir / "public"
    
    # Find JSON data files
    json_files = [
        extract_dir / "combined_patient_data.json",
        extract_dir / "enhanced_patient_data.json"
    ]
    
    # Filter to existing files
    existing_files = [str(f) for f in json_files if f.exists()]
    
    if not existing_files:
        logger.error("No JSON data files found!")
        logger.info("Expected files:")
        for f in json_files:
            logger.info(f"  - {f}")
        return
    
    logger.info(f"Found {len(existing_files)} JSON data files:")
    for f in existing_files:
        logger.info(f"  - {f}")
    
    try:
        # Create data processor
        processor = BiomarkerDataProcessor()
        
        # Process data and create dashboard
        dashboard_data = processor.create_dashboard_data(existing_files)
        
        # Export enhanced data
        enhanced_output = extract_dir / "processed_patient_data.json"
        processor.export_to_json(dashboard_data, str(enhanced_output))
        
        # Export for web dashboard
        web_output = public_dir / "dashboard_data.json"
        processor.export_to_json(dashboard_data, str(web_output))
        
        # Print summary
        print("\n" + "="*60)
        print("BIOMARKER ANALYSIS SUMMARY")
        print("="*60)
        print(f"Patient: {dashboard_data.patient_profile.name}")
        print(f"Age: {dashboard_data.patient_profile.age}")
        print(f"Gender: {dashboard_data.patient_profile.gender}")
        print(f"Total Reports: {dashboard_data.summary_stats['total_reports']}")
        print(f"Monitoring Period: {dashboard_data.summary_stats['monitoring_period_days']} days")
        print(f"Total Biomarkers: {dashboard_data.summary_stats['total_biomarkers']}")
        
        print(f"\nTREND ANALYSIS:")
        for biomarker_type, trend in dashboard_data.trends.items():
            print(f"  {biomarker_type.value}: {trend.trend_direction} ({trend.change_percentage:+.1f}%)")
        
        print(f"\nALERTS ({len(dashboard_data.alerts)}):")
        for alert in dashboard_data.alerts:
            print(f"  • {alert['message']}")
        
        print(f"\nData exported to:")
        print(f"  - {enhanced_output}")
        print(f"  - {web_output}")
        print("="*60)
        
        logger.info("Application completed successfully!")
        
    except Exception as e:
        logger.error(f"Application failed: {str(e)}")
        raise


if __name__ == "__main__":
    main() 