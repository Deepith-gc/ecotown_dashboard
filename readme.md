🩺 EcoTown Health Analytics Dashboard
A Clinical-Grade Biomarker Time Series Visualization Dashboard for monitoring patient biomarker trends over time. Designed for EcoTown Health Tech, this project delivers actionable clinical insights and interactive, mobile-friendly charts for clinical review.

🎯 Objective
Developed as part of the EcoTown Health Tech Internship, this project:
Extracts biomarker data from patient medical reports.
Displays interactive time series charts (using Chart.js).
Provides trend detection and clinical range indicators.
Enables actionable clinical insights for medical review.

⚡️ Features
📊 Dashboard
Interactive multi-series line charts for:
Lipid Profile (Total Cholesterol, LDL, HDL, Triglycerides).
Creatinine.
Vitamin D & B12.
HbA1c.

Visual alerts:
✅ Normal range
⚠️ Borderline
🔴 Abnormal

Responsive design:
Supports mobile, tablet, and desktop.

💡 Insights
Displays trend detection (Rising, Falling, or Stable) based on patient data.
Provides clinical range indicators:
Normal
Borderline
Abnormal
Displays clinical recommendations in alerts.

📁 Project Structure
ecotown_dashboard/
├─ index.html           # Main entry point
├─ app.js              # Logic for chart generation and trend detection
├─ style.css           # Styles for layout and color scheme
├─ combined_patient_data.json  # Extracted patient data
├─ .gitignore          # Excludes unnecessary files
├─ vercel.json         # Deployment configuration for Vercel
├─ README.md           # Project documentation

Tech Stack
Frontend: HTML5, CSS3, JavaScript (ES6), Chart.js
Deployment: Vercel
Data Processing: Python (optional for extracting biomarkers)

**Getting Started**
✅ Prerequisites
Node.js (v18 LTS recommended): Download Here
Vercel CLI: npm install -g vercel

Install & Run
Clone the Repository

git clone https://github.com/Deepith-gc/ecotown_dashboard.git
cd ecotown_dashboard
Deploy Locally
Install vercel globally:

npm install -g vercel
Start local deployment:
vercel dev

Deploy to Vercel
vercel
vercel --prod

🔍 Features Summary
Feature	Status
Interactive Time Series Charts	
Normal/Abnormal Indicators	
Responsive Dashboard	
Export Charts 
Dark Mode	
Clinical Summary & Alerts	
Trend Detection Logic	
Detailed Hover Tooltips	
Mobile Optimization	

Demo & Usage
Check out the live deployment for:
Patient Overview
Time Series Trends
Alerts & Insights
Exporting Reports

⚕️ Clinical Significance
This tool:
Enables early detection of clinical anomalies.
Supports patient counseling and data review.
Provides actionable recommendations for lifestyle or medical interventions.

🔐 Security Considerations
All patient data must be de-identified.
No PHI stored in the frontend.
Always adhere to clinical data privacy standards (HIPAA/GDPR).

For queries contact
Email: deepithgc@gmail.com
LinkedIn: www.linkedin.com/in/deepith-g-c

