import requests
import json

conv_id=None
def send_request(query,conv_id=None):
    url = "http://localhost:8000/query"

    headers = {
        "Content-Type": "application/json",
    }
    payload = json.dumps({
        "text": query
    })
    if conv_id:
        payload=json.dumps({
            "text": query,
            "conversation_id": conv_id
        })
    response = requests.post(url, headers=headers, data=payload)
    conv_id=response.json().get("conversation_id")
    return response.text


if __name__ == "__main__":
    try:
        print(send_request("create a calendar event at 2 pm ist tomorrow july 10 2025 for 1 hr title as party"))
        print(send_request("send good evening email to sri2014ram@gmail.com subject good evening body as good evening"))
    except :
        print("error")
