import os
import sys

from loguru import logger
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


def get_logger(name):
    # logger.remove()
    fmt = '<green>{time:YY/MM/DD HH:mm:ss}</> | <lvl>{level:7s}</> | <lvl>{message}</>'
    logger.add(
        'logs/' + name + '/{time:YY-MM-DD}.log', level='INFO', format=fmt,
        filter=lambda _: _['level'].name in ['INFO', 'WARNING'],
        rotation='00:00', encoding='UTF-8'
    )
    logger.add(
        'logs/' + name + '/{time:YY-MM-DD}-crash.log', level='ERROR', format=fmt,
        rotation='00:00', encoding='UTF-8'
    )
    logger.add(sys.stderr, format=fmt, level='INFO')
    return logger


# https://developers.google.com/calendar/api/quickstart/python
def get_service(logger):
    scopes = ['https://www.googleapis.com/auth/calendar']
    credentials = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        credentials = Credentials.from_authorized_user_file('token.json', scopes)
    # If there are no (valid) credentials available, let the user log in.
    if not credentials or not credentials.valid:
        logger.warning('Token - Invalid')
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', scopes)
            credentials = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(credentials.to_json())
        logger.info('Token - Refreshed')
    logger.info('Token - OK')
    return build('calendar', 'v3', credentials=credentials, cache_discovery=False)
