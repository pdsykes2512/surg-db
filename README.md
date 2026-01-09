# IMPACT - Integrated Monitoring Platform for Audit Care & Treatment

A production-ready NBOCA-compliant surgical outcomes tracking system for colorectal cancer care, built with modern web technologies and comprehensive data validation.

![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![NBOCA](https://img.shields.io/badge/NBOCA-COSD%20v9%2Fv10-orange.svg)

## 🎯 Overview

This system provides comprehensive surgical outcomes tracking with full National Bowel Cancer Audit (NBOCA) compliance. It enables healthcare providers to:

- Track patient episodes from diagnosis through treatment and follow-up
- Record detailed surgical procedures with OPCS-4 coding
- Maintain TNM staging and pathology data
- Generate NBOCA COSD v9/v10 XML exports for national audit submissions
- Validate data completeness and quality before submission
- Generate performance analytics and outcome reports
- Export reports to Excel for analysis and presentation

## ✨ Key Features

### Patient Management
- **NHS Number Validation**: Automatic formatting and validation
- **Demographics**: Complete patient information with BMI auto-calculation
- **Medical History**: Conditions, medications, allergies, smoking status
- **Episode Tracking**: Link multiple episodes per patient

### NBOCA COSD Compliance
- **59/59 Mandatory Fields**: All required fields implemented
- **XML Export**: COSD v9/v10 format for national submissions
- **Data Validator**: Pre-submission validation with detailed error reporting
- **Data Quality Dashboard**: Real-time completeness tracking per field
- **ICD-10 Validation**: 63 colorectal cancer codes with API lookup
- **OPCS-4 Validation**: 126 procedure codes with API lookup

### Clinical Data
- **Episode-Based Care**: Cancer, IBD, benign condition tracking
- **TNM Staging**: v7 and v8 support with all components
- **Pathology Results**: Grade, lymph nodes, margins, molecular markers
- **Treatment Recording**: Surgery, chemotherapy, radiotherapy
- **Complications**: Clavien-Dindo grading (I-V) with detailed tracking
- **Anastomotic Leaks**: ISGPS severity grading (A-C) with NBOCA compliance
- **Investigation Tracking**: Imaging, endoscopy, laboratory results (17,564+ records)
- **Outcomes Tracking**: Mortality (30/90-day), RTT, readmissions

### Analytics & Reports
- **Dashboard**: Real-time statistics and KPIs
- **Outcome Metrics**: Complication rates, mortality, readmissions, RTT
- **Surgeon Performance**: Aggregated metrics per clinician with yearly breakdown
- **NBOCA Reports**: 30/90-day mortality, anastomotic leak rates, conversion rates
- **Excel Export**: Professional formatted reports with styling
- **Trends Analysis**: Yearly trends (2023-2025) with color-coded metrics
- **Data Quality Dashboard**: Real-time completeness tracking per COSD field

### Security & Data Protection
- **JWT Authentication**: Secure token-based authentication
- **Role-Based Access**: Admin, surgeon, data entry, viewer roles
- **Field-Level Encryption**: AES-256 encryption for sensitive patient data (NHS numbers, MRN)
- **Password Hashing**: bcrypt with salt for password security
- **Audit Logging**: Comprehensive CRUD tracking with user context
- **Database Backups**: Automated daily backups with encryption and web UI
- **Admin Panel**: User and clinician management interface

## 🏗️ Tech Stack

### Frontend
- **React 18**: Modern component-based UI
- **TypeScript**: Type-safe development
- **Vite**: Fast build tool and dev server
- **Tailwind CSS**: Utility-first styling
- **React Router**: Client-side routing

### Backend
- **FastAPI**: High-performance async Python framework
- **Pydantic**: Data validation and settings management
- **Motor**: Async MongoDB driver
- **Python-JOSE**: JWT token handling
- **Passlib**: Password hashing with bcrypt
- **OpenPyXL**: Excel file generation

### Database
- **MongoDB**: Document-oriented NoSQL database
- **Collections**: 9 collections (patients, episodes, treatments, tumours, investigations, clinicians, surgeons, users, nhs_providers)
- **Indexes**: Optimized for patient_id, episode_id, NHS number, and date queries
- **Schema**: Full documentation in [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)

## 📋 Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **MongoDB 6.0+**
- **Git**

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/pdsykes2512/impact.git
cd impact
```

### 2. Backend Setup
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=surgical_outcomes
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
EOF

# Initialize database and create admin user
python -m app.database
cd ../execution
python create_admin_user.py
```

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Create .env file
cat > .env << EOF
VITE_API_URL=http://localhost:8000
EOF
```

### 4. Start Application
```bash
# Terminal 1: Start backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start frontend
cd frontend
npm run dev
```

### 5. Access Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Default Admin**: username: `admin`, password: `admin123` (change immediately!)

## 📚 Documentation

### Core Documentation
- [DATABASE_SCHEMA.md](docs/development/DATABASE_SCHEMA.md) - **Complete database schema reference** (9 collections, field specs, NBOCA/COSD mappings)
- [RECENT_CHANGES.md](RECENT_CHANGES.md) - Recent changes and update history
- [STYLE_GUIDE.md](docs/development/STYLE_GUIDE.md) - UI/UX design patterns and component standards

### Setup & Deployment
- [Quick Start](docs/setup/QUICK_START.md) - Get started in 5 minutes
- [Deployment Guide](docs/setup/DEPLOYMENT.md) - Production deployment instructions
- [Development Guide](docs/setup/DEVELOPMENT.md) - Developer setup and workflow
- [Service Management](docs/setup/SERVICE_MANAGEMENT.md) - Systemd service configuration

### User & API Documentation
- [User Guide](docs/guides/USER_GUIDE.md) - End-user instructions
- [API Documentation](docs/api/API_DOCUMENTATION.md) - Complete API reference
- [NBOCA Compliance](docs/implementation/NBOCA_FIELDS_STATUS.md) - Field mapping and status

### Data Management
- [Import Quick Start](execution/migrations/QUICKSTART.md) - Database import workflow
- [Data Migration Guide](execution/DATA_MIGRATION_GUIDE.md) - Migration procedures
- [Backup Guide](docs/guides/BACKUP_QUICK_REFERENCE.md) - Backup and restore

## 🔐 Security Considerations

### Production Checklist
- [ ] Change default admin password
- [ ] Generate new SECRET_KEY
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS properly
- [ ] Set up MongoDB authentication
- [ ] Enable MongoDB encryption at rest
- [ ] Configure firewall rules
- [ ] Set up regular backups
- [ ] Enable audit logging
- [ ] Review user permissions

### Environment Variables
Never commit these files:
- `.env` - Contains secrets and configuration
- `credentials.json` - OAuth credentials
- `token.json` - OAuth tokens
- `.bash_history` - May contain sensitive commands

## 📊 Sample Data

Load sample bowel cancer episodes for testing:
```bash
cd execution
python reset_and_populate_bowel_cancer.py
```

This creates:
- 8 patients with realistic demographics
- 8 bowel cancer episodes (colon and rectal)
- Complete TNM staging and pathology
- Surgical treatments with OPCS-4 codes
- Tumour records with molecular markers

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Manual Testing
1. Create a new patient
2. Add a cancer episode with tumour
3. Record a surgical treatment
4. Validate NBOCA compliance
5. Export to XML and Excel

## 📈 Performance

- **Backend**: FastAPI async operations for high concurrency
- **Database**: Indexed queries for sub-millisecond lookups
- **Frontend**: Code splitting and lazy loading
- **API Response**: <100ms average for typical queries

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- National Bowel Cancer Audit (NBOCA) for COSD specifications
- NHS Digital for ICD-10 and OPCS-4 coding standards
- OpenAI for development assistance
- FastAPI and React communities for excellent frameworks

## 📞 Support

For issues, questions, or contributions:
- **Issues**: https://github.com/pdsykes2512/impact/issues
- **Email**: support@example.com
- **Documentation**: https://github.com/pdsykes2512/impact/wiki

## 🗺️ Roadmap

### v1.1 (Released - December 2025)
- ✅ Outcome tracking (30/90-day mortality, RTT, readmissions)
- ✅ Complication tracking with Clavien-Dindo grading (I-V)
- ✅ Anastomotic leak tracking with ISGPS severity grading (A-C)
- ✅ Investigation tracking (imaging, endoscopy, laboratory)
- ✅ Comprehensive audit logging for all CRUD operations
- ✅ Data quality dashboard with completeness metrics
- ✅ Yearly outcome trends (2023-2025)
- ✅ Return to theatre (RTT) tracking
- ✅ Database backup system with encryption and web UI
- ✅ Field-level encryption for sensitive patient data
- ✅ Excel report export with professional formatting

### v1.2 (Q1 2026)
- [ ] PDF report export
- [ ] Mobile-responsive design improvements
- [ ] Advanced search and filtering with saved queries
- [ ] Data visualization charts (Chart.js/D3)
- [ ] Session timeout handling
- [ ] HTTPS/SSL configuration guide

### v2.0 (Q2-Q3 2026)
- [ ] Multi-tenancy support
- [ ] EHR integration architecture
- [ ] File upload for surgical notes/images
- [ ] Real-time collaboration features
- [ ] Lab results import functionality
- [ ] Automated report generation
- [ ] Print-friendly views for reports
- [ ] Keyboard shortcuts for common actions

## 📊 Statistics

- **Lines of Code**: ~15,000
- **API Endpoints**: 50+
- **Database Collections**: 9 (patients, episodes, treatments, tumours, investigations, clinicians, surgeons, users, nhs_providers)
- **ICD-10 Codes**: 63
- **OPCS-4 Codes**: 126
- **NBOCA Fields**: 59/59 ✅
- **Data Quality**: 100% clean (no leading numbers, standardized formats)

---

**Version**: 1.1.0
**Last Updated**: December 27, 2025
**Status**: Production Ready ✅
