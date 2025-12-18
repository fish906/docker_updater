import smtplib
import ssl
from email.message import EmailMessage
import logging
import os
import requests 
import pymsteams # type: ignore
from slack_sdk import WebClient # type: ignore
from slack_sdk.errors import SlackApiError  # type: ignore
from telegram import Bot # type: ignore

logging.basicConfig(
    level=logging.INFO,
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
        'email': False,
        'ntfy': False,
        'gotify': False,
        'teams': False,
        'slack': False,
        'telegram': False,
        'signal': False
    }

    return notification_config

def notification_mail(message):
    port = 465
    smptp_server_url = 'mail.example.com'
    mail_address = 'sender@example.com'
    smtp_password = 'password'
    mail_reciever = 'reciever@example.com'

    msg = EmailMessage()
    msg['Subject'] = 'Docker Updater Notification'
    msg['From'] = mail_address
    msg['To'] = mail_reciever
    msg.set_content(message)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smptp_server_url, port, context=context) as server:
            server.login(mail_address, smtp_password)
            server.send_message(msg)

        logger.info('Notification sent successfully via email!')

    except Exception as e:
        logger.info(f'Error occured: {e}')

    return

def notification_ntfy(message):
    ntfy_url = 'your-ntfy-url'

    try:
        r = requests.post(
            ntfy_url,
            data=message['body'],
            headers={
                'Title': message['title'],
                'Priority': "default" # Priority levels: min, low, default, high, urgent
            }
        )

        logger.info(f'Ntfy http status code: {r.status_code}')
        logger.info('Notification sent to ntfy!')

    except Exception as e:
        logger.info(f'Error occured: {e}')

    return 

def notification_gotify(message):
    gotify_apptoken = 'test_token'
    gotify_url = "gotify.exaple.com"
    gotify_url_final = f'https://{gotify_url}/message?token={gotify_apptoken}'

    try:
        requests.post(gotify_url_final,
            json= {
                "message": message['body'],
                "priority": 1, # Options from 0 to 10
                "title": message['title']
        })

        logger.info('Notification sent to gotify!')

    except Exception as e:
        logger.info(f'Error occured: {e}')

    return

def notfication_teams(message):
    try:
        teams_notification = pymsteams.connectorcard("MS Teams Webhook URL")
        teams_notification.text(message['body'])
        teams_notification.title(message['title'])
        teams_notification.send()

        logger.info('Notification sent to MS Teams!')

    except Exception as e:
        logger.info(f'Error occured: {e}')


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
    result = "4 Containers updated!"
    dict_message = turn_message_into_dict(result)

    if notification_setup()['email']:
        notification_mail(dict_message)

    if notification_setup()['ntfy']:
        notification_ntfy(dict_message)

    if notification_setup()['gotify']:
        notification_ntfy(dict_message)

    if notification_setup()['teams']:
        notification_ntfy(dict_message)

    if notification_setup()['slack']:
        notification_slack(dict_message)

    #if notification_setup()['telegram']:
    #    notification_slack(dict_message)

    #if notification_setup()['signal']:
    #    notification_slack(dict_message)