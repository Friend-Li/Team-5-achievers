from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time

# ✅ WAIT IMPORTS
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ✅ DATA
INSTRUCTORS = ["Sac", "John Smith"]
GROUPS = ["BLS", "ACLS", "PALS"]


# =========================
# LOGIN
# =========================
def login_aha():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    driver.get("https://atlas.heart.org/")
    time.sleep(5)

    try:
        driver.find_element(By.ID, "username").send_keys("Sacstatecpr@outlook.com")
        driver.find_element(By.ID, "password").send_keys("ssCPR123*")
        driver.find_element(By.ID, "login").click()

        print("✅ Logged into AHA")

    except Exception as e:
        print("❌ Login failed:", e)

    time.sleep(8)
    return driver


# =========================
# NAVIGATION (VERY STABLE)
# =========================
def navigate_to_students_page(driver):
    wait = WebDriverWait(driver, 30)

    try:
        print("➡️ Waiting for dashboard...")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(5)

        print("➡️ Finding Classes menu...")

        # Try multiple selectors
        try:
            classes = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//span[contains(text(),'Classes')]")))
        except:
            classes = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(text(),'Classes')]")))

        driver.execute_script("arguments[0].click();", classes)
        print("✅ Clicked Classes")

        time.sleep(4)

        print("➡️ Finding My Classes...")

        try:
            my_classes = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//span[contains(text(),'My Classes')]")))
        except:
            my_classes = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(text(),'My Classes')]")))

        driver.execute_script("arguments[0].click();", my_classes)
        print("✅ Clicked My Classes")

        time.sleep(5)

        print("➡️ Finding class rows...")

        rows = driver.find_elements(By.XPATH, "//tbody/tr")

        print(f"🔍 Rows found: {len(rows)}")

        if len(rows) == 0:
            print("❌ No classes found")
            return

        driver.execute_script("arguments[0].click();", rows[0])
        print("✅ Opened first class")

        time.sleep(6)

        print("➡️ On student page")
        print(f"👨‍🏫 Instructor: {INSTRUCTORS[0]}")
        print(f"📘 Group: {GROUPS[0]}")

    except Exception as e:
        print("❌ NAVIGATION ERROR:", e)


# =========================
# ACCEPT STUDENTS (STABLE)
# =========================
def accept_students(driver):
    try:
        print("➡️ Searching for buttons...")

        time.sleep(5)

        all_buttons = driver.find_elements(By.XPATH, "//button")

        print(f"🔍 Total buttons: {len(all_buttons)}")

        valid_buttons = []

        for b in all_buttons:
            try:
                text = b.text.strip().lower()
                if "accept" in text or "approve" in text or "confirm" in text:
                    valid_buttons.append(b)
            except:
                pass

        print(f"✅ Accept buttons found: {len(valid_buttons)}")

        if len(valid_buttons) == 0:
            print("⚠️ No students to accept")
            return

        for i, btn in enumerate(valid_buttons):
            try:
                driver.execute_script("arguments[0].scrollIntoView();", btn)
                time.sleep(1)

                driver.execute_script("arguments[0].click();", btn)

                instructor = INSTRUCTORS[i % len(INSTRUCTORS)]
                group = GROUPS[i % len(GROUPS)]

                print(f"✅ Accepted → Instructor: {instructor}, Group: {group}")

                time.sleep(2)

            except Exception as e:
                print("⚠️ Click failed:", e)

    except Exception as e:
        print("❌ ACCEPT ERROR:", e)


# =========================
# MAIN
# =========================
def main():
    driver = login_aha()

    navigate_to_students_page(driver)

    print("👉 Navigation complete")
    time.sleep(3)

    accept_students(driver)

    print("🎯 Done accepting students")

    input("Press Enter to close browser...")
    driver.quit()


if __name__ == "__main__":
    main()