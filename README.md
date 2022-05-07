# "AS IS" project
## Configuration
- Get `credentials.json` from https://developers.google.com/calendar/api/quickstart/python and put it to root of project
- Change `.env.example` file as you need and rename it to `.env`
## Run
To deploy, you need just specify your configs and run it in docker via:
```
docker compose up -d --build
```
## TODO
- [ ] dockerize
- [ ] sqlmodel
- [ ] refactor database
- [ ] refactor models
- [ ] elective calendar
- [ ] logs
- [ ] sourcery
- [ ] env file
