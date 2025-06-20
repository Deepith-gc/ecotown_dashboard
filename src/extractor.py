"""
Advanced Biomarker Extraction and Processing Engine
==================================================

Core extraction logic for biomarkers from PDF lab reports and JSON data.
Supports multiple extraction strategies and robust pattern matching.
"""

import re
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
import fitz  # PyMuPDF
import pdfplumber
from dateutil import parser as date_parser

from .models import BiomarkerType, UnitType, BiomarkerValue, LabReport, PatientProfile

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result of biomarker extraction attempt"""
    value: float
    unit: UnitType
    confidence: float
    context: str
    pattern_used: str


class BiomarkerExtractor:
    """Advanced biomarker extraction with multiple strategies"""
    
    def __init__(self):
        # Comprehensive biomarker patterns with multiple variations
        self.biomarker_patterns = {
            BiomarkerType.TOTAL_CHOLESTEROL: [
                # Primary patterns with units
                r"(?i)(?:Total\s+)?Cholesterol[:\s]*(\d{2,4}(?:\.\d+)?)\s*(mg/dL|mg/dl|mg%|%)",
                r"(?i)Cholesterol\s+Total[:\s]*(\d{2,4}(?:\.\d+)?)\s*(mg/dL|mg/dl|mg%|%)",
                # Secondary patterns
                r"(?i)Total\s+Cholesterol[:\s]*(\d{2,4}(?:\.\d+)?)",
                r"(?i)Cholesterol[^0-9]{0,15}(\d{2,4}(?:\.\d+)?)",
                # Fallback patterns
                r"(?i)Chol[^0-9]{0,10}(\d{2,4}(?:\.\d+)?)",
            ],
            BiomarkerType.LDL: [
                # Primary patterns
                r"(?i)\bLDL[:\s]*(\d{2,4}(?:\.\d+)?)\s*(mg/dL|mg/dl|mg%|%)",
                r"(?i)LDL\s+Cholesterol[:\s]*(\d{2,4}(?:\.\d+)?)\s*(mg/dL|mg/dl|mg%|%)",
                r"(?i)Low\s+Density\s+Lipoprotein[:\s]*(\d{2,4}(?:\.\d+)?)",
                # Secondary patterns
                r"(?i)\bLDL[^a-zA-Z0-9]{0,10}(\d{2,4}(?:\.\d+)?)",
                r"(?i)LDL[^0-9]{0,15}(\d{2,4}(?:\.\d+)?)",
            ],
            BiomarkerType.HDL: [
                # Primary patterns
                r"(?i)\bHDL[:\s]*(\d{2,4}(?:\.\d+)?)\s*(mg/dL|mg/dl|mg%|%)",
                r"(?i)HDL\s+Cholesterol[:\s]*(\d{2,4}(?:\.\d+)?)\s*(mg/dL|mg/dl|mg%|%)",
                r"(?i)High\s+Density\s+Lipoprotein[:\s]*(\d{2,4}(?:\.\d+)?)",
                # Secondary patterns
                r"(?i)\bHDL[^a-zA-Z0-9]{0,10}(\d{2,4}(?:\.\d+)?)",
                r"(?i)HDL[^0-9]{0,15}(\d{2,4}(?:\.\d+)?)",
            ],
            BiomarkerType.TRIGLYCERIDES: [
                # Primary patterns
                r"(?i)Triglycerides[:\s]*(\d{2,4}(?:\.\d+)?)\s*(mg/dL|mg/dl|mg%|%)",
                r"(?i)TG[:\s]*(\d{2,4}(?:\.\d+)?)\s*(mg/dL|mg/dl|mg%|%)",
                r"(?i)Triglyceride[:\s]*(\d{2,4}(?:\.\d+)?)",
                # Secondary patterns
                r"(?i)Triglycerides[^0-9]{0,15}(\d{2,4}(?:\.\d+)?)",
                r"(?i)TG[^0-9]{0,10}(\d{2,4}(?:\.\d+)?)",
            ],
            BiomarkerType.CREATININE: [
                # Primary patterns
                r"(?i)Creatinine[:\s]*(\d{1,3}(?:\.\d+)?)\s*(mg/dL|mg/dl|umol/L|μmol/L)",
                r"(?i)Serum\s+Creatinine[:\s]*(\d{1,3}(?:\.\d+)?)",
                r"(?i)Creat[^0-9]{0,10}(\d{1,3}(?:\.\d+)?)",
                # Secondary patterns
                r"(?i)Creatinine[^0-9]{0,15}(\d{1,3}(?:\.\d+)?)",
            ],
            BiomarkerType.VITAMIN_D: [
                # Primary patterns
                r"(?i)Vitamin\s+D[:\s]*(\d{1,3}(?:\.\d+)?)\s*(ng/mL|ng/ml|nmol/L)",
                r"(?i)25-OH\s+Vitamin\s+D[:\s]*(\d{1,3}(?:\.\d+)?)",
                r"(?i)25-Hydroxyvitamin\s+D[:\s]*(\d{1,3}(?:\.\d+)?)",
                r"(?i)Vit\s*D[:\s]*(\d{1,3}(?:\.\d+)?)",
                # Secondary patterns
                r"(?i)Vitamin\s*D[^0-9]{0,15}(\d{1,3}(?:\.\d+)?)",
                r"(?i)Vit\s*D[^0-9]{0,10}(\d{1,3}(?:\.\d+)?)",
            ],
            BiomarkerType.VITAMIN_B12: [
                # Primary patterns
                r"(?i)Vitamin\s+B\s*12[:\s]*(\d{3,5}(?:\.\d+)?)\s*(pg/mL|pg/ml|pmol/L)",
                r"(?i)Vit\s*B\s*12[:\s]*(\d{3,5}(?:\.\d+)?)",
                r"(?i)Cobalamin[:\s]*(\d{3,5}(?:\.\d+)?)",
                # Secondary patterns
                r"(?i)Vitamin\s*B\s*12[^0-9]{0,15}(\d{3,5}(?:\.\d+)?)",
                r"(?i)B12[^0-9]{0,10}(\d{3,5}(?:\.\d+)?)",
            ],
            BiomarkerType.HBA1C: [
                # Primary patterns
                r"(?i)Hb\s*A1c[:\s]*(\d{1,2}(?:\.\d+)?)\s*(%|percent)",
                r"(?i)Glycated\s+Hemoglobin[:\s]*(\d{1,2}(?:\.\d+)?)",
                r"(?i)HbA1c[:\s]*(\d{1,2}(?:\.\d+)?)",
                # Secondary patterns
                r"(?i)Hb\s*A1c[^0-9]{0,15}(\d{1,2}(?:\.\d+)?)",
                r"(?i)A1c[^0-9]{0,10}(\d{1,2}(?:\.\d+)?)",
            ]
        }
        
        # Reference ranges for validation
        self.reference_ranges = {
            BiomarkerType.TOTAL_CHOLESTEROL: {"min": 125, "max": 200, "unit": UnitType.MG_DL},
            BiomarkerType.LDL: {"min": 0, "max": 100, "unit": UnitType.MG_DL},
            BiomarkerType.HDL: {"min": 40, "max": 60, "unit": UnitType.MG_DL},
            BiomarkerType.TRIGLYCERIDES: {"min": 0, "max": 150, "unit": UnitType.MG_DL},
            BiomarkerType.CREATININE: {"min": 0.6, "max": 1.3, "unit": UnitType.MG_DL},
            BiomarkerType.VITAMIN_D: {"min": 30, "max": 100, "unit": UnitType.NG_ML},
            BiomarkerType.VITAMIN_B12: {"min": 200, "max": 900, "unit": UnitType.PG_ML},
            BiomarkerType.HBA1C: {"min": 4.0, "max": 5.6, "unit": UnitType.PERCENT}
        }
        
        # Unit mappings for standardization
        self.unit_mappings = {
            "mg/dL": UnitType.MG_DL,
            "mg/dl": UnitType.MG_DL,
            "mg%": UnitType.MG_DL,
            "%": UnitType.PERCENT,
            "percent": UnitType.PERCENT,
            "ng/mL": UnitType.NG_ML,
            "ng/ml": UnitType.NG_ML,
            "pg/mL": UnitType.PG_ML,
            "pg/ml": UnitType.PG_ML,
            "umol/L": UnitType.UMOL_L,
            "μmol/L": UnitType.UMOL_L,
            "nmol/L": UnitType.NMOL_L,
            "pmol/L": UnitType.PMOL_L,
        }

    def load_json_data(self, json_path: str) -> Dict[str, Any]:
        """Load existing JSON data files"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"✅ Loaded JSON data from: {json_path}")
            return data
        except Exception as e:
            logger.error(f"❌ Error loading JSON data from {json_path}: {str(e)}")
            return {}

    def convert_legacy_to_patient_profile(self, legacy_data: Dict[str, Any]) -> PatientProfile:
        """Convert legacy JSON format to new PatientProfile model"""
        try:
            # Extract patient information
            patient_id = legacy_data.get("patient", "Unknown").replace(" ", "_").upper()
            name = legacy_data.get("patient", "Unknown")
            age = legacy_data.get("age")
            gender = legacy_data.get("gender")
            
            # Convert reports
            reports = []
            for report_data in legacy_data.get("reports", []):
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
                        # Map legacy biomarker names to enum
                        biomarker_type = self._map_biomarker_name(biomarker_name)
                        if biomarker_type:
                            # Get reference range
                            ref_range = self.reference_ranges[biomarker_type]
                            
                            # Create BiomarkerValue
                            biomarker_value = BiomarkerValue(
                                value=float(value),
                                unit=ref_range["unit"],
                                reference_range={"min": ref_range["min"], "max": ref_range["max"]},
                                status=self._get_status(biomarker_type, float(value)),
                                confidence=1.0  # Legacy data assumed to be accurate
                            )
                            biomarkers[biomarker_type] = biomarker_value
                    except Exception as e:
                        logger.warning(f"Error converting biomarker {biomarker_name}: {str(e)}")
                
                # Create LabReport
                lab_report = LabReport(
                    report_date=report_date,
                    source_file=report_data.get("source_file", "Unknown"),
                    biomarkers=biomarkers,
                    extraction_metadata={
                        "converted_from_legacy": True,
                        "original_data": report_data
                    }
                )
                reports.append(lab_report)
            
            # Create PatientProfile
            patient_profile = PatientProfile(
                patient_id=patient_id,
                name=name,
                age=age,
                gender=gender,
                reports=reports
            )
            
            logger.info(f"✅ Converted legacy data: {len(reports)} reports, {sum(len(r.biomarkers) for r in reports)} biomarkers")
            return patient_profile
            
        except Exception as e:
            logger.error(f"❌ Error converting legacy data: {str(e)}")
            raise

    def _map_biomarker_name(self, legacy_name: str) -> Optional[BiomarkerType]:
        """Map legacy biomarker names to enum values"""
        mapping = {
            "Total Cholesterol": BiomarkerType.TOTAL_CHOLESTEROL,
            "LDL": BiomarkerType.LDL,
            "HDL": BiomarkerType.HDL,
            "Triglycerides": BiomarkerType.TRIGLYCERIDES,
            "Creatinine": BiomarkerType.CREATININE,
            "Vitamin D": BiomarkerType.VITAMIN_D,
            "Vitamin B12": BiomarkerType.VITAMIN_B12,
            "HbA1c": BiomarkerType.HBA1C,
        }
        return mapping.get(legacy_name)

    def _get_status(self, biomarker_type: BiomarkerType, value: float) -> str:
        """Determine clinical status based on reference ranges"""
        ref_range = self.reference_ranges[biomarker_type]
        min_val, max_val = ref_range["min"], ref_range["max"]
        
        if value < min_val:
            return "Low"
        elif value > max_val:
            return "High"
        else:
            return "Normal"

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using multiple strategies"""
        text_parts = []
        
        try:
            # Strategy 1: PyMuPDF (fitz)
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                text_parts.append(text)
            doc.close()
            
            # Strategy 2: pdfplumber (if PyMuPDF fails)
            if not any(text_parts):
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
            
            return " ".join(text_parts)
            
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {str(e)}")
            return ""

    def extract_date(self, text: str, filename: str = "") -> datetime:
        """Extract and parse date from text with multiple strategies"""
        try:
            # Strategy 1: Look for date patterns in text
            date_patterns = [
                r"(\d{4}-\d{2}-\d{2})",  # ISO format
                r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",  # DD/MM/YYYY or MM/DD/YYYY
                r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})",  # DD Month YYYY
                r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4})",  # Month DD, YYYY
                r"(\d{1,2}-\d{1,2}-\d{2,4})",  # DD-MM-YYYY
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        # Try multiple date formats
                        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y"]:
                            try:
                                return datetime.strptime(match.strip(), fmt)
                            except ValueError:
                                continue
                        
                        # Try dateutil parser as fallback
                        return date_parser.parse(match.strip())
                    except:
                        continue
            
            # Strategy 2: Extract from filename
            if filename:
                date_match = re.search(r"(\d{4}[-_]\d{2}[-_]\d{2})", filename)
                if date_match:
                    return datetime.strptime(date_match.group(1), "%Y-%m-%d")
            
            # Strategy 3: Default to current date
            logger.warning(f"No date found, using current date")
            return datetime.now()
            
        except Exception as e:
            logger.error(f"Error extracting date: {str(e)}")
            return datetime.now()

    def extract_biomarker(self, text: str, biomarker_type: BiomarkerType) -> Optional[ExtractionResult]:
        """Extract a single biomarker with confidence scoring"""
        patterns = self.biomarker_patterns.get(biomarker_type, [])
        
        for i, pattern in enumerate(patterns):
            try:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Extract value and unit
                    value = float(match.group(1))
                    
                    # Extract unit if available
                    unit = None
                    if len(match.groups()) > 1 and match.group(2):
                        unit_str = match.group(2)
                        unit = self.unit_mappings.get(unit_str)
                    
                    # Infer unit if not found
                    if not unit:
                        unit = self.reference_ranges[biomarker_type]["unit"]
                    
                    # Calculate confidence based on pattern position and context
                    confidence = 1.0 - (i * 0.15)  # Primary patterns have higher confidence
                    
                    # Get context for debugging
                    start = max(0, match.start() - 30)
                    end = min(len(text), match.end() + 30)
                    context = text[start:end].strip()
                    
                    # Validate value ranges
                    if self._validate_value(biomarker_type, value):
                        return ExtractionResult(
                            value=value,
                            unit=unit,
                            confidence=confidence,
                            context=context,
                            pattern_used=pattern
                        )
                    
            except (ValueError, IndexError) as e:
                logger.debug(f"Pattern {i} failed for {biomarker_type}: {str(e)}")
                continue
        
        return None

    def _validate_value(self, biomarker_type: BiomarkerType, value: float) -> bool:
        """Validate if the extracted value is within reasonable ranges"""
        ranges = {
            BiomarkerType.TOTAL_CHOLESTEROL: (50, 600),
            BiomarkerType.LDL: (20, 300),
            BiomarkerType.HDL: (10, 100),
            BiomarkerType.TRIGLYCERIDES: (20, 1000),
            BiomarkerType.CREATININE: (0.1, 20),
            BiomarkerType.VITAMIN_D: (1, 200),
            BiomarkerType.VITAMIN_B12: (50, 2000),
            BiomarkerType.HBA1C: (3, 20)
        }
        
        min_val, max_val = ranges.get(biomarker_type, (0, float('inf')))
        return min_val <= value <= max_val

    def extract_all_biomarkers(self, text: str) -> Dict[BiomarkerType, BiomarkerValue]:
        """Extract all biomarkers from text"""
        results = {}
        
        for biomarker_type in BiomarkerType:
            extraction_result = self.extract_biomarker(text, biomarker_type)
            if extraction_result:
                # Get reference range
                ref_range = self.reference_ranges[biomarker_type]
                
                # Create BiomarkerValue object
                biomarker_value = BiomarkerValue(
                    value=extraction_result.value,
                    unit=extraction_result.unit,
                    reference_range={"min": ref_range["min"], "max": ref_range["max"]},
                    status=self._get_status(biomarker_type, extraction_result.value),
                    confidence=extraction_result.confidence
                )
                
                results[biomarker_type] = biomarker_value
                logger.info(f"✅ {biomarker_type.value}: {extraction_result.value} {extraction_result.unit.value} (confidence: {extraction_result.confidence:.2f})")
            else:
                logger.warning(f"❌ {biomarker_type.value}: Not found")
        
        return results

    def parse_pdf_report(self, pdf_path: str) -> LabReport:
        """Parse a single PDF report"""
        logger.info(f"📄 Processing: {pdf_path}")
        
        try:
            # Extract text
            text = self.extract_text_from_pdf(pdf_path)
            if not text.strip():
                logger.error(f"Empty text extracted from {pdf_path}")
                return LabReport(
                    report_date=datetime.now(),
                    source_file=pdf_path,
                    biomarkers={},
                    extraction_metadata={"error": "Empty text extracted"}
                )
            
            # Extract date
            date = self.extract_date(text, os.path.basename(pdf_path))
            logger.info(f"📅 Date extracted: {date}")
            
            # Extract biomarkers
            biomarkers = self.extract_all_biomarkers(text)
            
            # Create extraction metadata
            metadata = {
                "text_length": len(text),
                "biomarkers_found": len(biomarkers),
                "extraction_timestamp": datetime.now().isoformat(),
                "patterns_used": {bm.value: biomarkers[bm].confidence for bm in biomarkers}
            }
            
            return LabReport(
                report_date=date,
                source_file=os.path.basename(pdf_path),
                biomarkers=biomarkers,
                extraction_metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {str(e)}")
            return LabReport(
                report_date=datetime.now(),
                source_file=pdf_path,
                biomarkers={},
                extraction_metadata={"error": str(e)}
            )


# Import os at the top level
import os 