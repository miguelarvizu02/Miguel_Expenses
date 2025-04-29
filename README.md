# Banamex Email Transaction Extractor

This script extracts transaction data from Banamex notification emails and exports it to a CSV file.

## Features

- Authenticates with Gmail API using OAuth 2.0
- Searches for emails from notificaciones@banamex.com with subject containing "Retiro/Compra"
- Only retrieves emails from the current year to avoid overloading
- Extracts structured data:
  - Monto (Amount)
  - Establecimiento (Establishment)
  - Fecha y hora (Date and time)
  - Estatus (Status)
  - Exitoso (Successful)
  - No. Autorizacion (Authorization number)
- Exports data to a CSV file

## Setup

1. Ensure you have Python 3.6+ installed
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Place your Google API credentials in `secrets/credentials.json`
   - If you don't have credentials, create them in the [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the Gmail API for your project
   - Create OAuth 2.0 credentials for a desktop application

## Usage

Run the script:
```
python main.py
```

The first time you run the script, it will open a browser window for you to authenticate with your Google account. After authentication, a token will be saved in `secrets/token.json` for future use.

The script will search for emails, extract transaction data, and save it to a CSV file named `banamex_transactions_YYYYMMDD_HHMMSS.csv` in the current directory.

## Notes

- The script requires internet access to connect to the Gmail API
- You must grant the script permission to read your Gmail messages
- The extraction patterns are designed for Banamex notification emails and may need adjustment if the email format changes
- The script only retrieves emails from the current year to improve performance and avoid processing too many messages
