from ..presence_utilities import Utilities
from ...localization.localization import Localizer
from ...utilities.logging import Logger
from valclient.exceptions import PhaseError
import time

def presence(rpc,client=None,data=None,content_data=None,config=None):
    if data is None:
        return

    party_state,party_size = Utilities.build_party_state(data)
    
    try:
        pregame = client.pregame_fetch_player()
        match_id = pregame.get("MatchID")
        if not match_id:
            return
        pregame_data = client.pregame_fetch_match(match_id)
        puuid = client.puuid

        pregame_player_data = {}
        for player in pregame_data.get("AllyTeam", {}).get("Players", []):
            if player.get("Subject") == puuid:
                pregame_player_data = player

        pregame_end_time = (pregame_data.get('PhaseTimeRemainingNS', 0) // 1000000000) + time.time()

        agent_image, agent_name = Utilities.fetch_agent_data(pregame_player_data.get("CharacterID", ""),content_data)
        select_state = Localizer.get_localized_text("presences","pregame","locked") if pregame_player_data.get("CharacterSelectionState") == "locked" else Localizer.get_localized_text("presences","pregame","selecting")
        small_image, mode_name = Utilities.fetch_mode_data(data,content_data)

        rpc.update(
            state=party_state,
            details=f"{Localizer.get_localized_text('presences','client_states','pregame')} - {mode_name}",
            end=pregame_end_time,
            large_image=agent_image,
            large_text=f"{select_state} - {agent_name}",
            small_image=small_image,
            small_text=mode_name,
            party_size=party_size,
            party_id=data.get("partyId", ""),
        )
    except PhaseError as e:
        Logger.debug(f"Pregame phase unavailable: {e}")
    except Exception:
        Logger.exception("Unable to update pregame presence")
