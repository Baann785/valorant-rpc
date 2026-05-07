from ...localization.localization import Localizer

def presence(rpc,client=None,data=None,content_data=None,config=None):
    repository = Localizer.get_config_value_or("", "startup", "update_repository")
    buttons = None
    if repository and Localizer.get_config_value_or(False, "startup", "show_github_link"):
        buttons = [{
            'label':Localizer.get_localized_text("presences","startup","view_github"),
            'url':f"https://github.com/{repository}"
        }]

    rpc.update(
        state=Localizer.get_localized_text("presences","startup","loading"),
        large_image=None,
        large_text="VALORANT-rpc",
        buttons=buttons
    )
