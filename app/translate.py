import requests
from app import app


def translate(text, source_language, dest_language):
    """
    This function translates a given piece of text from a prespecified source 
    language to a prespecified destination language.

    It currently uses Microsoft's REST API for translations:

    See https://docs.microsoft.com/en-us/azure/cognitive-services/translator/tutorial-build-flask-app-translation-synthesis
    for Microsoft's documentation for the API.
    """

    if 'MS_TRANSLATOR_KEY' not in app.config or not \
        app.config['MS_TRANSLATOR_KEY']:
        return "Error: the translation service is not configured."

    base_url = 'https://api.cognitive.microsofttranslator.com'
    path = '/translate?api-version=3.0'
    params = '&from={}&to={}'.format(source_language, dest_language)
    constructed_url = base_url + path + params

    auth = {
        'Ocp-Apim-Subscription-Key': app.config['MS_TRANSLATOR_KEY'],
        'Ocp-Apim-Subscription-Region': 'global'
    }

    # more than one object can be passed to the API
    body = [{'text': text}]

    # make a post request to the API, and handle the response
    r = requests.post(constructed_url, headers=auth, json=body)
    if r.status_code != 200:
        return "Error: the translation service failed."
    else:
        return r.json()[0]['translations'][0]['text']
