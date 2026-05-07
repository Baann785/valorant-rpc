import iso8601
from ..utilities.logging import Logger 
from ..localization.localization import Localizer
from ..webserver import server
debug = Logger.debug

class Utilities:
    @staticmethod
    def resolve_rpc_image(image):
        if not isinstance(image, str):
            return None

        image = image.strip()
        if image.lower().startswith(("https://", "http://")):
            return image

        return None

    @staticmethod 
    def build_party_state(data):
        party_state = Localizer.get_localized_text("presences","party_states","solo")
        party_size_val = data.get("partySize", 1)
        party_accessibility = data.get("partyAccessibility", "CLOSED")
        max_party_size = data.get("maxPartySize", 5)
        
        if party_size_val > 1:
            party_state = Localizer.get_localized_text("presences","party_states","in_party")   
        elif party_accessibility == "OPEN":
            party_state = Localizer.get_localized_text("presences","party_states","open")

        party_size = [party_size_val, max_party_size] if party_size_val > 1 or party_accessibility == "OPEN" else None
        if party_size is not None:
            if party_size[0] == 0: 
                party_size[0] = 1
            if party_size[1] < 1:
                party_size[1] = 1
        return party_state, party_size 

    @staticmethod 
    def iso8601_to_epoch(time):
        if time == "0001.01.01-00.00.00":
            return None
        try:
            split = time.split("-")
            split[0] = split[0].replace(".","-")
            split[1] = split[1].replace(".",":")
            split = "T".join(i for i in split)
            split = iso8601.parse_date(split).timestamp() #converts iso8601 to epoch
            return split
        except Exception:
            debug(f"invalid iso8601 timestamp: {time}")
            return None

    @staticmethod 
    def fetch_rank_data(client,content_data):
        content_data = content_data or {}
        try:
            season_uuid = content_data.get("season", {}).get("season_uuid")
            mmr = client.fetch_mmr().get("QueueSkills", {}).get("competitive", {}).get("SeasonalInfoBySeasonID", {}).get(season_uuid)
            if not mmr:
                return None,"Rank not found"
        except Exception:
            Logger.exception("Unable to fetch rank data")
            return None,"Rank not found"
        rank_data = {}
        for tier in content_data.get("comp_tiers", []):
            if tier.get("id") == mmr.get("CompetitiveTier"):
                rank_data = tier
        if not rank_data:
            return None,"Rank not found"
        rank_image = Utilities.resolve_rpc_image(rank_data.get("display_icon"))
        rank_text = f"{rank_data.get('display_name_localized', 'Rank')} - {mmr.get('RankedRating', 0)}{Localizer.get_localized_text('presences','leveling','ranked_rating')}" + (f" // #{mmr.get('LeaderboardRank')}" if mmr.get('LeaderboardRank', 0) != 0 else "") 

        return rank_image, rank_text
        
    @staticmethod 
    def fetch_map_data(coregame_data,content_data):
        content_data = content_data or {}
        map_id = coregame_data.get("MapID", "") if coregame_data else ""
        for gmap in content_data.get("maps", []):
            if gmap.get("path") == map_id:
                map_image = Utilities.resolve_rpc_image(gmap.get("display_icon"))
                return map_image, gmap.get("display_name", ""), gmap.get("display_name_localized", "")
        return None, "", ""
 
    @staticmethod 
    def fetch_agent_data(uuid,content_data):
        content_data = content_data or {}
        for agent in content_data.get("agents", []):
            if agent.get("uuid") == uuid:
                agent_image = Utilities.resolve_rpc_image(agent.get("display_icon"))
                agent_name = agent.get('display_name_localized', '?')
                return agent_image, agent_name
        return None,"?"

    @staticmethod
    def fetch_mode_data(data, content_data):
        queue_id = data.get('queueId', '') if data else ''
        content_data = content_data or {}
        image = Utilities.resolve_rpc_image(content_data.get("queue_icon_aliases", {}).get(queue_id))
        mode_name = content_data.get('queue_aliases', {}).get(queue_id, "Custom") if queue_id in content_data.get("queue_aliases", {}).keys() else "Custom"
        mode_name = Utilities.localize_content_name(mode_name, "presences", "modes", queue_id)
        return image,mode_name

    @staticmethod 
    def get_content_preferences(client,pref,presence,player_data,coregame_data,content_data):
        if pref == "rank":
            return Utilities.fetch_rank_data(client,content_data)
        if pref == "map": 
            gmap = Utilities.fetch_map_data(coregame_data,content_data)
            return gmap[0], gmap[2] or gmap[1] or "?"
        if pref == "agent": 
            return Utilities.fetch_agent_data(player_data.get("CharacterID", ""),content_data)
        return None, "?"

    @staticmethod
    def localize_content_name(default,*keys):
        localized = Localizer.get_localized_text(*keys)
        if localized is not None:
            return localized 
        return default

    @staticmethod 
    def get_join_state(client,config,presence=None):
        if not client or not config or not presence:
            return None

        menu_config = config.get("presences", {}).get("menu", {})
        show_join = menu_config.get("show_join_button_with_open_party")
        allow_requests = menu_config.get("allow_join_requests")
        if not show_join and not allow_requests:
            return None

        party_data = presence.get("partyPresenceData", {}) if isinstance(presence, dict) else {}
        party_id = party_data.get("partyId") or presence.get("partyId", "")
        party_accessibility = party_data.get("partyAccessibility") or presence.get("partyAccessibility", "CLOSED")
        party_accessibility = str(party_accessibility).upper()
        region = getattr(client, "region", None)
        friend_id = getattr(client, "puuid", None)

        if not party_id or not region:
            return None

        buttons = []
        if show_join and party_accessibility == "OPEN":
            url = server.build_confirm_url("join", party_id, region, config)
            if url:
                label = Localizer.get_localized_text("presences", "buttons", "join_party") or "Join Party"
                buttons.append({"label": label, "url": url})

        if allow_requests and party_accessibility != "OPEN" and friend_id:
            url = server.build_confirm_url("request", party_id, region, config, friend_id=friend_id)
            if url:
                label = Localizer.get_localized_text("presences", "buttons", "request_join") or "Request Join"
                buttons.append({"label": label, "url": url})

        return buttons or None
