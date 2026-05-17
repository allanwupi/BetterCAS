from datetime import date, datetime, UTC, timedelta
from unittest import TestCase
from flask import url_for
from sqlalchemy import TIME
from app import create_app, db
from app.config import TestConfig
from app.models import User, Friendship, Event, create_test_data
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from werkzeug.serving import make_server
import threading
import os
import time

localHost = "http://127.0.0.1:5000/"

# Choose a reasonable timeout for waiting for elements to appear on the page during Selenium tests
TIMEOUT_SECONDS = 10


class ServerThread(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True)
        self.server = make_server("127.0.0.1", 5000, app)

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


class WebpageActions:
    def __init__(self, driver):
        self.driver = driver
    
    def login(self, identifier="testuser", password="thisisatestpassword"):
        self.driver.get(localHost)
        identifier_input = self.driver.find_element(By.ID, "identifier")
        password_input = self.driver.find_element(By.ID, "password")
        submit_button = self.driver.find_element(By.ID, "submit")
        identifier_input.send_keys(identifier)
        password_input.send_keys(password)
        self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
        submit_button.click()
        WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.ID, "calendar"))
        )
        return self
    
    def logout(self):
        self.driver.find_element(By.ID, "logout").click()
        return self
    
    def navigate_to_calendar(self):
        self.driver.find_element(By.ID, "calendarLink").click()
        return self
    
    def navigate_to_todo(self):
        self.driver.find_element(By.ID, "todoLink").click()
        return self
    
    def navigate_to_friends(self):
        self.driver.find_element(By.ID, "friendsLink").click()
        return self
    
    def navigate_to_import(self):
        self.driver.find_element(By.ID, "importLink").click()
        return self

    def create_calendar_event(self, title, start=None, end=None, location="", description=""):
        self.driver.find_element(By.ID, "openEventModalBtn").click()
        if start is None:
            start = datetime.now(UTC)
        if end is None:
            end = start + timedelta(hours=1)
        title_input = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.ID, "eventTitle"))
        )
        start_time_input = self.driver.find_element(By.ID, "eventStart")
        end_time_input = self.driver.find_element(By.ID, "eventEnd")
        event_location_input = self.driver.find_element(By.ID, "eventLocation")
        event_description_input = self.driver.find_element(By.ID, "eventDescription")
        save_event_button = self.driver.find_element(By.ID, "saveEventBtn")

        title_input.send_keys(title)
        self.driver.execute_script(f"arguments[0].value = '{start.strftime('%Y-%m-%dT%H:%M:%S')}';", start_time_input)
        self.driver.execute_script(f"arguments[0].value = '{end.strftime('%Y-%m-%dT%H:%M:%S')}';", end_time_input)
        event_location_input.send_keys(location)
        event_description_input.send_keys(description)
        save_event_button.click()
        # Need to specify wait outside of function call (modal to disappear after saving event or alert to appear if there was an error)
        return self

    def create_todo_task(self, title, due_date=None):
        todo_title_input = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.ID, "todoInput"))
        )
        due_date_input = self.driver.find_element(By.ID, "todoDate")
        add_todo_button = self.driver.find_element(By.ID, "addTodoBtn")

        if due_date is None:
            due_date = datetime.now(UTC)

        todo_title_input.send_keys(title)
        self.driver.execute_script(f"arguments[0].value = '{due_date.strftime('%Y-%m-%dT%H:%M:%S')}';", due_date_input)
        add_todo_button.click()
        # Need to specify wait outside of function call (new task element to appear in list or alert to appear if there was an error)
        return self


class SeleniumTests(TestCase):
    def setUp(self):
        self.testApp =  create_app(TestConfig)
        self.app_context = self.testApp.app_context()
        self.app_context.push()
        db.create_all()
        create_test_data()

        self.server_thread = ServerThread(self.testApp)
        self.server_thread.start()

        options = webdriver.ChromeOptions()
        #options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        self.driver = webdriver.Chrome(options=options)
        return super().setUp()
    
    def tearDown(self):
        self.driver.quit()
        self.server_thread.shutdown()
        self.server_thread.join(timeout=5)

        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.app_context.pop()
        return super().tearDown()
    
    def test_valid_login(self):
        self.driver.get(localHost)
        identifier_input = self.driver.find_element(By.ID, "identifier")
        password_input = self.driver.find_element(By.ID, "password")
        submit_button = self.driver.find_element(By.ID, "submit")
        identifier_input.send_keys("testuser@example.com")
        password_input.send_keys("thisisatestpassword")
        self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
        submit_button.click()
        # successful login should redirect to calendar page, so we wait for an element on the calendar page to be present
        WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.ID, "calendar"))
        )
        self.assertIsNotNone(self.driver.find_element(By.ID, "calendar"), "Calendar element not found after successful login, expected to be on calendar page")
    
    def test_invalid_login(self):
        self.driver.get(localHost)
        identifier_input = self.driver.find_element(By.ID, "identifier")
        password_input = self.driver.find_element(By.ID, "password")
        submit_button = self.driver.find_element(By.ID, "submit")
        identifier_input.send_keys("invalid@example.com")
        password_input.send_keys("invalidpassword")

        self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
        submit_button.click()
        # invalid login should flash an error message
        alert_element = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.CLASS_NAME, "alert"))
        )
        self.assertIsNotNone(alert_element, "Alert message not found after invalid login")
        self.assertEqual(alert_element.text, "Invalid login details. Please try again.", "Alert message text does not match expected invalid login message")
    
    def test_navigation_links(self):
        # Tests that the sidebar navigation links work correctly and that the expected elements are present on each page after navigation
        webpage = WebpageActions(self.driver).login()
        WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.ID, "importLink"))
        )
        webpage.navigate_to_import()
        file_input_element = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.ID, "fileInput"))
        )
        self.assertIsNotNone(file_input_element, "File input not found after navigating to import page")
        webpage.navigate_to_friends()
        friends_element = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.ID, "friendSearchInput"))
        )
        self.assertIsNotNone(friends_element, "Friend search input not found after navigating to friends page")
        webpage.navigate_to_todo()
        todo_element = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.ID, "todoInput"))
        )
        self.assertIsNotNone(todo_element, "Todo input not found after navigating to todo page")
        webpage.navigate_to_calendar()
        calendar_element = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.ID, "calendar"))
        )
        self.assertIsNotNone(calendar_element, "Calendar element not found after navigating to calendar page")
        webpage.logout()
        WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.ID, "identifier"))
        )
        self.assertIsNotNone(self.driver.find_element(By.ID, "identifier"), "Identifier input not found after logout, expected to be on login page")

    def test_unauthenticated_access(self):
        self.driver.get(localHost + "calendar")
        # unauthenticated access should redirect to login page, so we wait for an element on the login page to be present
        WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.ID, "identifier"))
        )
        self.assertIsNotNone(self.driver.find_element(By.ID, "identifier"), "Identifier input not found after unauthenticated access, expected to be on login page")

    def test_create_and_delete_calendar_event(self):
        webpage = WebpageActions(self.driver).login()
        add_event_button = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.ID, "openEventModalBtn"))
        )
        add_event_button.click()
        title_input = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.ID, "eventTitle"))
        )
        self.assertIsNotNone(title_input, "Event title input not found in event creation modal")
        start_time_input = self.driver.find_element(By.ID, "eventStart")
        end_time_input = self.driver.find_element(By.ID, "eventEnd")
        event_location_input = self.driver.find_element(By.ID, "eventLocation")
        event_description_input = self.driver.find_element(By.ID, "eventDescription")
        save_event_button = self.driver.find_element(By.ID, "saveEventBtn")

        title_input.send_keys("Selenium Test Event")
        start = datetime.now(UTC)
        end = start + timedelta(hours=1)
        self.driver.execute_script(f"arguments[0].value = '{start.strftime('%Y-%m-%dT%H:%M:%S')}';", start_time_input)
        self.driver.execute_script(f"arguments[0].value = '{end.strftime('%Y-%m-%dT%H:%M:%S')}';", end_time_input)
        event_location_input.send_keys("Test Location")
        event_description_input.send_keys("Test Description")
        save_event_button.click()

        WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.invisibility_of_element_located((By.ID, "addEventModal"))
        )
        # Check that the database was updated with the new event
        created_event = Event.query.filter_by(title="Selenium Test Event").first()
        self.assertIsNotNone(created_event, "Created event not found in database")
        self.assertEqual(created_event.location, "Test Location", "Event location in database does not match expected value")
        self.assertEqual(created_event.description, "Test Description", "Event description in database does not match expected value")
        self.assertEqual(created_event.start.strftime("%Y-%m-%d %H:%M"), start.strftime("%Y-%m-%d %H:%M"), "Event start time in database does not match expected value")
        self.assertEqual(created_event.end.strftime("%Y-%m-%d %H:%M"), end.strftime("%Y-%m-%d %H:%M"), "Event end time in database does not match expected value")
        self.assertEqual(created_event.owner, "testuser@example.com", "Event owner email in database does not match expected value")

        # Attempt to delete the created event
        event_element = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'fc-event') and contains(., 'Selenium Test Event')]"))
        )
        event_element.click()
        delete_button = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.ID, "deleteEventBtn"))
        )
        delete_button.click()
        alert = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.alert_is_present()
        )
        self.assertEqual(alert.text, "Warning: this event is going to be deleted. Are you sure you want to continue?", f"Alert text does not match expected confirmation message when deleting event, got: {alert.text}")
        alert.accept()
        WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.invisibility_of_element_located((By.ID, "editEventModal"))
        )
        # Check that the database no longer contains the deleted event
        deleted_event = db.session.query(Event).filter_by(title="Selenium Test Event").first()
        self.assertIsNone(deleted_event, "Deleted event still found in database")
        # Check that the event element is no longer present on the calendar
        event_elements = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'fc-event') and contains(., 'Selenium Test Event')]")
        self.assertEqual(len(event_elements), 0, "Event element still found on calendar after deletion, expected it to be removed")

    def test_invalid_calendar_event(self):
        webpage = WebpageActions(self.driver).login()
        add_event_button = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.ID, "openEventModalBtn"))
        )
        add_event_button.click()
        title_input = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.ID, "eventTitle"))
        )
        self.assertIsNotNone(
            title_input,
            "Event title input not found in event creation modal"
        )
        start_time_input = self.driver.find_element(By.ID, "eventStart")
        end_time_input = self.driver.find_element(By.ID, "eventEnd")
        save_event_button = self.driver.find_element(By.ID, "saveEventBtn")

        self.driver.execute_script("arguments[0].value = '2026-12-31T22:00:00';", start_time_input)
        save_event_button.click()

        alert = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.alert_is_present()
        )
        self.assertEqual(alert.text, "Please enter the event title, start and end dates/times.", f"Alert text does not match expected error message for not specifying required fields for new event, got: {alert.text}")
        alert.accept()

        title_input.send_keys("Selenium Test Event")
        self.driver.execute_script("arguments[0].value = '2026-12-31T21:00:00';", end_time_input)
        save_event_button.click()

        alert = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.alert_is_present()
        )
        self.assertEqual(alert.text, "End date/time must be after the start date/time.", f"Alert text does not match expected error message after specifying invalid end date/time for new event, got: {alert.text}")
        alert.accept()

    def test_create_and_delete_todo_task(self):
        webpage = WebpageActions(self.driver).login("testuser2", "thisisanotherpassword")
        webpage.navigate_to_todo()
        webpage.create_todo_task(title="Selenium Test Task", due_date=datetime(2026, 12, 31, 22, 0, 0))
        WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.CLASS_NAME, "task-item"))
        )
        created_task = db.session.query(Event).filter_by(title="Selenium Test Task").first()
        self.assertIsNotNone(created_task, "Created todo task not found in database")
        self.assertTrue(created_task.isTask, "Created todo task in database does not have isTask set to True")
        self.assertEqual(created_task.title, "Selenium Test Task", "Created todo task in database does not have correct title")
        self.assertEqual(created_task.start.strftime("%Y-%m-%d %H:%M"), "2026-12-31 22:00", "Event start time in database does not match expected value")
        self.assertEqual(created_task.end.strftime("%Y-%m-%d %H:%M"), "2026-12-31 22:00", "Event end time in database does not match expected value")
        self.assertEqual(created_task.owner, "testuser2@example.com", "Task owner email in database does not match expected value")

        # Now attempt to delete the created task
        delete_button = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "delete-task"))
        )
        delete_button.click()
        WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "task-item"))
        )
        deleted_task = db.session.query(Event).filter_by(title="Selenium Test Task").first()
        self.assertIsNone(deleted_task, "Deleted todo task still found in database")

    def test_invalid_todo_task(self):
        webpage = WebpageActions(self.driver).login("testuser2", "thisisanotherpassword")
        webpage.navigate_to_todo()
        webpage.create_todo_task(title="", due_date=datetime(2026, 12, 31, 22, 0, 0))
        alert = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.alert_is_present()
        )
        self.assertEqual(
            alert.text,
            "Please enter a task.",
            f"Alert text does not match expected error message for creating todo task without title, got: {alert.text}"
        )
        alert.accept()
        webpage.navigate_to_todo()
        todo_title_input = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.ID, "todoInput"))
        )
        add_todo_button = self.driver.find_element(By.ID, "addTodoBtn")
        todo_title_input.send_keys('Task')
        add_todo_button.click()
        alert = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.alert_is_present()
        )
        self.assertEqual(
            alert.text,
            "Please set a due date.",
            f"Alert text does not match expected error message for creating todo task without due date, got: {alert.text}"
        )
        alert.accept()

    def test_update_todo_task(self):
        pass

    def test_create_friendship(self):
        pass

    def test_accept_friendship(self):
        pass

    def test_reject_friendship(self):
        pass

    def test_import_valid_ics_file(self):
        webpage = WebpageActions(self.driver).login().navigate_to_import()
        file_input = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.ID, "fileInput"))
        )

        file_path = os.path.abspath("tests/fixtures/testValid.ics")
        file_input.send_keys(file_path)

        self.driver.find_element(By.ID, "uploadBtn").click()

        alert = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.alert_is_present()
        )
        self.assertEqual(
            alert.text,
            "Successfully imported calendar!",
            f"Alert text does not match expected success message after importing valid ICS file, got: {alert.text}"
        )
        alert.accept()
        # Query the database to verify that the event from the ICS file was imported correctly
        imported_event = Event.query.filter_by(title="Test Event").first()
        self.assertIsNotNone(imported_event, "Imported event not found in database")

    def test_import_invalid_ics_frontend_rejection(self):
        webpage = WebpageActions(self.driver).login().navigate_to_import()
        file_input = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.ID, "fileInput"))
        )
        # ICS file contains no events
        file_path = os.path.abspath("tests/fixtures/testInvalidFrontendFail.ics")
        file_input.send_keys(file_path)

        self.driver.find_element(By.ID, "uploadBtn").click()
        alert = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.alert_is_present()
        )
        self.assertIn(
            "No events found in the .ics file",
            alert.text,
            f"Alert text does not match expected message for importing ICS file with no events, got: {alert.text}"
        )
        alert.accept()

    def test_export_valid_ics_file(self):
        download_dir = os.path.abspath("tests/downloads")

        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        # Shut down existing driver, need to set additional permissions for downloading
        self.driver.quit()
        new_options = webdriver.ChromeOptions()
        new_options.add_argument("--headless=new")
        new_options.add_argument("--window-size=1920,1080")
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        new_options.add_experimental_option("prefs", prefs)
        self.driver = webdriver.Chrome(options=new_options)

        webpage = WebpageActions(self.driver).login()
        
        WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.ID, "calendar"))
        )

        self.driver.get(localHost + "import")

        file_input = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.ID, "fileInput"))
        )

        file_path = os.path.abspath("tests/fixtures/testValid.ics")
        file_input.send_keys(file_path)

        self.driver.find_element(By.ID, "uploadBtn").click()

        alert = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.alert_is_present()
        )
        alert.accept()

        export_btn = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.ID, "exportBtn"))
        )
        export_btn.click()

        downloaded_file = None

        for _ in range(TIMEOUT_SECONDS):
            files = os.listdir(download_dir)
            ics_files = [f for f in files if f.endswith(".ics")]
            if ics_files:
                downloaded_file = os.path.join(download_dir, ics_files[0])
                break
            time.sleep(1)

        self.assertIsNotNone(downloaded_file, "No ICS file was downloaded after exporting a valid ICS file")
        
        with open(downloaded_file, "r", encoding="utf-8") as f:
            ics_data = f.read()

        self.assertIn("BEGIN:VCALENDAR", ics_data, "Exported ICS file does not contain BEGIN section")
        self.assertIn("END:VCALENDAR", ics_data, "Exported ICS file does not contain END section")
        self.assertIn("SUMMARY:Test Event", ics_data, "Exported ICS file does not contain Test Event")
        self.assertIn("UID:", ics_data, "Exported ICS file does not contain UID for Event")

    def test_export_empty_calendar_shows_error(self):
        webpage = WebpageActions(self.driver).login("testuser2", "thisisanotherpassword").navigate_to_import()
        # Test user 2 has no events
        export_btn = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.ID, "exportBtn"))
        )
        export_btn.click()
        alert = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.alert_is_present()
        )
        self.assertEqual(
            alert.text,
            "Error exporting calendar: No events to export",
            f"Alert text does not match expected error message for exporting empty calendar, got: {alert.text}"
        )
        alert.accept()
        
    def test_import_invalid_ics_backend_rejection(self):
        webpage = WebpageActions(self.driver).login().navigate_to_import()
        file_input = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.ID, "fileInput"))
        )
        # Path to INVALID ICS (dtstart not valid date)
        file_path = os.path.abspath("tests/fixtures/testInvalidBackendFail.ics")
        file_input.send_keys(file_path)
        self.driver.find_element(By.ID, "uploadBtn").click()

        alert = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.alert_is_present()
        )
        self.assertIn(
            "No valid events found in file",
            alert.text,
            f"Alert text does not match expected error message for no valid events in ICS file, got: {alert.text}"
        )
        alert.accept()

