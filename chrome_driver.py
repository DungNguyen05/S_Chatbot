from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import os
import platform
import tempfile
import uuid
import subprocess
import time
import socket
import logging
import shutil
import re
import signal
import psutil
from pathlib import Path

def create_chrome_driver(headless=True, binary_path=None, terminate_chrome=False):
    """
    Creates a Chrome WebDriver with robust handling of the 'user data directory already in use' error.
    
    This implementation uses multiple strategies to ensure this specific error is resolved:
    1. Creates truly unique user data directories with randomized paths
    2. Optionally terminates all Chrome processes before initialization
    3. Uses specific Chrome command line flags to prevent directory locking
    4. Implements proper permission handling for the temporary directories
    5. Sanitizes paths to avoid any special character issues
    
    Args:
        headless (bool): Whether to run Chrome in headless mode
        binary_path (str, optional): Path to Chrome executable. Auto-detected if None.
        terminate_chrome (bool): Whether to terminate existing Chrome processes. Default is False.
        
    Returns:
        webdriver.Chrome: Initialized Chrome WebDriver instance or None if failed
    """
    
    # Configure logging for detailed diagnostics
    logger = logging.getLogger("chrome_driver")
    logger.setLevel(logging.WARNING) # Change WARNING to INFO to see logging
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    logger.info("Initializing Chrome WebDriver with user data directory fix")
    
    # STEP 1: Optionally terminate Chrome processes
    if terminate_chrome:
        logger.info("Terminating existing Chrome processes as requested")
        _terminate_all_chrome_processes(logger)
    else:
        logger.info("Skipping Chrome process termination (terminate_chrome=False)")
    
    # STEP 2: Locate Chrome binary if not provided
    if not binary_path:
        binary_path = _find_chrome_binary(logger)
        if not binary_path:
            logger.error("Google Chrome binary not found. Please install Chrome or specify binary_path.")
            _print_chrome_installation_instructions()
            return None
    
    logger.info(f"Using Chrome binary: {binary_path}")
    
    # STEP 3: Create a truly unique user data directory with guaranteed uniqueness
    try:
        # Create base temp directory
        temp_dir = tempfile.mkdtemp(prefix="chrome_selenium_")
        
        # Create a unique subdirectory with multiple uniqueness factors
        timestamp = int(time.time())
        process_id = os.getpid()
        random_id = str(uuid.uuid4()).replace("-", "")
        
        # Combine all uniqueness factors into the path
        unique_dir_name = f"chrome_profile_{timestamp}_{process_id}_{random_id}"
        user_data_dir = os.path.join(temp_dir, unique_dir_name)
        
        # Create the directory with appropriate permissions
        os.makedirs(user_data_dir, exist_ok=True)
        
        # Set explicit permissions on Unix systems
        if platform.system() != "Windows":
            os.chmod(user_data_dir, 0o755)
            
        logger.info(f"Created guaranteed unique user data directory: {user_data_dir}")
    except Exception as e:
        logger.error(f"Failed to create temporary directory: {str(e)}")
        return None
    
    # STEP 4: Configure Chrome options with explicit focus on preventing the user data directory error
    options = Options()
    if binary_path:
        options.binary_location = binary_path
    
    # The critical flag that prevents the "user data directory already in use" error
    options.add_argument(f"--user-data-dir={user_data_dir}")
    
    # Additional flags that help prevent directory locking issues
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-sync")  # Prevents Chrome from syncing, which can lock the profile
    options.add_argument("--disable-background-networking")  # Reduces background activity
    
    # Increase timeouts to help with slow-loading pages
    options.add_argument("--disable-hang-monitor")
    options.add_argument("--disable-prompt-on-repost")
    
    # Platform-specific optimizations
    if platform.system() == "Linux":
        options.add_argument("--disable-features=VizDisplayCompositor")
    
    # Add headless mode if requested
    if headless:
        options.add_argument("--headless=new")
    
    # STEP 5: Set up the driver with careful error handling
    try:
        # Get chromedriver path using webdriver-manager
        from webdriver_manager.chrome import ChromeDriverManager
        driver_path = ChromeDriverManager().install()
        if not driver_path:
            logger.error("Failed to locate chromedriver executable")
            return None
            
        # Find an available port to prevent conflicts
        port = _find_free_port()
        logger.info(f"Using port {port} for driver communication")
        
        # Configure service with explicit logging
        service = Service(
            executable_path=driver_path,
            port=port,
            log_output=os.path.join(tempfile.gettempdir(), f"chromedriver_{process_id}.log")
        )
        
        # Initialize driver with the carefully prepared options
        logger.info("Initializing Chrome WebDriver with unique user data directory")
        driver = webdriver.Chrome(service=service, options=options)
        
        # Set extended timeouts to improve stability
        try:
            driver.set_page_load_timeout(60)  # 60 seconds for page loads
            driver.set_script_timeout(45)     # 45 seconds for scripts
            logger.info("Set extended timeouts for better stability")
        except Exception as e:
            logger.warning(f"Could not set timeouts: {str(e)}")
        
        # Test the driver with a simple navigation
        try:
            driver.get("about:blank")
            logger.info("Chrome WebDriver initialized successfully!")
            return driver
        except Exception as e:
            logger.error(f"Failed initial navigation test: {str(e)}")
            driver.quit()
            raise
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"Chrome WebDriver initialization failed: {error_message}")
        
        # Specific handling for the "user data directory already in use" error
        if "user data directory is already in use" in error_message:
            logger.error("Detected 'user data directory already in use' error")
            
            # Only attempt aggressive process cleanup if terminate_chrome is True
            if terminate_chrome:
                logger.info("Attempting more aggressive process cleanup...")
                _terminate_all_chrome_processes(logger, force=True)
                time.sleep(3)  # Wait for resources to be fully released
            else:
                logger.warning("Not attempting process cleanup because terminate_chrome=False")
                logger.info("Consider setting terminate_chrome=True if you continue to experience issues")
            
            try:
                # Clean up the failed directory
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                # Create a completely new directory with different path
                new_temp_dir = tempfile.mkdtemp(prefix="chrome_retry_")
                new_unique_dir = f"chrome_retry_{int(time.time())}_{os.getpid()}_{uuid.uuid4().hex}"
                new_user_data_dir = os.path.join(new_temp_dir, new_unique_dir)
                os.makedirs(new_user_data_dir, exist_ok=True)
                
                # Set proper permissions
                if platform.system() != "Windows":
                    os.chmod(new_user_data_dir, 0o755)
                
                logger.info(f"Retrying with new user data directory: {new_user_data_dir}")
                
                # Update options
                options.add_argument(f"--user-data-dir={new_user_data_dir}")
                
                # Try again with a new port
                new_port = _find_free_port()
                service = Service(executable_path=driver_path, port=new_port)
                driver = webdriver.Chrome(service=service, options=options)
                
                # Set extended timeouts to improve stability
                try:
                    driver.set_page_load_timeout(60)  # 60 seconds for page loads
                    driver.set_script_timeout(45)     # 45 seconds for scripts
                    logger.info("Set extended timeouts for better stability")
                except Exception as e:
                    logger.warning(f"Could not set timeouts: {str(e)}")
                
                # Verify initialization
                driver.get("about:blank")
                logger.info("Chrome WebDriver initialization successful on retry!")
                return driver
                
            except Exception as retry_err:
                logger.error(f"Retry also failed: {str(retry_err)}")
                logger.error("Could not resolve the 'user data directory already in use' error")
                _print_diagnostic_info(logger)
        else:
            # For other errors, print diagnostic information
            _print_diagnostic_info(logger)
        
        # Clean up resources
        try:
            if 'temp_dir' in locals() and temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
            
        return None

def _terminate_all_chrome_processes(logger, force=False):
    """
    Aggressively terminates all Chrome and chromedriver processes.
    
    This is a critical step for preventing "user data directory already in use" errors,
    as it ensures no lingering processes are keeping user data directories locked.
    
    Args:
        logger: Logger instance for output
        force (bool): Whether to use forceful termination methods
    """
    logger.info("Terminating all Chrome and chromedriver processes")
    system = platform.system().lower()
    
    try:
        # Method 1: OS-specific commands for process termination
        if system == "darwin":  # macOS
            # Use pkill with -9 for forceful termination if needed
            force_flag = "-9" if force else "-15"
            subprocess.run(["pkill", force_flag, "-f", "Google Chrome"], stderr=subprocess.DEVNULL, check=False)
            subprocess.run(["pkill", force_flag, "-f", "chromedriver"], stderr=subprocess.DEVNULL, check=False)
        elif system == "linux":
            force_flag = "-9" if force else "-15"
            subprocess.run(["pkill", force_flag, "-f", "chrome"], stderr=subprocess.DEVNULL, check=False)
            subprocess.run(["pkill", force_flag, "-f", "chromedriver"], stderr=subprocess.DEVNULL, check=False)
        elif system == "windows":
            # Use /F for forceful termination on Windows
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], stderr=subprocess.DEVNULL, check=False)
            subprocess.run(["taskkill", "/F", "/IM", "chromedriver.exe"], stderr=subprocess.DEVNULL, check=False)
        
        # Method 2: Use psutil for more thorough process detection and termination
        # This catches processes that might be missed by the OS-specific commands
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Check process name and command line for Chrome-related processes
                    proc_name = proc.info['name'].lower() if proc.info['name'] else ""
                    cmdline = ' '.join(proc.info['cmdline']).lower() if proc.info['cmdline'] else ""
                    
                    # Look for Chrome or chromedriver in process name or command line
                    is_chrome_process = (
                        "chrome" in proc_name or 
                        "chromedriver" in proc_name or
                        "chrome" in cmdline or
                        "chromedriver" in cmdline
                    )
                    
                    if is_chrome_process:
                        logger.info(f"Terminating process: {proc.pid} ({proc_name})")
                        if force:
                            proc.kill()  # Forceful termination
                        else:
                            proc.terminate()  # Graceful termination
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except ImportError:
            logger.warning("psutil not available for advanced process management")
        
        # Allow time for processes to terminate
        time.sleep(1)
        
        logger.info("Chrome processes terminated")
    except Exception as e:
        logger.warning(f"Error during process termination: {str(e)}")

def _find_chrome_binary(logger):
    """
    Locates the Google Chrome browser executable on the system.
    
    Args:
        logger: Logger instance
        
    Returns:
        str: Path to Chrome binary or None if not found
    """
    system = platform.system().lower()
    logger.info(f"Searching for Google Chrome on {system}")
    
    # Platform-specific search logic
    if system == "darwin":  # macOS
        search_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        ]
        
        # Check standard paths first
        for path in search_paths:
            if os.path.exists(path):
                logger.info(f"Found Chrome binary at: {path}")
                return path
    
    elif system == "linux":
        search_paths = [
            "/usr/bin/google-chrome-stable",
            "/usr/bin/google-chrome",
            "/usr/bin/chrome",
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium"
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                logger.info(f"Found Chrome binary at: {path}")
                return path
                
        # Try which command
        try:
            result = subprocess.run(["which", "google-chrome"], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                path = result.stdout.strip()
                logger.info(f"Found Chrome binary via which: {path}")
                return path
        except Exception:
            pass
    
    elif system == "windows":  # Windows
        search_paths = [
            os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 
                        "Google\\Chrome\\Application\\chrome.exe"),
            os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 
                        "Google\\Chrome\\Application\\chrome.exe")
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                logger.info(f"Found Chrome binary at: {path}")
                return path
    
    logger.warning("Google Chrome binary not found on this system")
    return None

def _find_free_port():
    """
    Finds an available network port for the WebDriver.
    
    Returns:
        int: Available port number
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

def _print_diagnostic_info(logger):
    """
    Prints diagnostic information to help troubleshoot WebDriver issues.
    
    Args:
        logger: Logger instance
    """
    logger.info("\n==== DIAGNOSTIC INFORMATION ====")
    
    # System information
    logger.info(f"OS: {platform.system()} {platform.release()}")
    logger.info(f"Python: {platform.python_version()}")
    
    # Check Chrome installation
    chrome_binary = _find_chrome_binary(logger)
    logger.info(f"Chrome binary found: {chrome_binary is not None}")
    if chrome_binary:
        logger.info(f"Chrome path: {chrome_binary}")
    
    # Check Chrome processes
    try:
        import psutil
        chrome_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                proc_name = proc.info['name'].lower() if proc.info['name'] else ""
                cmdline = ' '.join(proc.info['cmdline']).lower() if proc.info['cmdline'] else ""
                
                if "chrome" in proc_name or "chrome" in cmdline:
                    chrome_processes.append(f"PID {proc.pid}: {proc_name}")
            except:
                pass
        
        if chrome_processes:
            logger.info("Running Chrome processes:")
            for proc in chrome_processes:
                logger.info(f"  - {proc}")
        else:
            logger.info("No running Chrome processes found")
    except ImportError:
        logger.info("psutil not available for process checking")
    
    # Check for temp directories
    temp_dir = tempfile.gettempdir()
    logger.info(f"Temp directory: {temp_dir}")
    
    chrome_temp_dirs = []
    try:
        for item in os.listdir(temp_dir):
            if "chrome" in item.lower():
                chrome_temp_dirs.append(item)
        
        if chrome_temp_dirs:
            logger.info("Chrome-related temp directories:")
            for dir_name in chrome_temp_dirs[:5]:  # Show first 5 to avoid excessive output
                logger.info(f"  - {dir_name}")
            if len(chrome_temp_dirs) > 5:
                logger.info(f"  ... and {len(chrome_temp_dirs) - 5} more")
    except:
        logger.info("Could not check temp directories")
    
    # Check webdriver-manager installation
    try:
        import webdriver_manager
        logger.info(f"webdriver-manager version: {webdriver_manager.__version__}")
    except ImportError:
        logger.info("webdriver-manager not installed")
    
    logger.info("================================\n")

def _print_chrome_installation_instructions():
    """Prints instructions for installing Google Chrome."""
    system = platform.system().lower()
    
    print("\n==== Google Chrome Installation Instructions ====")
    
    if system == "darwin":  # macOS
        print("To install Google Chrome on macOS:")
        print("1. Download from: https://www.google.com/chrome/")
        print("2. Open the downloaded file and follow installation instructions")
        print("3. Move the app to your Applications folder")
        print("\nAlternatively, install via Homebrew:")
        print("    brew install --cask google-chrome")
    
    elif system == "linux":  # Ubuntu/Linux
        print("To install Google Chrome on Ubuntu/Debian Linux:")
        print("    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -")
        print("    sudo sh -c 'echo \"deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main\" >> /etc/apt/sources.list.d/google.list'")
        print("    sudo apt-get update")
        print("    sudo apt-get install google-chrome-stable")
    
    elif system == "windows":  # Windows
        print("To install Google Chrome on Windows:")
        print("1. Download from: https://www.google.com/chrome/")
        print("2. Run the installer and follow the instructions")
    
    print("\nAfter installation, you can specify the binary path manually:")
    if system == "darwin":
        print("    create_chrome_driver(binary_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')")
    elif system == "linux":
        print("    create_chrome_driver(binary_path='/usr/bin/google-chrome-stable')")
    elif system == "windows":
        print("    create_chrome_driver(binary_path='C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe')")
    
    print("====================================================\n")


# Example usage
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Additional requirements to install
    print("Required packages: selenium webdriver-manager psutil")
    print("Install with: pip install selenium webdriver-manager psutil")
    
    # Create Chrome WebDriver with error handling
    driver = create_chrome_driver(headless=False)
    
    if driver:
        try:
            # Test the driver
            driver.get("https://www.google.com")
            print(f"Page loaded successfully! Title: {driver.title}")
        finally:
            driver.quit()
    else:
        print("Failed to initialize Chrome WebDriver.")