#!/usr/bin/env python3
"""
ChromeDriver Setup Helper for Windows
This script helps you download and setup ChromeDriver manually
"""

import os
import sys
import requests
import zipfile
import subprocess
from pathlib import Path

def get_chrome_version():
    """Get installed Chrome version"""
    try:
        # Try to get Chrome version from registry
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
        version, _ = winreg.QueryValueEx(key, "version")
        winreg.CloseKey(key)
        return version
    except:
        try:
            # Alternative method
            result = subprocess.run([
                r"C:\Program Files\Google\Chrome\Application\chrome.exe", "--version"
            ], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split()[-1]
        except:
            pass
    
    return None

def download_chromedriver(version):
    """Download ChromeDriver for the given Chrome version"""
    try:
        # Get major version number
        major_version = version.split('.')[0]
        
        print(f"🔍 Getting latest ChromeDriver for Chrome {major_version}...")
        
        # Try new ChromeDriver download method first
        try:
            # New ChromeDriver API
            api_url = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
            response = requests.get(api_url)
            
            if response.status_code == 200:
                data = response.json()
                versions = data.get('versions', [])
                
                # Find the latest version for the major version
                latest_version = None
                for v in reversed(versions):
                    if v['version'].startswith(major_version + '.'):
                        latest_version = v
                        break
                
                if latest_version:
                    print(f"📦 Found ChromeDriver version: {latest_version['version']}")
                    
                    # Find Windows download URL
                    download_url = None
                    for download in latest_version.get('downloads', {}).get('chromedriver', []):
                        if download['platform'] == 'win32':
                            download_url = download['url']
                            break
                    
                    if download_url:
                        print(f"⬇️  Downloading ChromeDriver...")
                        response = requests.get(download_url)
                        
                        if response.status_code == 200:
                            # Save zip file
                            zip_path = "chromedriver.zip"
                            with open(zip_path, 'wb') as f:
                                f.write(response.content)
                            
                            # Extract zip file
                            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                                zip_ref.extractall(".")
                            
                            # Remove zip file
                            os.remove(zip_path)
                            
                            print("✅ ChromeDriver downloaded and extracted successfully!")
                            return True
                        else:
                            print(f"❌ Failed to download ChromeDriver: HTTP {response.status_code}")
                    else:
                        print("❌ No Windows download URL found")
                else:
                    print(f"❌ No ChromeDriver found for Chrome {major_version}")
            else:
                print(f"❌ Failed to get ChromeDriver versions: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"⚠️  New method failed: {e}")
        
        # Fallback to old method for older versions
        print("🔄 Trying legacy download method...")
        url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
        response = requests.get(url)
        
        if response.status_code == 200:
            chromedriver_version = response.text.strip()
            print(f"📦 Latest ChromeDriver version: {chromedriver_version}")
            
            # Download ChromeDriver
            download_url = f"https://chromedriver.storage.googleapis.com/{chromedriver_version}/chromedriver_win32.zip"
            print(f"⬇️  Downloading ChromeDriver...")
            
            response = requests.get(download_url)
            if response.status_code == 200:
                # Save zip file
                zip_path = "chromedriver.zip"
                with open(zip_path, 'wb') as f:
                    f.write(response.content)
                
                # Extract zip file
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(".")
                
                # Remove zip file
                os.remove(zip_path)
                
                print("✅ ChromeDriver downloaded and extracted successfully!")
                return True
            else:
                print(f"❌ Failed to download ChromeDriver: HTTP {response.status_code}")
                return False
        else:
            print(f"❌ Failed to get ChromeDriver version: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error downloading ChromeDriver: {str(e)}")
        return False

def check_chromedriver():
    """Check if ChromeDriver is available"""
    if os.path.exists("chromedriver.exe"):
        print("✅ ChromeDriver found in current directory")
        return True
    
    # Check if it's in PATH
    try:
        result = subprocess.run(["chromedriver", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ ChromeDriver found in PATH")
            return True
    except:
        pass
    
    print("❌ ChromeDriver not found")
    return False

def main():
    print("🔧 ChromeDriver Setup Helper for Windows")
    print("=" * 45)
    
    # Check if ChromeDriver is already available
    if check_chromedriver():
        print("🎉 ChromeDriver is ready to use!")
        return
    
    # Get Chrome version
    chrome_version = get_chrome_version()
    if not chrome_version:
        print("❌ Could not detect Chrome version")
        print("💡 Please make sure Google Chrome is installed")
        return
    
    print(f"🌐 Detected Chrome version: {chrome_version}")
    
    # Download ChromeDriver
    if download_chromedriver(chrome_version):
        print("\n🎉 ChromeDriver setup completed!")
        print("📁 ChromeDriver is now in the current directory")
        print("🚀 You can now run the LinkedIn scraper")
    else:
        print("\n❌ ChromeDriver setup failed")
        print("💡 Manual setup required:")
        print("1. Go to: https://chromedriver.chromium.org/")
        print("2. Download ChromeDriver for your Chrome version")
        print("3. Extract chromedriver.exe to this folder")

if __name__ == "__main__":
    main()