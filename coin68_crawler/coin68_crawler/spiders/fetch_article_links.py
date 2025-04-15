from selenium.webdriver.common.by import By
import time

DELAY = 5
RETRY = 3

def click(driver, page_count):
    retry = RETRY
    clickable = False

    while retry > 0 and not clickable:
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, f'button[aria-label="Go to page {page_count}"]')
            clickable = True
            next_button.click()
        except Exception as e:
            retry -= 1
            if retry == 0:
                print(f"❌ Failed to navigate to page {page_count}")
            clickable = False

        time.sleep(DELAY)
        
    return clickable

def skip(driver):
    retry = RETRY
    clickable = False

    while retry > 0 and not clickable:
        try:
            # Try multiple selectors, from most specific to most general
            selectors = [
                (By.XPATH, "//button[text()='Đồng ý']"),
                (By.XPATH, "//button[normalize-space(text())='Đồng ý']"),
                (By.XPATH, "//div[contains(@class, 'css-144iql5')]/button"),
                (By.CSS_SELECTOR, ".css-144iql5 > button"),
                (By.CSS_SELECTOR, "button.MuiButton-textPrimary.MuiButton-text"),
                (By.XPATH, "//button[contains(@class, 'MuiButtonBase-root') and contains(text(), 'Đồng ý')]")
            ]
            
            skip_button = None
            for selector_type, selector in selectors:
                try:
                    skip_button = driver.find_element(selector_type, selector)
                    if skip_button and skip_button.is_displayed():
                        # print(f"✅ Found skip button using: {selector}")
                        break
                except:
                    continue
            
            if not skip_button:
                raise Exception("Skip button not found with any selector")
                
            # Try to click with JavaScript for better reliability
            driver.execute_script("arguments[0].click();", skip_button)
            clickable = True
            print("✅ Clicked 'Skip' button")
            
        except Exception as e:
            clickable = False
            retry -= 1
            if retry == 0:
                print(f"❌ Failed to click 'Skip' button: {e}")
                
        time.sleep(DELAY)
        
    return clickable

def fetch_article_links(driver, target_count):
    """
    Fetch article links using a provided Chrome WebDriver.
    
    Args:
        driver: Initialized Chrome WebDriver instance
        target_count: Number of article links to collect
        
    Returns:
        list: Article URLs
    """
    if not driver:
        print("❌ Invalid WebDriver provided, cannot fetch article links.")
        return []

    url = 'https://coin68.com/article'
    driver.get(url)
    time.sleep(3)

    article_links = []
    current_count = 0
    page_count = 1

    try:
        while current_count < target_count:
            div_elements = driver.find_elements(By.CLASS_NAME, "MuiBox-root.css-3pvgyr")
            
            if page_count == 1 or len(div_elements) > 0:
                print(f"📄 Page {page_count}: Found {len(div_elements)} articles", end="\r", flush=True)

            for div_element in div_elements:
                link = div_element.find_element(By.TAG_NAME, 'a')
                href = link.get_attribute('href')
                article_links.append(href)

                current_count += 1
                if current_count >= target_count:
                    break

            if current_count >= target_count:
                break

            try:
                page_count += 1
                clickable = click(driver, page_count)
                    
                if not clickable:
                    skip(driver)
                    click(driver, page_count)

            except Exception as e:
                print(f"❌ Navigation error: {e}")
                break
                
    except Exception as e:
        print(f"❌ Error while fetching links: {e}")

    print(f"✅ Successfully fetched {len(article_links)} article links")
    return article_links