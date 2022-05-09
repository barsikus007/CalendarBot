# University calendar parser and updater script
## Configuration
- Get `credentials.json` from https://developers.google.com/calendar/api/quickstart/python and put it to root of project
- Change `.env.example` file as you need and rename it to `.env`
## Run
To deploy, you need just specify your configs and run it in docker via:
```bash
docker compose up -d --build
docker exec $(docker ps -aqf "name=calendarbot-calendar") python3 ./create_db.py
```
## Frontend
https://github.com/barsikus007/xalendar
## TODO
- [ ] logo generator
- [ ] refactor database
- [ ] refactor models
- [ ] elective calendar
- [ ] logs
