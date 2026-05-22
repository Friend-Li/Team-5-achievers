import requests
from msal import PublicClientApplication

# 🔑 REPLACE WITH YOUR VALUES
CLIENT_ID = "e265e314-7b13-4db6-8c47-02ebcae89ebf"
TENANT_ID = "5def4301-2f36-4c62-be6f-3a3f35782b26"

# Azure authority
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

# Permissions (delegated)
SCOPES = ["Mail.Read", "User.Read"]


# =========================
# GET TOKEN (DEVICE LOGIN)
# =========================
def get_token():
    app = PublicClientApplication(
        CLIENT_ID,
        authority=AUTHORITY
    )

    flow = app.initiate_device_flow(scopes=SCOPES)

    if "user_code" not in flow:
        print("❌ Failed to create device flow")
        print(flow)
        return None

    # 👉 VERY IMPORTANT MESSAGE
    print("\n👉 Follow this instruction:\n")
    print(flow["message"])   # shows correct login URL + code

    token = app.acquire_token_by_device_flow(flow)

    if "access_token" in token:
        print("\n✅ Token acquired successfully\n")
        return token["access_token"]
    else:
        print("\n❌ Token error:\n", token)
        return None


# =========================
# READ EMAILS FROM OUTLOOK
# =========================
def read_emails():
    token = get_token()

    if not token:
        print("❌ Cannot fetch emails (no token)")
        return

    headers = {
        "Authorization": f"Bearer {token}"
    }

    url = "https://graph.microsoft.com/v1.0/me/messages"

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()

        print("✅ Emails fetched successfully\n")

        emails = data.get("value", [])

        if not emails:
            print("⚠️ No emails found")
            return

        for i, msg in enumerate(emails[:5]):  # show first 5 emails
            subject = msg.get("subject")
            sender = msg.get("from", {}).get("emailAddress", {}).get("address")

            print(f"📩 Email {i+1}")
            print(f"From: {sender}")
            print(f"Subject: {subject}")
            print("-" * 40)

    else:
        print("❌ API Error:", response.status_code)
        print(response.text)


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    read_emails()