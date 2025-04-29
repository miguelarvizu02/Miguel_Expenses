import os
import base64
import re
import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
import email
from bs4 import BeautifulSoup
import datetime

# Define the scopes required for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail():
    """Authenticate with Gmail API using OAuth 2.0 credentials."""
    creds = None
    token_path = 'secrets/token.json'

    # Check if token.json exists with stored credentials
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_info(
            json.loads(open(token_path).read()), SCOPES)

    # If credentials don't exist or are invalid, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'secrets/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for future use
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def search_emails(service, query):
    """Search for emails matching the query."""
    try:
        # Get list of messages matching the query
        result = service.users().messages().list(userId='me', q=query).execute()
        messages = result.get('messages', [])

        if not messages:
            print("No messages found.")
            return []

        print(f"Found {len(messages)} messages.")
        return messages
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []

def get_email_content(service, msg_id):
    """Get the content of an email by its ID."""
    try:
        # Get the message details
        message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

        # Get email payload
        payload = message['payload']
        headers = payload.get('headers', [])

        # Extract subject and date
        subject = ""
        date = ""
        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']
            if header['name'] == 'Date':
                date = header['value']

        # Get email body
        parts = payload.get('parts', [])
        body = ""

        if not parts:
            # If no parts, try to get body from payload directly
            if 'body' in payload and 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        else:
            # Process parts to find HTML or text content
            for part in parts:
                if part['mimeType'] == 'text/html':
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
                elif part['mimeType'] == 'text/plain':
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')

        return {
            'subject': subject,
            'date': date,
            'body': body
        }
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None

def extract_transaction_data(email_content):
    """Extract transaction data from email content."""
    # Parse HTML content
    soup = BeautifulSoup(email_content['body'], 'html.parser')

    # Initialize data dictionary
    data = {
        'Monto': None,
        'Establecimiento': None,
        'Fecha y hora': None,
        'Estatus': None,
        'Exitoso': None,
        'No. Autorizacion': None
    }

    # Extract text content
    text_content = soup.get_text()

    # Extract amount (Monto)
    amount_match = re.search(r'(?:Monto|Importe)[:\s]*\$?([\d,]+\.\d{2})', text_content)
    if amount_match:
        data['Monto'] = amount_match.group(1).replace(',', '')

    # Extract establishment (Establecimiento)
    establishment_match = re.search(r'(?:Establecimiento|Comercio)[:\s]*([\w\s]+)', text_content)
    if establishment_match:
        data['Establecimiento'] = establishment_match.group(1).strip()

    # Extract date and time (Fecha y hora)
    date_match = re.search(r'(?:Fecha|Fecha y hora)[:\s]*(\d{1,2}/\d{1,2}/\d{2,4}(?:\s+\d{1,2}:\d{1,2}(?::\d{1,2})?)?)', text_content)
    if date_match:
        data['Fecha y hora'] = date_match.group(1)
    else:
        # Try to parse from email date
        try:
            parsed_date = email.utils.parsedate_to_datetime(email_content['date'])
            data['Fecha y hora'] = parsed_date.strftime('%d/%m/%Y %H:%M:%S')
        except:
            pass

    # Extract status (Estatus)
    status_match = re.search(r'(?:Estatus|Estado)[:\s]*(\w+)', text_content)
    if status_match:
        data['Estatus'] = status_match.group(1)

    # Determine if successful (Exitoso)
    if 'aprobad' in text_content.lower() or 'exitoso' in text_content.lower():
        data['Exitoso'] = 'Sí'
    else:
        data['Exitoso'] = 'No'

    # Extract authorization number (No. Autorizacion)
    auth_match = re.search(r'(?:No\.\s*Autorizaci[oó]n|Autorizaci[oó]n)[:\s]*(\w+)', text_content)
    if auth_match:
        data['No. Autorizacion'] = auth_match.group(1)

    return data

def main():
    """Main function to process emails and extract transaction data."""
    # Authenticate with Gmail API
    service = authenticate_gmail()

    # Search for emails from notificaciones@banamex.com with subject containing "Retiro/Compra"
    # Only get emails from the current year to avoid overloading the script
    current_year = datetime.datetime.now().year
    query = f'from:notificaciones@banamex.com subject:"Retiro/Compra" after:{current_year}/01/01'
    messages = search_emails(service, query)

    # Process each email and extract data
    transaction_data = []
    for message in messages:
        email_content = get_email_content(service, message['id'])
        if email_content:
            data = extract_transaction_data(email_content)
            transaction_data.append(data)

    # Create pandas DataFrame
    if transaction_data:
        df = pd.DataFrame(transaction_data)

        # Export to CSV
        csv_filename = f'banamex_transactions_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        df.to_csv(csv_filename, index=False)
        print(f"Data exported to {csv_filename}")
    else:
        print("No transaction data found.")

if __name__ == '__main__':
    import json  # Import here to avoid circular import issues
    main()
