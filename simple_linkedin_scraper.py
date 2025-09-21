#!/usr/bin/env python3
"""
Simple LinkedIn Profile Scraper
Loads credentials from environment variables, only asks for profile URL
"""

import time
import random
import json
import os
from typing import Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SimpleLinkedInScraper:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.is_logged_in = False
        
        # Load credentials from environment variables
        self.email = os.getenv('LINKEDIN_EMAIL')
        self.password = os.getenv('LINKEDIN_PASSWORD')
        
        if not self.email or not self.password:
            print("❌ Error: LinkedIn credentials not found in environment variables")
            print("Please create a .env file with:")
            print("LINKEDIN_EMAIL=your_email@gmail.com")
            print("LINKEDIN_PASSWORD=your_linkedin_password")
            raise ValueError("Missing LinkedIn credentials")
        
    def find_chromedriver(self):
        """Find ChromeDriver in current directory or system paths"""
        import platform
        
        # Check for Azure/Linux system chromedriver first
        if os.path.exists('/usr/local/bin/chromedriver'):
            return '/usr/local/bin/chromedriver'
        
        # Platform-specific paths
        is_windows = platform.system() == 'Windows'
        
        if is_windows:
            possible_paths = [
                "chromedriver.exe",
                "./chromedriver.exe", 
                "chromedriver-win32/chromedriver.exe",
                "./chromedriver-win32/chromedriver.exe"
            ]
        else:
            # Linux/Unix paths only
            possible_paths = [
                "chromedriver",
                "./chromedriver",
                "/usr/bin/chromedriver",
                "/usr/local/bin/chromedriver"
            ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return os.path.abspath(path)
        
        # Search in current directory and subdirectories (platform-specific)
        target_files = ["chromedriver.exe"] if is_windows else ["chromedriver"]
        for root, dirs, files in os.walk("."):
            for file in files:
                if file in target_files:
                    return os.path.abspath(os.path.join(root, file))
        
        # Try using webdriver-manager as fallback for cloud deployment
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            print("🔧 Using webdriver-manager to install ChromeDriver...")
            driver_path = ChromeDriverManager().install()
            if driver_path and os.path.exists(driver_path):
                print(f"✅ ChromeDriver installed via webdriver-manager at: {driver_path}")
                return driver_path
        except Exception as e:
            print(f"⚠️ webdriver-manager failed: {str(e)}")
        
        return None
        
    def setup_driver(self):
        """Setup Chrome driver"""
        try:
            print("🔧 Setting up Chrome driver...")
            
            chromedriver_path = self.find_chromedriver()
            if not chromedriver_path:
                print("❌ ChromeDriver not found. Please run 'python setup_chromedriver.py' first.")
                return False
            
            options = Options()
            options.add_argument('--headless')  # Run in background - no browser window
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-web-security')
            options.add_argument('--allow-running-insecure-content')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-logging')
            options.add_argument('--log-level=3')
            
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36')
            
            service = Service(chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 60)
            
            print("✅ Driver setup completed")
            return True
            
        except Exception as e:
            print(f"❌ Error setting up driver: {str(e)}")
            return False
    
    def random_delay(self, min_delay=3, max_delay=7):
        """Add random delay between actions"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
    
    def login(self):
        """Login to LinkedIn using environment variables"""
        if not self.driver:
            if not self.setup_driver():
                return False
        
        try:
            print("🔐 Logging in to LinkedIn...")
            
            self.driver.get("https://www.linkedin.com/login")
            self.random_delay()
            
            email_field = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
            email_field.clear()
            email_field.send_keys(self.email)
            self.random_delay()
            
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(self.password)
            self.random_delay()
            
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            try:
                self.wait.until(
                    lambda driver: any([
                        "feed" in driver.current_url,
                        "mynetwork" in driver.current_url,
                        "dashboard" in driver.current_url,
                        "checkpoint" in driver.current_url
                    ])
                )
            except TimeoutException:
                if "login" in self.driver.current_url:
                    print("❌ Login failed - check credentials in .env file")
                    return False
            
            if "checkpoint" in self.driver.current_url:
                print("⚠️  LinkedIn security challenge detected. Please complete it manually.")
                input("Press Enter after completing the challenge...")
            
            self.is_logged_in = True
            print("✅ Successfully logged in to LinkedIn")
            return True
            
        except Exception as e:
            print(f"❌ Login failed: {str(e)}")
            return False
    
    def expand_content(self):
        """Try to expand 'See more' sections"""
        try:
            see_more_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'see more') or contains(text(), 'See more') or contains(text(), '...see more')]")
            for button in see_more_buttons:
                try:
                    self.driver.execute_script("arguments[0].click();", button)
                    time.sleep(1)
                except:
                    pass
        except:
            pass
    
    def scroll_to_load_content(self):
        """Scroll through the page to load all content"""
        try:
            print("📜 Loading all content...")
            
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            for i in range(8):  # Increased scrolling
                self.driver.execute_script(f"window.scrollTo(0, {(i+1) * 1000});")
                time.sleep(3)  # Increased wait time
                self.expand_content()
                
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height != last_height:
                    last_height = new_height
                    print(f"✅ Page expanded during scroll {i+1}")
            
            # Scroll to bottom and wait
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(3)
            
        except Exception as e:
            print(f"⚠️  Error during content loading: {str(e)}")
    
    def debug_page_content(self):
        """Debug method to see what's actually on the page"""
        try:
            print("🔍 DEBUG: Analyzing page content...")
            
            # Check for any h2 headings
            headings = self.driver.find_elements(By.TAG_NAME, "h2")
            print(f"Found {len(headings)} h2 headings:")
            for i, heading in enumerate(headings[:10]):
                try:
                    text = heading.text.strip()
                    if text:
                        print(f"  H2 {i+1}: {text}")
                except:
                    pass
            
            # Check for experience-related text
            exp_keywords = ["Experience", "experience", "Work", "Career"]
            for keyword in exp_keywords:
                elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
                if elements:
                    print(f"Found {len(elements)} elements containing '{keyword}'")
            
            # Check for education-related text
            edu_keywords = ["Education", "education", "School", "University"]
            for keyword in edu_keywords:
                elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
                if elements:
                    print(f"Found {len(elements)} elements containing '{keyword}'")
            
            # Check for common LinkedIn selectors
            selectors_to_check = [
                ".pvs-list__paged-list-item",
                ".pvs-entity",
                ".artdeco-list__item",
                ".pv-entity__summary-info",
                ".pv-profile-section"
            ]
            
            for selector in selectors_to_check:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"Found {len(elements)} elements with selector: {selector}")
            
        except Exception as e:
            print(f"⚠️  Debug error: {str(e)}")
    
    def scrape_profile(self, profile_url: str) -> Optional[Dict]:
        """Scrape LinkedIn profile data"""
        if not self.is_logged_in:
            if not self.login():
                return None
        
        try:
            print(f"🔍 Scraping profile: {profile_url}")
            
            self.driver.get(profile_url)
            self.random_delay()
            
            # Wait for page to load
            self.wait.until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".pv-text-details__left-panel")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".ph5.pb5")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".scaffold-layout__main"))
                )
            )
            print("✅ Profile page loaded")
            
            # Load all content
            self.scroll_to_load_content()
            
            # Debug what's on the page
            self.debug_page_content()
            
            profile_data = {}
            
            # Extract all sections
            profile_data.update(self._extract_basic_info())
            profile_data.update(self._extract_about_section())
            
            # Try experience extraction with strict validation
            exp_data = self._extract_experience_detailed()
            if not exp_data.get('experience'):
                print("⚠️  Standard experience extraction failed, trying fallback...")
                exp_data = self._extract_experience_fallback()
            
            # Final cleanup - remove any invalid experience entries
            if exp_data.get('experience'):
                valid_experience = []
                for exp in exp_data['experience']:
                    if self._is_valid_experience_entry(exp):
                        valid_experience.append(exp)
                    else:
                        print(f"🗑️  Removing invalid experience: {exp.get('title', 'Unknown')}")
                exp_data['experience'] = valid_experience
            
            profile_data.update(exp_data)
            
            # Try education extraction with strict validation
            edu_data = self._extract_education_detailed()
            if not edu_data.get('education'):
                print("⚠️  Standard education extraction failed, trying fallback...")
                edu_data = self._extract_education_fallback()
            
            # Final cleanup - remove any invalid education entries
            if edu_data.get('education'):
                valid_education = []
                for edu in edu_data['education']:
                    if self._is_valid_education_entry(edu):
                        valid_education.append(edu)
                    else:
                        print(f"🗑️  Removing invalid education: {edu.get('school', 'Unknown')}")
                edu_data['education'] = valid_education
            
            profile_data.update(edu_data)
            
            profile_data.update(self._extract_skills_detailed())
            
            if any(profile_data.values()):
                print("✅ Profile scraped successfully")
                return profile_data
            else:
                print("❌ No profile data extracted")
                return None
            
        except Exception as e:
            print(f"❌ Error scraping profile: {str(e)}")
            return None
    
    def _extract_basic_info(self) -> Dict:
        """Extract basic profile information"""
        basic_info = {}
        
        # Name
        name_selectors = ["h1.text-heading-xlarge", ".pv-text-details__left-panel h1", ".ph5 h1"]
        for selector in name_selectors:
            try:
                name_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                basic_info['name'] = name_element.text.strip()
                print(f"✅ Found name: {basic_info['name']}")
                break
            except NoSuchElementException:
                continue
        
        # Headline
        headline_selectors = [".text-body-medium.break-words", ".pv-text-details__left-panel .text-body-medium"]
        for selector in headline_selectors:
            try:
                headline_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                basic_info['headline'] = headline_element.text.strip()
                print(f"✅ Found headline")
                break
            except NoSuchElementException:
                continue
        
        # Location
        location_selectors = [".text-body-small.inline.t-black--light.break-words", ".pv-text-details__left-panel .text-body-small"]
        for selector in location_selectors:
            try:
                location_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                location_text = location_element.text.strip()
                if 'contact info' not in location_text.lower():
                    basic_info['location'] = location_text
                    print(f"✅ Found location: {basic_info['location']}")
                    break
            except NoSuchElementException:
                continue
        
        # Followers and connections
        try:
            followers_element = self.driver.find_element(By.XPATH, "//span[contains(text(), 'followers')]")
            basic_info['followers'] = followers_element.text.strip()
        except NoSuchElementException:
            basic_info['followers'] = "Not found"
        
        
        return basic_info
    
    def _extract_about_section(self) -> Dict:
        """Extract detailed About section"""
        about_data = {}
        
        try:
            print("🔍 Extracting About section...")
            
            about_selectors = [
                "#about ~ * .full-width",
                ".pv-about-section .pv-about__summary-text",
                "[data-field='about'] .full-width",
                ".pv-about .inline-show-more-text",
                ".about .full-width"
            ]
            
            for selector in about_selectors:
                try:
                    about_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in about_elements:
                        text = element.text.strip()
                        if text and len(text) > 50:
                            about_data['about'] = text
                            print(f"✅ Found About section ({len(text)} characters)")
                            return about_data
                except NoSuchElementException:
                    continue
            
            # Alternative approach
            try:
                about_heading = self.driver.find_element(By.XPATH, "//h2[contains(text(), 'About')]")
                parent = about_heading.find_element(By.XPATH, "./following-sibling::*")
                about_text = parent.text.strip()
                if about_text and len(about_text) > 50:
                    about_data['about'] = about_text
                    print(f"✅ Found About section via heading ({len(about_text)} characters)")
                    return about_data
            except NoSuchElementException:
                pass
            
            about_data['about'] = "Not found"
            
        except Exception as e:
            about_data['about'] = "Error extracting"
        
        return about_data
    
    def _extract_experience_detailed(self) -> Dict:
        """Extract detailed work experience with improved targeting"""
        experience_data = {'experience': []}
        
        try:
            print("🔍 Extracting Experience with precise targeting...")
            
            # First, try to find and scroll to the experience section
            experience_found = False
            try:
                experience_heading = self.driver.find_element(By.XPATH, "//h2[contains(text(), 'Experience')]")
                self.driver.execute_script("arguments[0].scrollIntoView();", experience_heading)
                time.sleep(3)
                experience_found = True
                print("✅ Found Experience section")
                
                # Try to find the parent container of the experience section
                parent_section = experience_heading.find_element(By.XPATH, "./ancestor::section[1]")
                
                # Look specifically within this section for experience entries
                exp_selectors_in_section = [
                    ".pvs-list__paged-list-item",
                    ".pvs-entity",
                    "li",
                    ".artdeco-list__item"
                ]
                
                exp_items = []
                for selector in exp_selectors_in_section:
                    try:
                        items = parent_section.find_elements(By.CSS_SELECTOR, selector)
                        if items:
                            print(f"✅ Found {len(items)} experience items in section with selector: {selector}")
                            exp_items = items
                            break
                    except:
                        continue
                
                if exp_items:
                    for i, item in enumerate(exp_items[:6]):  # Limit to 6 items
                        try:
                            item_text = item.text.strip()
                            
                            # Skip irrelevant items - be very strict about what we accept
                            skip_keywords = [
                                'experience', 'education', 'skills', 'about', 'interests', 'endorsed by', 
                                'badges', 'badgetype', 'account', 'top voices', 'companies', 'groups',
                                'schools', 'followers', 'follow', 'endorsements', 'see more', 'show all',
                                'recommendations', 'activity', 'licenses', 'certifications', 'projects',
                                'publications', 'honors', 'awards', 'test scores', 'courses', 'organizations'
                            ]
                            
                            # Skip if item is too short or contains skip keywords
                            if (len(item_text) < 30 or 
                                any(keyword in item_text.lower() for keyword in skip_keywords) or
                                item_text.lower().strip() in skip_keywords):
                                print(f"⏭️  Skipping irrelevant item: {item_text[:50]}...")
                                continue
                            
                            # Additional validation: must look like actual job experience
                            if not self._looks_like_experience_entry(item_text):
                                print(f"⏭️  Skipping non-experience item: {item_text[:50]}...")
                                continue
                            
                            # Parse the text structure
                            lines = [line.strip() for line in item_text.split('\n') if line.strip()]
                            
                            if len(lines) >= 2:
                                exp_data = {
                                    'title': 'Not extracted',
                                    'company': 'Not extracted',
                                    'duration': 'Not extracted',
                                    'location': 'Not extracted',
                                    'description': 'Not extracted'
                                }
                                
                                # First line is usually the job title
                                if len(lines[0]) < 100 and not any(skip in lines[0].lower() for skip in ['experience', 'skills', 'endorsed']):
                                    exp_data['title'] = lines[0]
                                
                                # Second line is often company name
                                if len(lines) > 1 and len(lines[1]) < 100:
                                    # Check if it looks like a company (has common company indicators)
                                    company_line = lines[1]
                                    if any(indicator in company_line.lower() for indicator in ['ltd', 'llc', 'inc', 'corp', 'technologies', 'solutions', 'company', 'group']):
                                        exp_data['company'] = company_line
                                    elif '·' not in company_line and len(company_line) > 5:
                                        exp_data['company'] = company_line
                                
                                # Look for duration in the lines
                                for line in lines:
                                    if any(time_indicator in line.lower() for time_indicator in ['year', 'month', 'present', '2020', '2021', '2022', '2023', '2024']):
                                        exp_data['duration'] = line
                                        break
                                
                                # Look for location
                                for line in lines:
                                    if any(loc_indicator in line.lower() for loc_indicator in ['dubai', 'bangladesh', 'dhaka', 'emirates', 'on-site', 'remote']):
                                        exp_data['location'] = line
                                        break
                                
                                # Use remaining lines as description
                                desc_lines = []
                                for line in lines[2:]:  # Skip title and company
                                    if (line != exp_data['duration'] and line != exp_data['location'] and 
                                        len(line) > 30):  # Only substantial lines
                                        desc_lines.append(line)
                                
                                if desc_lines:
                                    exp_data['description'] = ' '.join(desc_lines[:2])  # Limit to 2 sentences
                                
                                # Only add if we have meaningful title AND company data
                                if (exp_data['title'] != 'Not extracted' and exp_data['company'] != 'Not extracted' and
                                    len(exp_data['title']) > 5 and len(exp_data['company']) > 5):
                                    # Final validation: ensure this looks like real experience data
                                    if self._validate_experience_data(exp_data):
                                        experience_data['experience'].append(exp_data)
                                        print(f"✅ Extracted experience {len(experience_data['experience'])}: {exp_data['title']} at {exp_data['company']}")
                                    else:
                                        print(f"⏭️  Rejected invalid experience data: {exp_data['title']}")
                        
                        except Exception as e:
                            print(f"⚠️  Error processing experience item {i}: {str(e)}")
                            continue
                
            except NoSuchElementException:
                print("⚠️  Experience section not found")
                return experience_data
        
        except Exception as e:
            print(f"⚠️  Error extracting experience: {str(e)}")
        
        return experience_data
    
    def _looks_like_experience_entry(self, text: str) -> bool:
        """Check if text looks like a genuine experience entry"""
        text_lower = text.lower()
        
        # Must contain job-related indicators
        job_indicators = [
            'director', 'manager', 'engineer', 'analyst', 'consultant', 'specialist',
            'lead', 'senior', 'junior', 'associate', 'executive', 'officer',
            'developer', 'designer', 'architect', 'coordinator', 'supervisor',
            'partner', 'founder', 'ceo', 'cto', 'cfo', 'vp', 'head'
        ]
        
        # Must contain company/time indicators
        company_indicators = [
            'ltd', 'llc', 'inc', 'corp', 'company', 'technologies', 'solutions',
            'systems', 'services', 'group', 'full-time', 'part-time', 'present',
            'year', 'month', '2020', '2021', '2022', '2023', '2024'
        ]
        
        has_job_indicator = any(indicator in text_lower for indicator in job_indicators)
        has_company_indicator = any(indicator in text_lower for indicator in company_indicators)
        
        # Must have both job and company/time indicators
        return has_job_indicator and has_company_indicator
    
    def _validate_experience_data(self, exp_data: Dict) -> bool:
        """Final validation for experience data quality"""
        title = exp_data.get('title', '').lower()
        company = exp_data.get('company', '').lower()
        
        # Reject if title or company contains irrelevant keywords
        invalid_keywords = [
            'skills', 'interests', 'badges', 'endorsements', 'followers',
            'recommendations', 'activity', 'top voices', 'companies', 'groups'
        ]
        
        if any(keyword in title for keyword in invalid_keywords):
            return False
        
        if any(keyword in company for keyword in invalid_keywords):
            return False
        
        # Must have reasonable job title indicators
        job_title_indicators = [
            'director', 'manager', 'engineer', 'analyst', 'consultant',
            'lead', 'senior', 'partner', 'founder', 'ceo', 'cto'
        ]
        
        if not any(indicator in title for indicator in job_title_indicators):
            return False
        
        return True
    
    def _extract_education_detailed(self) -> Dict:
        """Extract detailed education information with improved targeting"""
        education_data = {'education': []}
        
        try:
            print("🔍 Extracting Education with precise targeting...")
            
            # First, try to find and scroll to the education section
            education_found = False
            try:
                education_heading = self.driver.find_element(By.XPATH, "//h2[contains(text(), 'Education')]")
                self.driver.execute_script("arguments[0].scrollIntoView();", education_heading)
                time.sleep(3)
                education_found = True
                print("✅ Found Education section")
                
                # Try to find the parent container of the education section
                parent_section = education_heading.find_element(By.XPATH, "./ancestor::section[1]")
                
                # Look specifically within this section for education entries
                edu_selectors_in_section = [
                    ".pvs-list__paged-list-item",
                    ".pvs-entity",
                    "li",
                    ".artdeco-list__item"
                ]
                
                edu_items = []
                for selector in edu_selectors_in_section:
                    try:
                        items = parent_section.find_elements(By.CSS_SELECTOR, selector)
                        if items:
                            print(f"✅ Found {len(items)} education items in section with selector: {selector}")
                            edu_items = items
                            break
                    except:
                        continue
                
                if edu_items:
                    for i, item in enumerate(edu_items[:4]):  # Limit to 4 items
                        try:
                            item_text = item.text.strip()
                            
                            # Skip irrelevant items - be strict about education content
                            skip_keywords = [
                                'education', 'experience', 'skills', 'about', 'interests', 'show all',
                                'see more', 'licenses', 'certifications', 'courses', 'organizations',
                                'recommendations', 'activity', 'endorsements', 'followers'
                            ]
                            
                            if (len(item_text) < 20 or 
                                any(keyword in item_text.lower() for keyword in skip_keywords)):
                                print(f"⏭️  Skipping irrelevant education item: {item_text[:50]}...")
                                continue
                            
                            # Additional validation: must look like actual education entry
                            if not self._looks_like_education_entry(item_text):
                                print(f"⏭️  Skipping non-education item: {item_text[:50]}...")
                                continue
                            
                            # Parse the text structure
                            lines = [line.strip() for line in item_text.split('\n') if line.strip()]
                            
                            if len(lines) >= 1:
                                edu_data = {
                                    'school': 'Not extracted',
                                    'degree': 'Not extracted',
                                    'duration': 'Not extracted',
                                    'description': 'Not extracted'
                                }
                                
                                # Look for school name (usually contains university, school, etc.)
                                for line in lines:
                                    if any(school_indicator in line.lower() for school_indicator in 
                                          ['university', 'college', 'school', 'institute', 'academy']):
                                        edu_data['school'] = line
                                        break
                                
                                # If no school found by keywords, use first substantial line
                                if edu_data['school'] == 'Not extracted' and lines:
                                    if len(lines[0]) > 10:
                                        edu_data['school'] = lines[0]
                                
                                # Look for degree/program information
                                for line in lines:
                                    if any(degree_indicator in line.lower() for degree_indicator in 
                                          ['bachelor', 'master', 'phd', 'degree', 'bsc', 'msc', 'ba', 'ma', 'program', 'seed', 'transformation']):
                                        if line != edu_data['school']:  # Don't duplicate school name
                                            edu_data['degree'] = line
                                            break
                                
                                # Look for duration/years
                                for line in lines:
                                    if any(time_indicator in line for time_indicator in ['2020', '2021', '2022', '2023', '2024', '2015', '2016', '2017', '2018', '2019']):
                                        if '-' in line or 'to' in line.lower():  # Looks like a date range
                                            edu_data['duration'] = line
                                            break
                                
                                # Use remaining lines as description
                                desc_lines = []
                                for line in lines:
                                    if (line != edu_data['school'] and line != edu_data['degree'] and 
                                        line != edu_data['duration'] and len(line) > 20):
                                        desc_lines.append(line)
                                
                                if desc_lines:
                                    edu_data['description'] = ' '.join(desc_lines[:2])  # Limit to 2 lines
                                
                                # Only add if we have meaningful school AND degree info
                                if (edu_data['school'] != 'Not extracted' and len(edu_data['school']) > 10):
                                    # Final validation: ensure this looks like real education data
                                    if self._validate_education_data(edu_data):
                                        education_data['education'].append(edu_data)
                                        print(f"✅ Extracted education {len(education_data['education'])}: {edu_data['degree']} from {edu_data['school']}")
                                    else:
                                        print(f"⏭️  Rejected invalid education data: {edu_data['school']}")
                        
                        except Exception as e:
                            print(f"⚠️  Error processing education item {i}: {str(e)}")
                            continue
                
            except NoSuchElementException:
                print("⚠️  Education section not found")
                return education_data
        
        except Exception as e:
            print(f"⚠️  Error extracting education: {str(e)}")
        
        return education_data
    
    def _looks_like_education_entry(self, text: str) -> bool:
        """Check if text looks like a genuine education entry"""
        text_lower = text.lower()
        
        # Must contain education-related indicators
        education_indicators = [
            'university', 'college', 'school', 'institute', 'academy',
            'bachelor', 'master', 'phd', 'degree', 'bsc', 'msc', 'ba', 'ma',
            'program', 'course', 'diploma', 'certificate', 'engineering',
            'business', 'science', 'arts', 'technology', 'management'
        ]
        
        # Must contain time indicators
        time_indicators = [
            '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024',
            'year', 'semester', '-', 'to'
        ]
        
        has_education_indicator = any(indicator in text_lower for indicator in education_indicators)
        has_time_indicator = any(indicator in text_lower for indicator in time_indicators)
        
        # Must have both education and time indicators
        return has_education_indicator and has_time_indicator
    
    def _validate_education_data(self, edu_data: Dict) -> bool:
        """Final validation for education data quality"""
        school = edu_data.get('school', '').lower()
        
        # Must contain valid school indicators
        valid_school_indicators = [
            'university', 'college', 'school', 'institute', 'academy', 'stanford', 'harvard', 'mit'
        ]
        
        if not any(indicator in school for indicator in valid_school_indicators):
            return False
        
        # Reject if contains irrelevant keywords
        invalid_keywords = [
            'skills', 'interests', 'badges', 'endorsements', 'followers',
            'recommendations', 'activity', 'top voices', 'companies'
        ]
        
        if any(keyword in school for keyword in invalid_keywords):
            return False
        
        return True
    
    def _is_valid_experience_entry(self, exp_data: Dict) -> bool:
        """Ultra-strict final validation for experience entries"""
        title = exp_data.get('title', '').strip()
        company = exp_data.get('company', '').strip()
        
        # Reject if any field is "Not extracted" or empty
        if (not title or not company or 
            title == 'Not extracted' or company == 'Not extracted' or
            len(title) < 5 or len(company) < 5):
            return False
        
        # Reject if title contains any invalid patterns
        invalid_title_patterns = [
            'mir has', 'badgetype', 'account', 'skills', 'interests', 'endorsed',
            'followers', 'endorsements', 'recommendations', 'activity', 'badges',
            'top voices', 'companies', 'groups', 'see more', 'show all'
        ]
        
        if any(pattern in title.lower() for pattern in invalid_title_patterns):
            return False
        
        # Must contain valid job title words
        valid_title_words = [
            'director', 'manager', 'engineer', 'analyst', 'consultant', 'lead',
            'senior', 'partner', 'founder', 'ceo', 'cto', 'cfo', 'head', 'vp'
        ]
        
        if not any(word in title.lower() for word in valid_title_words):
            return False
        
        # Company should not contain skill/badge keywords
        invalid_company_patterns = [
            'endorsed', 'endorsements', 'skills', 'months', 'voices'
        ]
        
        if any(pattern in company.lower() for pattern in invalid_company_patterns):
            return False
        
        return True
    
    def _is_valid_education_entry(self, edu_data: Dict) -> bool:
        """Ultra-strict final validation for education entries"""
        school = edu_data.get('school', '').strip()
        
        # Reject if school is "Not extracted" or empty
        if (not school or school == 'Not extracted' or len(school) < 10):
            return False
        
        # Must contain valid education indicators
        valid_education_words = [
            'university', 'college', 'school', 'institute', 'academy'
        ]
        
        if not any(word in school.lower() for word in valid_education_words):
            return False
        
        # Reject if contains invalid patterns
        invalid_patterns = [
            'endorsed', 'endorsements', 'skills', 'badges', 'followers',
            'recommendations', 'activity', 'top voices'
        ]
        
        if any(pattern in school.lower() for pattern in invalid_patterns):
            return False
        
        return True
    
    def _extract_experience_fallback(self) -> Dict:
        """Fallback method to extract experience using aggressive DOM search"""
        experience_data = {'experience': []}
        
        try:
            print("🔍 FALLBACK: Searching DOM for experience patterns...")
            
            # First, try to find the experience section by scrolling and looking for it
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.3);")
            time.sleep(2)
            
            # Look for all possible selectors that might contain experience items
            fallback_selectors = [
                "li[data-field='experience']",
                "[aria-label*='Experience']",
                ".experience-section",
                ".pv-profile-section__card-item-v2",
                ".pv-entity__summary-info",
                ".pv-position-entity",
                "article",
                ".pvs-list li",
                ".artdeco-card",
                "section[data-field='experience'] ul li",
                "[id*='experience'] li",
                ".pvs-entity__caption-wrapper"
            ]
            
            found_items = []
            for selector in fallback_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"✅ FALLBACK: Found {len(elements)} items with selector: {selector}")
                        for element in elements:
                            try:
                                text = element.text.strip()
                                if (text and len(text) > 20 and len(text) < 500 and 
                                    text not in [item.get('raw_text', '') for item in found_items]):
                                    
                                    # Check if this looks like experience content
                                    text_lower = text.lower()
                                    experience_indicators = [
                                        'director', 'manager', 'engineer', 'analyst', 'lead',
                                        'partner', 'consultant', 'specialist', 'coordinator',
                                        'senior', 'junior', 'associate', 'executive', 'officer',
                                        'full-time', 'part-time', 'present', 'years', 'months',
                                        'inc', 'ltd', 'llc', 'corp', 'company', 'technologies',
                                        'solutions', 'systems', 'services', 'group'
                                    ]
                                    
                                    if any(indicator in text_lower for indicator in experience_indicators):
                                        found_items.append({
                                            'raw_text': text,
                                            'element': element
                                        })
                                        
                                        if len(found_items) >= 10:
                                            break
                            except:
                                continue
                        
                        if found_items:
                            break
                except:
                    continue
            
            # Process found items to extract structured data
            for item in found_items[:5]:  # Limit to 5 items
                try:
                    text = item['raw_text']
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    
                    exp_data = {
                        'title': 'Not extracted',
                        'company': 'Not extracted', 
                        'duration': 'Not extracted',
                        'description': 'Not extracted'
                    }
                    
                    # Try to parse the text structure
                    if len(lines) >= 2:
                        # First line is often the job title
                        if len(lines[0]) < 100:
                            exp_data['title'] = lines[0]
                        
                        # Second line might be company
                        if len(lines) > 1 and len(lines[1]) < 100:
                            # Check if it looks like a company name
                            company_indicators = ['inc', 'ltd', 'llc', 'corp', 'technologies', 'solutions', 'systems']
                            if any(indicator in lines[1].lower() for indicator in company_indicators):
                                exp_data['company'] = lines[1]
                        
                        # Look for duration in any line
                        for line in lines:
                            if ('year' in line.lower() or 'month' in line.lower() or 
                                'present' in line.lower() or '20' in line):
                                exp_data['duration'] = line
                                break
                        
                        # Use remaining text as description
                        if len(lines) > 2:
                            exp_data['description'] = ' '.join(lines[2:])[:200]
                    
                    else:
                        # Single line, try to parse it
                        exp_data['title'] = text[:100]
                    
                    experience_data['experience'].append(exp_data)
                    print(f"✅ FALLBACK: Extracted experience: {exp_data['title'][:50]}...")
                
                except Exception as e:
                    print(f"⚠️  Error processing item: {str(e)}")
                    continue
            
            if not experience_data['experience']:
                print("⚠️  FALLBACK: No experience items could be extracted")
        
        except Exception as e:
            print(f"⚠️  Fallback experience extraction error: {str(e)}")
        
        return experience_data
    
    def _extract_education_fallback(self) -> Dict:
        """Fallback method to extract education using aggressive DOM search"""
        education_data = {'education': []}
        
        try:
            print("🔍 FALLBACK: Searching DOM for education patterns...")
            
            # Scroll to education area
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.5);")
            time.sleep(2)
            
            # Look for all possible selectors that might contain education items
            fallback_selectors = [
                "li[data-field='education']",
                "[aria-label*='Education']",
                ".education-section",
                ".pv-profile-section__card-item-v2",
                ".pv-entity__summary-info",
                ".pv-education-entity",
                "article",
                ".pvs-list li",
                ".artdeco-card",
                "section[data-field='education'] ul li",
                "[id*='education'] li",
                ".pvs-entity__caption-wrapper"
            ]
            
            found_items = []
            for selector in fallback_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"✅ FALLBACK: Found {len(elements)} items with selector: {selector}")
                        for element in elements:
                            try:
                                text = element.text.strip()
                                if (text and len(text) > 10 and len(text) < 300 and 
                                    text not in [item.get('raw_text', '') for item in found_items]):
                                    
                                    # Check if this looks like education content
                                    text_lower = text.lower()
                                    education_indicators = [
                                        'university', 'college', 'school', 'institute', 'academy',
                                        'bachelor', 'master', 'phd', 'degree', 'diploma', 'certificate',
                                        'bsc', 'msc', 'ba', 'ma', 'stanford', 'harvard', 'mit',
                                        'engineering', 'business', 'science', 'arts', 'technology',
                                        'graduate', 'undergraduate', 'program', 'course'
                                    ]
                                    
                                    if any(indicator in text_lower for indicator in education_indicators):
                                        # Exclude profile headline and basic info
                                        if not any(exclude in text_lower for exclude in ['co-founder', 'forbes', 'bangladesh']):
                                            found_items.append({
                                                'raw_text': text,
                                                'element': element
                                            })
                                            
                                            if len(found_items) >= 8:
                                                break
                            except:
                                continue
                        
                        if found_items:
                            break
                except:
                    continue
            
            # Process found items to extract structured data
            for item in found_items[:3]:  # Limit to 3 items
                try:
                    text = item['raw_text']
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    
                    edu_data = {
                        'school': 'Not extracted',
                        'degree': 'Not extracted', 
                        'duration': 'Not extracted',
                        'description': 'Not extracted'
                    }
                    
                    # Try to parse the text structure
                    if len(lines) >= 1:
                        # Look for school name (usually has university, college, etc.)
                        for line in lines:
                            if any(indicator in line.lower() for indicator in ['university', 'college', 'school', 'institute']):
                                edu_data['school'] = line
                                break
                        
                        # If no school found, use first line
                        if edu_data['school'] == 'Not extracted' and lines:
                            edu_data['school'] = lines[0]
                        
                        # Look for degree information
                        for line in lines:
                            if any(indicator in line.lower() for indicator in ['bachelor', 'master', 'phd', 'degree', 'bsc', 'msc', 'ba', 'ma', 'program']):
                                edu_data['degree'] = line
                                break
                        
                        # Look for duration in any line
                        for line in lines:
                            if ('20' in line and len(line) < 50) or any(year_indicator in line.lower() for year_indicator in ['year', 'semester']):
                                edu_data['duration'] = line
                                break
                        
                        # Use additional lines as description
                        if len(lines) > 2:
                            desc_lines = [l for l in lines if l != edu_data['school'] and l != edu_data['degree'] and l != edu_data['duration']]
                            if desc_lines:
                                edu_data['description'] = ' '.join(desc_lines[:2])[:200]
                    
                    education_data['education'].append(edu_data)
                    print(f"✅ FALLBACK: Extracted education: {edu_data['school'][:50]}...")
                
                except Exception as e:
                    print(f"⚠️  Error processing education item: {str(e)}")
                    continue
            
            if not education_data['education']:
                print("⚠️  FALLBACK: No education items could be extracted")
        
        except Exception as e:
            print(f"⚠️  Fallback education extraction error: {str(e)}")
        
        return education_data
    
    def _extract_skills_detailed(self) -> Dict:
        """Extract detailed skills"""
        skills_data = {'skills': []}
        
        try:
            print("🔍 Extracting Skills...")
            
            try:
                skills_heading = self.driver.find_element(By.XPATH, "//h2[contains(text(), 'Skills')]")
                self.driver.execute_script("arguments[0].scrollIntoView();", skills_heading)
                time.sleep(3)
            except NoSuchElementException:
                return skills_data
            
            skill_elements = self.driver.find_elements(By.CSS_SELECTOR, ".pvs-entity span[aria-hidden='true']")
            
            for element in skill_elements:
                try:
                    skill_text = element.text.strip()
                    if skill_text and len(skill_text) < 50 and skill_text not in skills_data['skills']:
                        skills_data['skills'].append(skill_text)
                except:
                    continue
            
            skills_data['skills'] = list(set(skills_data['skills']))[:20]
            print(f"✅ Extracted {len(skills_data['skills'])} skills")
        
        except Exception as e:
            pass
        
        return skills_data
    
    def save_data(self, data: Dict, filename: str = None):
        """Save scraped data to file"""
        if not data:
            return
        
        os.makedirs('./output', exist_ok=True)
        
        if not filename:
            name = data.get('name', 'unknown').replace(' ', '_').lower()
            timestamp = int(time.time())
            filename = f"{name}_profile_{timestamp}.json"
        
        filepath = os.path.join('./output', filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Profile data saved to: {filepath}")
            return filepath
        
        except Exception as e:
            print(f"❌ Error saving data: {str(e)}")
            return None
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()

def scrape_single_profile(profile_url: str):
    """Scrape a single LinkedIn profile"""
    scraper = SimpleLinkedInScraper()
    
    try:
        profile_data = scraper.scrape_profile(profile_url)
        
        if profile_data:
            filepath = scraper.save_data(profile_data)
            
            # Display summary
            print(f"\n📊 PROFILE EXTRACTION SUMMARY:")
            print(f"Name: {profile_data.get('name', 'N/A')}")
            print(f"Headline: {profile_data.get('headline', 'N/A')[:100]}...")
            print(f"Location: {profile_data.get('location', 'N/A')}")
            print(f"Followers: {profile_data.get('followers', 'N/A')}")
            
            about_text = profile_data.get('about', '')
            if about_text and about_text != 'Not found':
                print(f"About: {len(about_text)} characters extracted")
            else:
                print("About: Not found")
            
            print(f"Experience: {len(profile_data.get('experience', []))} entries")
            print(f"Education: {len(profile_data.get('education', []))} entries")
            print(f"Skills: {len(profile_data.get('skills', []))} entries")
            
            return filepath
        else:
            print("❌ Failed to scrape profile")
            return None
    
    finally:
        scraper.close()

def main():
    print("🚀 Simple LinkedIn Profile Scraper")
    print("=" * 40)
    print("Credentials loaded from .env file")
    print()
    
    while True:
        profile_url = input("Enter LinkedIn profile URL (or 'quit' to exit): ").strip()
        
        if profile_url.lower() in ['quit', 'exit', 'q']:
            break
        
        if not profile_url.startswith('https://www.linkedin.com/in/'):
            print("❌ Please enter a valid LinkedIn profile URL")
            continue
        
        print(f"\n🔍 Starting extraction for: {profile_url}")
        filepath = scrape_single_profile(profile_url)
        
        if filepath:
            print(f"✅ Profile successfully scraped and saved!")
        else:
            print("❌ Profile extraction failed")
        
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()