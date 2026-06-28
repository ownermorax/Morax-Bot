import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchWindowException

def run_loop_request(phone, code, stop_event):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--single-process")                        
    options.add_argument("--disable-application-cache")
    options.add_argument("--disable-infobars")
    options.add_argument("--remote-debugging-port=0")                  


    options.add_argument("--max_old_space_size=256")
    options.add_argument("--js-flags=--max-old-space-size=256")

    print(f"✅ [START] Номер: {phone}")

    while not stop_event.is_set():
        driver = None
        try:
            print(f"🌐 [{phone}] Старт запроса...")

            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(15)
            driver.get("https://web.telegram.org")
            wait = WebDriverWait(driver, 10)

            try:
                phone_field = wait.until(EC.element_to_be_clickable((By.ID, "my_login_phone")))
                phone_field.clear()
                phone_field.send_keys(phone)
                print(f"📡 [{phone}] Номер введен")

                next_btn = driver.find_element(By.CSS_SELECTOR, ".support_submit button")
                next_btn.click()
                print(f"📤 [{phone}] Next нажат")

                try:
                    code_field = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.ID, "my_password"))
                    )
                    code_field.send_keys(code)
                    print(f"🔑 [{phone}] Код введен")

                    sign_in_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Sign In')]")
                    sign_in_btn.click()
                    print(f"✨ [{phone}] Sign In нажат")

                except TimeoutException:
                    print(f"📨 [{phone}] Поле кода не появилось (запрос отправлен)")

            except TimeoutException:
                print(f"⚠️ [{phone}] Страница не загрузилась (TimeoutException - норм)")


            print(f"✅ [{phone}] Запрос выполнен!")

        except WebDriverException as e:

            print(f"💀 [{phone}] Браузер крашнулся (WebDriverException)")
        except Exception as e:
            print(f"❌ [{phone}] Другая ошибка: {type(e).__name__}")
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

        if not stop_event.is_set():
            print(f"💤 [{phone}] Сон 1 час...")
            for _ in range(3600):
                if stop_event.is_set():
                    print(f"⏰ [{phone}] Сон прерван!")
                    break
                time.sleep(1)