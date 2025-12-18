import smtplib
import ssl
from email.message import EmailMessage
import logging
import os
import requests 
from dotenv import load_dotenv # type: ignore
import pymsteams # type: ignore
from slack_sdk import WebClient # type: ignore
from slack_sdk.errors import SlackApiError  # type: ignore

load_dotenv()

logging.basicConfig(
    level= os.getenv("LOG_LEVEL", "INFO").upper(),
    datefmt= '%Y/%m/%d %H:%M:%S',
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def turn_message_into_dict(message):
    dict_message = {
        'title': 'Watchless Notification',
        'body': message
    }
    return dict_message

def notification_setup():
    notification_config = {
        'email': os.getenv("EMAIL_NOTIFICATION", default= False),
        'ntfy': os.getenv("NTFY_NOTIFICATION", default= False),
        'gotify': os.getenv("GOTIFY_NOTIFICATION", default= False),
        'teams': os.getenv("MSTEAMS_NOTIFICATION", default= False),
        'slack': os.getenv("SLACK_NOTIFICATION", default= False),
        'telegram': False,
        'signal': False
    }

    return notification_config

def notification_mail(message):
    port = 465
    smptp_server_url = os.getenv("SMTP_SERVER_URL")
    mail_address = os.getenv("MAIL_SENDER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    mail_reciever = os.getenv("MAIL_RECIEVER")

    msg = EmailMessage()
    msg['Subject'] = 'Docker Updater Notification'
    msg['From'] = mail_address
    msg['To'] = mail_reciever
    msg.set_content(message['body'])

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smptp_server_url, port, context=context) as server:
            server.login(mail_address, smtp_password)
            server.send_message(msg)

        logger.info('Notification sent successfully via email!')

    except Exception as e:
        logger.info(f'Mail: Error occured: {e}')

    return

def notification_ntfy(message):
    ntfy_url = os.getenv("NTFY_URL")

    if ntfy_url:
        logger.debug("ntfy url has been provided")

    else:
        logger.error("No url has been provided for ntfy!")

    try:
        r = requests.post(
            ntfy_url,
            data=message['body'],
            headers={
                'Title': message['title'],
                'Priority': os.getenv("NTFY_PRIORITY_LEVEL") # Priority levels: min, low, default, high, urgent
            }
        )

        logger.info('Notification sent to ntfy!')

    except Exception as e:
        logger.error(f'Ntfy: Error occured: {e}')

    return 

def notification_gotify(message):
    gotify_apptoken = os.getenv("GOTIFY_APPTOKEN")
    gotify_url = os.getenv("GOTIFY_URL")
    gotify_url_final = f'https://{gotify_url}/message?token={gotify_apptoken}'

    try:
        requests.post(gotify_url_final,
            json= {
                "message": message['body'],
                "priority": os.getenv("GOTIFY_PRIORITY_LEVEL", default=2), # Options from 0 to 10
                "title": message['title']
        })

        logger.info('Notification sent to gotify!')

    except Exception as e:
        logger.info(f'Gotify: Error occured: {e}')

    return

def notfication_teams(message):
    msteams_webhook_url = os.getenv("MSTEAMS_URL")

    try:
        teams_notification = pymsteams.connectorcard(msteams_webhook_url)
        teams_notification.text(message['body'])
        teams_notification.title(message['title'])
        teams_notification.send()

        logger.info('Notification sent to MS Teams!')

    except Exception as e:
        logger.info(f'TEAMS: Error occured: {e}')


    return

def notification_slack(message):
    client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
    channel_id = os.getenv("SLACK_CHANNEL_NAME")

    try:
        result = client.chat_postMessage(
            channel=channel_id,
            text = message['body']
        )

        logger.debug(result)

    except SlackApiError as e:
        logger.error(f'Error while sending Slack notification: {e}')

    return

def notification_telegram(message):
    return

def notificaion_signal(message):
    return


if __name__ == '__main__':
    setup = notification_setup()
    result = "4 Containers updated!"
    dict_message = turn_message_into_dict(result)

    if setup['email'].lower() == 'true':
        notification_mail(dict_message)

    if setup['ntfy'].lower() == 'true':
        notification_ntfy(dict_message)

    if setup['gotify'].lower == 'true':
        notification_gotify(dict_message)

    if setup['teams'].lower() == 'true':
        notfication_teams(dict_message)

    if setup['slack'].lower() == 'true':
        notification_slack(dict_message)

    #if notification_setup()['telegram']:
    #    notification_telegram(dict_message)

    #if notification_setup()['signal']:
    #    notification_signal(dict_message)