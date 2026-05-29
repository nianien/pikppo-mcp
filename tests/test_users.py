from app.tools.users import get_user_profile, update_user_profile


async def test_default_profile_present_after_init():
    profile = await get_user_profile()
    assert profile["preferred_language"] == "zh"
    assert profile["service_type"] == "ollama"
    assert profile["service_host"] == "http://localhost:11434"


async def test_update_persists_across_reads():
    await update_user_profile(user_name="Sky", preferred_language="en", current_model="llama3")
    profile = await get_user_profile()
    assert profile["user_name"] == "Sky"
    assert profile["preferred_language"] == "en"
    assert profile["current_model"] == "llama3"


async def test_update_with_no_fields_is_noop():
    before = await get_user_profile()
    after = await update_user_profile()
    assert before == after
