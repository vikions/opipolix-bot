

MARKETS = {
    "metamask": {
        "title": "MetaMask Token by June 30",
        "condition_id": "0x44878f202dd18a286de9235acec372e9e6e6ca2b28d269c4138fc2604c9b78a9",
        "question_id": "0x44878f202dd18a286de9235acec372e9e6e6ca2b28d269c4138fc2604c9b78a9",
        "tokens": {
            "yes": "110325437323003864440364193681628128179433892752231328064623776035311134623682",
            "no": "77680902575693269510705775150133261883431641996305813878639196300490247886068"
        },
        "clob_token_ids": {
            "yes": "110325437323003864440364193681628128179433892752231328064623776035311134623682",
            "no": "77680902575693269510705775150133261883431641996305813878639196300490247886068"
        },
        "emoji": "🦊",
        "polymarket_id": 604067,
        "opinion_id": 793,
        "slug": "will-metamask-launch-a-token-by-june-30"
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
    },
    "abstract": {
        "title": "Abstract Token by Dec 31, 2026",
        "condition_id": "0xd008c45c5320e7453b4e7725bda285cd822a3a61adef14759f2aadf0778c64b6",
        "question_id": "0xd008c45c5320e7453b4e7725bda285cd822a3a61adef14759f2aadf0778c64b6",
        "tokens": {
            "yes": "105292534464588119413823901919588224897612305776681795693919323419047416388812",
            "no": "98646985707839121837958202212263078387820716702786874164268337295747851893706"
        },
        "clob_token_ids": {
            "yes": "105292534464588119413823901919588224897612305776681795693919323419047416388812",
            "no": "98646985707839121837958202212263078387820716702786874164268337295747851893706"
        },
        "emoji": "🎨",
        "polymarket_id": 718188,
        "slug": "will-abstract-launch-a-token-by-december-31-2026"
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
