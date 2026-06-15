# AI Sales & Payment Assistant on WhatsApp

A production-ready Django application that automates customer conversations and payment processing through WhatsApp. Leverages AI-powered intent detection, state-driven workflows, and seamless payment integration for the Nigerian market.

## 🚀 Features

- **WhatsApp Integration** - Direct customer engagement via Twilio WhatsApp Business API
- **AI-Powered Conversations** - Google Gemini integration for intelligent, context-aware responses
- **Intent Detection** - Automatic classification of customer messages (greeting, product inquiry, buying intent, objections, support requests)
- **Workflow Automation** - State-driven customer journey with automated follow-ups and time-delayed actions
- **Payment Gateway Integration** - Seamless Paystack integration for dynamic payment links and transaction tracking
- **Admin Dashboard** - Live chat monitoring, payment ledger, and configurable prompts
- **Celery Task Queue** - Asynchronous processing for timely follow-ups and reminders
- **RESTful APIs** - Comprehensive API endpoints for customers, conversations, payments, and webhooks

## 🛠 Tech Stack

### Backend
- **Django** 5.2 - Web framework
- **Django REST Framework** 3.15.2 - REST API development
- **Celery** 5.4.0 - Task queue for async operations
- **Redis** 5.2.1 - Cache and message broker

### AI & NLP
- **Google Generative AI** 0.8.5 - Gemini integration for natural language processing

### Messaging & Payments
- **Twilio** 9.4.3 - WhatsApp API integration
- **Paystack API** - Payment processing and webhook handling

### Database
- **MySQL** 8.0+ - Primary data store
- **MySQLClient** 2.2.7 - MySQL adapter for Python

### Utilities
- **CORS Headers** 4.6.0 - Cross-origin resource sharing
- **Python Decouple** 3.8 - Environment configuration management
- **Gunicorn** 23.0.0 - WSGI server for production

## 📋 Prerequisites

Before setting up the project, ensure you have:

- Python 3.10+
- MySQL 8.0+ (or compatible)
- Redis 5.0+
- Git
- A Twilio account with WhatsApp API credentials
- A Paystack account with API keys
- A Google Cloud account with Gemini API access

### Installation Links
- [Python Download](https://www.python.org/downloads/)
- [MySQL Community Edition](https://dev.mysql.com/downloads/mysql/)
- [Redis for Windows](https://github.com/microsoftarchive/redis/releases) or [WSL](https://learn.microsoft.com/en-us/windows/wsl/install)

## 🔧 Installation & Setup

### 1. Clone the Repository
```bash
cd "c:\Users\HP\Documents\temitope\AI Sales & Payment Assistant on WhatsApp"
```

### 2. Create Virtual Environment
```powershell
# Create virtual environment
python -m venv myenv

# Activate virtual environment (Windows PowerShell)
.\myenv\Scripts\Activate.ps1

# If you get execution policy error, run:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3. Install Dependencies
```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration
DB_ENGINE=django.db.backends.mysql
DB_NAME=your_database_name
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Twilio Configuration
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=your-twilio-phone

# Paystack Configuration
PAYSTACK_PUBLIC_KEY=your-paystack-public-key
PAYSTACK_SECRET_KEY=your-paystack-secret-key

# Google Gemini Configuration
GOOGLE_API_KEY=your-google-api-key

# Business Settings
BUSINESS_NAME=Your Business Name
BUSINESS_PHONE=your-business-phone
```

### 5. Database Setup

```bash
# Run migrations
python manage.py migrate

# Create a superuser for admin access
python manage.py createsuperuser

# Load initial business settings (optional)
python manage.py migrate customers 0002_seed_business_settings
```

### 6. Verify MySQL Connection
```bash
# Test database connectivity
python manage.py dbshell
```

## ▶️ Running the Application

### Development Server
```bash
python manage.py runserver
```

Access the application at `http://127.0.0.1:8000/`

### Celery Worker (for async tasks)
```bash
# In a new terminal with activated venv
celery -A config worker -l info
```

### Redis Server
```bash
# Ensure Redis is running (on Windows via WSL or native build)
redis-cli ping
# Expected output: PONG
```

## 🧪 Running Tests

Execute the test suite:
```bash
# Run all tests
python manage.py test

# Run tests for specific app
python manage.py test apps.ai_engine
python manage.py test apps.conversations
python manage.py test apps.payments
python manage.py test apps.customers

# Run with verbose output
python manage.py test --verbosity=2
```

## 📁 Project Structure

```
├── apps/                      # Core application modules
│   ├── ai_engine/            # AI/NLP logic (Gemini integration, intent classification)
│   ├── conversations/        # WhatsApp conversation management
│   ├── customers/            # Customer profiles and management
│   ├── dashboard/            # Admin dashboard views
│   ├── messaging/            # Twilio integration and message templates
│   ├── payments/             # Paystack integration and transaction tracking
│   └── workflows/            # State machine and workflow automation
├── config/                    # Project configuration
│   ├── settings/             # base.py, development.py, production.py
│   ├── urls.py               # Main URL routing
│   ├── wsgi.py               # WSGI application
│   └── celery.py             # Celery configuration
├── logs/                      # Application logs
├── myenv/                     # Python virtual environment
├── static/                    # Static files (CSS, JS)
├── manage.py                  # Django management script
├── requirements.txt           # Project dependencies
└── README.md                  # This file
```

## 🔌 API Endpoints

### Customers API
- `GET/POST /api/customers/` - List and create customers
- `GET/PUT /api/customers/{id}/` - Retrieve and update customer

### Conversations API
- `GET/POST /api/conversations/` - List and create conversations
- `GET /api/conversations/{id}/messages/` - Get conversation messages

### Payments API
- `GET/POST /api/payments/` - List and create payments
- `GET /api/payments/{id}/` - Retrieve payment details
- `POST /api/payments/webhook/` - Paystack webhook endpoint

### Webhooks
- `POST /webhooks/conversations/whatsapp/` - Incoming WhatsApp messages
- `POST /webhooks/payments/paystack/` - Payment confirmations

## 🔄 Workflow States

The system enforces the following state transitions:

1. **NEW_LEAD** → Automated introduction message sent
2. **AWAITING_REPLY** → Follow-up #1 triggered after 6 hours of no response
3. **INTERESTED** → AI generates pricing and payment link upon buying intent
4. **PENDING_PAYMENT** → Reminders sent every 24 hours (max 3 reminders)
5. **PAID** → Receipt sent, workflow completes
6. **SUPPORT_NEEDED** → Escalated to human agent

## 📊 Admin Dashboard

Access the admin interface at `/admin/` with your superuser credentials:

- **Live Chat View** - Monitor ongoing conversations in real-time
- **Payment Ledger** - Track all transactions (amount, status, date)
- **Response Editor** - Customize AI prompts and business settings

## 🚨 Common Issues & Troubleshooting

### MySQL Connection Error
```
Error: (2003, "Can't connect to MySQL server")
```
**Solution**: Ensure MySQL is running and credentials in `.env` are correct.

### Redis Connection Error
```
Error: ConnectionRefusedError: [Errno 111] Connection refused
```
**Solution**: Start Redis server. On Windows, use WSL or the native Redis build.

### Celery Tasks Not Running
**Solution**: Ensure Redis is running and Celery worker is active in a separate terminal.

### Twilio Webhook Not Receiving Messages
**Solution**: 
- Verify your public URL is correctly configured in Twilio Console
- Check that your webhook endpoint is accessible from the internet
- Confirm firewall/router isn't blocking incoming requests

## 📚 Documentation

- [Local Testing Guide](./LOCAL_TESTING_GUIDE.md) - Detailed setup for Windows development
- [Product Requirements Document](./PRD.md) - Full system specification and architecture
- [Implementation Plan](./plans/01_implementation_plan.md) - Development roadmap
- [Task Breakdown](./plans/02_task_breakdown.md) - Sprint-level tasks

## 🤝 Contributing

1. Create a feature branch from `main`
2. Make your changes with clear, descriptive commits
3. Write tests for new functionality
4. Submit a pull request with a detailed description

## 📝 License

This project is proprietary and confidential. Unauthorized copying or distribution is prohibited.

## 👨‍💻 Support

For issues, questions, or collaboration:
- Check existing documentation
- Review the LOCAL_TESTING_GUIDE.md for setup help
- Check test files for usage examples

---

**Built with ❤️ for the Nigerian market** — Automating sales and payments through WhatsApp.
