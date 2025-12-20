

MARKETS = {
    "metamask": {
        "title": "MetaMask Token 2025",
        "condition_id": "0x702e5d8f4b8e6b8e9b7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7",
        "question_id": "0x702e5d8f4b8e6b8e9b7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7",
        "tokens": {
            "yes": "101163575689611177694586697172798294092987709960375574777760542313937687808591",
            "no": "102949690272049881918816161009598998660276278148863115139226223419430092123884"
        },
        "clob_token_ids": {
            "yes": "101163575689611177694586697172798294092987709960375574777760542313937687808591",
            "no": "102949690272049881918816161009598998660276278148863115139226223419430092123884"
        },
        "emoji": "🦊",
        "polymarket_id": 604067,
        "opinion_id": 793
    },
    "base": {
        "title": "Base Token 2025",
        "condition_id": "0x03de82c50244e51820f56b682cd2227ce0d35fac94178275811034294a7d1e8b",
        "question_id": "0x03de82c50244e51820f56b682cd2227ce0d35fac94178275811034294a7d1e8b",
        "tokens": {
            "yes": "104771646709660831592727707032658923058293444911215259720234012315470229507167",
            "no": "91704486839398022652930625279905848372527977307744447009017770224967808697336"
        },
        "clob_token_ids": {
            "yes": "104771646709660831592727707032658923058293444911215259720234012315470229507167",
            "no": "91704486839398022652930625279905848372527977307744447009017770224967808697336"
        },
        "emoji": "🔵",
        "polymarket_id": 598930,
        "opinion_id": 1270
    }
}


def get_market(alias: str):
    
    return MARKETS.get(alias.lower())


def get_all_markets():
    
    return MARKETS


def is_market_ready(alias: str) -> bool:
    
    market = get_market(alias)
    if not market:
        return False
    
   
    if market['condition_id'] == 'TBD':
        return False
    if market['tokens']['yes'] == 'TBD':
        return False
    
    return True
