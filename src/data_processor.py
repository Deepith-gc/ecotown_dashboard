"""
Data Processor for Biomarker Analysis
====================================

Processes and analyzes biomarker data from JSON files and provides
enhanced insights and trend analysis.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from collections import defaultdict

from .models import (
    PatientProfile, LabReport, BiomarkerType, BiomarkerValue, 
    BiomarkerTrend, DashboardData
)
from .extractor import BiomarkerExtractor

logger = logging.getLogger(__name__)


class BiomarkerDataProcessor:
    """Processes and analyzes biomarker data"""
    
    def __init__(self):
        self.extractor = BiomarkerExtractor()
        
    def load_and_process_data(self, json_paths: List[str]) -> PatientProfile:
        """Load and process multiple JSON data files"""
        logger.info(f"🔄 Loading data from {len(json_paths)} files")
        
        all_reports = []
        patient_info = {}
        
        for json_path in json_paths:
            try:
                # Load JSON data
                data = self.extractor.load_json_data(json_path)
                if not data:
                    continue
                
                # Extract patient info from first file
                if not patient_info:
                    patient_info = {
                        "patient_id": data.get("patient", "Unknown").replace(" ", "_").upper(),
                        "name": data.get("patient", "Unknown"),
                        "age": data.get("age"),
                        "gender": data.get("gender")
                    }
                
                # Process reports
                for report_data in data.get("reports", []):
                    # Parse date
                    date_str = report_data.get("report_date", "Unknown")
                    if date_str == "Unknown":
                        report_date = datetime.now()
                    else:
                        try:
                            report_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        except:
                            report_date = datetime.now()
                    
                    # Convert biomarkers
                    biomarkers = {}
                    for biomarker_name, value in report_data.get("biomarkers", {}).items():
                        try:
                            biomarker_type = self.extractor._map_biomarker_name(biomarker_name)
                            if biomarker_type:
                                ref_range = self.extractor.reference_ranges[biomarker_type]
                                
                                biomarker_value = BiomarkerValue(
                                    value=float(value),
                                    unit=ref_range["unit"],
                                    reference_range={"min": ref_range["min"], "max": ref_range["max"]},
                                    status=self.extractor._get_status(biomarker_type, float(value)),
                                    confidence=1.0
                                )
                                biomarkers[biomarker_type] = biomarker_value
                        except Exception as e:
                            logger.warning(f"Error processing biomarker {biomarker_name}: {str(e)}")
                    
                    # Create LabReport
                    lab_report = LabReport(
                        report_date=report_date,
                        source_file=report_data.get("source_file", f"from_{json_path}"),
                        biomarkers=biomarkers,
                        extraction_metadata={
                            "source_file": json_path,
                            "original_data": report_data
                        }
                    )
                    all_reports.append(lab_report)
                    
            except Exception as e:
                logger.error(f"Error processing {json_path}: {str(e)}")
        
        # Sort reports by date
        all_reports.sort(key=lambda x: x.report_date)
        
        # Create PatientProfile
        patient_profile = PatientProfile(
            patient_id=patient_info.get("patient_id", "UNKNOWN"),
            name=patient_info.get("name", "Unknown"),
            age=patient_info.get("age"),
            gender=patient_info.get("gender"),
            reports=all_reports
        )
        
        logger.info(f"✅ Processed {len(all_reports)} reports with {sum(len(r.biomarkers) for r in all_reports)} total biomarkers")
        return patient_profile
    
    def calculate_trends(self, patient_profile: PatientProfile) -> Dict[BiomarkerType, BiomarkerTrend]:
        """Calculate trends for each biomarker"""
        trends = {}
        
        for biomarker_type in BiomarkerType:
            # Collect all values for this biomarker
            values = []
            dates = []
            
            for report in patient_profile.reports:
                if biomarker_type in report.biomarkers:
                    biomarker = report.biomarkers[biomarker_type]
                    values.append(biomarker.value)
                    dates.append(report.report_date)
            
            if len(values) < 2:
                continue
            
            # Calculate trend direction and strength
            trend_direction, trend_strength = self._calculate_trend_direction(values)
            
            # Calculate percentage change
            if values[0] != 0:
                change_percentage = ((values[-1] - values[0]) / values[0]) * 100
            else:
                change_percentage = 0.0
            
            # Create BiomarkerTrend
            trend = BiomarkerTrend(
                biomarker=biomarker_type,
                values=values,
                dates=dates,
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                latest_value=values[-1],
                change_percentage=change_percentage
            )
            
            trends[biomarker_type] = trend
        
        return trends
    
    def _calculate_trend_direction(self, values: List[float]) -> Tuple[str, float]:
        """Calculate trend direction and strength"""
        if len(values) < 2:
            return "stable", 0.0
        
        # Calculate linear regression
        x = np.arange(len(values))
        y = np.array(values)
        
        # Simple linear regression
        n = len(values)
        sum_x = np.sum(x)
        sum_y = np.sum(y)
        sum_xy = np.sum(x * y)
        sum_x2 = np.sum(x * x)
        
        # Calculate slope
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Calculate R-squared for trend strength
        y_mean = np.mean(y)
        ss_tot = np.sum((y - y_mean) ** 2)
        ss_res = np.sum((y - (slope * x + (sum_y - slope * sum_x) / n)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # Determine direction
        if abs(slope) < 0.01:  # Very small slope
            direction = "stable"
        elif slope > 0:
            direction = "rising"
        else:
            direction = "falling"
        
        return direction, min(r_squared, 1.0)
    
    def generate_summary_stats(self, patient_profile: PatientProfile) -> Dict[str, Any]:
        """Generate summary statistics"""
        stats = {
            "total_reports": len(patient_profile.reports),
            "monitoring_period_days": 0,
            "total_biomarkers": 0,
            "biomarker_counts": {},
            "status_summary": {"Normal": 0, "High": 0, "Low": 0},
            "latest_values": {},
            "critical_alerts": []
        }
        
        if patient_profile.reports:
            # Calculate monitoring period
            dates = [r.report_date for r in patient_profile.reports]
            stats["monitoring_period_days"] = (max(dates) - min(dates)).days
            
            # Count biomarkers and status
            for report in patient_profile.reports:
                stats["total_biomarkers"] += len(report.biomarkers)
                
                for biomarker_type, biomarker in report.biomarkers.items():
                    # Count by biomarker type
                    stats["biomarker_counts"][biomarker_type.value] = \
                        stats["biomarker_counts"].get(biomarker_type.value, 0) + 1
                    
                    # Count by status
                    if biomarker.status:
                        stats["status_summary"][biomarker.status] += 1
                    
                    # Store latest values
                    stats["latest_values"][biomarker_type.value] = biomarker.value
                    
                    # Check for critical values
                    if biomarker.status in ["High", "Low"]:
                        ref_range = biomarker.reference_range
                        if ref_range:
                            if biomarker.status == "High" and biomarker.value > ref_range["max"] * 1.5:
                                stats["critical_alerts"].append({
                                    "biomarker": biomarker_type.value,
                                    "value": biomarker.value,
                                    "status": "Critically High",
                                    "reference_max": ref_range["max"]
                                })
                            elif biomarker.status == "Low" and biomarker.value < ref_range["min"] * 0.5:
                                stats["critical_alerts"].append({
                                    "biomarker": biomarker_type.value,
                                    "value": biomarker.value,
                                    "status": "Critically Low",
                                    "reference_min": ref_range["min"]
                                })
        
        return stats
    
    def generate_alerts(self, patient_profile: PatientProfile, trends: Dict[BiomarkerType, BiomarkerTrend]) -> List[Dict[str, str]]:
        """Generate clinical alerts and recommendations"""
        alerts = []
        
        # Check latest values for abnormalities
        if patient_profile.reports:
            latest_report = patient_profile.reports[-1]
            
            for biomarker_type, biomarker in latest_report.biomarkers.items():
                if biomarker.status != "Normal":
                    # Get trend information
                    trend_info = trends.get(biomarker_type)
                    trend_text = ""
                    if trend_info:
                        if trend_info.trend_direction == "rising" and biomarker.status == "High":
                            trend_text = " (trending upward)"
                        elif trend_info.trend_direction == "falling" and biomarker.status == "Low":
                            trend_text = " (trending downward)"
                    
                    # Generate alert message
                    alert = {
                        "type": "biomarker_alert",
                        "severity": "high" if biomarker.status in ["High", "Low"] else "medium",
                        "biomarker": biomarker_type.value,
                        "value": f"{biomarker.value} {biomarker.unit.value}",
                        "status": biomarker.status,
                        "message": f"{biomarker_type.value} is {biomarker.status.lower()}{trend_text}. Current value: {biomarker.value} {biomarker.unit.value}",
                        "recommendation": self._get_recommendation(biomarker_type, biomarker.status, biomarker.value)
                    }
                    alerts.append(alert)
        
        # Check for trends that might be concerning
        for biomarker_type, trend in trends.items():
            if trend.trend_direction == "rising" and trend.change_percentage > 20:
                alerts.append({
                    "type": "trend_alert",
                    "severity": "medium",
                    "biomarker": biomarker_type.value,
                    "message": f"{biomarker_type.value} has increased by {trend.change_percentage:.1f}% over the monitoring period",
                    "recommendation": f"Monitor {biomarker_type.value} closely and consider lifestyle modifications"
                })
            elif trend.trend_direction == "falling" and trend.change_percentage < -20:
                alerts.append({
                    "type": "trend_alert",
                    "severity": "medium",
                    "biomarker": biomarker_type.value,
                    "message": f"{biomarker_type.value} has decreased by {abs(trend.change_percentage):.1f}% over the monitoring period",
                    "recommendation": f"Monitor {biomarker_type.value} closely and consider supplementation if appropriate"
                })
        
        return alerts
    
    def _get_recommendation(self, biomarker_type: BiomarkerType, status: str, value: float) -> str:
        """Get clinical recommendation based on biomarker status"""
        recommendations = {
            BiomarkerType.TOTAL_CHOLESTEROL: {
                "High": "Consider dietary changes, exercise, and medication if prescribed by your doctor.",
                "Low": "Monitor for underlying health conditions that may cause low cholesterol."
            },
            BiomarkerType.LDL: {
                "High": "Focus on heart-healthy diet, regular exercise, and consider medication.",
                "Low": "Low LDL is generally good for heart health."
            },
            BiomarkerType.HDL: {
                "High": "Excellent! High HDL is protective for heart health.",
                "Low": "Increase physical activity and consider heart-healthy diet changes."
            },
            BiomarkerType.TRIGLYCERIDES: {
                "High": "Reduce sugar and refined carbs, increase physical activity.",
                "Low": "Low triglycerides are generally beneficial."
            },
            BiomarkerType.CREATININE: {
                "High": "Consult with healthcare provider about kidney function.",
                "Low": "May indicate reduced muscle mass or other conditions."
            },
            BiomarkerType.VITAMIN_D: {
                "High": "Consider reducing supplementation and consult healthcare provider.",
                "Low": "Increase sun exposure, dietary sources, or consider supplementation."
            },
            BiomarkerType.VITAMIN_B12: {
                "High": "High levels are usually not harmful but consult healthcare provider.",
                "Low": "Consider B12 supplementation or dietary changes."
            },
            BiomarkerType.HBA1C: {
                "High": "Focus on blood sugar management through diet, exercise, and medication.",
                "Low": "Monitor for hypoglycemia or other conditions."
            }
        }
        
        return recommendations.get(biomarker_type, {}).get(status, "Continue monitoring and consult healthcare provider.")
    
    def create_dashboard_data(self, json_paths: List[str]) -> DashboardData:
        """Create complete dashboard data from JSON files"""
        logger.info("🚀 Creating dashboard data from JSON files")
        
        # Load and process data
        patient_profile = self.load_and_process_data(json_paths)
        
        # Calculate trends
        trends = self.calculate_trends(patient_profile)
        
        # Generate summary statistics
        summary_stats = self.generate_summary_stats(patient_profile)
        
        # Generate alerts
        alerts = self.generate_alerts(patient_profile, trends)
        
        # Create DashboardData
        dashboard_data = DashboardData(
            patient_profile=patient_profile,
            trends=trends,
            summary_stats=summary_stats,
            alerts=alerts
        )
        
        logger.info(f"✅ Dashboard data created: {len(trends)} trends, {len(alerts)} alerts")
        return dashboard_data
    
    def export_to_json(self, dashboard_data: DashboardData, output_path: str) -> None:
        """Export dashboard data to JSON format"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(dashboard_data.dict(), f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"💾 Dashboard data exported to: {output_path}")
        except Exception as e:
            logger.error(f"❌ Error exporting data: {str(e)}")
            raise 