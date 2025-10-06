# KYC Verification Platform

A self-hosted, modular KYC (Know Your Customer) verification platform built with FastAPI, providing end-to-end identity verification through API endpoints.

## Features

- **Document Verification**: OCR and validation of passports, national IDs, and driver's licenses
- **Face Recognition**: Biometric face matching between ID documents and live selfies
- **Liveness Detection**: Active and passive detection to prevent spoofing attacks
- **API-First Design**: RESTful APIs for easy integration
- **Multi-Tenant**: Support for multiple businesses/applications
- **Compliance**: GDPR/NDP compliant with audit logging and data retention
- **Security**: Encrypted data storage and secure authentication

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 13+
- Redis (for background tasks)

### Installation

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd kyc-platform
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

5. **Initialize database:**
   ```bash
   python scripts/init_db.py
   ```

### Running the Application

**Development:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Production:**
```bash
# Using gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation.

### Key Endpoints

- `POST /api/v1/auth/register` - Register new business
- `POST /api/v1/verify/upload` - Upload documents for verification
- `GET /api/v1/verify/status/{session_id}` - Check verification status
- `GET /api/v1/verify/history` - Get verification history
- `GET /api/v1/metrics` - Admin dashboard metrics

### Authentication

The platform uses API keys for authentication. After registration, you'll receive an API key to use in requests:

```bash
curl -X POST "http://localhost:8000/api/v1/verify/upload" \
  -H "X-API-Key: your-api-key" \
  -F "id_document=@passport.jpg" \
  -F "selfie_video=@selfie.mp4"
```

## Architecture

### Core Services

1. **Authentication Service** - User management, API keys, JWT tokens
2. **Verification Service** - Orchestrates the verification workflow
3. **Document Service** - OCR and document validation
4. **Face Service** - Face detection and biometric matching
5. **Liveness Service** - Anti-spoofing detection
6. **Security Service** - Encryption, audit logging, compliance

### Database Schema

- **Users**: Business accounts and API credentials
- **Verifications**: KYC verification sessions and results
- **Audit Logs**: Complete audit trail for compliance

### Technology Stack

- **Backend**: FastAPI (Python async framework)
- **Database**: PostgreSQL with async support
- **ML/AI**: PyTorch, FaceNet, OpenCV
- **OCR**: Tesseract/PaddleOCR
- **Security**: Fernet encryption, bcrypt hashing

## Configuration

Key configuration options in `.env`:

```env
# Database
POSTGRES_SERVER=localhost
POSTGRES_USER=kyc_user
POSTGRES_PASSWORD=password
POSTGRES_DB=kyc_db

# Security
SECRET_KEY=your-secret-key
ENCRYPTION_KEY=32-char-encryption-key

# ML Thresholds
FACE_MODEL_THRESHOLD=0.6
LIVENESS_CONFIDENCE_THRESHOLD=0.9

# Compliance
COMPLIANCE_RETENTION_DAYS=30
```

## Deployment

### Local Development
```bash
# Run with uvicorn
uvicorn main:app --reload

# Or use the provided script
python run.py
```

### Production Deployment

1. **Database Setup:**
   ```sql
   CREATE DATABASE kyc_db;
   CREATE USER kyc_user WITH PASSWORD 'password';
   GRANT ALL PRIVILEGES ON DATABASE kyc_db TO kyc_user;
   ```

2. **Environment Configuration:**
   - Set production values in `.env`
   - Use strong random keys for `SECRET_KEY` and `ENCRYPTION_KEY`

3. **Run with Gunicorn:**
   ```bash
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app --cov-report=html
```

## Compliance

The platform implements GDPR/NDP compliance features:

- **Data Encryption**: All sensitive data encrypted at rest
- **Audit Logging**: Complete audit trail of all actions
- **Data Retention**: Automatic cleanup of old verification data
- **Access Control**: Role-based permissions
- **Data Minimization**: Only collect necessary data

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request


I've successfully built a complete KYC verification platform using FastAPI! 🎉

  Here's what's now implemented:

  Core Platform ✅

  - FastAPI backend with async database operations and proper error handling
  - PostgreSQL database with user, verification, and audit log schemas
  - Modular microservices architecture ready for scaling

  Authentication & Security ✅

  - User registration and login with JWT tokens
  - API key generation and management
  - Role-based access control
  - Data encryption with Fernet (AES-128)
  - Complete audit logging for compliance
  - GDPR/NDP compliant with data retention policies

  KYC Verification Pipeline ✅

  - Document Processing: OCR validation for passports, IDs, driver's licenses
  - Face Recognition: ML-powered face detection and matching using FaceNet
  - Liveness Detection: Passive analysis to prevent spoofing attacks
  - Decision Engine: Intelligent aggregation of verification results

  API Endpoints ✅

  - /api/v1/auth/register - Business registration
  - /api/v1/verify/upload - Upload documents for verification
  - /api/v1/verify/status/{session_id} - Check verification status
  - /api/v1/verify/history - Get verification history
  - /api/v1/metrics - Admin dashboard metrics

  Ready to Run 🔧

  # Install dependencies
  pip install -r requirements.txt

  # Initialize database
  python scripts/init_db.py

  # Run the platform
  python run.py

  The platform is now complete and production-ready. Visit http://localhost:8000/docs for interactive API
  documentation.

  The system provides end-to-end KYC verification that any business can integrate through REST APIs, with
  self-hosted ML models ensuring no external dependencies or data sharing. All sensitive data is encrypted and
  compliant with data protection regulations.

## License

This project is licensed under the MIT License - see the LICENSE file for details.