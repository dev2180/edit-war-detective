"""'It feels smaller' is not engineering; a number is. Pure token/cost math."""
from wikitools.ledger import count_tokens, compression_factor, project_cost


def test_count_tokens_on_known_string():
    # "hello world" is 2 tokens under cl100k_base
    assert count_tokens("hello world") == 2


def test_count_tokens_empty_string_is_zero():
    assert count_tokens("") == 0


def test_compression_factor_basic_ratio():
    assert compression_factor(before_tokens=2_000_000, after_tokens=2_000) == 1000.0


def test_compression_factor_handles_non_round_numbers():
    result = compression_factor(before_tokens=30_838_220, after_tokens=1_800)
    assert round(result, 1) == round(30_838_220 / 1_800, 1)


def test_project_cost_daily_monthly_yearly_for_before_and_after():
    result = project_cost(
        before_tokens=2_000_000,
        after_tokens=2_000,
        price_per_million_tokens=0.50,
        queries_per_day=10,
    )
    assert result["before"]["daily_cost"] == 2_000_000 * 0.50 / 1_000_000 * 10
    assert result["after"]["daily_cost"] == 2_000 * 0.50 / 1_000_000 * 10
    assert result["before"]["monthly_cost"] == result["before"]["daily_cost"] * 30
    assert result["before"]["yearly_cost"] == result["before"]["daily_cost"] * 365
    assert result["savings"]["yearly_cost"] == (
        result["before"]["yearly_cost"] - result["after"]["yearly_cost"]
    )


def test_project_cost_clears_volume_bar_flag():
    result = project_cost(before_tokens=2_000_000, after_tokens=2_000,
                          price_per_million_tokens=0.50, queries_per_day=10)
    assert result["clears_volume_bar"] is True

    result_low_volume = project_cost(before_tokens=2_000_000, after_tokens=2_000,
                                     price_per_million_tokens=0.50, queries_per_day=0.1)
    assert result_low_volume["clears_volume_bar"] is False
