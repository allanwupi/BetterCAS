from datetime import datetime, UTC, timedelta
from unittest import TestCase
from app import create_app, db
from app.config import TestConfig
from app.models import User, Friendship, FriendshipStatus, Event, create_test_data
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


# Helper functions for Selenium tests to wait for elements to be present or clickable before interacting with them
def wait_for_id(driver, element_id):
    return WebDriverWait(driver, TIMEOUT_SECONDS).until(EC.presence_of_element_located((By.ID, element_id)))

def wait_for_clickable_id(driver, element_id):
    return WebDriverWait(driver, TIMEOUT_SECONDS).until(EC.element_to_be_clickable((By.ID, element_id)))

def wait_for_alert(driver):
    return WebDriverWait(driver, TIMEOUT_SECONDS).until(EC.alert_is_present())


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
        identifier_input = wait_for_id(self.driver, "identifier")
        password_input = wait_for_id(self.driver, "login-password")
        submit_button = wait_for_clickable_id(self.driver, "login-submit")
        identifier_input.send_keys(identifier)
        password_input.send_keys(password)
        self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
        submit_button.click()
        return self

    def signup(self, email, username, password, confirm_password):
        self.driver.get(localHost)
        wait_for_clickable_id(self.driver, "signup-tab").click()
        email_input = wait_for_id(self.driver, "email")
        username_input = wait_for_id(self.driver, "username")
        password_input = wait_for_id(self.driver, "signup-password")
        confirm_password_input = wait_for_id(self.driver, "confirm-password")
        submit_button = wait_for_clickable_id(self.driver, "signup-submit")

        email_input.send_keys(email)
        username_input.send_keys(username)
        password_input.send_keys(password)
        confirm_password_input.send_keys(confirm_password)
        submit_button.click()
        return self
    
    def logout(self):
        wait_for_clickable_id(self.driver, "logout").click()
        return self
    
    def navigate_to_calendar(self):
        calendarLink = wait_for_clickable_id(self.driver, "calendarLink")
        calendarLink.click()
        return self
    
    def navigate_to_todo(self):
        todoLink = wait_for_clickable_id(self.driver, "todoLink")
        todoLink.click()
        return self
    
    def navigate_to_friends(self):
        friendsLink = wait_for_clickable_id(self.driver, "friendsLink")
        friendsLink.click()
        return self
    
    def navigate_to_import(self):
        importLink = wait_for_clickable_id(self.driver, "importLink")
        importLink.click()
        return self

    def create_calendar_event(self, title, start=None, end=None, location="", description=""):
        wait_for_clickable_id(self.driver, "openEventModalBtn").click()
        if start is None:
            start = datetime.now(UTC)
        if end is None:
            end = start + timedelta(hours=1)
        title_input = wait_for_clickable_id(self.driver, "eventTitle")
        start_time_input = wait_for_id(self.driver, "eventStart")
        end_time_input = wait_for_id(self.driver, "eventEnd")
        event_location_input = wait_for_id(self.driver, "eventLocation")
        event_description_input = wait_for_id(self.driver, "eventDescription")
        save_event_button = wait_for_clickable_id(self.driver, "saveEventBtn")

        title_input.send_keys(title)
        self.driver.execute_script(f"arguments[0].value = '{start.strftime('%Y-%m-%dT%H:%M:%S')}';", start_time_input)
        self.driver.execute_script(f"arguments[0].value = '{end.strftime('%Y-%m-%dT%H:%M:%S')}';", end_time_input)
        event_location_input.send_keys(location)
        event_description_input.send_keys(description)
        save_event_button.click()
        # Need to specify wait outside of function call (modal to disappear after saving event or alert to appear if there was an error)
        return self

    def create_todo_task(self, title, due_date=None):
        todo_title_input = wait_for_id(self.driver, "todoInput")
        due_date_input = wait_for_id(self.driver, "todoDate")
        add_todo_button = wait_for_clickable_id(self.driver, "addTodoBtn")

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
        options.add_argument("--headless=new")
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
        WebpageActions(self.driver).login(
            identifier="testuser@example.com",
            password="thisisatestpassword"
        )
        # successful login should redirect to calendar page, so we wait for an element on the calendar page to be present
        self.assertIsNotNone(wait_for_id(self.driver, "calendar"), "Calendar element not found after successful login, expected to be on calendar page")
    
    def test_invalid_login(self):
        WebpageActions(self.driver).login(
            identifier="testuser@example.com",
            password="thisisnottherightpassword"
        )
        # invalid login should flash an error message
        alert_element = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.CLASS_NAME, "alert"))
        )
        self.assertIsNotNone(alert_element, "Alert message not found after invalid login")
        self.assertEqual(alert_element.text, "Invalid login details. Please try again.", "Alert message text does not match expected invalid login message")

    def test_valid_signup(self):
        webpage = WebpageActions(self.driver).signup(
            email="testuser3@example.com",
            username="testuser3",
            password="testpassword",
            confirm_password="testpassword"
        )
        # successful signup should redirect to calendar page, so we wait for the calendar to be visible
        self.assertIsNotNone(wait_for_id(self.driver, "calendar"), "Calendar not found after successful signup, expected to be on calendar page")
    
    def test_invalid_signup_duplicate_usernames(self):
        webpage = WebpageActions(self.driver).signup(
            email="testuser3@example.com",
            username="testuser",
            password="testpassword",
            confirm_password="testpassword"
        )
        alert_element = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.CLASS_NAME, "alert"))
        )
        self.assertIsNotNone(alert_element, "Alert message not found after invalid signup")
        self.assertEqual(alert_element.text, "That username is already taken.", f"Alert message text does not match duplicate username message, got: {alert_element.text}")

    def test_invalid_signup_duplicate_emails(self):
        webpage = WebpageActions(self.driver).signup(
            email="testuser@example.com",
            username="testuser3",
            password="testpassword",
            confirm_password="testpassword"
        )
        # invalid signup should flash an error message
        alert_element = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.CLASS_NAME, "alert"))
        )
        self.assertIsNotNone(alert_element, "Alert message not found after invalid signup")
        self.assertEqual(alert_element.text, f"An account with that email already exists.", "Alert message text does not match duplicate email message, got: {alert_element.text}")

    def test_invalid_signup_mismatched_passwords(self):
        webpage = WebpageActions(self.driver).signup(
            email="testuser3@example.com",
            username="testuser3",
            password="testpassword",
            confirm_password="testpassword2"
        )
        alert_element = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.CLASS_NAME, "alert"))
        )
        self.assertIsNotNone(alert_element, "Alert message not found after invalid signup")
        self.assertEqual(alert_element.text, f"Passwords do not match.", "Alert message text does not match mismatched passwords message, got: {alert_element.text}")

    def test_navigation_links(self):
        # Tests that the sidebar navigation links work correctly and that the expected elements are present on each page after navigation
        webpage = WebpageActions(self.driver).login()
        webpage.navigate_to_import()
        file_input_element = wait_for_id(self.driver, "fileInput")
        self.assertIsNotNone(file_input_element, "File input not found after navigating to import page")
        webpage.navigate_to_friends()
        friends_element = wait_for_id(self.driver, "friendSearchInput")
        self.assertIsNotNone(friends_element, "Friend search input not found after navigating to friends page")
        webpage.navigate_to_todo()
        todo_element = wait_for_id(self.driver, "todoInput")
        self.assertIsNotNone(todo_element, "Todo input not found after navigating to todo page")
        webpage.navigate_to_calendar()
        calendar_element = wait_for_id(self.driver, "calendar")
        self.assertIsNotNone(calendar_element, "Calendar element not found after navigating to calendar page")
        webpage.logout()
        self.assertIsNotNone(wait_for_id(self.driver, "identifier"), "Identifier input not found after logout, expected to be on login page")

    def test_unauthenticated_access(self):
        self.driver.get(localHost + "calendar")
        # unauthenticated access should redirect to login page, so we wait for an element on the login page to be present
        self.assertIsNotNone(wait_for_id(self.driver, "identifier"), "Identifier input not found after unauthenticated access, expected to be on login page")

    def test_create_calendar_event(self):
        webpage = WebpageActions(self.driver).login()
        add_event_button = wait_for_clickable_id(self.driver, "openEventModalBtn")
        add_event_button.click()
        title_input = wait_for_clickable_id(self.driver, "eventTitle")
        self.assertIsNotNone(title_input, "Event title input not found in event creation modal")
        start_time_input = wait_for_id(self.driver, "eventStart")
        end_time_input = wait_for_id(self.driver, "eventEnd")
        event_location_input = wait_for_id(self.driver, "eventLocation")
        event_description_input = wait_for_id(self.driver, "eventDescription")
        save_event_button = wait_for_clickable_id(self.driver, "saveEventBtn")

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

    def test_delete_calendar_event(self):
        # Directly create an event in the database with the current date and time
        start = datetime.now(UTC)
        end = start + timedelta(hours=1)
        event_to_delete = Event(title="Selenium Test Event", start=start, end=end, owner="testuser@example.com")
        db.session.add(event_to_delete)
        db.session.commit()
        webpage = WebpageActions(self.driver).login().navigate_to_calendar()
        # Attempt to delete the created event
        event_element = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'fc-event') and contains(., 'Selenium Test Event')]"))
        )
        event_element.click()
        delete_button = wait_for_clickable_id(self.driver, "deleteEventBtn")
        delete_button.click()
        alert = wait_for_alert(self.driver)
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
        add_event_button = wait_for_clickable_id(self.driver, "openEventModalBtn")
        add_event_button.click()
        title_input = wait_for_clickable_id(self.driver, "eventTitle")
        
        self.assertIsNotNone(
            title_input,
            "Event title input not found in event creation modal"
        )
        start_time_input = wait_for_id(self.driver, "eventStart")
        end_time_input = wait_for_id(self.driver, "eventEnd")
        save_event_button = wait_for_clickable_id(self.driver, "saveEventBtn")

        self.driver.execute_script("arguments[0].value = '2026-12-31T22:00:00';", start_time_input)
        save_event_button.click()

        alert = wait_for_alert(self.driver)
        self.assertEqual(alert.text, "Please enter the event title, start and end dates/times.", f"Alert text does not match expected error message for not specifying required fields for new event, got: {alert.text}")
        alert.accept()

        title_input.send_keys("Selenium Test Event")
        self.driver.execute_script("arguments[0].value = '2026-12-31T21:00:00';", end_time_input)
        save_event_button.click()

        alert = wait_for_alert(self.driver)
        self.assertEqual(alert.text, "End date/time must be after the start date/time.", f"Alert text does not match expected error message after specifying invalid end date/time for new event, got: {alert.text}")
        alert.accept()

    def test_create_todo_task(self):
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

    def test_delete_todo_task(self):
        webpage = WebpageActions(self.driver).login("testuser", "thisisatestpassword").navigate_to_todo()
        # First event in list (chronological order) is "Assignment Due" which has status Completed. We will attempt to delete this task.
        filter_by_completed_button = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.XPATH, "//button[text()='Completed']"))
        )
        filter_by_completed_button.click() # Assignment Due is the only task with Completed status
        delete_button = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "delete-task"))
        )
        delete_button.click()
        WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "task-item"))
        )
        deleted_task = db.session.query(Event).filter_by(title="Assignment Due").first()
        self.assertIsNone(deleted_task, "Deleted todo task still found in database")

    def test_invalid_todo_task(self):
        webpage = WebpageActions(self.driver).login("testuser2", "thisisanotherpassword")
        webpage.navigate_to_todo()
        webpage.create_todo_task(title="", due_date=datetime(2026, 12, 31, 22, 0, 0))
        alert = wait_for_alert(self.driver)
        self.assertEqual(
            alert.text,
            "Please enter a task.",
            f"Alert text does not match expected error message for creating todo task without title, got: {alert.text}"
        )
        alert.accept()
        webpage.navigate_to_todo()
        todo_title_input = wait_for_clickable_id(self.driver, "todoInput")
        add_todo_button = wait_for_clickable_id(self.driver, "addTodoBtn")
        todo_title_input.send_keys('Task')
        add_todo_button.click()
        alert = wait_for_alert(self.driver)
        self.assertEqual(
            alert.text,
            "Please set a due date.",
            f"Alert text does not match expected error message for creating todo task without due date, got: {alert.text}"
        )
        alert.accept()

    def test_update_todo_task(self):
        webpage = WebpageActions(self.driver).login().navigate_to_todo()
        WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.CLASS_NAME, "task-item"))
        )
        dropdown_button = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "dropdown-toggle"))
        )
        # First event in list (chronological order) is "Assignment Due" which has status Completed.
        # We will change the status to "In Progress"
        dropdown_button.click()
        mark_in_progress_button = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "mark-in-progress"))
        )
        mark_in_progress_button.click()
        WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.text_to_be_present_in_element((By.CLASS_NAME, "task-status-badge"), "In Progress")
        )
        # Check that the database was updated with the new task status
        updated_task = Event.query.filter_by(title="Assignment Due").first()
        self.assertIsNotNone(updated_task, "Task to update not found in database")
        self.assertEqual(updated_task.taskStatus.value, "In Progress", "Task status in database does not match expected value after update")

    def test_create_friendship(self):
        webpage = WebpageActions(self.driver).login().navigate_to_friends()
        friend_search_input = wait_for_clickable_id(self.driver, "friendSearchInput")
        friend_search_input.send_keys("testuser2")
        add_friend_button = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "friends-small-btn"))
        )
        add_friend_button.click()
        # Wait for a friend row div to appear containing the details of test user 2
        outgoing_friend_request = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.XPATH, "//div[span[text()='@testuser2 (testuser2@example.com)']]"))
        )
        self.assertIsNotNone(outgoing_friend_request, "Outgoing friend request not found after sending friend request")
        # Check that the database contains a new friendship with the correct requester, receiver and status
        friendship = db.session.query(Friendship).filter_by(requester_email="testuser@example.com", receiver_email="testuser2@example.com").first()
        self.assertIsNotNone(friendship, "Friendship not found in database after sending friend request")
        self.assertEqual(friendship.status.value, "pending", f"Friendship status in database does not match 'pending' as expected after sending friend request, got {friendship.status.value}")

    def test_accept_friendship(self):
        # For this test we will directly create a pending friendship in the database and then accept it through the frontend
        pending_friendship = Friendship(requester_email="testuser@example.com", receiver_email="testuser2@example.com", status=FriendshipStatus.PENDING)
        db.session.add(pending_friendship)
        db.session.commit()
        webpage = WebpageActions(self.driver).login("testuser2", "thisisanotherpassword").navigate_to_friends()
        # Wait for a friend request row div to appear containing the details of test user 1
        incoming_friend_request = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.XPATH, "//div[span[text()='@testuser (testuser@example.com)']]"))
        )
        self.assertIsNotNone(incoming_friend_request, "Incoming friend request not found after sending friend request")

        accept_friend_button = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "friends-small-btn"))
        )
        accept_friend_button.click()
    
        # Wait until a button appears for the new friend indicating the request has been accepted
        WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.element_to_be_clickable((By.XPATH, "//button[text()='Select']"))
        )
        # Check that the database was updated with the new friendship status
        db.session.expire_all()  # Expire session to ensure we get the updated value from the database
        updated_friendship = db.session.query(Friendship).filter_by(requester_email="testuser@example.com", receiver_email="testuser2@example.com").first()
        self.assertIsNotNone(updated_friendship, "Friendship not found in database after accepting friend request")
        self.assertEqual(updated_friendship.status.value, "accepted", f"Friendship status in database does not match 'accepted' as expected after accepting friend request, got {updated_friendship.status.value}")

    def test_reject_friendship(self):
        # For this test we will directly create a pending friendship in the database and then reject it through the frontend to test that flow
        pending_friendship = Friendship(requester_email="testuser@example.com", receiver_email="testuser2@example.com", status=FriendshipStatus.PENDING)
        db.session.add(pending_friendship)
        db.session.commit()
        webpage = WebpageActions(self.driver).login("testuser2", "thisisanotherpassword").navigate_to_friends()
        # Wait for a friend request row div to appear containing the details of test user 1
        incoming_friend_request = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.XPATH, "//div[span[text()='@testuser (testuser@example.com)']]"))
        )
        self.assertIsNotNone(incoming_friend_request, "Incoming friend request not found after sending friend request")
        # Find the reject button for the incoming friend request and click it
        reject_friend_button = self.driver.find_element(By.CLASS_NAME, "friends-remove-btn")
        reject_friend_button.click()
        # Wait until the friend request is removed from the UI
        WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.staleness_of(incoming_friend_request)
        )
        # Check that the database was updated with the rejected friendship status
        db.session.expire_all()  # Expire session to ensure we get the updated value from the database
        updated_friendship = db.session.query(Friendship).filter_by(requester_email="testuser@example.com", receiver_email="testuser2@example.com").first()
        self.assertIsNotNone(updated_friendship, "Friendship not found in database after rejecting friend request")
        self.assertEqual(updated_friendship.status.value, "rejected", f"Friendship status in database does not match 'rejected' as expected after rejecting friend request, got {updated_friendship.status.value}") 
    
    def test_remove_friend(self):
        # For this test we will directly create an accepted friendship in the database and then remove it through the frontend to test that flow
        accepted_friendship = Friendship(requester_email="testuser@example.com", receiver_email="testuser2@example.com", status=FriendshipStatus.ACCEPTED)
        db.session.add(accepted_friendship)
        db.session.commit()
        webpage = WebpageActions(self.driver).login().navigate_to_friends()
        # Wait for a friend row div to appear containing the details
        friend_row = WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.presence_of_element_located((By.XPATH, "//div[span[text()='@testuser2 (testuser2@example.com)']]"))
        )
        # Find the remove friend button and click it
        remove_friend_button = friend_row.find_element(By.CLASS_NAME, "friends-remove-btn")
        remove_friend_button.click()
        alert = wait_for_alert(self.driver)
        self.assertEqual(alert.text, "Are you sure you want to remove this friend or request?", f"Alert text does not match expected confirmation message when removing friend, got: {alert.text}")
        alert.accept()
        # Wait until the friend is removed from the UI
        WebDriverWait(self.driver, TIMEOUT_SECONDS).until(
            EC.staleness_of(friend_row)
        )
        # Check that the database was updated and the friendship has been deleted
        db.session.expire_all()  # Expire session to ensure we get the updated value from the database
        updated_friendship = db.session.query(Friendship).filter_by(requester_email="testuser@example.com", receiver_email="testuser2@example.com").first()
        self.assertIsNone(updated_friendship, "Friendship found in database after removing friend")

    def test_import_valid_ics_file(self):
        webpage = WebpageActions(self.driver).login().navigate_to_import()
        file_input = wait_for_id(self.driver, "fileInput")
        file_path = os.path.abspath("tests/fixtures/testValid.ics")
        file_input.send_keys(file_path)
        wait_for_clickable_id(self.driver, "uploadBtn").click()

        alert = wait_for_alert(self.driver)
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
        file_input = wait_for_id(self.driver, "fileInput")
        # ICS file contains no events and should be rejected by frontend validation with an appropriate error message
        file_path = os.path.abspath("tests/fixtures/testInvalidFrontendFail.ics")
        file_input.send_keys(file_path)

        wait_for_clickable_id(self.driver, "uploadBtn").click()
        alert = wait_for_alert(self.driver)
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

        webpage = WebpageActions(self.driver).login().navigate_to_import()
        
        file_input = wait_for_id(self.driver, "fileInput")

        file_path = os.path.abspath("tests/fixtures/testValid.ics")
        file_input.send_keys(file_path)

        wait_for_clickable_id(self.driver, "uploadBtn").click()

        alert = wait_for_alert(self.driver)
        self.assertEqual(
            alert.text,
            "Successfully imported calendar!",
            f"Alert text does not match expected success message after importing valid ICS file, got: {alert.text}"
        )
        alert.accept()

        export_btn = wait_for_clickable_id(self.driver, "exportBtn")
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
        export_btn = wait_for_clickable_id(self.driver, "exportBtn")
        export_btn.click()
        alert = wait_for_alert(self.driver)
        self.assertEqual(
            alert.text,
            "Error exporting calendar: No events to export",
            f"Alert text does not match expected error message for exporting empty calendar, got: {alert.text}"
        )
        alert.accept()
        
    def test_import_invalid_ics_backend_rejection(self):
        webpage = WebpageActions(self.driver).login().navigate_to_import()
        file_input = wait_for_id(self.driver, "fileInput")
        # Path to INVALID ICS (dtstart not valid date)
        file_path = os.path.abspath("tests/fixtures/testInvalidBackendFail.ics")
        file_input.send_keys(file_path)
        wait_for_clickable_id(self.driver, "uploadBtn").click()

        alert = wait_for_alert(self.driver)
        self.assertIn(
            "No valid events found in file",
            alert.text,
            f"Alert text does not match expected error message for no valid events in ICS file, got: {alert.text}"
        )
        alert.accept()
