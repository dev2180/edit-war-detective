"""'It feels smaller' is not engineering; a number is. Token/cost math."""
import tiktoken

_enc = tiktoken.get_encoding("cl100k_base")

# Below this, the yearly token bill doesn't justify the engineering time
# (see hackathon rules: "optimization must clear a volume bar").
VOLUME_BAR_QUERIES_PER_DAY = 1


def count_tokens(text):
    if not text:
        return 0
    return len(_enc.encode(text))


def compression_factor(before_tokens, after_tokens):
    return before_tokens / after_tokens


def _cost_block(tokens, price_per_million_tokens, queries_per_day):
    daily = tokens * price_per_million_tokens / 1_000_000 * queries_per_day
    return {
        "daily_cost": daily,
        "monthly_cost": daily * 30,
        "yearly_cost": daily * 365,
    }


def project_cost(before_tokens, after_tokens, price_per_million_tokens, queries_per_day):
    before = _cost_block(before_tokens, price_per_million_tokens, queries_per_day)
    after = _cost_block(after_tokens, price_per_million_tokens, queries_per_day)
    savings = {k: before[k] - after[k] for k in before}
    return {
        "before": before,
        "after": after,
        "savings": savings,
        "compression_x": compression_factor(before_tokens, after_tokens),
        "clears_volume_bar": queries_per_day >= VOLUME_BAR_QUERIES_PER_DAY,
    }
