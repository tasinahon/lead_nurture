# Lead Nurturing Campaign Manager - Frontend

A comprehensive Streamlit-based frontend for managing lead nurturing campaigns, client relationships, and email automation.

## 🚀 Features

### Core Functionality
- **User Management**: Create and manage user accounts
- **Client Management**: Add, view, and manage client profiles
- **Campaign Planning**: Create and approve day-wise campaign plans
- **Email Management**: Track introductory emails and follow-up sequences
- **Analytics Dashboard**: Monitor campaign performance and client engagement

### Key Pages
1. **User Creation**: Register new users with company details
2. **Main Dashboard**: Central hub with navigation and overview metrics
3. **Client Management**: 
   - Create new clients
   - View all clients with filtering and search
   - Detailed client profiles
4. **Campaign Workflow**:
   - View client profiles with comprehensive information
   - Review introductory email content and status
   - Examine campaign strategies
   - Edit and approve day-wise campaign plans
5. **Follow-up Dashboard**: Monitor scheduled and sent follow-up emails

## 📁 Project Structure

```
frontend/
├── main.py                 # Main application entry point
├── config.py              # Configuration and API endpoints
├── requirements.txt       # Python dependencies
├── utils/
│   └── api_client.py      # API communication utilities
└── pages/
    ├── user_creation.py   # User registration page
    ├── client_creation.py # Client creation form
    ├── client_list.py     # Client listing and search
    ├── client_details.py  # Detailed client view
    ├── profile_view.py    # Client profile information
    ├── intro_mail_view.py # Introductory email details
    ├── strategy_view.py   # Campaign strategy display
    ├── campaign_plan.py   # Campaign planning and approval
    └── follow_up_dashboard.py # Follow-up email monitoring
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8 or higher
- Access to the backend API (deployed or local)

### Install Dependencies
```bash
cd frontend
pip install -r requirements.txt
```

### Configure Backend URL
The frontend is designed to work with your deployed backend. You can configure the backend URL in several ways:

#### Method 1: Environment Variable
```bash
export BACKEND_URL="https://lead-nurturing-chdmhca2e2fbauav.eastus-01.azurewebsites.net"
```

#### Method 2: Direct Configuration
Edit `config.py` and update the `BACKEND_URL`:
```python
BACKEND_URL = "https://your-deployed-backend.azurewebsites.net"
```

#### Method 3: Runtime Configuration
The app includes a sidebar setting to change the backend URL while running.

## 🚀 Running the Application

### Start the Streamlit App
```bash
streamlit run main.py
```

The application will open in your browser at `http://localhost:8501`

### Alternative Port
```bash
streamlit run main.py --server.port 8502
```

## 📖 User Guide

### Getting Started
1. **Create User Account**: Start by creating a user account with your details
2. **Add Clients**: Navigate to "Create Client" to add your first client
3. **View Client Details**: Click on any client to see their comprehensive information
4. **Manage Campaigns**: Use the four action buttons (Profile, Intro Mail, Strategy, Campaign Plan) for detailed management

### Navigation Flow
```
User Creation → Main Dashboard → Client Management → Campaign Workflow
```

### Key Workflows

#### Client Onboarding
1. Create Client → View Client Details → View Profile → Create Strategy → Campaign Plan → Approve

#### Campaign Management
1. Client List → Client Details → Campaign Plan → Edit & Suggest Improvements → Approve Campaign

#### Follow-up Monitoring
1. Main Dashboard → Follow-up Mails → Filter by Status → View Details

## 🔧 Configuration Options

### Backend Integration
The frontend automatically connects to your deployed backend APIs:
- User management APIs
- Client management APIs  
- Campaign planning APIs (`/plan-for-approval`, `/suggest-improvement`, `/approve`)
- Follow-up tracking APIs (`/campaign-executions`)

### Customization
- **Backend URL**: Easily changeable via config or environment variable
- **UI Theme**: Streamlit's built-in theming options
- **Page Layout**: Configurable in `config.py`

## 📊 API Integration

### Key Endpoints Used
- `POST /api/users/` - User creation
- `GET/POST /api/clients/` - Client management
- `GET /api/clients/{id}/profile/` - Client profiles
- `GET /api/clients/{id}/introductory-email/` - Intro email details
- `GET /api/clients/{id}/strategy/` - Strategy information
- `GET /api/plan-for-approval/` - Campaign plans
- `POST /api/suggest-improvement/` - Campaign improvements
- `POST /api/approve/` - Campaign approval
- `GET /api/campaign-executions/` - Follow-up emails

### Error Handling
- Automatic API error detection and user-friendly messages
- Graceful fallbacks for missing data
- Debug information available in expandable sections

## 🎯 Features Overview

### Dashboard Analytics
- Total introductory emails sent
- Reply rates and engagement metrics
- Follow-up campaign statistics
- Client activity summaries

### Client Management
- Comprehensive client profiles
- Social media integration
- Communication preferences


### Campaign Planning
- Day-wise campaign editing
- Improvement suggestions workflow
- Campaign approval process
- Real-time plan updates

### Follow-up Monitoring
- Scheduled email tracking
- Content preview
- Status filtering
- Client-specific follow-ups

## 🔍 Troubleshooting

### Common Issues

#### API Connection Problems
1. Check backend URL in sidebar settings
2. Verify backend is running and accessible
3. Check network connectivity
4. Review browser console for errors

#### Missing Data
1. Ensure backend database is populated
2. Check API endpoints are returning data
3. Verify user permissions and client associations

#### Page Navigation Issues
1. Clear browser cache and session storage
2. Restart the Streamlit application
3. Check for JavaScript console errors

### Debug Features
- **Debug Information**: Available in expandable sections on each page
- **API Status**: Sidebar connection testing
- **Raw Data Views**: JSON displays for troubleshooting
- **Database Counts**: Debug endpoint for data verification

## 🚀 Deployment Options

### Local Development
```bash
streamlit run main.py --server.port 8501
```

### Production Deployment
The frontend can be deployed to various platforms:

#### Streamlit Cloud
1. Push code to GitHub repository
2. Connect to Streamlit Cloud
3. Configure environment variables
4. Deploy automatically

#### Docker Deployment
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "main.py", "--server.address", "0.0.0.0"]
```

#### Heroku Deployment
1. Create `Procfile`: `web: streamlit run main.py --server.port=$PORT --server.address=0.0.0.0`
2. Configure environment variables
3. Deploy via Git or GitHub integration

## 📝 Notes

### Backend Compatibility
- Designed for your specific backend API structure
- Handles authentication and session management
- Supports real-time data updates
- Graceful error handling for API failures

### Performance Considerations
- Efficient API calls with caching where appropriate
- Minimal data loading for better user experience
- Responsive design for various screen sizes
- Background processing for long-running operations

### Security Features
- No sensitive data stored in frontend
- API key management through environment variables
- Secure communication with backend APIs
- User session management

## 🔄 Future Enhancements
- Real-time notifications for email replies
- Advanced analytics and reporting
- Bulk operations for client management
- Email template customization
- Integration with external email providers
- Mobile-responsive improvements