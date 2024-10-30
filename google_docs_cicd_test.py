import os
import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

# Authentication setup
SCOPES = ['https://www.googleapis.com/auth/documents']
DOCUMENT_ID = '1Lwhd7ZmVo19BmPdb73XgKj7EZmCimDS4wBnLwFdcCFY'

# Load credentials
creds = service_account.Credentials.from_service_account_file(
    'path/to/service_account.json', scopes=SCOPES)

service = build('docs', 'v1', credentials=creds)

def read_document():
    try:
        document = service.documents().get(documentId=DOCUMENT_ID).execute()
        print('The document title is: {}'.format(document.get('title')))
        return document
    except HttpError as err:
        print(err)

def append_text(text):
    try:
        requests = [
            {
                'insertText': {
                    'location': {
                        'index': 1,
                    },
                    'text': text
                }
            }
        ]
        result = service.documents().batchUpdate(documentId=DOCUMENT_ID, body={'requests': requests}).execute()
        print(f"Text appended: {text}")
    except HttpError as err:
        print(err)

def delete_text(start_index, end_index):
    try:
        requests = [
            {
                'deleteContentRange': {
                    'range': {
                        'startIndex': start_index,
                        'endIndex': end_index
                    }
                }
            }
        ]
        result = service.documents().batchUpdate(documentId=DOCUMENT_ID, body={'requests': requests}).execute()
        print(f"Text deleted from index {start_index} to {end_index}")
    except HttpError as err:
        print(err)

# Example usage
if __name__ == '__main__':
    # Read the document
    read_document()
    
    # Append new text
    append_text("\nĐÃ TỰ GHI, SỬA, XOÁ, ĐỌC\n")
    
    # Delete a range of text (example indices)
    delete_text(1, 15)

