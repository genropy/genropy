#!/usr/bin/env python
# encoding: utf-8


# FIXME: avoid using sys.argv but use argparse instead

import sys
import smtplib

description = "send an email"

from email.mime.text import MIMEText

def sendmail(host, from_address, to_address, subject, body, user='', password='', ssl=None):
    msg = MIMEText(body)

    if isinstance(to_address, str):
        to_address = [k.strip() for k in to_address.split(',')]
    msg['Subject'] = subject
    msg['From'] = from_address
    msg['To'] = ','.join(to_address)

    if ssl:
        port = 587
    else:
        port = 25

    s = smtplib.SMTP(host=host, port=port)
    s.set_debuglevel(1)
    s.ehlo()
    if ssl:
        s.starttls()
        s.ehlo()
    if user:
        s.login(user, password)
    s.sendmail(from_address, to_address, msg.as_string())
    s.quit()


def main():

    user = password = ssl = None
    if len(sys.argv) > 5:
        user = sys.argv[5]
    if len(sys.argv) > 6:
        password = sys.argv[6]
    if len(sys.argv) > 7:
        ssl = sys.argv[7]
    import os.path

    body = sys.stdin.read()
    body.split('\n')
    body = '\n'.join([f for f in body if not os.path.basename(f).startswith('.')])
    sendmail(host=sys.argv[1],
             from_address=sys.argv[2],
             to_address=sys.argv[3],
             subject=sys.argv[4],
             body=sys.stdin.read(),
             user=user,
             password=password,
             ssl=ssl
             )

if __name__ == '__main__':
    main()
