import requests
import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from config import API_KEY_DIFFBOT

API_KEY = os.getenv("DIFFBOT_API_KEY", API_KEY_DIFFBOT)
BASE_URL = "https://api.diffbot.com/v3/article"

DELAY = 4
RETRY = 3
PAGE_LOAD_TIMEOUT = 30  # Default timeout in seconds

def update_article(driver, articles):
    print("🔍 Starting to fetch article content")

    successful_count = 0
    failed_count = 0
    timeout_count = 0

    for i, article in enumerate(articles):
        article_num = i + 1
        count = 0
        success = False 
        article['content'] = None

        try:
            # Set a page load timeout and handle it explicitly
            driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
            try:
                driver.get(article['url'])
            except TimeoutException:
                print(f"⏩ Skipping article {article_num}/{len(articles)}: Page load timeout (30s)")
                timeout_count += 1
                failed_count += 1
                continue
            except WebDriverException as e:
                print(f"⏩ Skipping article {article_num}/{len(articles)}: Browser error")
                failed_count += 1
                continue
                
            while count < RETRY and not success:
                try:
                    # Multiple XPath strategies
                    xpaths = [
                        "//h1[@class='post-title']//a[@rel='']",
                        "//h1[contains(@class, 'post-title')]//a",
                        "//a[contains(@class, 'post-title-link')]"
                    ]
                    
                    link = None
                    for xpath in xpaths:
                        try:
                            # Use a shorter timeout for finding elements (10s)
                            link = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.XPATH, xpath))
                            )
                            if link:
                                break
                        except TimeoutException:
                            continue
                    
                    if not link:
                        raise Exception("No matching link found")
                    
                    # Multiple click strategies
                    click_methods = [
                        lambda: link.click(),
                        lambda: driver.execute_script("arguments[0].click();", link),
                        lambda: driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click'));", link)
                    ]
                    
                    for method in click_methods:
                        try:
                            method()
                            break
                        except:
                            continue
                    
                    # Window handling
                    if len(driver.window_handles) > 1:
                        driver.switch_to.window(driver.window_handles[-1])
                    
                    article['url'] = driver.current_url
                    success = True

                except TimeoutException:
                    count += 1
                    if count == RETRY:
                        print(f"⏩ Skipping article {article_num}/{len(articles)}: Element search timeout")
                    time.sleep(2)
                except Exception as e:
                    count += 1
                    if count == RETRY:
                        print(f"⏩ Skipping article {article_num}/{len(articles)}: Navigation failed")
                    time.sleep(2)

            if not success: 
                article['url'] = None 
                failed_count += 1
            
            else:
                try:
                    params = {
                        'token': API_KEY, 
                        'url': article['url'],
                    }

                    response = requests.get(BASE_URL, params=params)

                    if response.status_code == 200:
                        data = response.json()

                        if "objects" in data and data["objects"]:
                            all_data = data["objects"][0]
                            article['content'] = str(all_data.get("text"))
                            successful_count += 1
                            print(f"✅ Article {article_num}/{len(articles)}: Content fetched successfully", end="\r", flush=True)
                        else:
                            failed_count += 1
                            print(f"⏩ Skipping article {article_num}/{len(articles)}: No content in API response")
                        
                    else:
                        failed_count += 1
                        print(f"⏩ Skipping article {article_num}/{len(articles)}: API error {response.status_code}")
                    
                except Exception as e:
                    failed_count += 1
                    print(f"⏩ Skipping article {article_num}/{len(articles)}: API error - {str(e)}")
                
                time.sleep(DELAY)
        
        except TimeoutException:
            failed_count += 1
            timeout_count += 1
            print(f"⏩ Skipping article {article_num}/{len(articles)}: Timeout error")
        except Exception as e:
            failed_count += 1
            print(f"⏩ Skipping article {article_num}/{len(articles)}: General error - {str(e)}")

    # Provide a summary with timeout statistics
    print(f"✅ Articles processed: {len(articles)} | Successful: {successful_count} | Failed: {failed_count} (Timeouts: {timeout_count})")
    
    # Provide recommendations if there were many timeouts
    if timeout_count > 0:
        print("\n⚠️ Timeout errors detected. Consider these solutions:")
        print("1. Increase the page load timeout in the code (currently 30s)")
        print("2. Check your internet connection speed")
        print("3. Reduce the number of concurrent browser operations")
        print("4. Add more delay between requests")