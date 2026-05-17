# MyCal

## Description
A web app developed for the CITS3403 Agile Web Development group project. This is a calendar and task reminder tool for university assignments and studying, featuring:
- Calendar
- To-do list
- View availability of friends
- Import and export calendars

## List of Group Members
| UWA ID   | Name               | GitHub Username |
|----------|--------------------|-----------------|
| 23810308 | Allan Wu           | allanwupi       |
| 24272225 | Audrey Mills       | Rangarade       |
| 24367195 | Hongshen Zheng     | hz7443          |
| 24227546 | Tashan Kirubagaran | tashan-kiru     |

## Instructions

### Launching the App
Install dependencies:

```bash
pip install -r requirements.txt
```

Set a secret key environment variable:
```bash
export MYCAL_SECRET_KEY="your-secret-key-here"
```

In Windows Powershell, run this instead:
```powershell
$Env:MYCAL_SECRET_KEY="your-secret-key-here"
```

Initalise/update database tables:

```bash
flask --app mycal db upgrade
```

Run the app:

```bash
flask --app mycal run
```

Then open the local Flask URL:

```text
http://127.0.0.1:5000/
```

### Tests
Run unit tests:

```bash
python -m unittest tests.unit_tests -v
```

Run Selenium tests:

```bash
python -m unittest tests.selenium_tests -v
```
