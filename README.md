# LinkedIn Profile Scraper

A Python-based LinkedIn profile scraper that can extract comprehensive profile information using Selenium WebDriver with anti-detection measures.

## ⚠️ Important Disclaimer

This tool is for educational purposes only. Please be aware that:

- LinkedIn's Terms of Service prohibit automated scraping
- Use this tool responsibly and respect rate limits
- Consider using LinkedIn's official API for legitimate business purposes
- The authors are not responsible for any misuse of this tool

## Features

- 🔐 Secure login with email/password authentication
- 🛡️ Anti-detection measures using undetected-chromedriver
- 📊 Comprehensive profile data extraction:
  - Basic information (name, headline, location, about)
  - Work experience
  - Education
  - Skills
  - Contact information (if available)
- 🎯 Human-like behavior with random delays
- 💾 Multiple output formats (JSON, TXT)
- 🖥️ Both command-line and interactive modes

## Installation

1. Clone or download this repository
2. Install required dependencies:

```bash
pip install -r requirements.txt
```

3. Set up your environment variables (optional):

```bash
# Create a .env file with your credentials
LINKEDIN_EMAIL=your_email@gmail.com
LINKEDIN_PASSWORD=your_password
HEADLESS_MODE=false
DELAY_MIN=2
DELAY_MAX=5
```

## Usage

### Command Line Mode

```bash
# Basic usage with environment variables
python main.py "https://www.linkedin.com/in/username"

# With explicit credentials
python main.py "https://www.linkedin.com/in/username" --email your_email@gmail.com --password your_password

# Headless mode
python main.py "https://www.linkedin.com/in/username" --headless

# Custom output format
python main.py "https://www.linkedin.com/in/username" --format txt --output profile_data.txt
```

### Interactive Mode

Run without arguments to start interactive mode:

```bash
python main.py
```

This allows you to:
- Enter credentials once
- Scrape multiple profiles
- See real-time progress

## Configuration

Edit `config.py` to customize:

- **DELAY_MIN/MAX**: Random delay range between actions (seconds)
- **TIMEOUT**: Maximum wait time for page elements (seconds)
- **MAX_RETRIES**: Number of retry attempts
- **OUTPUT_DIR**: Directory for saved files
- **USER_AGENTS**: List of user agents for rotation

## Output Format

### JSON Output
```json
{
  "name": "John Doe",
  "headline": "Software Engineer at Tech Company",
  "location": "San Francisco, CA",
  "about": "Passionate about technology...",
  "experience": [
    {
      "title": "Senior Software Engineer",
      "company": "Tech Company",
      "duration": "2020 - Present"
    }
  ],
  "education": [
    {
      "school": "University of California",
      "degree": "Bachelor of Science in Computer Science",
      "duration": "2016 - 2020"
    }
  ],
  "skills": ["Python", "JavaScript", "React"],
  "email": "john.doe@email.com",
  "phone": "+1 (555) 123-4567"
}
```

## Anti-Detection Features

- **Undetected ChromeDriver**: Uses modified ChromeDriver to avoid detection
- **Random User Agents**: Rotates between different browser user agents
- **Human-like Typing**: Simulates natural typing patterns
- **Random Delays**: Adds realistic delays between actions
- **Window Management**: Proper window sizing and positioning

## Troubleshooting

### Common Issues

1. **Login Failed**
   - Verify your email and password
   - Check if 2FA is enabled (may need to disable temporarily)
   - Try running in non-headless mode first

2. **Profile Not Loading**
   - Ensure the profile URL is correct and public
   - Check your internet connection
   - Try increasing the timeout in config.py

3. **ChromeDriver Issues**
   - The tool uses undetected-chromedriver which should auto-update
   - If issues persist, try updating Chrome browser

4. **Rate Limiting**
   - Increase delays between requests
   - Use fewer concurrent sessions
   - Consider using proxies for high-volume scraping

### Error Messages

- `❌ Login timeout`: Check credentials or network connection
- `❌ Profile not found`: Verify the LinkedIn URL is correct
- `❌ Must be logged in`: Ensure successful authentication first

## Legal Considerations

- **Terms of Service**: LinkedIn prohibits automated data collection
- **Rate Limiting**: Respect LinkedIn's servers and implement proper delays
- **Data Privacy**: Only scrape public information and respect privacy laws
- **Commercial Use**: Consider LinkedIn's official API for business purposes

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is for educational purposes only. Use at your own risk and responsibility.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review LinkedIn's current page structure (it changes frequently)
3. Ensure all dependencies are properly installed
4. Verify your credentials and network connection