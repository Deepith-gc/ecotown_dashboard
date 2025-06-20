"""
Data Models for Biomarker Extraction System
===========================================

Defines the data structures used throughout the application.
"""

from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class BiomarkerType(str, Enum):
    """Enumeration of supported biomarker types"""
    TOTAL_CHOLESTEROL = "Total Cholesterol"
    LDL = "LDL"
    HDL = "HDL"
    TRIGLYCERIDES = "Triglycerides"
    CREATININE = "Creatinine"
    VITAMIN_D = "Vitamin D"
    VITAMIN_B12 = "Vitamin B12"
    HBA1C = "HbA1c"


class UnitType(str, Enum):
    """Enumeration of measurement units"""
    MG_DL = "mg/dL"
    NG_ML = "ng/mL"
    PG_ML = "pg/mL"
    PERCENT = "%"
    UMOL_L = "μmol/L"
    NMOL_L = "nmol/L"
    PMOL_L = "pmol/L"


class BiomarkerValue(BaseModel):
    """Individual biomarker measurement"""
    value: float = Field(..., description="Numeric value of the biomarker")
    unit: UnitType = Field(..., description="Unit of measurement")
    reference_range: Optional[Dict[str, float]] = Field(
        None, description="Reference range (min, max)"
    )
    status: Optional[str] = Field(None, description="Status: Normal, High, Low")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Extraction confidence score")

    @validator('value')
    def validate_value(cls, v):
        if v < 0:
            raise ValueError('Biomarker value cannot be negative')
        return v


class LabReport(BaseModel):
    """Individual laboratory report"""
    report_date: datetime = Field(..., description="Date of the report")
    source_file: str = Field(..., description="Original PDF filename")
    biomarkers: Dict[BiomarkerType, BiomarkerValue] = Field(
        default_factory=dict, description="Extracted biomarkers"
    )
    extraction_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Extraction process metadata"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PatientProfile(BaseModel):
    """Complete patient profile with all reports"""
    patient_id: str = Field(..., description="Unique patient identifier")
    name: str = Field(..., description="Patient name")
    age: Optional[int] = Field(None, ge=0, le=150, description="Patient age")
    gender: Optional[str] = Field(None, description="Patient gender")
    reports: List[LabReport] = Field(default_factory=list, description="All lab reports")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExtractionRequest(BaseModel):
    """Request model for PDF extraction"""
    patient_id: str = Field(..., description="Patient identifier")
    patient_name: str = Field(..., description="Patient name")
    patient_age: Optional[int] = Field(None, description="Patient age")
    patient_gender: Optional[str] = Field(None, description="Patient gender")


class ExtractionResponse(BaseModel):
    """Response model for extraction results"""
    success: bool = Field(..., description="Extraction success status")
    patient_profile: Optional[PatientProfile] = Field(None, description="Extracted patient data")
    message: str = Field(..., description="Response message")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")


class BiomarkerTrend(BaseModel):
    """Biomarker trend analysis"""
    biomarker: BiomarkerType = Field(..., description="Biomarker type")
    values: List[float] = Field(..., description="Historical values")
    dates: List[datetime] = Field(..., description="Corresponding dates")
    trend_direction: str = Field(..., description="Trend: rising, falling, stable")
    trend_strength: float = Field(..., ge=0.0, le=1.0, description="Trend strength")
    latest_value: float = Field(..., description="Most recent value")
    change_percentage: float = Field(..., description="Percentage change from first to last")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DashboardData(BaseModel):
    """Complete dashboard data structure"""
    patient_profile: PatientProfile = Field(..., description="Patient information")
    trends: Dict[BiomarkerType, BiomarkerTrend] = Field(
        default_factory=dict, description="Trend analysis for each biomarker"
    )
    summary_stats: Dict[str, Any] = Field(
        default_factory=dict, description="Summary statistics"
    )
    alerts: List[Dict[str, str]] = Field(
        default_factory=list, description="Clinical alerts and recommendations"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        } 