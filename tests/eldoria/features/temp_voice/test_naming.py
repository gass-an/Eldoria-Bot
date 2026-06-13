from eldoria.features.temp_voice.naming import build_temp_voice_channel_name
def test_build_temp_voice_channel_name_strips_leading_decorations():
    assert build_temp_voice_channel_name("➕ - Duo", "member.display_name") == "Duo de member.display_name"
def test_build_temp_voice_channel_name_keeps_plain_parent_name():
    assert build_temp_voice_channel_name("Team", "member.display_name") == "Team de member.display_name"
def test_build_temp_voice_channel_name_collapses_whitespace_and_uses_fallbacks():
    assert build_temp_voice_channel_name("   ➕   Chill   ", "   ") == "Chill de membre"
