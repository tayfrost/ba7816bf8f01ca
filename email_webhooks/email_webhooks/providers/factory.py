#from providers.outlook_provider import OutlookProvider
from providers.gmail_provider import GmailProvider

def get_provider(provider_name: str):
    providers = {
       # "outlook": OutlookProvider(),
        "gmail": GmailProvider(),
    }

    provider = providers.get(provider_name)
    if not provider:
        raise ValueError("Unsupported provider")

    return provider#
