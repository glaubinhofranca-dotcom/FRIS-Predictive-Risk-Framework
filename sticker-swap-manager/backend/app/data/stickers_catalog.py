SECTIONS = [
    {"id": "INTRO", "name": "Introdução", "emoji": "🏆", "color": "#FFD700",
     "stickers": list(range(1, 11))},
    {"id": "TROPHY", "name": "Troféu & História", "emoji": "🥇", "color": "#C0392B",
     "stickers": list(range(11, 21))},
    {"id": "STADIUMS", "name": "Estádios", "emoji": "🏟️", "color": "#2980B9",
     "stickers": list(range(21, 61))},
    {"id": "HOST", "name": "Cidades-Sede", "emoji": "🌎", "color": "#27AE60",
     "stickers": list(range(61, 81))},
    {"id": "GRA", "name": "Grupo A", "emoji": "🇦🇷", "color": "#75AADB",
     "stickers": list(range(81, 97))},
    {"id": "GRB", "name": "Grupo B", "emoji": "🇧🇷", "color": "#009C3B",
     "stickers": list(range(97, 113))},
    {"id": "GRC", "name": "Grupo C", "emoji": "🇺🇸", "color": "#B22234",
     "stickers": list(range(113, 129))},
    {"id": "GRD", "name": "Grupo D", "emoji": "🇲🇽", "color": "#006847",
     "stickers": list(range(129, 145))},
    {"id": "GRE", "name": "Grupo E", "emoji": "🇫🇷", "color": "#0055A4",
     "stickers": list(range(145, 161))},
    {"id": "GRF", "name": "Grupo F", "emoji": "🇩🇪", "color": "#000000",
     "stickers": list(range(161, 177))},
    {"id": "GRG", "name": "Grupo G", "emoji": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "color": "#CF142B",
     "stickers": list(range(177, 193))},
    {"id": "GRH", "name": "Grupo H", "emoji": "🇮🇹", "color": "#009246",
     "stickers": list(range(193, 209))},
    {"id": "GRI", "name": "Grupo I", "emoji": "🇲🇦", "color": "#C1272D",
     "stickers": list(range(209, 225))},
    {"id": "GRJ", "name": "Grupo J", "emoji": "🇸🇳", "color": "#00853F",
     "stickers": list(range(225, 241))},
    {"id": "GRK", "name": "Grupo K", "emoji": "🇯🇵", "color": "#BC002D",
     "stickers": list(range(241, 257))},
    {"id": "GRL", "name": "Grupo L", "emoji": "🇰🇷", "color": "#CD2E3A",
     "stickers": list(range(257, 273))},
    {"id": "GRM", "name": "Grupo M", "emoji": "🇨🇴", "color": "#FCD116",
     "stickers": list(range(273, 289))},
    {"id": "GRN", "name": "Grupo N", "emoji": "🇺🇾", "color": "#5EB6E4",
     "stickers": list(range(289, 305))},
    {"id": "GRO", "name": "Grupo O", "emoji": "🇵🇹", "color": "#006600",
     "stickers": list(range(305, 321))},
    {"id": "GRP", "name": "Grupo P", "emoji": "🇵🇱", "color": "#DC143C",
     "stickers": list(range(321, 337))},
    {"id": "STAR", "name": "Estrelas da Copa", "emoji": "⭐", "color": "#8E44AD",
     "stickers": list(range(337, 381))},
    {"id": "SPEC", "name": "Especiais Brilhantes", "emoji": "✨", "color": "#F39C12",
     "stickers": list(range(381, 421))},
    {"id": "GOALS", "name": "Grandes Gols Históricos", "emoji": "⚽", "color": "#16A085",
     "stickers": list(range(421, 451))},
    {"id": "LEGENDS", "name": "Lendas da Copa", "emoji": "🏅", "color": "#E74C3C",
     "stickers": list(range(451, 491))},
    {"id": "COACH", "name": "Técnicos", "emoji": "📋", "color": "#2C3E50",
     "stickers": list(range(491, 521))},
    {"id": "REFERE", "name": "Árbitros", "emoji": "🟨", "color": "#F1C40F",
     "stickers": list(range(521, 541))},
    {"id": "FINAL8", "name": "Oitavas & Quartas", "emoji": "🎯", "color": "#1ABC9C",
     "stickers": list(range(541, 591))},
    {"id": "SEMI", "name": "Semifinais", "emoji": "🎖️", "color": "#E67E22",
     "stickers": list(range(591, 631))},
    {"id": "FINALE", "name": "A Grande Final", "emoji": "🏆", "color": "#D4AF37",
     "stickers": list(range(631, 671))},
]

TEAM_NAMES = {
    "GRA": ["Argentina", "Chile", "Peru"],
    "GRB": ["Brasil", "Equador", "Paraguai"],
    "GRC": ["EUA", "Canadá", "Bahamas"],
    "GRD": ["México", "Jamaica", "Cuba"],
    "GRE": ["França", "Bélgica", "Portugal"],
    "GRF": ["Espanha", "Alemanha", "Países Baixos"],
    "GRG": ["Inglaterra", "País de Gales", "Escócia"],
    "GRH": ["Itália", "Croácia", "Ucrânia"],
    "GRI": ["Marrocos", "Senegal", "Camarões"],
    "GRJ": ["Egito", "Nigéria", "Argélia"],
    "GRK": ["Arábia Saudita", "Irã", "Catar"],
    "GRL": ["Japão", "Coreia do Sul", "Austrália"],
    "GRM": ["Colômbia", "Uruguai", "Bolívia"],
    "GRN": ["Costa Rica", "Honduras", "Panamá"],
    "GRO": ["Sérvia", "Suíça", "Áustria"],
    "GRP": ["Polônia", "Rep. Tcheca", "Eslováquia"],
}

STICKER_SUFFIXES = [
    "Emblema", "Goleiro", "Zagueiro 1", "Zagueiro 2", "Lateral D.",
    "Lateral E.", "Volante", "Meia 1", "Meia 2", "Atacante 1",
    "Atacante 2", "Capitão"
]


def get_sticker_info(number: int) -> dict:
    for section in SECTIONS:
        if number in section["stickers"]:
            section_id = section["id"]
            relative_pos = section["stickers"].index(number)

            if section_id.startswith("GR") and len(section_id) == 3:
                teams = TEAM_NAMES.get(section_id, ["Time A", "Time B", "Time C"])
                team_idx = relative_pos // (len(section["stickers"]) // 3)
                team_idx = min(team_idx, len(teams) - 1)
                team = teams[team_idx]
                suffix_idx = relative_pos % len(STICKER_SUFFIXES)
                suffix = STICKER_SUFFIXES[suffix_idx]
                name = f"{team} - {suffix}"
            elif section_id == "INTRO":
                names = ["Capa do Álbum", "Apresentação FIFA", "Mascote Oficial",
                         "Logo Copa 2026", "Bola Oficial", "Apresentação Panini",
                         "Índice A", "Índice B", "Patrocinadores", "Contra-capa"]
                name = names[relative_pos] if relative_pos < len(names) else f"Introdução #{relative_pos+1}"
            elif section_id == "TROPHY":
                names = ["Taça Jules Rimet", "Trophy FIFA 1974", "Medalha de Ouro",
                         "Pódio 2022", "Troféu de Prata", "Copa 1930", "Copa 1950",
                         "Copa 1970", "Copa 1990", "Copa 2006"]
                name = names[relative_pos] if relative_pos < len(names) else f"Troféu #{relative_pos+1}"
            elif section_id == "STADIUMS":
                stadiums = [
                    "MetLife Stadium - NY/NJ", "AT&T Stadium - Dallas", "SoFi Stadium - LA",
                    "Levi's Stadium - SF", "Arrowhead Stadium - KC", "Rose Bowl - Pasadena",
                    "Soldier Field - Chicago", "Gillette Stadium - Boston", "Lincoln FR - Philadelphia",
                    "NRG Stadium - Houston", "Hard Rock Stadium - Miami",
                    "BC Place - Vancouver", "BMO Field - Toronto", "Stade Saputo - Montreal",
                    "Estadio Azteca - CDMX", "Estadio Akron - GDL", "Estadio BBVA - MTY"
                ]
                idx = relative_pos // 3
                sub = ["Exterior", "Interior", "Panorâmica"][relative_pos % 3]
                name = f"{stadiums[idx]} ({sub})" if idx < len(stadiums) else f"Estádio #{relative_pos+1}"
            elif section_id == "HOST":
                cities = ["Nova York", "Dallas", "Los Angeles", "São Francisco",
                          "Kansas City", "Seattle", "Chicago", "Boston",
                          "Philadelphia", "Houston", "Miami",
                          "Vancouver", "Toronto", "Montreal",
                          "Cidade do México", "Guadalajara", "Monterrey"]
                name = cities[relative_pos] if relative_pos < len(cities) else f"Cidade #{relative_pos+1}"
            else:
                name = f"{section['name']} #{number - section['stickers'][0] + 1}"

            return {
                "number": number,
                "name": name,
                "section": section["name"],
                "section_id": section_id,
                "section_color": section["color"],
                "section_emoji": section["emoji"],
            }
    return {"number": number, "name": f"Figurinha #{number}", "section": "Desconhecido",
            "section_id": "UNK", "section_color": "#888", "section_emoji": "❓"}


def get_all_stickers() -> list:
    return [get_sticker_info(n) for n in range(1, 671)]
