

MARKETS = {
    "metamask": {
        "title": "MetaMask Token by June 30",
        "condition_id": "0x44878f202dd18a286de9235acec372e9e6e6ca2b28d269c4138fc2604c9b78a9",
        "question_id": "345acac3f10334ee1a2b87ce7032353f51f65f7423c2f62f58fea99faada0568",
        "tokens": {
            "yes": "110325437323003864440364193681628128179433892752231328064623776035311134623682",
            "no": "77680902575693269510705775150133261883431641996305813878639196300490247886068"
        },
        "clob_token_ids": {
            "yes": "110325437323003864440364193681628128179433892752231328064623776035311134623682",
            "no": "77680902575693269510705775150133261883431641996305813878639196300490247886068"
        },
        "emoji": "\U0001F98A",
        "polymarket_id": 657287,
        "opinion_id": 2103,
        "slug": "will-metamask-launch-a-token-by-june-30"
    },
    "base": {
        "title": "Base Token by June 30, 2026",
        "condition_id": "0x9873d0448faebb53d0040a958b40bfd17960f57a164f69a36f2f400e945c36c1",
        "question_id": "5edaba7685a684795b662fbe3e13e8eaad28f3333c20462ee8efe415690fb467",
        "tokens": {
            "yes": "73916079699906389194973750600611907885736641148308464550611829122042479621960",
            "no": "111395431477341319990490806549685062184767317046913627686270380262287734089926"
        },
        "clob_token_ids": {
            "yes": "73916079699906389194973750600611907885736641148308464550611829122042479621960",
            "no": "111395431477341319990490806549685062184767317046913627686270380262287734089926"
        },
        "emoji": "🔵",
        "polymarket_id": 821172,
        "opinion_id": 2112,
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
    },
    "extended": {
        "title": "Extended Token by March 31, 2026",
        "condition_id": "0x9b6965c07fd3e8c163b52312c7d2d0a7ffff1baf9e652ae156b538898ac72396",
        "question_id": "0x9b6965c07fd3e8c163b52312c7d2d0a7ffff1baf9e652ae156b538898ac72396",
        "tokens": {
            "yes": "80202018619101908013933944100239367385491528832020028327612486898619283802751",
            "no": "33249883623946882498042187494418816609278977641116912274628462290026666786835"
        },
        "clob_token_ids": {
            "yes": "80202018619101908013933944100239367385491528832020028327612486898619283802751",
            "no": "33249883623946882498042187494418816609278977641116912274628462290026666786835"
        },
        "emoji": "🧬",
        "polymarket_id": 690612,
        "slug": "will-extended-launch-a-token-by-march-31-2026"
    },
    "opinion_fdv": {
        "title": "Opinion FDV above $1B one day after launch?",
        "condition_id": "0x170e907f54cd05c3f181067798610feb95f590d5d4be2bdda699c83249e2666e",
        "question_id": "0x170e907f54cd05c3f181067798610feb95f590d5d4be2bdda699c83249e2666e",
        "tokens": {
            "yes": "50352926775492572007129313229442771572343916931005903007424590093174311630298",
            "no": "24347171758774499938462633574721292772800062019156311729242237473590058137270"
        },
        "clob_token_ids": {
            "yes": "50352926775492572007129313229442771572343916931005903007424590093174311630298",
            "no": "24347171758774499938462633574721292772800062019156311729242237473590058137270"
        },
        "emoji": "FDV",
        "polymarket_id": 1068300,
        "slug": "opinion-fdv-above-1b-one-day-after-launch"
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
