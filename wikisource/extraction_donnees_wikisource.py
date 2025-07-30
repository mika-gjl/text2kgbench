import requests
import mwparserfromhell

API_URL = "https://fr.wikisource.org/w/api.php"

def get_subpages(prefix):
    params = {
        "action": "query",
        "list": "allpages",
        "apprefix": prefix,
        "aplimit": "max",
        "format": "json"
    }
    response = requests.get(API_URL, params=params)
    data = response.json()
    pages = data['query']['allpages']
    return [page['title'] for page in pages]

def get_wikitext(title):
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": title,
        "rvprop": "content",
        "format": "json"
    }
    response = requests.get(API_URL, params=params)
    pages = response.json()['query']['pages']
    page = next(iter(pages.values()))
    content = page['revisions'][0]['*'] if 'revisions' in page else ''
    return content

def parse_text(wikitext):
    wikicode = mwparserfromhell.parse(wikitext)
    return wikicode.strip_code()

wikitext = get_wikitext("Page:Lazare_-_Dictionnaire_administratif_et_historique_des_rues_de_Paris_et_de_ses_monuments,_1844.djvu/176")
# text = parse_text(wikitext)
print(wikitext)
