from pathlib import Path
from typing import Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
import smtplib
import os
from dotenv import load_dotenv
from pathlib import Path
from langchain.tools import tool

load_dotenv()
def is_in_extenstions(path: Path, extensions: list = None) -> bool:
    """
    Check if the path extension is in the list of extensions.

    Args:
        path (Path): The path to check.
        extensions (list): The list of extensions to check against.

    Returns:
        bool: True if the path extension is in the list of extensions, False otherwise.
    """
    supported_extensions = [".txt", ".csv", ".json", ".xml"]
    if extensions is None:
        extensions = supported_extensions
    if not isinstance(extensions, list):
        raise TypeError("extensions must be a list")
    if not isinstance(path, Path):
        raise TypeError("path must be a Path object")
    return path.suffix in extensions



@tool
def send_email_with_attachment(recipient: str, file_path: str) -> None:
    """
    Sends an email with an attachment using a Gmail account.

    Parameters:
    - recipient (str): The recipient's email address.
    - file_path (str): The file path of the attachment to be sent.
    """
    FROM_EMAIL = os.getenv("GMAIL_ACCOUNT")
    APP_PASSWORD = os.getenv("GOOGLE_APP_PASSWORD")
    try:
        # Create the email content
        msg = MIMEMultipart('mixed')
        msg['Subject'] = 'Test Email'
        msg['From'] = FROM_EMAIL
        msg['To'] = recipient

        # Attach the file
        with open(file_path, 'rb') as f:
            part = MIMEApplication(f.read())
            part.add_header('Content-Disposition', 'attachment', filename=Path(file_path).name)
            msg.attach(part)

        # Connect to Gmail SMTP server and send the email
        smtp = smtplib.SMTP('smtp.gmail.com', 587)
        smtp.ehlo()
        smtp.starttls()
        smtp.login(FROM_EMAIL, APP_PASSWORD)
        status = smtp.sendmail(FROM_EMAIL, recipient, msg.as_string())
        smtp.quit()

        if status == {}:
            return "Email sent successfully!"
        else:
            return f"Email sending failed: {status}"

    except Exception as e:
        return f"An error occurred while sending the email: {str(e)}"