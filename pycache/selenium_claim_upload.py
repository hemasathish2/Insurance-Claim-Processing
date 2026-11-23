"""Run Flask server first. Requires Chrome and Selenium installed."""
import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

url=os.environ.get('APP_URL','http://127.0.0.1:5001')
file=str((Path(__file__).parent/'samples'/'sample_document.txt').resolve())
driver=webdriver.Chrome()
try:
    driver.get(url+'/claims/new')
    driver.find_element(By.NAME,'claimant').send_keys('Selenium Demo')
    driver.find_element(By.NAME,'policy_number').send_keys('POL-SEL-01')
    driver.find_element(By.NAME,'incident_date').send_keys('11/05/2026')
    driver.find_element(By.NAME,'claim_amount').send_keys('2500')
    driver.find_element(By.NAME,'category').send_keys('Vehicle')
    driver.find_element(By.NAME,'document').send_keys(file)
    driver.find_element(By.CSS_SELECTOR,'button[type=submit]').click()
    WebDriverWait(driver,10).until(EC.url_contains('/claims/CLM-'))
    WebDriverWait(driver,10).until(EC.presence_of_element_located((By.CLASS_NAME,'pill')))
    assert 'SUBMITTED' in driver.page_source
    driver.save_screenshot('selenium_submission.png')
    print('PASS: submitted claim and screenshot saved to selenium_submission.png')
finally:driver.quit()
